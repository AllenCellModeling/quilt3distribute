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
def dataset(example_frame, example_readme):
    return Dataset(example_frame, "test_dataset", "me", example_readme)


def test_dataset_props(dataset):
    assert dataset.data is not None
    newly_generated_readme = dataset.readme
    assert dataset.readme == newly_generated_readme


@pytest.mark.parametrize("usage_doc_or_link", [
    ("https://docs.quiltdata.com"),
    ("https://docs.quiltdata.com/walkthrough/installing-a-package"),
    ("https://docs.quiltdata.com/walkthrough/reading-from-a-package")
])
def test_dataset_readme_usage_attachment(dataset, usage_doc_or_link):
    dataset.add_usage_doc(usage_doc_or_link)


@pytest.mark.parametrize("license_doc_or_link", [
    ("https://opensource.org/licenses/MIT"),
    ("https://opensource.org/licenses/BSD-2-Clause"),
    ("https://opensource.org/licenses/MPL-2.0")
])
def test_dataset_readme_license_attachment(dataset, license_doc_or_link):
    dataset.add_license(license_doc_or_link)


@pytest.mark.parametrize("columns", [
    (["Structure"]),
    (["CellId", "Structure"]),
    pytest.param(["DoesNotExist"], marks=pytest.mark.raises(exception=ValueError)),
    pytest.param(["DoesNotExist1", "DoesNotExist2"], marks=pytest.mark.raises(exception=ValueError))
])
def test_dataset_index_on_columns(dataset, columns):
    dataset.index_on_columns(columns)


@pytest.mark.parametrize("columns", [
    (["3dReadPath"]),
    (["3dReadPath", "2dReadPath"]),
    pytest.param(["DoesNotExistPath"], marks=pytest.mark.raises(exception=ValueError)),
    pytest.param(["DoesNotExistPath1", "DoesNotExistPath2"], marks=pytest.mark.raises(exception=ValueError))
])
def test_dataset_set_path_columns(dataset, columns):
    dataset.set_path_columns(columns)


def test_dataset_distribute(dataset):
    with mock.patch("t4.Package.push") as mocked_package_push:
        mocked_package_push.return_value = "NiceTryGuy"
        dataset.distribute("s3://my-bucket", "some message")
