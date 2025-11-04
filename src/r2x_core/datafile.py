"""Data Model for datafiles (refactored to nested models)."""

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    ValidationError,
    computed_field,
    model_validator,
)

from .file_types import EXTENSION_MAPPING, FileFormat
from .result import Err, Ok, Result
from .utils import validate_file_extension, validate_glob_pattern


class FileInfo(BaseModel):
    """File metadata and properties.

    Contains descriptive information about the data file, including its role
    in the workflow, whether it contains time series data, and units for
    single-column files.

    Attributes
    ----------
    description : str | None
        Human-readable description of the file purpose.
    is_input : bool
        Whether the file is an input source. Default is True.
    is_optional : bool
        Whether the file is optional for processing. Default is False.
    is_timeseries : bool
        Whether the file contains time series data. Default is False.
    units : str | None
        Units for single-column numeric data. Default is None.

    See Also
    --------
    :class:`DataFile` : Complete data file configuration.
    """

    description: Annotated[str | None, Field(description="Description of the data file")] = None
    is_input: Annotated[bool, Field(description="Whether this is an input file")] = True
    is_optional: Annotated[bool, Field(description="Whether this file is optional")] = False
    is_timeseries: Annotated[bool, Field(description="Whether file contains time series data")] = False
    units: Annotated[str | None, Field(description="Units for single-column data")] = None


class ReaderConfig(BaseModel):  # type: ignore
    """Reader configuration for file loading.

    Specifies how to read the data file, including keyword arguments for
    the default reader or a custom function for specialized file formats.

    Attributes
    ----------
    function : Callable[[Path], Any] | None
        Custom reader function that takes file path and returns loaded data.
        If None, uses the default reader for the file type. Default is None.
    kwargs : dict[str, Any]
        Keyword arguments passed to the reader function. Default is empty.

    See Also
    --------
    :class:`DataFile` : Complete data file configuration.
    :class:`DataStore` : Container that uses ReaderConfig to load files.
    """

    kwargs: Annotated[dict[str, Any], Field(default_factory=dict, description="Keyword arguments for reader")]
    function: Annotated[Callable[[Path], Any] | None, Field(description="Custom reader function")] = None


class TabularProcessing(BaseModel):
    """Data transformations for tabular files (CSV, HDF5, Parquet, etc.).

    Defines a sequence of operations to apply to tabular data after loading.
    Supports column selection, filtering, reshaping, aggregation, and more.

    Attributes
    ----------
    select_columns : list[str] | None
        List of column names to keep. Removes all other columns.
    drop_columns : list[str] | None
        List of column names to remove.
    column_mapping : dict[str, str] | None
        Maps original column names to new names.
    rename_index : str | None
        New name for the index.
    column_schema : dict[str, str] | None
        Maps column names to data types for type coercion.
    filter_by : dict[str, Any] | None
        Conditions for filtering rows by column values.
    set_index : str | None
        Column name to use as the index.
    reset_index : bool | None
        If True, converts index to a regular column.
    pivot_on : str | None
        Column to pivot on for reshaping data.
    unpivot_on : list[str] | None
        Columns to unpivot for reshaping data.
    group_by : list[str] | None
        Columns to group by for aggregation.
    aggregate_on : dict[str, str] | None
        Mapping of columns to aggregation functions.
    sort_by : dict[str, str] | None
        Columns and sort directions for ordering.
    distinct_on : list[str] | None
        Columns to use for deduplication.
    replace_values : dict[Any, Any] | None
        Maps old values to new values for replacement.
    fill_null : dict[str, Any] | None
        Specifies fill values for null entries by column.

    See Also
    --------
    :class:`DataFile` : Uses TabularProcessing in proc_spec field.
    :class:`JSONProcessing` : Transformations for JSON files.
    """

    select_columns: Annotated[list[str] | None, Field(description="Columns to keep")] = None
    drop_columns: Annotated[list[str] | None, Field(description="Columns to remove")] = None
    column_mapping: Annotated[dict[str, str] | None, Field(description="Column rename mapping")] = None
    rename_index: Annotated[str | None, Field(description="Rename the index")] = None
    column_schema: Annotated[dict[str, str] | None, Field(description="Column type definitions")] = None
    filter_by: Annotated[dict[str, Any] | None, Field(description="Row filters")] = None
    set_index: Annotated[str | None, Field(description="Column to set as index")] = None
    reset_index: Annotated[bool | None, Field(description="Convert index to column")] = None
    pivot_on: Annotated[str | None, Field(description="Column to pivot on")] = None
    unpivot_on: Annotated[list[str] | None, Field(description="Columns to unpivot")] = None
    group_by: Annotated[list[str] | None, Field(description="Columns to group by")] = None
    aggregate_on: Annotated[dict[str, str] | None, Field(description="Aggregation spec")] = None
    sort_by: Annotated[dict[str, str] | None, Field(description="Sort specification")] = None
    distinct_on: Annotated[list[str] | None, Field(description="Columns for deduplication")] = None
    replace_values: Annotated[dict[Any, Any] | None, Field(description="Value replacement map")] = None
    fill_null: Annotated[dict[str, Any] | None, Field(description="Null fill values")] = None


