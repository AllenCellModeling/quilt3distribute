#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from unittest import mock

import pandas as pd
from pathlib import Path

from t4distribute import Dataset


@pytest.fixture
def example_csv(data_dir):
    return data_dir / "example.csv"


@pytest.fixture
def example_frame(example_csv):
    return pd.read_csv(example_csv)


@pytest.fixture
def example_readme(data_dir):
    return data_dir / "README.md"


def test_dataset_init_csv(example_csv, example_readme):
    Dataset(example_csv, "test_dataset", "me", example_readme)


@pytest.mark.parametrize("dataset", [
    pytest.param("/this/does/not/exist.csv", marks=pytest.mark.raises(exception=FileNotFoundError)),
    pytest.param(Path("/this/does/not/exist.csv"), marks=pytest.mark.raises(exception=FileNotFoundError))
])
def test_dataset_init_fail_csv_does_not_exist(example_readme, dataset):
    Dataset(dataset, "test_dataset", "me", example_readme)


def test_dataset_init_fail_csv_is_dir(data_dir, example_readme):
    with pytest.raises(IsADirectoryError):
        Dataset(data_dir, "test_dataset", "me", example_readme)


def test_dataset_init_frame(example_frame, example_readme):
    Dataset(example_frame, "test_dataset", "me", example_readme)


@pytest.mark.parametrize("dataset", [
    (pd.DataFrame([{"hello": "world"}, {"hello": "jackson"}])),
    pytest.param(1, marks=pytest.mark.raises(exception=TypeError)),
    pytest.param(("wrong", "type"), marks=pytest.mark.raises(exception=TypeError))
])
def test_dataset_init_types(example_readme, dataset):
    Dataset(dataset, "test_dataset", "me", example_readme)


@pytest.mark.parametrize("readme_path", [
    pytest.param("/this/does/not/exist.md", marks=pytest.mark.raises(exception=FileNotFoundError)),
    pytest.param(Path("/this/does/not/exist.md"), marks=pytest.mark.raises(exception=FileNotFoundError))
])
def test_dataset_init_fail_readme_does_not_exist(example_frame, readme_path):
    Dataset(example_frame, "test_dataset", "me", readme_path)


def test_dataset_init_fail_readme_is_dir(example_frame, data_dir):
    with pytest.raises(IsADirectoryError):
        Dataset(example_frame, "test_dataset", "me", data_dir)


@pytest.mark.parametrize("name", [
    ("test_dataset"),
    ("test-dataset"),
    ("test dataset"),
    ("Test Dataset"),
    ("TEsT-DaTAseT"),
    ("test_dataset_1234"),
    pytest.param("////This///Will///Fail////", marks=pytest.mark.raises(exception=ValueError)),
    pytest.param("@@@~!(@*!_~*~ADSH*@Hashd87g)", marks=pytest.mark.raises(exception=ValueError))
])
def test_dataset_return_or_raise_approved_name(example_frame, example_readme, name):
    Dataset(example_frame, name, "me", example_readme)


@pytest.fixture
def no_additions_dataset(example_frame, example_readme):
    return Dataset(example_frame, "test_dataset", "me", example_readme)


def test_dataset_props(no_additions_dataset):
    assert no_additions_dataset.data is not None
    newly_generated_readme = no_additions_dataset.readme
    assert no_additions_dataset.readme == newly_generated_readme


@pytest.mark.parametrize("usage_doc_or_link", [
    ("https://docs.quiltdata.com"),
    ("https://docs.quiltdata.com/walkthrough/installing-a-package"),
    ("https://docs.quiltdata.com/walkthrough/reading-from-a-package")
])
def test_dataset_readme_usage_attachment(no_additions_dataset, usage_doc_or_link):
    no_additions_dataset.add_usage_doc(usage_doc_or_link)


@pytest.mark.parametrize("license_doc_or_link", [
    ("https://opensource.org/licenses/MIT"),
    ("https://opensource.org/licenses/BSD-2-Clause"),
    ("https://opensource.org/licenses/MPL-2.0")
])
def test_dataset_readme_license_attachment(no_additions_dataset, license_doc_or_link):
    no_additions_dataset.add_license(license_doc_or_link)


@pytest.mark.parametrize("columns", [
    (["Structure"]),
    (["CellId", "Structure"]),
    pytest.param(["DoesNotExist"], marks=pytest.mark.raises(exception=ValueError)),
    pytest.param(["DoesNotExist1", "DoesNotExist2"], marks=pytest.mark.raises(exception=ValueError))
])
def test_dataset_index_on_columns(no_additions_dataset, columns):
    no_additions_dataset.index_on_columns(columns)


@pytest.mark.parametrize("columns", [
    (["3dReadPath"]),
    (["3dReadPath", "2dReadPath"]),
    pytest.param(["DoesNotExistPath"], marks=pytest.mark.raises(exception=ValueError)),
    pytest.param(["DoesNotExistPath1", "DoesNotExistPath2"], marks=pytest.mark.raises(exception=ValueError))
])
def test_dataset_set_path_columns(no_additions_dataset, columns):
    no_additions_dataset.set_path_columns(columns)


@pytest.mark.parametrize("columns", [
    ({"3dReadPath": "3dImages"}),
    ({"3dReadPath": "3dImages", "2dReadPath": "2dImages"}),
    pytest.param({"DNE": "DNELabeled"}, marks=pytest.mark.raises(exception=ValueError)),
    pytest.param({"DNE1": "DNELabeled1", "DNE2": "DNELabeled2"}, marks=pytest.mark.raises(exception=ValueError))
])
def test_dataset_set_column_names_map(no_additions_dataset, columns):
    no_additions_dataset.set_column_names_map(columns)


def test_dataset_set_extra_files_exists(no_additions_dataset, example_readme):
    no_additions_dataset.set_extra_files([example_readme])
    no_additions_dataset.set_extra_files({"extra": [example_readme]})


@pytest.mark.parametrize("files", [
    pytest.param(["/this/does/not/exist.png"], marks=pytest.mark.raises(exception=FileNotFoundError)),
    pytest.param({"extras": ["/this/does/not/exist.png"]}, marks=pytest.mark.raises(exception=FileNotFoundError))
])
def test_dataset_set_extra_files_fails(no_additions_dataset, files):
    no_additions_dataset.set_extra_files(files)


@pytest.fixture
def extra_additions_dataset(example_frame, example_readme):
    ds = Dataset(example_frame, "test_dataset", "me", example_readme)
    ds.set_path_columns(["2dReadPath"])
    ds.set_extra_files([example_readme])
    ds.set_column_names_map({"2dReadPath": "MappedPath"})
    return ds


@pytest.mark.parametrize("push_uri", [
    (None),
    ("s3://fake-uri")
])
def test_dataset_distribute(no_additions_dataset, extra_additions_dataset, push_uri):
    with mock.patch("t4.Package.push") as mocked_package_push:
        mocked_package_push.return_value = "NiceTryGuy"
        no_additions_dataset.distribute(push_uri, "some message")
        extra_additions_dataset.distribute(push_uri, "some message")
