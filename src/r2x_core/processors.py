"""Data transformation pipeline for tabular and JSON data.

This module implements a functional processing pipeline that applies transformations
to data based on specifications in DataFile configurations. Transformations are
organized by data type (Polars LazyFrame for tabular, dict for JSON) with a
registration system allowing custom transformations.

Pipeline architecture:
- Tabular: lowercase → drop_columns → rename → pivot → cast → filter → select
- JSON: rename_keys → drop_columns → select_columns → filter → select_keys

All placeholder substitution in filter_by specifications uses curly braces
(e.g., {solve_year}) and requires a placeholders dictionary at processing time.

See Also
--------
:class:`~r2x_core.datafile.DataFile` : File configuration with processing specs.
:class:`~r2x_core.datafile.TabularProcessing` : Tabular data transformation config.
:class:`~r2x_core.datafile.JSONProcessing` : JSON data transformation config.
"""

import re
from collections.abc import Callable
from typing import Any

import polars as pl
from loguru import logger
from polars.datatypes.classes import DataTypeClass

from r2x_core.types import JSONType

from .datafile import DataFile, FileProcessing, JSONProcessing, TabularProcessing
from .exceptions import ValidationError
from .result import Err, Ok, Result

# Regex to find simple placeholders
_PLACEHOLDER_PATTERN = re.compile(r"\{([^}]+)\}")


def substitute_placeholders(
    value: Any, placeholders: dict[str, Any] | None = None
) -> Result[Any, ValueError]:
    """Replace {variable} placeholders in values using provided mapping.

    Recursively substitutes placeholders in strings, lists, and dictionaries.
    Placeholders must be complete values (e.g., {year}, not prefix_{year}).

    Parameters
    ----------
    value : Any
        String, list, dict, or scalar value potentially containing placeholders.
    placeholders : dict[str, Any] | None
        Mapping from placeholder names to replacement values. Required if
        placeholders are found in value.

    Returns
    -------
    Result[Any, ValueError]
        Ok(substituted_value) on success, Err(ValueError) if placeholders found
        without mapping or placeholder name not in mapping dictionary.

    Examples
    --------
    >>> result = substitute_placeholders("{year}", {"year": 2030})
    >>> result.unwrap()
    2030

    >>> result = substitute_placeholders({"year": "{y}"}, {"y": 2030})
    >>> result.unwrap()
    {'year': 2030}
    """
    if not isinstance(value, str | list | dict):
        return Ok(value)

    if isinstance(value, str) and "{" not in value:
        return Ok(value)

    def substitute_value(val: Any) -> Result[Any, ValueError]:
        """Recursively substitute placeholders in a value."""
        if isinstance(val, str):
            if "{" not in val:
                return Ok(val)

            match = _PLACEHOLDER_PATTERN.fullmatch(val)
            if match:
                var_name = match.group(1)
                if placeholders is None:
                    return Err(
                        ValueError(
                            f"Found placeholder '{{{var_name}}}' but no placeholders provided.\n"
                            "Hint: Pass placeholders parameter when calling read_data_file(), "
                            "or use literal values instead of placeholders."
                        )
                    )
                if var_name not in placeholders:
                    available = ", ".join(placeholders.keys())
                    return Err(
                        ValueError(
                            f"Placeholder '{{{var_name}}}' not found in placeholders.\n"
                            f"Available placeholders: {available}"
                        )
                    )
                return Ok(placeholders[var_name])

            if _PLACEHOLDER_PATTERN.search(val):
                return Err(
                    ValueError(
                        f"Found placeholder pattern in '{val}' but it's not a complete placeholder.\n"
                        "Placeholders must be the entire value, e.g., use '{variable}' not 'prefix_{variable}'"
                    )
                )
            return Ok(val)

        elif isinstance(val, list):
            new_list = []
            for item in val:
                res = substitute_value(item)
                if res.is_err():
                    return res  # propagate error
                new_list.append(res.unwrap())
            return Ok(new_list)

        elif isinstance(val, dict):
            new_dict = {}
            for k, v in val.items():
                res = substitute_value(v)
                if res.is_err():
                    return res
                new_dict[k] = res.unwrap()
            return Ok(new_dict)

        return Ok(val)

    return substitute_value(value)


