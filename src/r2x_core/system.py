"""R2X Core System class - subclass of infrasys.System with R2X-specific functionality."""

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
    auto_add_composed_components : bool, default False
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
        return super().from_json(
            filename=filename, upgrade_handler=upgrade_handler, **kwargs
        )  # type: ignore

    def export_component_to_csv(
        self,
        component: type[Component],
        fields: list[str] | None = None,
        filter_func: Callable[[Component], bool] | None = None,
        fpath: PathLike[str] | None = None,
        key_mapping: dict[str, str] | None = None,
        unnest_key: str = "name",
        **dict_writer_kwargs: Any,
    ) -> list[dict[str, Any]] | None:
        """Export component data to CSV file.

        This method extracts component data, optionally filters and transforms it,
        and writes it to a CSV file. Useful for exporting system data for analysis
        or use in other tools.

        Parameters
        ----------
        component : type[Component]
            Component class to export (e.g., ACBus, Generator).
        fields : list, optional
            List of field names to include. If None, exports all fields.
        filter_func : Callable, optional
            Function to filter components. Should accept a component and return bool.
        fpath : PathLike, optional
            Output CSV file path. If None, returns data without writing.
        key_mapping : dict, optional
            Dictionary mapping component field names to CSV column names.
        unnest_key : str, default "name"
            Field name to use when unnesting nested objects.
        **dict_writer_kwargs
            Additional arguments passed to csv.DictWriter.

        Returns
        -------
        None or list[dict]
            If fpath is None, returns list of dictionaries. Otherwise writes to file.

        Examples
        --------
        Export all buses:

        >>> system.export_component_to_csv(ACBus, fpath="buses.csv")

        Export filtered generators with custom fields:

        >>> system.export_component_to_csv(
        ...     Generator,
        ...     fields=["name", "active_power", "bus"],
        ...     filter_func=lambda g: g.active_power > 100,
        ...     fpath="large_generators.csv"
        ... )

        See Also
        --------
        to_records : Convert system components to dictionary records
        infrasys.system.System.get_components : Retrieve components by type

        Notes
        -----
        This method is inspired by the legacy r2x.api.System.export_component_to_csv
        but simplified for r2x-core's use cases.
        """
        logger.debug("Exporting {} components to CSV", component.__name__)
        # Get components
        components = self.get_components(component)

        # Apply filter if provided
        if filter_func is not None:
            components = [c for c in components if filter_func(c)]

        # Convert to records
        records = [c.model_dump() for c in components]

        # Filter fields if specified
        if fields is not None:
            records = [
                {k: v for k, v in record.items() if k in fields} for record in records
            ]

        # Apply key mapping if provided
        if key_mapping is not None:
            records = [
                {key_mapping.get(k, k): v for k, v in record.items()}
                for record in records
            ]

        # Write to CSV if path provided
        if fpath is not None:
            import csv

            fpath = Path(fpath)
            fpath.parent.mkdir(parents=True, exist_ok=True)

            if records:
                with open(fpath, "w", newline="") as f:
                    writer = csv.DictWriter(
                        f, fieldnames=records[0].keys(), **dict_writer_kwargs
                    )
                    writer.writeheader()
                    writer.writerows(records)
                logger.info(
                    "Exported {} {} to {}", len(records), component.__name__, fpath
                )
            else:
                logger.warning("No components to export for {}", component.__name__)
            return None
        else:
            return records
