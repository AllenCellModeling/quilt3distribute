#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import logging
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple, Type, Union

import numpy as np
import pandas as pd
from tabulate import tabulate
from tqdm import tqdm

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class FeatureDefinition(object):
    def __init__(
        self,
        dtype: Type,
        validation_functions: Optional[Union[List[Callable], Tuple[Callable]]] = None,
        cast_values: bool = False,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        units: Optional[str] = None
    ):
        # Handle non tuple values
        if validation_functions is None:
            validation_functions = tuple()
        elif isinstance(validation_functions, list):
            validation_functions = tuple(validation_functions)

        # Ensure functions was passed as a tuple
        if not isinstance(validation_functions, tuple):
            raise TypeError(
                f"FeatureDefinitions must be initialized with either no, a list, or a tuple of validation functions."
            )

        # Store configuration
        self.dtype = dtype
        self.validation_functions = validation_functions
        self.cast_values = cast_values
        self.display_name = display_name
        self.description = description
        self.units = units

        # If dtype passed was Path, always attempt to cast
        if dtype == Path:
            self.cast_values = True

    def __str__(self):
        short_info = f"[display_name: '{self.display_name}', dtype: '{self.dtype}', cast values: {self.cast_values}]"
        return f"<FeatureDefinition {short_info}>"

    def __repr__(self):
        return str(self)


def _generate_schema_template(df: pd.DataFrame) -> Dict[str, FeatureDefinition]:
    # Create feature definition for each column
    feature_definitions = {}
    for col in df.columns:
        # Make basic schema
        display_name = col.replace("_", " ").replace("-", " ").replace("  ", " ").replace(".", "").title()

        # Create counter of types and choose most popular type
        dtypes = Counter([v.__class__ for v in df[col].values])

        # Get most popular
        # This is a good post explaining what is happening
        # https://www.robjwells.com/2015/08/python-counter-gotcha-with-max/
        dtype = dtypes.most_common(1)[0][0]

        # Only cast values when more than one type is present
        cast_values = len(dtypes) > 1

        # Check for path indicator
        if any(sub in col.lower() for sub in ["file", "path", "_dir", "directory"]) and not col.lower().endswith("id"):
            # Confirm most popular type is common path type
            if any(t == dtype for t in (str, Path)):
                # Set ctype to Path
                dtype = Path

        # Create definition
        feature_definitions[col] = FeatureDefinition(
            dtype=dtype,
            cast_values=cast_values,
            display_name=display_name
        )

    return feature_definitions


class ValidatedFeature(object):
    def __init__(
        self,
        name: str,
        dtype: Type,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        units: Optional[str] = None,
        validation_functions: Optional[Tuple[Callable]] = None
    ):
        # Store configuration
        self._name = name
        self._dtype = dtype
        self.display_name = display_name
        self.description = description
        self.units = units
        self._validation_functions = validation_functions

    @property
    def name(self) -> str:
        return self._name

    @property
    def dtype(self) -> Type:
        dtype = str(self._dtype).replace("<class '", "")[:-2]
        return dtype

    @property
    def validation_functions(self) -> Tuple[Callable]:
        return self._validation_functions

    def to_dict(self) -> Dict[str, Union[str, Type, Tuple[Callable]]]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "display_name": self.display_name,
            "description": self.description,
            "units": self.units,
            "validation_functions": self.validation_functions
        }

    def __str__(self):
        return f"<ValidatedFeature [name: {self.name}, dtype: {self.dtype}, display_name: {self.display_name}]"

    def __repr__(self):
        return str(self)


