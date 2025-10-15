"""Simplified data transformations for different data types."""

from collections.abc import Callable
from functools import partial
from typing import Any

import polars as pl
from loguru import logger
from polars.datatypes.classes import DataTypeClass

from .datafile import DataFile

TransformFunction = Callable[[Any, DataFile], Any]


def transform_tabular_data(data_file: DataFile, data: pl.LazyFrame) -> pl.LazyFrame:
    """Transform tabular data to LazyFrame with applied transformations.

    Applies transformations in order:
        lowercase -> drop -> rename -> pivot -> schema -> filter -> select

    Parameters
    ----------
    data_file : DataFile
        Configuration with transformation instructions.
    data : pl.LazyFrame
        Input tabular data.

    Returns
    -------
    pl.LazyFrame
        Transformed lazy frame.

    Notes
    -----
    Always returns a LazyFrame for consistent lazy evaluation.
    """
    # Convert to LazyFrame if needed
    df = data.lazy() if isinstance(data, pl.DataFrame) else data

    pipeline = [
        partial(pl_lowercase, data_file),
        partial(pl_drop_columns, data_file),
        partial(pl_rename_columns, data_file),
        partial(pl_pivot_on, data_file),
        partial(pl_cast_schema, data_file),
        partial(pl_apply_filters, data_file),
        partial(pl_select_columns, data_file),
    ]

    transformed_data = df
    for transform_func in pipeline:
        transformed_data = transform_func(transformed_data)

    return transformed_data


def pl_pivot_on(data_file: DataFile, df: pl.LazyFrame) -> pl.LazyFrame:
    """Unpivot (melt) the DataFrame based on configuration.

    Transforms wide-format data to long-format by converting all columns
    into rows with a new value column. This prevents single-row data from
    being misinterpreted as column headers.

    Parameters
    ----------
    data_file : DataFile
        Configuration with pivot instructions. Uses pivot_on attribute
        to specify the name of the new value column.
    df : pl.LazyFrame
        Input lazy frame to be unpivoted.

    Returns
    -------
    pl.LazyFrame
        Unpivoted lazy frame with only the new value column.

    Notes
    -----
    This function addresses a common data structure issue where files like
    modeledyears.csv contain single rows with values spread across columns
    (e.g., years: 2020, 2025, 2030). Without unpivoting, these values might
    be incorrectly treated as column headers rather than data. The unpivot
    operation converts each column value into a separate row, ensuring proper
    data interpretation.
    """
    if not data_file.pivot_on:
        return df

    all_columns = df.collect_schema().names()

    return df.unpivot(on=all_columns, variable_name="tmp", value_name=data_file.pivot_on).select(
        data_file.pivot_on
    )


def transform_json_data(data_file: DataFile, data: dict[str, Any]) -> dict[str, Any]:
    """Transform JSON/dict data using functional pipeline.

    Applies transformations in order: rename → filter → select.

    Parameters
    ----------
    data : dict
        Input JSON/dict data.
    data_file : DataFile
        Configuration with transformation instructions.

    Returns
    -------
    dict
        Transformed dictionary.
    """
    # Create pipeline using partial functions with data_file bound
    pipeline = [
        partial(json_rename_keys, data_file),
        partial(json_apply_filters, data_file),
        partial(json_select_keys, data_file),
    ]

    # Apply each transformation in sequence
    result = data
    for transform_func in pipeline:
        result = transform_func(result)

    return result


def pl_lowercase(data_file: DataFile, df: pl.LazyFrame) -> pl.LazyFrame:
    """Convert all string columns to lowercase."""
    logger.trace("Lowercase columns: {}", df.collect_schema().names())
    result = df.with_columns(pl.col(pl.String).str.to_lowercase()).rename(
        {column: column.lower() for column in df.collect_schema().names()}
    )
    logger.trace("New columns: {}", result.collect_schema().names())
    return result


def pl_drop_columns(data_file: DataFile, df: pl.LazyFrame) -> pl.LazyFrame:
    """Drop specified columns if they exist."""
    if not data_file.drop_columns:
        return df

    # Only drop columns that actually exist
    existing_cols = [col for col in data_file.drop_columns if col in df.collect_schema().names()]
    if existing_cols:
        logger.debug("Dropping columns {} from {}", existing_cols, data_file.name)
        return df.drop(existing_cols)
    return df


def pl_rename_columns(data_file: DataFile, df: pl.LazyFrame) -> pl.LazyFrame:
    """Rename columns based on mapping."""
    if not data_file.column_mapping:
        return df

    # Only rename columns that exist
    valid_mapping = {
        old: new for old, new in data_file.column_mapping.items() if old in df.collect_schema().names()
    }
    if valid_mapping:
        logger.debug("Renaming columns {} in {}", valid_mapping, data_file.name)
        return df.rename(valid_mapping)
    return df


