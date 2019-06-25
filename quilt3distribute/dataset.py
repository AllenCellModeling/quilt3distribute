#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
import quilt3
from markdown2 import markdown
from tqdm import tqdm

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

        # Check type
        if not isinstance(dataset, pd.DataFrame):
            raise TypeError("Dataset's may only be initialized with a path to csv or a pandas dataframe.")

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
        self.index_columns = []
        self.path_columns = []
        self.column_names_map = {}
        self.extra_files = {}

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

        Wrapper around quilt3distribute.documentation.README.append_readme_standards.
        """
        self.readme.append_readme_standards(usage_doc_or_link=doc_or_link)

    def add_license(self, doc_or_link: Union[str, Path]):
        """
        Add a document's content or add a link to a publically accessibly resource for license details.

        :param doc_or_link: A filepath or string uri to a resource for license details.

        Wrapper around quilt3distribute.documentation.README.append_readme_standards.
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

        self.index_columns = columns

    def set_path_columns(self, columns: List[str]):
        """
        Explicit override for which columns will be used for file distribution.

        :param columns: A list of columns to use for file distribution.
        """
        # Check columns
        if not any(col in self.data.columns for col in columns):
            raise ValueError(f"One or more columns provided were not found in the dataset. Received: {columns}")

        self.path_columns = columns

    def set_column_names_map(self, columns: Dict[str, str]):
        """
        Explicit override for the labeling of column names on file distribution.
        Example, a column ("2dReadPath") is detected to have files, in the package that file will be placed in a
        directory called "2dReadPath". Using this function, those directory names can be explicitly overridden.

        :param columns: A mapping of current column name contain files to desired labeled directory name.
        """
        # Check columns
        if not any(col in self.data.columns for col in columns):
            raise ValueError(f"One or more columns provided were not found in the dataset. Received: {columns}")

        self.column_names_map = columns

    @staticmethod
    def return_or_raise_approved_name(name: str) -> str:
        """
        Attempt to clean a string to match the pattern expected by Quilt 3.
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

    def set_extra_files(self, files: Union[List[Union[str, Path]], Dict[str, List[Union[str, Path]]]]):
        """
        Datasets commonly have extra or supporting files. Any file passed to this function will be added to the
        requested directory.

        :param files: When provided a list of string or Path objects all paths provided in the list will be sent to the
            same logical key "supporting_files". When provided a dictionary mapping strings to list of string or Path
            objects, the paths will be placed in logical keys labeled by their dictionary entry.
        """
        # Convert to dictionary
        if isinstance(files, list):
            files = {"supporting_files": files}

        # Check all paths provided
        converted = {}
        for lk_parent, files_list in files.items():
            converted[lk_parent] = []
            for f in files_list:
                converted[lk_parent].append(Path(f).expanduser().resolve(strict=True))

        # Set the paths
        self.extra_files = converted

    def distribute(
        self,
        push_uri: Optional[str] = None,
        message: Optional[str] = None,
        attach_associates: bool = True,
    ) -> quilt3.Package:
        """
        Push a package to a specific S3 bucket. If no bucket is provided, the un-built, un-pushed package is returned.
        You can push a dataset with the same name multiple times to the same bucket multiple times as instead of
        overriding a prior dataset, Quilt simply creates a new dataset version. Please refer to Quilt documentation for
        more details: https://docs.quiltdata.com

        :param push_uri: The S3 bucket uri to push to. Example: "s3://quilt-jacksonb"
        :param message: An optional message to attach to that version of the dataset.
        :param attach_associates: Boolean option to attach associates as metadata to each file. Associates are used
            to retain quick navigation between related files.
        :return: The built and optionally pushed quilt3.Package.
        """
        # Confirm name matches approved pattern
        # We previously checked during init, but the name could have been changed
        name = self.return_or_raise_approved_name(self.name)

        # Create empty package
        pkg = quilt3.Package()

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
            if len(self.path_columns) > 0:
                fp_cols = self.path_columns
            else:
                fp_cols = v_ds.schema.df.index[v_ds.schema.df["dtype"].str.contains("Path")].tolist()

            # Create associate mappings: List[Dict[str, str]]
            # This list is in index order. Meaning that as the column values are descended we can simply add a
            # new associate to the already existing associate map at that list index.
            associates = []

            # Set all files
            with tqdm(total=len(fp_cols) * len(v_ds.data), desc="Constructing package") as pbar:
                for col in fp_cols:
                    # Check display name for col
                    if col in self.column_names_map:
                        col_label = self.column_names_map[col]
                    else:
                        col_label = col

                    # Update values to the logical key as they are set
                    for i, val in enumerate(v_ds.data[col].values):
                        pk = Path(val).expanduser().resolve()
                        if pk.is_file():
                            key = str(uuid4()).replace("-", "")
                            unique_name = f"{key}_{val.name}"
                            lk = f"{col_label}/{unique_name}"
                            v_ds.data[col].values[i] = lk

                            # Attach metadata to object
                            meta = {index_col: str(v_ds.data[index_col].values[i]) for index_col in self.index_columns}
                            pkg.set(lk, pk, meta)

                            # Update associates
                            try:
                                associates[i][col_label] = lk
                            except IndexError:
                                associates.append({col_label: lk})
                        else:
                            lk = f"{col_label}/{val.name}"
                            v_ds.data[col].values[i] = lk
                            pkg.set_dir(lk, pk)

                        # Update progress bar
                        pbar.update()

            # Attach associates if desired
            if attach_associates:
                for i, associate_mapping in tqdm(enumerate(associates), desc="Creating associate metadata blocks"):
                    for col, lk in associate_mapping.items():
                        # Having dictionary expansion in this order means that associates will override a prior
                        # existing `associates` key, this is assumed safe because attach_associates was set to True.
                        pkg[lk].set_meta({**pkg[lk].meta, **{"associates": associate_mapping}})

            # Store validated dataset in the temp dir with paths replaced
            meta_path = Path(tmpdir, "metadata.csv")
            v_ds.data.to_csv(meta_path, index=False)
            pkg.set("metadata.csv", meta_path)

            # Set logical keys for all extra files
            for lk_parent, files_list in self.extra_files.items():
                for f in files_list:
                    pkg.set(f"{lk_parent}/{f.name}", f)

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