class JSONProcessing(BaseModel):
    """Data transformations for JSON files.

    Defines operations for processing JSON-structured data, including key
    selection, filtering, and value transformations.

    Attributes
    ----------
    key_mapping : dict[str, str] | None
        Maps original JSON keys to new key names.
    rename_index : str | None
        New name for the dictionary keys.
    drop_columns : list[str] | None
        Keys to remove from nested dictionaries.
    filter_by : dict[str, Any] | None
        Conditions for filtering JSON objects by key values.
    replace_values : dict[Any, Any] | None
        Maps old values to new values for replacement.
    select_keys : list[str] | None
        Select specific keys to keep.

    See Also
    --------
    :class:`DataFile` : Uses JSONProcessing in proc_spec field.
    :class:`TabularProcessing` : Transformations for tabular files.
    """

    key_mapping: Annotated[dict[str, str] | None, Field(description="Key rename mapping (JSON-specific)")] = (
        None
    )
    rename_index: Annotated[str | None, Field(description="Rename dict keys")] = None
    drop_keys: Annotated[list[str] | None, Field(description="Keys to drop from nested dicts")] = None
    filter_by: Annotated[dict[str, Any] | None, Field(description="Filter conditions")] = None
    replace_values: Annotated[dict[Any, Any] | None, Field(description="Value replacement map")] = None
    select_keys: Annotated[list[str] | None, Field(description="Select certain keys.")] = None


FileProcessing = TabularProcessing | JSONProcessing


class DataFile(BaseModel):
    """Data file configuration with nested structure.

    Defines how to locate, read, and transform a single data file. Supports
    absolute paths, relative paths, and glob patterns. Processing is applied
    after reading and is type-specific (tabular or JSON).

    Parameters
    ----------
    name : str
        Unique identifier for this file mapping.
    fpath : Path | None, optional
        Absolute path to the data file. Exactly one of fpath, relative_fpath,
        or glob must be specified. Default is None.
    relative_fpath : Path | str | None, optional
        Path relative to DataStore folder. Default is None.
    glob : str | None, optional
        Glob pattern to locate files. Default is None.
    info : FileInfo | None, optional
        File metadata including role, optionality, time series flag.
        Default is None.
    reader : ReaderConfig | None, optional
        Reader configuration specifying kwargs and custom functions.
        Default is None.
    proc_spec : FileProcessing | None, optional
        Data transformations (TabularProcessing or JSONProcessing).
        Default is None.

    Raises
    ------
    ValueError
        If path sources are not exactly one of: fpath, relative_fpath, glob.
    ValueError
        If file type does not support time series and is_timeseries is True.

    See Also
    --------
    :class:`FileInfo` : File metadata.
    :class:`ReaderConfig` : Reader configuration.
    :class:`TabularProcessing` : Transformations for tabular files.
    :class:`JSONProcessing` : Transformations for JSON files.
    :class:`DataStore` : Container that manages DataFile instances.
    """

    name: Annotated[str, Field(description="Name of the mapping")]
    fpath: Annotated[
        FilePath | None, AfterValidator(validate_file_extension), Field(description="Absolute file path")
    ] = None
    relative_fpath: Annotated[Path | str | None, Field(description="Relative file path")] = None
    glob: Annotated[str | None, AfterValidator(validate_glob_pattern), Field(description="Glob pattern")] = (
        None
    )
    info: Annotated[FileInfo | None, Field(description="File metadata")] = None
    reader: Annotated[ReaderConfig | None, Field(description="Reader configuration")] = None
    proc_spec: Annotated[FileProcessing | None, Field(description="Data transformations")] = None

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_path_sources(self) -> "DataFile":
        """Validate that exactly one of fpath, relative_fpath, or glob is specified."""
        paths_set = sum([self.fpath is not None, self.relative_fpath is not None, self.glob is not None])
        if paths_set == 0:
            msg = "Exactly one of 'fpath', 'relative_fpath', or 'glob' must be specified"
            raise ValueError(msg)
        if paths_set > 1:
            msg = "Multiple path sources specified. Use exactly one of: 'fpath', 'relative_fpath', or 'glob'"
            raise ValueError(msg)
        return self

    @computed_field  # type: ignore
    @property
    def file_type(self) -> FileFormat:
        """Computed file type based on file extension."""
        if self.fpath is not None:
            extension = self.fpath.suffix.lower()
        elif self.relative_fpath is not None:
            rel_path = (
                Path(self.relative_fpath) if isinstance(self.relative_fpath, str) else self.relative_fpath
            )
            extension = rel_path.suffix.lower()
        elif self.glob is not None:
            if "." in self.glob:
                extension = "." + self.glob.rsplit(".", 1)[-1].rstrip("*?[]")
            else:
                msg = "Cannot determine file type from glob pattern without extension"
                raise ValueError(msg)
        else:
            msg = "Either fpath, relative_fpath, or glob must be set"
            raise ValueError(msg)

        file_type_class = EXTENSION_MAPPING.get(extension)
        if file_type_class is None:
            msg = f"Unsupported file extension: {extension}"
            raise ValueError(msg)

        if self.info and self.info.is_timeseries and not file_type_class.supports_timeseries:
            msg = f"File type {file_type_class.__name__} does not support time series data"
            raise ValueError(msg)

        return file_type_class()


