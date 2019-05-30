#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
import re
import tempfile
from typing import List, Optional, Union
from uuid import uuid4

from markdown2 import markdown
import pandas as pd
import t4

from .documentation import README, ReplacedPath
from .validation import validate

###############################################################################

log = logging.getLogger(__name__)


###############################################################################


class Dataset(object):
    def __init__(
        self,
        dataset: Union[str, Path, pd.DataFrame],
        name: str,
        package_owner: str,
        readme_path: Union[str, Path]
    ):
        """
        Initialize a dataset object.

        :param dataset: Filepath or preloaded pandas dataframe.
        :param name: A name for the dataset. May only contain alphabetic and underscore characters.
        :param package_owner: The name of the dataset owner. To be attached to the dataset name.
        :param readme_path: A path to a markdown README file.
        """
        # Read the dataset
        if isinstance(dataset, (str, Path)):
            dataset = Path(dataset).expanduser().resolve(strict=True)
            if dataset.is_dir():
                raise IsADirectoryError(dataset)

            # Read
            dataset = pd.read_csv(dataset)

        # Check readme
        readme_path = Path(readme_path).expanduser().resolve(strict=True)
        if readme_path.is_dir():
            raise IsADirectoryError(readme_path)

        # Confirm name matches allowed pattern
        name = self.return_or_raise_approved_name(name)

        # Store basic
        self._data = dataset
        self.name = name
        self.package_owner = package_owner
        self.readme_path = readme_path

        # Lazy loaded
        self._readme = None
        self._index_columns = []
        self._path_columns = []

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def generate_readme(self):
        self._readme = README(self.readme_path)
        return self._readme

    @property
    def readme(self):
        if self._readme:
            return self._readme

        return self.generate_readme()

    def add_usage_doc(self, doc_or_link: Union[str, Path]):
        self.readme.append_readme_standards(usage_doc_or_link=doc_or_link)

    def add_license(self, doc_or_link: Union[str, Path]):
        self.readme.append_readme_standards(license_doc_or_link=doc_or_link)

    def index_on_columns(self, columns: List[str]):
        # Check columns
        if not any(col in self.data.columns for col in columns):
            raise ValueError(f"One or more columns provided were not found in the dataset. Received: {columns}")

        self._index_columns = columns

    def set_path_columns(self, columns: List[str]):
        # Check columns
        if not any(col in self.data.columns for col in columns):
            raise ValueError(f"One or more columns provided were not found in the dataset. Received: {columns}")

        self._path_columns = columns

    @staticmethod
    def return_or_raise_approved_name(name: str):
        name = name.lower().replace(" ", "_").replace("-", "_")
        if not re.match(r"^[a-z0-9_\-]*$", name):
            raise ValueError(
                f"Dataset names may only include lowercase alphanumeric, underscore, and hyphen characters. "
                f"Received: {name}"
            )

        return name

    def distribute(
        self,
        push_uri: Optional[str] = None,
        message: Optional[str] = None
    ) -> t4.Package:
        # Confirm name matches approved pattern
        # We previously checked during init, but the name could have been changed
        name = self.return_or_raise_approved_name(self.name)

        # Create empty package
        pkg = t4.Package()

        # Write any extra files to tempdir to send to the build
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set all referenced files
            updated_references = []
            text = self.readme.text
            for f in self.readme.referenced_files:
                replaced = ReplacedPath(f, f"reference_files/{f.name}")
                updated_references.append(replaced)
                text = text.replace(str(replaced.prior), replaced.updated)
                pkg.set(replaced.updated, str(replaced.prior.expanduser().resolve()))

            # Write the updated readme to temp
            readme_pk = Path(tmpdir, "README.md")
            with open(readme_pk, "w") as readme_write:
                readme_write.write(text)

            # Set the readme
            pkg.set("README.md", readme_pk)

            # Validate the dataset
            v_ds = validate(self.data)

            # Set package contents
            if len(self._path_columns) > 0:
                fp_cols = self._path_columns
            else:
                fp_cols = v_ds.schema.df.index[v_ds.schema.df["dtype"] == "pathlib.Path"].tolist()
            for col in fp_cols:
                # Update values to the logical key as they are set
                for i, val in enumerate(v_ds.data[col].values):
                    pk = Path(val).expanduser().resolve()
                    if pk.is_file():
                        key = str(uuid4()).replace("-", "")
                        unique_name = f"{key}_{val.name}"
                        lk = f"{col}/{unique_name}"
                        v_ds.data[col].values[i] = lk

                        # Attach metadata to object
                        meta = {index_col: str(v_ds.data[index_col].values[i]) for index_col in self._index_columns}
                        pkg.set(lk, pk, meta)
                    else:
                        lk = f"{col}/{val.name}"
                        v_ds.data[col].values[i] = lk
                        pkg.set_dir(lk, pk)

            # Store validated dataset in the temp dir with paths replaced
            meta_path = Path(tmpdir, "metadata.csv")
            v_ds.data.to_csv(meta_path, index=False)
            pkg.set("metadata.csv", meta_path)

            # Optionally push
            if push_uri:
                pkg = pkg.push(f"{self.package_owner}/{name}", dest=push_uri, message=message)

        return pkg

    def __str__(self):
        return f"<Dataset [package: {self.package_owner}/{self.name}, shape: {self.data.shape}]>"

    def __repr__(self):
        return str(self)

    def _repr_html_(self):
        # Swap the markdown table for an html render of the schema table
        return markdown(self.readme.text)