def process_tabular_data(
    data_file: DataFile, data_frame: pl.LazyFrame, proc_spec: TabularProcessing
) -> pl.LazyFrame:
    """Apply tabular data transformations sequentially.

    Executes a pipeline of transformations (lowercase, drop, rename, pivot, cast,
    filter, select) on a Polars LazyFrame according to TabularProcessing configuration.

    Parameters
    ----------
    data_file : DataFile
        File configuration providing context for logging and validation.
    data_frame : pl.LazyFrame
        Input tabular data in lazy evaluation mode.
    proc_spec : TabularProcessing
        Processing specification defining transformations to apply.

    Returns
    -------
    pl.LazyFrame
        Transformed LazyFrame with all operations applied in sequence.

    See Also
    --------
    :func:`pl_lowercase` : Lowercase string columns and column names.
    :func:`pl_drop_columns` : Remove specified columns.
    :func:`pl_rename_columns` : Apply column name mapping.
    """
    pipeline = [
        pl_lowercase,
        pl_drop_columns,
        pl_rename_columns,
        pl_pivot_on,
        pl_cast_schema,
        pl_apply_filters,
        pl_select_columns,
    ]

    output_data = data_frame
    for fp_function in pipeline:
        output_data = fp_function(data_file=data_file, proc_spec=proc_spec, data_frame=output_data)

    return output_data


def process_json_data(data_file: DataFile, json_data: JSONType, proc_spec: JSONProcessing) -> JSONType:
    """Apply JSON data transformations sequentially.

    Executes a pipeline of transformations (rename_keys, drop_columns, select_columns,
    filter, select_keys) on nested dict/list structures per JSONProcessing configuration.
    Transformations work recursively on nested structures.

    Parameters
    ----------
    data_file : DataFile
        File configuration providing context for logging and validation.
    json_data : JSONType
        Input JSON data (dict, list of dicts, or nested structures).
    proc_spec : JSONProcessing
        Processing specification defining transformations to apply.

    Returns
    -------
    JSONType
        Transformed JSON data with all operations applied in sequence.

    See Also
    --------
    :func:`json_rename_keys` : Apply key name mapping recursively.
    :func:`json_drop_columns` : Remove specified keys recursively.
    :func:`json_apply_filters` : Filter dicts by key-value criteria.
    """
    pipeline = [
        json_rename_keys,
        json_drop_columns,
        json_select_columns,
        json_apply_filters,
        json_select_keys,
    ]
    result = json_data
    for transform_func in pipeline:
        result = transform_func(data_file=data_file, json_data=result, proc_spec=proc_spec)

    return result


def pl_pivot_on(data_file: DataFile, data_frame: pl.LazyFrame, proc_spec: TabularProcessing) -> pl.LazyFrame:
    """Unpivot (melt) the DataFrame based on configuration."""
    if not proc_spec or not proc_spec.pivot_on:
        return data_frame

    value_name = proc_spec.pivot_on
    collected = data_frame.collect()
    all_columns = collected.columns

    values = []
    for col in all_columns:
        values.extend(collected[col].to_list())

    new_df = pl.DataFrame({value_name: values})
    logger.trace("Pivoting columns: {} for {}", value_name, data_file.name)
    return new_df.lazy()


def pl_lowercase(data_file: DataFile, data_frame: pl.LazyFrame, proc_spec: TabularProcessing) -> pl.LazyFrame:
    """Convert all string columns to lowercase."""
    result = data_frame.with_columns(pl.col(pl.String).str.to_lowercase()).rename(
        {column: column.lower() for column in data_frame.collect_schema().names()}
    )
    logger.trace("Lowercase columns: {} for {}", result.collect_schema().names(), data_file.name)
    return result


def pl_drop_columns(
    data_file: DataFile, data_frame: pl.LazyFrame, proc_spec: TabularProcessing
) -> pl.LazyFrame:
    """Drop specified columns if they exist."""
    if not proc_spec or not proc_spec.drop_columns:
        return data_frame

    existing_cols = [col for col in proc_spec.drop_columns if col in data_frame.collect_schema().names()]
    if existing_cols:
        logger.debug("Dropping columns {} from {}", existing_cols, data_file.name)
        return data_frame.drop(existing_cols)
    return data_frame


