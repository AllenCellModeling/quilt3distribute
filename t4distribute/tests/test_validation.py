#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import pytest

import numpy as np

from t4distribute import FeatureDefinition
from t4distribute.validation import Validator


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


@pytest.mark.parametrize("values, definition", [
    (np.ones(5), FeatureDefinition(np.float64)),
    (np.array(["hello", "world"]), FeatureDefinition(str)),
    (np.ones(5), FeatureDefinition(np.float64, (lambda x: x == 1,))),
    pytest.param(np.ones(5), FeatureDefinition(Path), marks=pytest.mark.raises(exception=ValueError)),
    pytest.param(
        np.array(["hello", "world"]), FeatureDefinition(int, cast_values=True),
        marks=pytest.mark.raises(exception=ValueError)
    ),
    pytest.param(np.array(["hello", "world"]), FeatureDefinition(int), marks=pytest.mark.raises(exception=TypeError)),
    pytest.param(
        np.array(["1.png", "2.png"]), FeatureDefinition(Path),
        marks=pytest.mark.raises(exception=FileNotFoundError)
    ),
    pytest.param(
        np.array([Path("1.png"), Path("2.png")]), FeatureDefinition(Path),
        marks=pytest.mark.raises(exception=FileNotFoundError)
    ),
    pytest.param(
        np.ones(5), FeatureDefinition(np.float64, (lambda x: x == 2,)), marks=pytest.mark.raises(exception=ValueError)
    )
])
def test_validator_process(values, definition):
    v = Validator("test", values, definition)

    v.process()
