#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from quilt3distribute import file_utils


@pytest.fixture
def example_csv(data_dir):
    return data_dir / "example.csv"


def test_create_unique_logical_key(example_csv):
    assert file_utils.create_unique_logical_key(example_csv) == "9023f477_example.csv"
    assert file_utils.create_unique_logical_key(str(example_csv)) == "9023f477_example.csv"
