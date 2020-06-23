#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import (Callable, Dict, List, NamedTuple, Optional, Set, Tuple,
                    Type, Union)

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
        """
        Initialize a new feature definition. A feature definition can be as simple as providing a data type (dtype) or
        can be incredibly specific by including validation and cleaning operations or providing metadata. If dtype of
        pathlib.Path is provided, cast_values is automatically set to True.

        :param dtype: The data type for the feature.
        :param validation_functions: A list or tuple of callable functions to validate each instance of the feature.
        :param cast_values: In the case that an instance of the feature is found that doesn't match the dtype provided,
            should that instance be attempted to cast to the provided dtype.
        :param display_name: Metadata attachment for a display name to be given to the feature.
        :param description: Metadata attachment for a description for the feature.
        :param units: Metadata attachment for unit details for the feature.
        """
        # Handle non tuple values
        if validation_functions is None:
            validation_functions = tuple()
        elif isinstance(validation_functions, list):
            validation_functions = tuple(validation_functions)

        # Ensure functions was passed as a tuple
        if not isinstance(validation_functions, tuple):
            raise TypeError(
                "FeatureDefinitions must be initialized with either no, a list, or a tuple of validation functions."
            )

        # Ensure all items provided in validation functions are callable
        if not all(callable(f) for f in validation_functions):
            raise TypeError(
                f"Items provided as validation functions must be callable. Received: {validation_functions}"
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
    """
    Helper function to generate a schema template (a dictionary of column name to FeatureDefinitions). This function
    makes strong assumptions about which columns headers indicate that a value is a filepath or not. It also, attempts
    to determine if value casting should be turned on based off the number of unique types present in a column.
    """
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


class PlannedDelayedDropError(Exception):
    def __init__(self, message: str, **kwargs):
        self.message = message

    def __str__(self):
        return self.message


class PlannedDelayedDropResult(NamedTuple):
    index: int
    error: PlannedDelayedDropError


class ValidatedFeature(object):
    def __init__(
        self,
        name: str,
        dtype: Type,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        units: Optional[str] = None,
        validation_functions: Optional[Tuple[Callable]] = None,
        errored_results: Optional[Set[PlannedDelayedDropResult]] = None
    ):
        """
        A feature that has it's core validation attributes locked but metadata freely mutable.

        :param name: The name for the feature in the dataset (usually this is the column).
        :param dtype: A single data type for the feature.
        :param display_name: A display name for the feature.
        :param description: A description for the feature.
        :param units: Units for the feature.
        :param validation_functions: The tuple of validation functions ran against the feature values.
        :param errored_results: An optional set of PlannedDelayedDropResults that errored out during validation.
        """
        # Store configuration
        self._name = name
        self._dtype = dtype
        self.display_name = display_name
        self.description = description
        self.units = units
        self._validation_functions = validation_functions

        if errored_results:
            self._errored_results = errored_results
        else:
            self._errored_results = set()

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

    @property
    def errored_results(self) -> Set[int]:
        return self._errored_results

    def to_dict(self) -> Dict[str, Union[str, Type, Tuple[Callable]]]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "display_name": self.display_name,
            "description": self.description,
            "units": self.units,
            "validation_functions": self.validation_functions,
            "errored_results": self.errored_results
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
        definition: FeatureDefinition,
        drop_on_error: bool = False
    ):
        """
        A container to manage feature values and feature definition that can actually process (validate) the feature.

        :param name: The name of the feature (usually this is the column name).
        :param values: The np.ndarray of feature values.
        :param definition: The feature definition to validate against.
        :param drop_on_error: In the case that an error occurs during validation should the row be dropped and
            validation continue.
        """
        # Store configuration
        self.name = name
        self.values = values
        self.definition = definition
        self.drop_on_error = drop_on_error

    def process(self, progress_bar: Optional[tqdm] = None) -> ValidatedFeature:
        """
        Use the feature definition stored on this object to attempt to validate the feature.

        :param progress_bar: An optional tqdm progress bar to update as the values are processed.
        :return: A ValidatedFeature object representing that this feature has been checked.
        """
        # Create empty errored results set
        errored_results = set()

        # Begin checking
        for i in range(len(self.values)):
            try:
                # Short ref to value
                val = self.values[i]
                val_descriptor = f"from column: '{self.name}', at index: {i}: ({type(val)} '{val}')"

                # Attempt type casting
                if self.definition.cast_values:
                    # Uncomment to fix windows paths
                    # Still debating the best way to do this
                    # Ideally we would want to detect which path sep was provided and what is the current os path sep
                    # Fix windows paths
                    # DEAR GOD WHY WINDOWS WHY
                    # if self.definition.dtype == Path:
                    #     val = val.replace("\\", "/")

                    try:
                        val = self.definition.dtype(val)
                        self.values[i] = val
                    except (ValueError, TypeError):
                        msg = f"Could not cast value {val_descriptor} to received type {self.definition.dtype}."
                        if self.drop_on_error:
                            raise PlannedDelayedDropError(msg)
                        else:
                            raise ValueError(msg)

                # Check type
                if not isinstance(val, self.definition.dtype):
                    msg = (
                        f"Value {val_descriptor} does not match the type specification received "
                        f"{self.definition.dtype}."
                    )
                    if self.drop_on_error:
                        raise PlannedDelayedDropError(msg)
                    else:
                        raise TypeError(msg)

                # Confirm paths
                if self.definition.dtype == Path:
                    if not val.exists():
                        msg = f"Filepath {val_descriptor} was not found."
                        if self.drop_on_error:
                            raise PlannedDelayedDropError(msg)
                        else:
                            raise FileNotFoundError(msg)

                # Check values
                for func_index, f in enumerate(self.definition.validation_functions):
                    if not f(val):
                        msg = f"Value {val_descriptor} failed validation function {func_index}."
                        if self.drop_on_error:
                            raise PlannedDelayedDropError(msg)
                        else:
                            raise ValueError(msg)

            except PlannedDelayedDropError as e:
                errored_results.add(PlannedDelayedDropResult(index=i, error=e))

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
            validation_functions=self.definition.validation_functions,
            errored_results=errored_results
        )