def create_data_files_from_records(
    records: list[dict[str, Any]], folder_path: Path
) -> Result[list[DataFile], list[ValidationError]]:
    """Create DataFile instances from record dictionaries.

    Resolves file paths relative to folder_path before validation. Collects
    all validation errors rather than failing on the first error.

    Parameters
    ----------
    records : list[dict[str, Any]]
        List of dictionaries containing DataFile configuration.
    folder_path : Path
        Base folder for resolving relative paths.

    Returns
    -------
    Result[list[DataFile], list[ValidationError]]
        Ok containing list of DataFile instances, or Err containing all
        validation errors encountered during processing.

    See Also
    --------
    :class:`DataFile` : The model class being constructed.
    :func:`resolve_data_file_path` : Function for path resolution.
    """
    data_files: list[DataFile] = []
    errors: list[ValidationError] = []

    for idx, record in enumerate(records):
        try:
            resolved = resolve_data_file_path(record["fpath"], folder_path)
            record["fpath"] = resolved

            data_files.append(DataFile.model_validate(record))

        except (KeyError, TypeError) as exc:
            errors.append(
                ValidationError.from_exception_data(
                    title=f"Record[{idx}] missing or invalid fpath",
                    line_errors=[{"type": "value_error", "input": str(exc), "loc": ("fpath",)}],
                )
            )

        except FileNotFoundError as exc:
            errors.append(
                ValidationError.from_exception_data(
                    title=f"Record[{idx}] path resolution error",
                    line_errors=[
                        {"type": "value_error.path.not_found", "input": str(exc), "loc": ("fpath",)}
                    ],
                )
            )

        except ValidationError as exc:
            errors.append(exc)

    if errors:
        return Err(errors)

    return Ok(data_files)


def resolve_data_file_path(raw_path: str | Path, folder_path: Path) -> Path:
    """Resolve a file path relative or absolute to folder_path.

    Converts relative paths to absolute using folder_path as the base.
    Absolute paths are used as-is. Raises FileNotFoundError if the
    resolved path does not exist.

    Parameters
    ----------
    raw_path : str | Path
        Path to resolve (relative or absolute).
    folder_path : Path
        Base folder for resolving relative paths.

    Returns
    -------
    Path
        Resolved absolute path.

    Raises
    ------
    FileNotFoundError
        If the resolved path does not exist.

    See Also
    --------
    :func:`create_data_files_from_records` : Uses this function for batch
        path resolution.
    """
    path = Path(raw_path)
    resolved = path if path.is_absolute() else folder_path / path

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")

    return resolved
