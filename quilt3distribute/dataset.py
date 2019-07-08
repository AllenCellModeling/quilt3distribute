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

from . import file_utils
from .documentation import README
from .validation import validate

###############################################################################

log = logging.getLogger(__name__)


# This could actually include dictionaries, lists, and tuples but for the sake of simplicity we only allow these types.
# Details here: https://docs.python.org/3/library/json.html#json.JSONEncoder
JSONSerializableTypes = (str, int, float, bool, type(None))


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
            raise TypeError(
                f"Dataset's may only be initialized with a path to csv or a pandas dataframe. Received: {type(dataset)}"
            )

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
        self.metadata_columns = []
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

    def set_metadata_columns(self, columns: List[str]):
        """
        Use the manifest contents to attach metadata to the files found in the dataset.

        :param columns: A list of columns to use for metadata attachment.

        Example row: `{"CellId": 1, "Structure": "lysosome", "2dReadPath": "/allen...", "3dReadPath": "/allen..."}`
        Attach structure metadata: `dataset.set_metadata_columns(["Structure"])`
        Results in the files found at the 2dReadPath and the 3dReadPath both having `{"Structure": "lysosome"}` attached

        In short: the values in each column provided will be used for metadata attachment for every file found.
        """
        # Check columns
        if not any(col in self.data.columns for col in columns):
            raise ValueError(f"One or more columns provided were not found in the dataset. Received: {columns}")

        self.metadata_columns = columns

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

    @staticmethod
    def _recursive_clean(pkg: quilt3.Package, metadata_reduction_map: Dict[str, bool]):
        # For all keys in current package level
        for key in pkg:
            # If it is a PackageEntry object, we know we have hit a leaf node
            if isinstance(pkg[key], quilt3.packages.PackageEntry):
                # Reduce the metadata to a single value where it can
                cleaned_meta = {}
                for meta_k, meta_v in pkg[key].meta.items():
                    # If the metadata reduction map at the metadata column (or meta_k) can be reduced/ collapsed (True)
                    # Reduce/ collapse the metadata
                    # Reminder: this step will make the metadata access for every file of the same file type the same
                    # format. Example: all files under the key "FOV" will have the same metadata access after this
                    # function runs. All the metadata access for the same file type across the package, if one file has
                    # a list of values for the metadata key, "A", we want all files of the same type to all have list of
                    # values for the metadata key, "A".
                    # We also can't just use a set here for two reasons, the first is simply that sets are not JSON
                    # serializable. "But you can just cast to a set then back to a list!!!". The second reason is that
                    # because a file can have multiple list of values in it's metadata, if we cast to a set, one list
                    # may be reduced to two items while another, different metadata list of values may be reduced to
                    # a single item. Which leads to the problem of matching up metadata to metadata for the same file.
                    # The example to use here is looking at an FOV files metadata:
                    # {"CellID": [1, 2, 3], "CellIndex": [4, 8, 12]} By having them both as list without any chance of
                    # reduction means that it is easy to match metadata values to each other.
                    # "CellId" 1 maps to "CellIndex" 4, 2 maps to 8, and 3 maps to 12 in this case.
                    if metadata_reduction_map[meta_k]:
                        cleaned_meta[meta_k] = meta_v[0]
                    # Else, do not reduce
                    else:
                        cleaned_meta[meta_k] = meta_v

                # Update the object with the cleaned metadata
                pkg[key].set_meta(cleaned_meta)
            else:
                Dataset._recursive_clean(pkg[key], metadata_reduction_map)

        return pkg

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
            text = self.readme.text
            for rf in self.readme.referenced_files:
                replaced = f"referenced_files/{rf.resolved.name}"
                text = text.replace(rf.target, replaced)
                pkg.set(replaced, str(rf.resolved))

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

            # Create metadata reduction map
            # This will be used to clean up and standardize the metadata access after object construction
            # Metadata column name to boolean value for should or should not reduce metadata values
            # This will be used during the "clean up the package metadata step"
            # If we have multiple files each with the same keys for the metadata, but for one reason or another, one
            # packaged file's value for a certain key is a list while another's is a single string, this leads to a
            # confusing mixed return value API for the same _type_ of object. Example:
            # fov/
            #   obj1/
            #      {example_key: "hello"}
            #   obj2/
            #      {example_key: ["hello", "world"]}
            # Commonly this happens when a manifest has rows of unique instances of a child object but retains a
            # reference to a parent object, example: rows of information about unique cells that were all generated
            # using the same algorithm, whose information is stored in a column, for each cell information row.
            # This could result in some files (which only have one cell) being a single string while other files
            # (which have more than one cell) being a list of the same string over and over again.
            # "Why spend all this time to reduce/ collapse the metadata anyway?", besides making it so that users won't
            # have to call `obj2.meta["example_key"][0]` every time they want the value, and besides the fact that it
            # standardizes the metadata api, the biggest reason is that S3 objects can only have 2KB of metadata,
            # without this reduction/ collapse step, manifests are more likely to hit that limit and cause a package
            # distribution error.
            metadata_reduction_map = {index_col: True for index_col in self.metadata_columns}

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
                        # Fully resolve the path
                        physical_key = Path(val).expanduser().resolve()

                        # Just using val.name could result in files that shouldn't be grouped being grouped
                        # Example column:
                        # SourceReadpath
                        # a/0.tiff
                        # a/1.tiff
                        # b/0.tiff
                        # b/1.tiff
                        # Even though there are four files, this would result in both a/0.tiff and b/0.tiff, and,
                        # a/1.tiff and b/1.tiff being grouped together. To solve this we can prepend a the first couple
                        # of characters from a hash of the fully resolved path to the logical key.
                        unique_file_name = file_utils.create_unique_logical_key(physical_key)
                        logical_key = f"{col_label}/{unique_file_name}"
                        if physical_key.is_file():
                            v_ds.data[col].values[i] = logical_key

                            # Create metadata dictionary to attach to object
                            meta = {}
                            for meta_col in self.metadata_columns:
                                # Short reference to current metadata value
                                v = v_ds.data[meta_col].values[i]

                                # Enforce simple JSON serializable type
                                # First check if value is a numpy value
                                # It likely is because pandas relies on numpy
                                # All numpy types have the "dtype" attribute and can be cast to python type by using
                                # the `item` function, details here:
                                # https://docs.scipy.org/doc/numpy/reference/generated/numpy.ndarray.item.html
                                if hasattr(v, "dtype"):
                                    v = v.item()
                                if isinstance(v, JSONSerializableTypes):
                                    meta[meta_col] = [v]
                                else:
                                    raise TypeError(
                                        f"Non-simple-JSON-serializable type found in column: '{meta_col}', "
                                        f"at index: {i}: ({type(v)} '{v}').\n\n "
                                        f"At this time only the following types are allowing in metadata: "
                                        f"{JSONSerializableTypes}"
                                    )

                            # Check if object already exists
                            if logical_key in pkg:
                                # Join the two meta dictionaries
                                joined_meta = {}
                                for meta_col, curr_v in pkg[logical_key].meta.items():
                                    # Join the values for the current iteration of the metadata
                                    joined_values = [*curr_v, *meta[meta_col]]

                                    # Only check if the metadata at this index can be reduced if currently is still
                                    # being decided. We know if the metadata value at this index is still be decided if:
                                    # the boolean value in the metadata reduction map is True, as in, this index can be
                                    # reduced or collapsed.
                                    # The other reason to make this check is so that we don't override an earlier False
                                    # reduction value. In the case where early on we encounter an instance of the
                                    # metadata that should not be reduced but then later on we say it can be, this check
                                    # prevents that. As we want all metadata access across the dataset to be uniform.
                                    if metadata_reduction_map[meta_col]:
                                        # Update the metadata reduction map
                                        # For the current column being checked, as long as it is still being
                                        # determined that the column can be reduced (aka we have entered this if block)
                                        # check if we can still reduce the metadata after the recent addition.
                                        # "We can reduce the metadata if the count of the first value (or any value) is
                                        # the same as the length of the entire list of values"
                                        # This runs quickly for small lists as seen here:
                                        # https://stackoverflow.com/questions/3844801/check-if-all-elements-in-a-list-are-identical
                                        metadata_reduction_map[meta_col] = (
                                            joined_values.count(joined_values[0]) == len(joined_values)
                                        )

                                    # Attached the joined values to the joined metadata
                                    joined_meta[meta_col] = joined_values

                                # Update meta
                                pkg[logical_key].set_meta(joined_meta)

                            # Object didn't already exist, simply set it
                            else:
                                pkg.set(logical_key, physical_key, meta)

                            # Update associates
                            try:
                                associates[i][col_label] = logical_key
                            except IndexError:
                                associates.append({col_label: logical_key})
                        else:
                            v_ds.data[col].values[i] = logical_key
                            pkg.set_dir(logical_key, physical_key)

                        # Update progress bar
                        pbar.update()

            # Clean up package metadata
            pkg = self._recursive_clean(pkg, metadata_reduction_map)

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
