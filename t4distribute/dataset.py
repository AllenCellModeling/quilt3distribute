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

        # Init readme
        readme = README(readme_path)

        # Confirm name matches allowed pattern
        name = self.return_or_raise_approved_name(name)

        # Store basic
        self._data = dataset
        self.name = name
        self.package_owner = package_owner
        self._readme = readme
        self.readme_path = readme.fp

        # Lazy loaded
        self._index_columns = []
        self._path_columns = []

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def readme(self) -> README:
        return self._readme

    def add_usage_doc(self, doc_or_link: Union[str, Path]):
        """
        Add a document's content or add a link to a publically accessibly resource for documentation and usage examples.

        :param doc_or_link: A filepath or string uri to a resource detailing usage of this dataset.

        Wrapper around t4distribute.documentation.README.append_readme_standards.
        """
        self.readme.append_readme_standards(usage_doc_or_link=doc_or_link)

    def add_license(self, doc_or_link: Union[str, Path]):
        """
        Add a document's content or add a link to a publically accessibly resource for license details.

        :param doc_or_link: A filepath or string uri to a resource for license details.

        Wrapper around t4distribute.documentation.README.append_readme_standards.
        """
        self.readme.append_readme_standards(license_doc_or_link=doc_or_link)

    def index_on_columns(self, columns: List[str]):
        """
        Use the manifest contents to attach metadata to the files found in the dataset.

        :param columns: A list of columns to use for metadata attachment.

        Example row: `{"CellId": 1, "Structure": "lysosome", "2dReadPath": "/allen...", "3dReadPath": "/allen..."}`
        Attach structure metadata: `dataset.index_on_columns(["Structure"])`
        Results in the files found at the 2dReadPath and the 3dReadPath both having `{"Structure": "lysosome"}` attached
        """
        # Check columns
        if not any(col in self.data.columns for col in columns):
            raise ValueError(f"One or more columns provided were not found in the dataset. Received: {columns}")

        self._index_columns = columns

    def set_path_columns(self, columns: List[str]):
        """
        Explicit override for which columns will be used for file distribution.

        :param columns: A list of columns to use for file distribution.
        """
        # Check columns
        if not any(col in self.data.columns for col in columns):
            raise ValueError(f"One or more columns provided were not found in the dataset. Received: {columns}")

        self._path_columns = columns

    @staticmethod
    def return_or_raise_approved_name(name: str) -> str:
        """
        Attempt to clean a string to match the pattern expected by Quilt 3/ T4.
        If after the cleaning operation, it still doesn't match the approved pattern, will raise a ValueError.

        :param name: String name to clean.
        :return: Cleaned name.
        """
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
        """
        Push a package to a specific S3 bucket. If no bucket is provided, the un-built, un-pushed package is returned.
        You can push a dataset with the same name multiple times to the same bucket multiple times as instead of
        overriding a prior dataset, Quilt simply creates a new dataset version. Please refer to Quilt documentation for
        more details: https://docs.quiltdata.com

        :param push_uri: The S3 bucket uri to push to. Example: "s3://quilt-jacksonb"
        :param message: An optional message to attach to that version of the dataset.
        :return: The built and optionally pushed t4.Package.
        """
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
