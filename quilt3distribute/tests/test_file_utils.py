#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

import pytest

from quilt3distribute import file_utils


@pytest.fixture
def example_csv(data_dir):
    return data_dir / "example.csv"


def test_create_unique_logical_key(example_csv):
    # Create examples of what should be the same logical key but one with pathlib.Path and the other a string
    path_created_logical_key = file_utils.create_unique_logical_key(example_csv)
    str_created_logical_key = file_utils.create_unique_logical_key(str(example_csv))

    # Should be a hex string followed by the filename
    regexp = re.compile("[a-z0-9]_example.csv")

    # Assert that both generated logical keys match the pattern
    # We can't just use a predetermined hash here because depending on the testing machine, the fully resolved
    # filepath may be different
    assert regexp.match(path_created_logical_key)
    assert regexp.match(str_created_logical_key)

    # Assert that the two logical keys are the same
    assert path_created_logical_key == str_created_logical_key
