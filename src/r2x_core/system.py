"""R2X Core System class - subclass of infrasys.System with R2X-specific functionality."""

import csv
from collections.abc import Callable
from os import PathLike
from pathlib import Path
from typing import Any

from infrasys.component import Component
from infrasys.system import System as InfrasysSystem
from loguru import logger


class System(InfrasysSystem):
    """R2X Core System class extending infrasys.System.

    This class extends infrasys.System to provide R2X-specific functionality
    for data model translation and system construction. It maintains compatibility
    with infrasys while adding convenience methods for component export and
    system manipulation.

    The System serves as the central data store for all components (buses, generators,
    branches, etc.) and their associated time series data. It provides methods for:
    - Adding and retrieving components
    - Managing time series data
    - Serialization/deserialization (JSON)
    - Exporting components to various formats (CSV, records, etc.)

    Parameters
    ----------
    name : str
        Unique identifier for the system.
    description : str, optional
        Human-readable description of the system.
    auto_add_composed_components : bool, default True
        If True, automatically add composed components (e.g., when adding a Generator
        with a Bus, automatically add the Bus to the system if not already present).

    Attributes
    ----------
    name : str
        System identifier.
    description : str
        System description.

    Examples
    --------
    Create a basic system:

    >>> from r2x_core import System
    >>> system = System(name="MySystem", description="Test system")

    Create a system with auto-add for composed components:

    >>> system = System(name="MySystem", auto_add_composed_components=True)

    Add components to the system:

    >>> from infrasys import Component
    >>> # Assuming you have component classes defined
    >>> bus = ACBus(name="Bus1", voltage=230.0)
    >>> system.add_component(bus)

    Serialize and deserialize:

    >>> system.to_json("system.json")
    >>> loaded_system = System.from_json("system.json")

    See Also
    --------
    infrasys.system.System : Parent class providing core system functionality
    r2x_core.parser.BaseParser : Parser framework for building systems

    Notes
    -----
    This class maintains backward compatibility with the legacy r2x.api.System
    while being simplified for r2x-core's focused scope. The main differences:

    - Legacy r2x.api.System: Full-featured with CSV export, filtering, version tracking
    - r2x-core.System: Lightweight wrapper focusing on system construction and serialization

    The r2x-core.System delegates most functionality to infrasys.System, adding only
    R2X-specific enhancements as needed.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize R2X Core System.

        Parameters
        ----------
        *args
            Positional arguments passed to infrasys.System.
        **kwargs
            Keyword arguments passed to infrasys.System.
        """
        super().__init__(*args, **kwargs)
        logger.debug("Created R2X Core System: {}", self.name)

    def __str__(self) -> str:
        """Return string representation of the system.

        Returns
        -------
        str
            String showing system name and component count.
        """
        num_components = self._components.get_num_components()
        return f"System(name={self.name}, components={num_components})"

    def __repr__(self) -> str:
        """Return detailed string representation.

        Returns
        -------
        str
            Same as __str__().
        """
        return str(self)

    def to_json(
        self,
        filename: Path | str,
        overwrite: bool = False,
        indent: int | None = None,
        data: Any = None,
    ) -> None:
        """Serialize system to JSON file.

        Parameters
        ----------
        filename : Path or str
            Output JSON file path.
        overwrite : bool, default False
            If True, overwrite existing file. If False, raise error if file exists.
        indent : int, optional
            JSON indentation level. If None, uses compact format.
        data : optional
            Additional data to include in serialization.

        Returns
        -------
        None

        Raises
        ------
        FileExistsError
            If file exists and overwrite=False.

        Examples
        --------
        >>> system.to_json("output/system.json", overwrite=True, indent=2)

        See Also
        --------
        from_json : Load system from JSON file
        """
        logger.info("Serializing system '{}' to {}", self.name, filename)
        return super().to_json(filename, overwrite=overwrite, indent=indent, data=data)

    @classmethod
    def from_json(
        cls,
        filename: Path | str,
        upgrade_handler: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> "System":
        """Deserialize system from JSON file.

        Parameters
        ----------
        filename : Path or str
            Input JSON file path.
        upgrade_handler : Callable, optional
            Function to handle data model version upgrades.
        **kwargs
            Additional keyword arguments passed to infrasys deserialization.

        Returns
        -------
        System
            Deserialized system instance.

        Raises
        ------
        FileNotFoundError
            If file does not exist.
        ValueError
            If JSON format is invalid.

        Examples
        --------
        >>> system = System.from_json("input/system.json")

        With version upgrade handling:

        >>> def upgrade_v1_to_v2(data):
        ...     # Custom upgrade logic
        ...     return data
        >>> system = System.from_json("old_system.json", upgrade_handler=upgrade_v1_to_v2)

        See Also
        --------
        to_json : Serialize system to JSON file
        """
        logger.info("Deserializing system from {}", filename)
        return super().from_json(filename=filename, upgrade_handler=upgrade_handler, **kwargs)  # type: ignore

    def components_to_records(
        self,
        filter_func: Callable[[Component], bool] | None = None,
        fields: list[str] | None = None,
        key_mapping: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Convert system components to a list of dictionaries (records).

        This method retrieves components from the system and converts them to
        dictionary records, with optional filtering, field selection, and key mapping.

        Parameters
        ----------
        filter_func : Callable, optional
            Function to filter components. Should accept a component and return bool.
            If None, converts all components in the system.
        fields : list, optional
            List of field names to include. If None, includes all fields.
        key_mapping : dict, optional
            Dictionary mapping component field names to record keys.

        Returns
        -------
        list[dict[str, Any]]
            List of component records as dictionaries.

        Examples
        --------
        Get all components as records:

        >>> records = system.components_to_records()

        Get only generators:

        >>> from my_components import Generator
        >>> records = system.components_to_records(
        ...     filter_func=lambda c: isinstance(c, Generator)
        ... )

        Get specific fields with renamed keys:

        >>> records = system.components_to_records(
        ...     fields=["name", "voltage"],
        ...     key_mapping={"voltage": "voltage_kv"}
        ... )

        See Also
        --------
        export_components_to_csv : Export components to CSV file
        get_components : Retrieve components by type with filtering
        """
        # Get all components, applying filter if provided
        components = list(self.get_components(Component, filter_func=filter_func))

        # Convert to records
        records = [c.model_dump() for c in components]

        # Filter fields if specified
        if fields is not None:
            records = [{k: v for k, v in record.items() if k in fields} for record in records]

        # Apply key mapping if provided
        if key_mapping is not None:
            records = [{key_mapping.get(k, k): v for k, v in record.items()} for record in records]

        return records

    def export_components_to_csv(
        self,
        file_path: PathLike[str],
        filter_func: Callable[[Component], bool] | None = None,
        fields: list[str] | None = None,
        key_mapping: dict[str, str] | None = None,
        **dict_writer_kwargs: Any,
    ) -> None:
        """Export all components or filtered components to CSV file.

        This method exports components from the system to a CSV file. You can
        optionally provide a filter function to select specific components.

        Parameters
        ----------
        file_path : PathLike
            Output CSV file path.
        filter_func : Callable, optional
            Function to filter components. Should accept a component and return bool.
            If None, exports all components in the system.
        fields : list, optional
            List of field names to include. If None, exports all fields.
        key_mapping : dict, optional
            Dictionary mapping component field names to CSV column names.
        **dict_writer_kwargs
            Additional arguments passed to csv.DictWriter.

        Examples
        --------
        Export all components:

        >>> system.export_components_to_csv("all_components.csv")

        Export only generators using a filter:

        >>> from my_components import Generator
        >>> system.export_components_to_csv(
        ...     "generators.csv",
        ...     filter_func=lambda c: isinstance(c, Generator)
        ... )

        Export buses with custom filter:

        >>> from my_components import ACBus
        >>> system.export_components_to_csv(
        ...     "high_voltage_buses.csv",
        ...     filter_func=lambda c: isinstance(c, ACBus) and c.voltage > 100
        ... )

        Export with field selection and renaming:

        >>> system.export_components_to_csv(
        ...     "buses.csv",
        ...     filter_func=lambda c: isinstance(c, ACBus),
        ...     fields=["name", "voltage"],
        ...     key_mapping={"voltage": "voltage_kv"}
        ... )

        See Also
        --------
        components_to_records : Convert components to dictionary records
        get_components : Retrieve components by type with filtering
        """
        # Get records using components_to_records method
        records = self.components_to_records(filter_func=filter_func, fields=fields, key_mapping=key_mapping)

        # Fail fast if no records to export
        if not records:
            logger.warning("No components to export")
            return

        # Write to CSV
        fpath = Path(file_path)
        fpath.parent.mkdir(parents=True, exist_ok=True)

        with open(fpath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=records[0].keys(), **dict_writer_kwargs)
            writer.writeheader()
            writer.writerows(records)
        logger.info("Exported {} components to {}", len(records), fpath)