def pl_rename_columns(
    data_file: DataFile, data_frame: pl.LazyFrame, proc_spec: TabularProcessing
) -> pl.LazyFrame:
    """Rename columns based on mapping."""
    if not proc_spec or not proc_spec.column_mapping:
        return data_frame

    valid_mapping = {
        old: new
        for old, new in proc_spec.column_mapping.items()
        if old in data_frame.collect_schema().names()
    }
    if valid_mapping:
        logger.debug("Renaming columns {} in {}", valid_mapping, data_file.name)
        return data_frame.rename(valid_mapping)
    return data_frame


def pl_cast_schema(
    data_file: DataFile, data_frame: pl.LazyFrame, proc_spec: TabularProcessing
) -> pl.LazyFrame:
    """Cast columns to specified data types."""
    if not proc_spec or not proc_spec.column_schema:
        return data_frame

    cast_exprs = []
    for col, type_str in (proc_spec.column_schema or {}).items():
        if col in data_frame.collect_schema().names():
            try:
                polars_type = _get_polars_type(type_str)
            except ValueError:
                # Re-raise so callers/tests can observe the failure
                raise
            cast_exprs.append(pl.col(col).cast(polars_type))

    if not cast_exprs:
        return data_frame
    logger.trace("Applying schema {} to {}", proc_spec.column_schema, data_file.name)
    return data_frame.with_columns(cast_exprs)


def pl_apply_filters(
    data_file: DataFile, data_frame: pl.LazyFrame, proc_spec: TabularProcessing
) -> pl.LazyFrame:
    """Apply row filters."""
    if not proc_spec or not proc_spec.filter_by:
        return data_frame

    filters = [
        pl_build_filter_expr(col, value)
        for col, value in (proc_spec.filter_by or {}).items()
        if col in data_frame.collect_schema().names()
    ]

    if not filters:
        return data_frame
    combined_filter = filters[0]
    for filter_expr in filters[1:]:
        combined_filter = combined_filter & filter_expr
    logger.trace("Applying {} filters to {}", len(filters), data_file.name)
    return data_frame.filter(combined_filter)


def pl_select_columns(
    data_file: DataFile, data_frame: pl.LazyFrame, proc_spec: TabularProcessing
) -> pl.LazyFrame:
    """Select specific columns (index + value columns)."""
    if not proc_spec or not proc_spec.select_columns:
        return data_frame

    cols_to_select = []
    if proc_spec.set_index:
        cols_to_select.extend(proc_spec.select_columns)
    cols_to_select.extend(proc_spec.select_columns)

    unique_cols = list(
        dict.fromkeys(col for col in cols_to_select if col in data_frame.collect_schema().names())
    )
    if not unique_cols:
        return data_frame

    logger.trace("Selecting {} columns from {}", len(unique_cols), data_file.name)
    return data_frame.select(unique_cols)


