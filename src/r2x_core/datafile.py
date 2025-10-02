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
    computed_field,
)

from .file_types import EXTENSION_MAPPING, FileType
from .utils import (
    validate_file_extension,
)


class DataFile(BaseModel):
    r"""DataModel class for data files.

    This class defines how individual data files should be read, processed, and filtered
    within the R2X framework. It uses Pydantic for validation and automatic type conversion.

    Parameters
    ----------
    name : str
        Unique identifier for this file mapping configuration.
    fpath : pathlib.Path
        Path to the data file relative to the ReEDS case directory. Must have a
        supported extension (.csv, .tsv, .h5, .hdf5, .json, .xml).
    description : str, optional
        Human-readable description of the data file contents.
    is_input : bool, default True
        Whether this file represents input data (True) or output data (False).
    is_optional : bool, default False
        Whether the file is optional. If True, missing files will not raise errors.
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
    file_type : FileType
        Computed property that returns the appropriate FileType class based on
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
    <class 'TableFile'>

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
    - File paths are validated to ensure they have supported extensions
    - The `file_type` property is computed automatically and excluded from serialization
    - Column operations are applied in order: mapping → dropping → schema → filtering

    See Also
    --------
    FileType: Class for file types.
    DataStore : Container for managing multiple DataFile instances
    DataReader : Service class for actually loading and processing the files
    """

    name: Annotated[str, Field(description="Name of the mapping.")]
    fpath: Annotated[
        FilePath,
        AfterValidator(validate_file_extension),
        Field(description="File path (must exist)"),
    ]
    description: Annotated[
        str | None, Field(description="Description of the data file")
    ] = None
    is_input: Annotated[bool, Field(description="Whether this is an input file")] = True
    is_optional: Annotated[bool, Field(description="Whether this file is optional")] = (
        False
    )
    units: Annotated[str | None, Field(description="Units for the data")] = None
    reader_function: Annotated[
        Callable[[Path], Any] | None,
        Field(
            description="Custom reader function (callable) that takes a Path and returns data"
        ),
    ] = None
    column_mapping: Annotated[
        dict[str, str] | None, Field(description="Column name mappings")
    ] = None
    index_columns: Annotated[
        list[str] | None, Field(description="Index column names")
    ] = None
    value_columns: Annotated[
        list[str] | None, Field(description="Value column names")
    ] = None
    drop_columns: Annotated[list[str] | None, Field(description="Columns to drop")] = (
        None
    )
    column_schema: Annotated[
        dict[str, str] | None,
        Field(
            description="User-defined column names/types (used if input data has no column headers)"
        ),
    ] = None
    filter_by: Annotated[
        dict[str, Any] | None,
        Field(description="Column filters as {column_name: value}"),
    ] = None
    pivot_on: Annotated[str | None, Field(description="Column to pivot on")] = None
    aggregate_function: Annotated[
        str | None, Field(description="Aggregation function")
    ] = None

    model_config = ConfigDict(frozen=True)

    @computed_field  # type: ignore[misc]
    @property
    def file_type(self) -> FileType:
        """Computed file type based on file extension.

        Returns
        -------
        type[FileType]
            FileType class determined from file extension
        """
        return EXTENSION_MAPPING[self.fpath.suffix.lower()]()