def pl_cast_schema(data_file: DataFile, df: pl.LazyFrame) -> pl.LazyFrame:
    """Cast columns to specified data types."""
    if not data_file.column_schema:
        return df

    # Build cast expressions for existing columns
    cast_exprs = [
        pl.col(col).cast(_get_polars_type(type_str))
        for col, type_str in data_file.column_schema.items()
        if col in df.collect_schema().names()
    ]

    if cast_exprs:
        logger.debug("Applying schema to {}", data_file.name)
        return df.with_columns(cast_exprs)
    return df


def pl_apply_filters(data_file: DataFile, df: pl.LazyFrame) -> pl.LazyFrame:
    """Apply row filters."""
    if not data_file.filter_by:
        return df

    # Build filter expressions for existing columns
    filters = [
        pl_build_filter_expr(col, value)
        for col, value in data_file.filter_by.items()
        if col in df.collect_schema().names()
    ]

    if filters:
        logger.debug("Applying {} filters to {}", len(filters), data_file.name)
        # Combine all filters with AND
        combined_filter = filters[0]
        for filter_expr in filters[1:]:
            combined_filter = combined_filter & filter_expr
        return df.filter(combined_filter)
    return df


def pl_select_columns(data_file: DataFile, df: pl.LazyFrame) -> pl.LazyFrame:
    """Select specific columns (index + value columns)."""
    if not data_file.value_columns:
        return df

    # Combine index and value columns, removing duplicates
    cols_to_select = []
    if data_file.index_columns:
        cols_to_select.extend(data_file.index_columns)
    cols_to_select.extend(data_file.value_columns)

    # Keep only existing columns, preserve order, remove duplicates
    unique_cols = list(dict.fromkeys(col for col in cols_to_select if col in df.collect_schema().names()))

    if unique_cols:
        logger.debug("Selecting {} columns from {}", len(unique_cols), data_file.name)
        return df.select(unique_cols)
    return df


def json_rename_keys(data_file: DataFile, data: dict[str, Any]) -> dict[str, Any]:
    """Rename keys based on column mapping."""
    if not data_file.key_mapping:
        return data

    logger.debug("Applying key mapping to {}", data_file.name)
    return {data_file.key_mapping.get(k, k): v for k, v in data.items()}


def json_apply_filters(data_file: DataFile, data: dict[str, Any]) -> dict[str, Any]:
    """Filter JSON data by key-value pairs."""
    if not data_file.filter_by:
        return data

    logger.debug("Applying JSON filters to {}", data_file.name)
    return {
        k: v
        for k, v in data.items()
        if k not in data_file.filter_by or _matches_filter(v, data_file.filter_by[k])
    }


def json_select_keys(data_file: DataFile, data: dict[str, Any]) -> dict[str, Any]:
    """Select specific keys from JSON data."""
    if not data_file.value_columns:
        return data

    logger.debug("Selecting keys from {}", data_file.name)
    all_keys = (data_file.index_columns or []) + data_file.value_columns
    return {k: v for k, v in data.items() if k in all_keys}


def transform_xml_data(data: Any, data_file: DataFile) -> Any:
    """Transform XML data - placeholder for future implementation."""
    logger.debug("XML transformation placeholder for {}", data_file.name)
    return data


TRANSFORMATIONS: dict[type | tuple[type, ...], Callable[[DataFile, Any], Any]] = {
    pl.LazyFrame: transform_tabular_data,
    dict: transform_json_data,
    # We can add more as needed: tuple: transform_xml_data, etc.
}


def apply_transformation(data_file: DataFile, data: Any) -> Any:
    """Apply appropriate transformation based on data type.

    Parameters
    ----------
    data : Any
        Raw data to transform.
    data_file : DataFile
        Configuration with transformation instructions.

    Returns
    -------
    Any
        Transformed data.
    """
    for registered_types, transform_func in TRANSFORMATIONS.items():
        if isinstance(data, registered_types):
            return transform_func(data_file, data)

    logger.debug("No transformation for type {} in {}", type(data).__name__, data_file.name)
    return data


def register_transformation(data_types: type | tuple[type, ...], func: TransformFunction) -> None:
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
    """Check if value matches filter criteria."""
    if isinstance(filter_value, list):
        return bool(value in filter_value)
    return bool(value == filter_value)


def _get_polars_type(type_str: str) -> DataTypeClass:
    """Convert string to polars DataType."""
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
    # Special datetime year filtering
    if column == "datetime" and isinstance(value, int | list):
        if isinstance(value, list):
            return pl.col("datetime").dt.year().is_in(value)
        return pl.col("datetime").dt.year() == value

    # Regular filtering
    if isinstance(value, list):
        return pl.col(column).is_in(value)
    return pl.col(column) == value  # type: ignore[no-any-return]