def json_rename_keys(data_file: DataFile, json_data: JSONType, proc_spec: JSONProcessing) -> JSONType:
    """Rename keys based on key mapping from JSONProcessing.

    Applies renaming recursively to nested dictionaries.
    """
    if not proc_spec or not proc_spec.key_mapping:
        return json_data

    mapping = proc_spec.key_mapping

    def rename_keys_recursive(obj: JSONType) -> JSONType:
        """Recursively rename keys in nested JSON structure.

        Parameters
        ----------
        obj : JSONType
            JSON object (dict, list, or scalar) to process.

        Returns
        -------
        JSONType
            Object with renamed keys applied recursively.
        """
        if isinstance(obj, dict):
            return {mapping.get(k, k): rename_keys_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [rename_keys_recursive(item) for item in obj]
        return obj

    logger.debug("Applying key mapping {} to {}", mapping, data_file.name)
    return rename_keys_recursive(json_data)


def json_drop_columns(data_file: DataFile, json_data: JSONType, proc_spec: JSONProcessing) -> JSONType:
    """Drop specified columns/keys from JSON data recursively."""
    if not proc_spec or not proc_spec.drop_keys:
        return json_data

    drop_keys = proc_spec.drop_keys

    def drop_keys_recursive(obj: JSONType) -> JSONType:
        """Recursively remove specified keys from nested JSON structure.

        Parameters
        ----------
        obj : JSONType
            JSON object (dict, list, or scalar) to process.

        Returns
        -------
        JSONType
            Object with specified keys removed recursively.
        """
        if isinstance(obj, dict):
            return {k: drop_keys_recursive(v) for k, v in obj.items() if k not in drop_keys}
        elif isinstance(obj, list):
            return [drop_keys_recursive(item) for item in obj]
        return obj

    logger.debug("Dropping columns {} from {}", drop_keys, data_file.name)
    return drop_keys_recursive(json_data)


def json_select_columns(data_file: DataFile, json_data: JSONType, proc_spec: JSONProcessing) -> JSONType:
    """Select specific columns/keys from JSON data."""
    if not proc_spec or not proc_spec.select_keys:
        return json_data

    columns_to_select = proc_spec.select_keys

    def select_keys_recursive(obj: JSONType) -> JSONType:
        """Recursively select specified keys from nested JSON structure.

        Parameters
        ----------
        obj : JSONType
            JSON object (dict, list, or scalar) to process.

        Returns
        -------
        JSONType
            Object with only selected keys preserved recursively.
        """
        if isinstance(obj, dict):
            return {k: select_keys_recursive(v) for k, v in obj.items() if k in columns_to_select}
        elif isinstance(obj, list):
            return [select_keys_recursive(item) for item in obj]
        return obj

    logger.trace("Selecting keys {} from {}", columns_to_select, data_file.name)
    return select_keys_recursive(json_data)


def json_apply_filters(
    data_file: DataFile,
    json_data: JSONType,
    proc_spec: JSONProcessing | None,
) -> JSONType:
    """Filter JSON data by key-value pairs."""
    if not proc_spec or not proc_spec.filter_by:
        return json_data

    filters = proc_spec.filter_by

    def matches(obj: JSONType) -> bool:
        """Check if object matches all filter criteria.

        Parameters
        ----------
        obj : JSONType
            Object to check against filters.

        Returns
        -------
        bool
            True if object is a dict and matches all filter conditions.
        """
        if not isinstance(obj, dict):
            return False
        return all(_matches_filter(obj.get(k), v) for k, v in filters.items())

    logger.trace("Applying filter {} to {}", filters, data_file.name)

    # handle list of dicts
    if isinstance(json_data, list):
        return [obj for obj in json_data if matches(obj)]

    # handle dict
    if isinstance(json_data, dict):
        if matches(json_data):
            return json_data
        # else: filter sub-dicts
        return {k: v for k, v in json_data.items() if matches(v)}

    return json_data


def json_select_keys(
    data_file: DataFile,
    json_data: JSONType,
    proc_spec: JSONProcessing | None,
) -> JSONType:
    """Select specific keys from JSON data (dict or list of dicts)."""
    if not proc_spec or not proc_spec.select_keys:
        return json_data

    keys = set(proc_spec.select_keys)
    logger.trace("Selecting keys {} from {}", keys, data_file.name)

    if isinstance(json_data, list):
        return [{k: v for k, v in obj.items() if k in keys} for obj in json_data if isinstance(obj, dict)]

    if isinstance(json_data, dict):
        return {k: v for k, v in json_data.items() if k in keys}

    return json_data


def transform_xml_data(data: Any, data_file: DataFile) -> Any:
    """Transform XML data - placeholder for future implementation."""
    logger.debug("XML transformation placeholder for {}", data_file.name)
    return data


TRANSFORMATIONS: dict[type | tuple[type, ...], Callable[[DataFile, Any, Any], Any]] = {
    pl.LazyFrame: process_tabular_data,
    dict: process_json_data,
    # We can add more as needed: tuple: transform_xml_data, etc.
}


def apply_processing(
    data_file: DataFile,
    data: Any,
    proc_spec: FileProcessing | None,
    placeholders: dict[str, Any] | None = None,
) -> Result[Any, ValueError | ValidationError]:
    """Apply appropriate transformation based on data type.

    Parameters
    ----------
    data_file : DataFile
        Configuration with transformation instructions.
    data : Any
        Raw data to transform.
    proc_spec : FileProcessing | None
        Processing specification (TabularProcessing or JSONProcessing).
    placeholders : dict[str, Any] | None
        Dictionary mapping placeholder variable names to their values.
        Used to substitute placeholders like {solve_year} in filter_by.

    Returns
    -------
    Any
        Transformed data.

    Raises
    ------
    ValueError
        If placeholders are found in filter_by but no placeholders dict provided.
    """
    if not proc_spec:
        return Ok(data)

    if proc_spec.filter_by:
        result_substitution = substitute_placeholders(proc_spec.filter_by, placeholders)

        if result_substitution.is_err():
            error = result_substitution.err()
            return Err(error)

        substituted = result_substitution.unwrap()
        new_proc = proc_spec.model_copy(update={"filter_by": substituted})
        data_file = data_file.model_copy(update={"proc_spec": new_proc})
        proc_spec = new_proc

    for registered_types, transform_func in TRANSFORMATIONS.items():
        if isinstance(data, registered_types):
            return Ok(transform_func(data_file, data, proc_spec))

    logger.debug("No transformation for type {} in {}", type(data).__name__, data_file.name)
    return Ok(data)


def register_transformation(data_types: type | tuple[type, ...], func: Callable[..., Any]) -> None:
    """Register a custom transformation function.

    Parameters
    ----------
    data_types : type or tuple of types
        Data type(s) this function can handle.
    func : TransformFunction
        Function that takes (data_file, data) and returns transformed data.

    Examples
    --------
    >>> def transform_my_data(data_file: DataFile, data: MyType) -> MyType:
    ...     # Custom transformation logic
    ...     return data
    >>> register_transformation(MyType, transform_my_data)
    """
    TRANSFORMATIONS[data_types] = func


def _matches_filter(value: Any, filter_value: Any) -> bool:
    """Check if value matches filter criteria.

    Supports both single value and list comparisons. For lists, checks membership.
    Used internally by JSON and tabular filter operations.

    Parameters
    ----------
    value : Any
        Actual value from data to test.
    filter_value : Any or list
        Target value or list of values to match against.

    Returns
    -------
    bool
        True if value equals filter_value (single) or is in filter_value (list).
    """
    if isinstance(filter_value, list):
        return bool(value in filter_value)
    return bool(value == filter_value)


def _get_polars_type(type_str: str) -> DataTypeClass:
    """Convert type name string to Polars DataType class.

    Maps common type names to Polars type objects. Supports aliases
    (e.g., 'string', 'str'; 'int', 'integer'; 'float', 'double').

    Parameters
    ----------
    type_str : str
        Type name (case-insensitive): string, str, int, int32, integer, float,
        double, bool, boolean, date, datetime.

    Returns
    -------
    DataTypeClass
        Corresponding Polars data type.

    Raises
    ------
    ValueError
        If type_str is not recognized in the type mapping.
    """
    mapping = {
        "string": pl.String,
        "str": pl.String,
        "int": pl.Int64,
        "int32": pl.Int32,
        "integer": pl.Int64,
        "float": pl.Float64,
        "double": pl.Float64,
        "bool": pl.Boolean,
        "boolean": pl.Boolean,
        "date": pl.Date,
        "datetime": pl.Datetime,
    }
    polars_type = mapping.get(type_str.lower())
    if polars_type is None:
        msg = f"Unsupported data type: {type_str}"
        raise ValueError(msg)
    return polars_type


def pl_build_filter_expr(column: str, value: Any) -> pl.Expr:
    """Build polars filter expression."""
    if column == "datetime" and isinstance(value, int | list):
        if isinstance(value, list):
            return pl.col("datetime").dt.year().is_in(value)
        return pl.col("datetime").dt.year() == value

    col_expr = pl.col(column)

    if isinstance(value, list):
        value = [str(v) for v in value]
        return col_expr.cast(pl.Utf8).is_in(value)

    value = str(value)
    return col_expr.cast(pl.Utf8) == value  # type: ignore[no-any-return]
