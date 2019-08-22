#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quilt3distribute import FeatureDefinition
from quilt3distribute.validation import Validator, validate


@pytest.mark.parametrize("dtype, validation_functions", [
    (str, []),
    (str, ()),
    (str, (lambda x: x == "hello world",)),
    (str, (lambda x: "hello" in x, lambda x: "world" in x)),
    (Path, ()),
    pytest.param(str, {lambda x: x == "non-iterable-type"}, marks=pytest.mark.raises(exception=TypeError)),
    pytest.param(str, ("this will fail because not callable",), marks=pytest.mark.raises(exception=TypeError))
])
def test_feature_def_init(dtype, validation_functions):
    fd = FeatureDefinition(dtype, validation_functions)

    # Specific check for path behavior
    if dtype == Path:
        assert fd.cast_values


@pytest.mark.parametrize("values, definition, drop_on_error, expected_drops", [
    (np.ones(5), FeatureDefinition(np.float64), False, set()),
    (np.ones(5), FeatureDefinition(np.float64), True, set()),
    (np.array(["hello", "world"]), FeatureDefinition(str), False, set()),
    (np.ones(5), FeatureDefinition(np.float64, (lambda x: x == 1,)), False, set()),
    pytest.param(np.ones(5), FeatureDefinition(Path), False, set(), marks=pytest.mark.raises(exception=ValueError)),
    (np.ones(5), FeatureDefinition(Path), True, set([0, 1, 2, 3, 4])),
    pytest.param(
        np.array(["hello", "world"]), FeatureDefinition(int, cast_values=True), False, set(),
        marks=pytest.mark.raises(exception=ValueError)
    ),
    (np.array(["hello", "world"]), FeatureDefinition(int, cast_values=True), True, set([0, 1])),
    pytest.param(
        np.array(["hello", "world"]), FeatureDefinition(int), False, set(),
        marks=pytest.mark.raises(exception=TypeError)
    ),
    (np.array(["hello", "world"]), FeatureDefinition(int), True, set([0, 1])),
    pytest.param(
        np.array(["1.png", "2.png"]), FeatureDefinition(Path), False, set(),
        marks=pytest.mark.raises(exception=FileNotFoundError)
    ),
    (np.array(["1.png", "2.png"]), FeatureDefinition(Path), True, set([0, 1])),
    pytest.param(
        np.array([Path("1.png"), Path("2.png")]), FeatureDefinition(Path), False, set(),
        marks=pytest.mark.raises(exception=FileNotFoundError)
    ),
    (np.array([Path("1.png"), Path("2.png")]), FeatureDefinition(Path), True, set([0, 1])),
    pytest.param(
        np.ones(5), FeatureDefinition(np.float64, (lambda x: x == 2,)), False, set(),
        marks=pytest.mark.raises(exception=ValueError)
    ),
    (np.ones(5), FeatureDefinition(np.float64, (lambda x: x == 2,)), True, set([0, 1, 2, 3, 4]))
])
def test_validator_process(values, definition, drop_on_error, expected_drops):
    v = Validator("test", values, definition, drop_on_error)

    results = v.process()

    if drop_on_error:
        assert expected_drops == {r.index for r in results.errored_results}
    else:
        assert len(results.errored_results) == 0


@pytest.mark.parametrize("data, drop_on_error, expected_len", [
    (pd.DataFrame([{"floats": 1.0}, {"floats": 2.0}]), False, 2),
    pytest.param(
        pd.DataFrame([{"test_path": "1.png"}, {"test_path": "2.png"}]), False, 2,
        marks=pytest.mark.raises(exception=FileNotFoundError)
    ),
    (pd.DataFrame([{"test_path": "1.png"}, {"test_path": "2.png"}]), True, 0)
])
def test_validate(data, drop_on_error, expected_len):
    results = validate(data, drop_on_error=drop_on_error)

    if drop_on_error:
        assert len(results.data) == expected_len
