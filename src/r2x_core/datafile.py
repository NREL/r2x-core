"""Data Model for datafiles."""

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


class DataFile(BaseModel):
    r"""DataModel class for data files.

    This class defines how individual data files should be read, processed, and filtered
    within the R2X framework. It uses Pydantic for validation and automatic type conversion.

    Parameters
    ----------
    name : str
        Unique identifier for this file mapping configuration.
    fpath : pathlib.Path, optional
        Absolute or absolute-like path to the data file. Must exist and have a
        supported extension (.csv, .tsv, .h5, .hdf5, .json, .xml).
        Exactly one of fpath, relative_fpath, or glob must be specified.
    relative_fpath : pathlib.Path | str, optional
        Path to the data file relative to a DataStore's folder_path. Useful when
        multiple files are stored in a base directory and you want to specify only
        the relative path. Must have a supported extension.
        Exactly one of fpath, relative_fpath, or glob must be specified.
    glob : str, optional
        Glob pattern to locate a file by extension (e.g., '*.xml', 'data_?.csv').
        Must contain at least one wildcard character (*, ?, [, ]).
        Pattern must match exactly one file.
        Exactly one of fpath, relative_fpath, or glob must be specified.
    description : str, optional
        Human-readable description of the data file contents.
    is_input : bool, default True
        Whether this file represents input data (True) or output data (False).
    is_optional : bool, default False
        Whether the file is optional. If True, missing files will not raise errors.
    is_timeseries : bool, default False
        Whether the file contains time series data. Time series files must use
        formats that support time series (CSV, TSV, HDF5, Parquet). Files marked
        as time series with unsupported formats will raise a validation error.
    units : str, optional
        Physical units for numeric data in the file (e.g., "MW", "$/MWh").
    reader_function : Callable[[Path], Any], optional
        Custom reader function (callable) to use instead of the default file type reader.
        The function should accept a Path argument and return the loaded data.
    column_mapping : dict[str, str], optional
        Mapping of original column names to desired column names as {old_name: new_name}.
    index_columns : list[str], optional
        List of column names to treat as index columns when selecting data.
    value_columns : list[str], optional
        List of column names containing the actual data values to retain.
    drop_columns : list[str], optional
        List of column names to remove from the data after loading.
    column_schema : dict[str, str], optional
        Schema defining column names and types as {column_name: type_string}.
        Used when the input file lacks headers. Type strings: "string", "int", "float".
    filter_by : dict[str, Any], optional
        Row-level filters to apply as {column_name: value_or_list}.
        Supports special values "solve_year" and "weather_year".
    pivot_on : str, optional
        Column name to pivot the data on (for reshaping operations).
    aggregate_function : str, optional
        Function name for aggregating data after pivoting.

    Attributes
    ----------
    file_type : FileFormat
        Computed property that returns the appropriate FileFormat class based on
        the file extension. Automatically determined from `fpath.suffix`.

    Examples
    --------
    Basic file mapping for a CSV file:

    >>> mapping = DataFile(
    ...     name="generation_data",
    ...     fpath="outputs/gen_h.csv",
    ...     description="Hourly generation by technology",
    ...     units="MWh",
    ... )
    >>> mapping.file_type
    <class 'TableFormat'>

    File mapping with column operations:

    >>> mapping = DataFile(
    ...     name="capacity_data",
    ...     fpath="inputs/cap_tech.csv",
    ...     column_mapping={"old_tech": "technology", "cap_mw": "capacity"},
    ...     drop_columns=["unused_col"],
    ...     filter_by={"year": 2030, "region": ["CA", "TX"]},
    ... )

    File mapping with custom reader function:

    >>> from plexosdb import PlexosDB
    >>> mapping = DataFile(
    ...     name="plexos_data",
    ...     fpath="model.xml",
    ...     reader_function=PlexosDB.from_xml,  # Callable function
    ... )

    File mapping with relative path (when used with DataStore):

    >>> mapping = DataFile(
    ...     name="generation_data",
    ...     relative_fpath="outputs/gen_h.csv",  # Relative to DataStore folder_path
    ...     description="Hourly generation by technology",
    ... )

    File mapping with glob pattern (when filename is unknown):

    >>> mapping = DataFile(
    ...     name="model_file",
    ...     glob="*.xml",  # Finds any XML file in directory
    ...     description="User-renamed model file",
    ... )

    Optional file with lambda reader:

    >>> mapping = DataFile(
    ...     name="simple_text",
    ...     fpath="data.txt",
    ...     is_optional=True,
    ...     reader_function=lambda p: p.read_text().strip().split(r"\n"),
    ...     column_schema={"line": "string"},
    ... )

    Notes
    -----
    - Exactly one of `fpath`, `relative_fpath`, or `glob` must be specified
    - `fpath` must be an absolute or existing path that is validated immediately
    - `relative_fpath` is validated when combined with DataStore.folder_path
    - Glob patterns must contain at least one wildcard (*, ?, [, ]) and must match exactly one file
    - File type is inferred from the file extension (or from glob pattern ending)
    - The `file_type` property is computed automatically and excluded from serialization
    - Column operations are applied in order: mapping → dropping → schema → filtering

    See Also
    --------
    FileFormat: Class for file formats.
    DataStore : Container for managing multiple DataFile instances
    DataReader : Service class for actually loading and processing the files
    """

    name: Annotated[str, Field(description="Name of the mapping.")]
    fpath: Annotated[
        FilePath | None,
        AfterValidator(validate_file_extension),
        Field(description="Absolute file path (must exist). Use this for absolute paths."),
    ] = None
    relative_fpath: Annotated[
        Path | str | None,
        Field(
            description="Relative file path (relative to DataStore.folder_path). Use this for paths relative to a base folder."
        ),
    ] = None
    glob: Annotated[
        str | None,
        AfterValidator(validate_glob_pattern),
        Field(description="Glob pattern to locate file (e.g., '*.xml'). Must match exactly one file."),
    ] = None
    description: Annotated[str | None, Field(description="Description of the data file")] = None
    is_input: Annotated[bool, Field(description="Whether this is an input file")] = True
    is_optional: Annotated[bool, Field(description="Whether this file is optional")] = False
    is_timeseries: Annotated[
        bool,
        Field(
            description="Whether this file contains time series data. "
            "Time series files must use supported formats (CSV, HDF5, Parquet)."
        ),
    ] = False
    units: Annotated[str | None, Field(description="Units for the data")] = None
    reader_function: Annotated[
        Callable[[Path], Any] | None,
        Field(description="Custom reader function (callable) that takes a Path and returns data"),
    ] = None
    reader_kwargs: Annotated[
        dict[str, Any] | None,
        Field(description="Key-Word arguments passed to the reader function."),
    ] = None
    column_mapping: Annotated[dict[str, str] | None, Field(description="Column name mappings")] = None
    key_mapping: Annotated[
        dict[str, str] | None,
        Field(description="Keys name mappings (applicable for JSON files)."),
    ] = None
    index_columns: Annotated[list[str] | None, Field(description="Index column names")] = None
    value_columns: Annotated[list[str] | None, Field(description="Value column names")] = None
    drop_columns: Annotated[list[str] | None, Field(description="Columns to drop")] = None
    column_schema: Annotated[
        dict[str, str] | None,
        Field(description="User-defined column names/types (used if input data has no column headers)"),
    ] = None
    filter_by: Annotated[
        dict[str, Any] | None,
        Field(description="Column filters as {column_name: value}"),
    ] = None
    pivot_on: Annotated[str | None, Field(description="Column to pivot on")] = None
    aggregate_function: Annotated[str | None, Field(description="Aggregation function")] = None

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_path_sources(self) -> "DataFile":
        """Validate that exactly one of fpath, relative_fpath, or glob is specified.

        Returns
        -------
        DataFile
            The validated instance

        Raises
        ------
        ValueError
            If none of fpath/relative_fpath/glob are specified, or more than one are specified
        """
        paths_set = sum([self.fpath is not None, self.relative_fpath is not None, self.glob is not None])

        if paths_set == 0:
            msg = "Exactly one of 'fpath', 'relative_fpath', or 'glob' must be specified"
            raise ValueError(msg)

        if paths_set > 1:
            msg = (
                "Multiple path sources specified. "
                "Use exactly one of: 'fpath' (absolute path), 'relative_fpath' (relative path), or 'glob' (pattern matching)."
            )
            raise ValueError(msg)

        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def file_type(self) -> FileFormat:
        """Computed file type based on file extension.

        Returns
        -------
        FileFormat
            FileFormat instance determined from file extension

        Raises
        ------
        ValueError
            If the file extension is not supported or if marked as time series
            but the file type doesn't support time series data.
        """
        if self.fpath is not None:
            extension = self.fpath.suffix.lower()
        elif self.relative_fpath is not None:
            # Convert to Path if string
            rel_path = (
                Path(self.relative_fpath) if isinstance(self.relative_fpath, str) else self.relative_fpath
            )
            extension = rel_path.suffix.lower()
        elif self.glob is not None:
            # Extract extension from glob pattern (e.g., '*.xml' -> '.xml')
            # Takes the final extension after the last dot
            if "." in self.glob:
                extension = "." + self.glob.rsplit(".", 1)[-1].rstrip("*?[]")
            else:
                msg = "Cannot determine file type from glob pattern without extension"
                raise ValueError(msg)
        else:
            msg = "Either fpath, relative_fpath, or glob must be set to determine file type"
            raise ValueError(msg)

        file_type_class = EXTENSION_MAPPING.get(extension)

        if file_type_class is None:  # pragma: no cover
            # Defensive check - should be caught by field validator
            msg = f"Unsupported file extension: {extension}"
            raise ValueError(msg)

        # If marked as time series, verify the file type supports it
        if self.is_timeseries and not file_type_class.supports_timeseries:
            msg = f"File type {file_type_class.__name__} does not support time series data."
            raise ValueError(msg)

        return file_type_class()


def create_data_files_from_records(
    records: list[dict[str, Any]], folder_path: Path
) -> Result[list[DataFile], list[ValidationError]]:
    """Construct a list of DataFile objects from a list of record dicts.

    Ensures:
    - `fpath` exists and is resolvable relative to folder_fpath
    - resolution happens before model validation
    - all ValidationError instances are collected
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
    """Resolve a relative or absolute raw path."""
    path = Path(raw_path)
    resolved = path if path.is_absolute() else folder_path / path

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")

    return resolved