class ValidationReturn(NamedTuple):
    name: str
    feature: ValidatedFeature


def _validate_helper(validator: Validator, progress_bar: Optional[tqdm] = None) -> ValidatedFeature:
    """
    A concurrency helper function to manage validator io.
    """
    return ValidationReturn(validator.name, validator.process(progress_bar))


class Schema(object):
    def __init__(self, features: Dict[str, ValidatedFeature]):
        """
        A schema is the summation of multiple validated and unvalidated features for a Dataset. It provides helpful
        methods for viewing which features have and have not been validated and with which data types, functions, and
        metadata.

        :param features: A dictionary mapping the dataset manifest column names to ValidatedFeatures.
        """
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
                    "validation_functions": None,
                    "errored_results": None
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
    drop_on_error: bool = False,
    n_workers: Optional[int] = None,
    show_progress: bool = True
) -> ValidatedDataset:
    """
    A function that validates a dataset against the proposed schema.

    :param data: A pandas dataframe to validate.
    :param schema: The proposed schema to validate the dataset against.
        A dictionary mapping dataframe column names to FeatureDefinitions.
        If no schema provided, it will use `_generate_schema_template` to generate one for the data provided.
    :param drop_on_error: In the case that an error occurs during validation should the row be dropped and validation
        continue.
    :param n_workers: The number of threads to use during validation.
    :param show_progress: Boolean option to show or hide progress bar.
    :return: A ValidatedDataset object that stores the cleaned copy of the data as well as the validated schema.

    Validation isn't a CPU intensive task so async threadpool is used over processpool.
    The most intensive task is file existence checks.
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
        definition=definition,
        drop_on_error=drop_on_error
    ) for column, definition in schema.items()]

    # Multiprocess validation
    with ThreadPoolExecutor(n_workers) as exe:
        # Some people don't like progress bars, @heeler @AetherUnbound 🙃
        if show_progress:
            with tqdm(total=len(validators) * len(data), desc="Validating") as pbar:
                validate_partial = partial(_validate_helper, progress_bar=pbar)
                validated_features = list(exe.map(validate_partial, validators))
        else:
            validated_features = list(exe.map(_validate_helper, validators))

    # Display any errors that occured during validation
    for vf in validated_features:
        if len(vf.feature.errored_results) > 0:
            log.warning(f"Validation against column {vf.name} resulted in {len(vf.feature.errored_results)} errors.")

            # Display errors for this feature
            for i, er in enumerate(vf.feature.errored_results):
                log.warning(er.error)

                # Break after first ten
                if i == 9:
                    log.warning("...")
                    break

    # Drop any indicies that errored out during validation
    if drop_on_error:
        # Combine all errored indicie sets
        master_set = set()
        for vf in validated_features:
            master_set = master_set.union([er.index for er in vf.feature.errored_results])

        # Drop all errored indicies
        to_validate = to_validate.drop(list(master_set))

    return ValidatedDataset(to_validate, Schema({f.name: f.feature for f in validated_features}))