class Validator(object):
    def __init__(
        self,
        name: str,
        values: np.ndarray,
        definition: FeatureDefinition
    ):
        # Store configuration
        self.name = name
        self.values = values
        self.definition = definition

    def process(self, progress_bar: Optional[tqdm] = None) -> ValidatedFeature:
        # Begin checking
        for i in range(len(self.values)):
            # Short ref to value
            val = self.values[i]
            val_descriptor = f"from column: '{self.name}', from index: {i}: ({type(val)} '{val}')"

            # Attempt type casting
            if self.definition.cast_values:
                # Fix windows paths
                # DEAR GOD WHY WINDOWS WHY
                if self.definition.dtype == Path:
                    val = val.replace("\\", "/")

                try:
                    val = self.definition.dtype(val)
                    self.values[i] = val
                except ValueError:
                    raise ValueError(
                        f"Could not cast value {val_descriptor} to received type {self.definition.dtype}."
                    )

            # Check type
            if not isinstance(val, self.definition.dtype):
                raise TypeError(
                    f"Value {val_descriptor} does not match the type specification received {self.definition.dtype}."
                )

            # Confirm paths
            if self.definition.dtype == Path:
                if not val.exists():
                    raise FileNotFoundError(f"Filepath {val_descriptor} was not found.")

            # Check values
            for func_index, f in enumerate(self.definition.validation_functions):
                if not f(val):
                    raise ValueError(
                        f"Value {val_descriptor} failed validation function {func_index}."
                    )

            # Update progress
            if progress_bar:
                progress_bar.update()

        # Everything passed return validated feature
        return ValidatedFeature(
            name=self.name,
            dtype=self.definition.dtype,
            display_name=self.definition.display_name,
            description=self.definition.description,
            units=self.definition.units,
            validation_functions=self.definition.validation_functions
        )


class ValidationReturn(NamedTuple):
    name: str
    feature: ValidatedFeature


def _validate_helper(validator: Validator, progress_bar: Optional[tqdm] = None) -> ValidatedFeature:
    return ValidationReturn(validator.name, validator.process(progress_bar))


class Schema(object):
    def __init__(self, features: Dict[str, ValidatedFeature]):
        # Store all data
        self._feats = features

        # Construct schema dataframe
        self._df = []
        for name, feat in self.features.items():
            if feat:
                self._df.append(feat.to_dict())
            else:
                self._df.append({
                    "name": name,
                    "dtype": None,
                    "display_name": None,
                    "description": None,
                    "units": None,
                    "validation_functions": None
                })

        # Set schema dataframe
        self._df = pd.DataFrame(self._df)
        self._df = self._df.set_index("name")

    @property
    def features(self) -> Dict[str, ValidatedFeature]:
        return self._feats

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def validated(self) -> List[str]:
        # Return any features that are validated
        # Known validated when the feature is not None
        return [f for f in self.features if self.features[f]]

    @property
    def unvalidated(self) -> List[str]:
        # Return any features that are not validated
        # Known not validated when the feature is None
        return [f for f in self.features if self.features[f] is None]

    def _tabulate(self, tablefmt: str = "html") -> str:
        """
        Wrapper around tabulate.
        """
        # We don't really care about rendering the validation functions
        schema_table = self.df.drop("validation_functions", axis=1)
        schema_table = tabulate(schema_table, headers=list(schema_table.columns), tablefmt=tablefmt)

        return schema_table

    def __getitem__(self, key):
        return self.features[key]

    def __str__(self):
        return f"<Schema [Percent Features Validated: {len(self.validated) / len(self.features) * 100}%]"

    def _repr_html_(self):
        return self.df.to_html()

    def __repr__(self):
        return str(self)


class ValidatedDataset(NamedTuple):
    data: pd.DataFrame
    schema: Schema


def validate(
    data: pd.DataFrame,
    schema: Optional[Dict[str, FeatureDefinition]] = None,
    n_workers: Optional[int] = None,
    show_progress: bool = True
) -> ValidatedDataset:
    """
    Validate a dataset.
    """
    # Generate a template
    if schema is None:
        schema = _generate_schema_template(data)

    # Create a copy of the dataset to use for validation as values may change during validation
    to_validate = data.copy()

    # Create validators for every column passed in schema
    validators = [Validator(
        name=column,
        values=to_validate[column].values,
        definition=definition
    ) for column, definition in schema.items()]

    # Multiprocess validation
    with ThreadPoolExecutor(n_workers) as exe:
        # Some people don't like progress bars, @jamie @mattb 🙃
        if show_progress:
            with tqdm(total=len(validators) * len(data), desc="Validating") as pbar:
                validate_partial = partial(_validate_helper, progress_bar=pbar)
                validated_features = list(exe.map(validate_partial, validators))
        else:
            validated_features = list(exe.map(_validate_helper, validators))

    return ValidatedDataset(to_validate, Schema({f.name: f.feature for f in validated_features}))
