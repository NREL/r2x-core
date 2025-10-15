"""R2X Core System class - subclass of infrasys.System with R2X-specific functionality."""

import csv
import sys
import tempfile
from collections.abc import Callable
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any

import orjson
from infrasys.component import Component
from infrasys.system import System as InfrasysSystem
from infrasys.utils.sqlite import backup
from loguru import logger

from r2x_core import units

if TYPE_CHECKING:
    from r2x_core.upgrader import DataUpgrader


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

    def __init__(
        self,
        base_power: float | None = None,
        *,
        name: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize R2X Core System.

        Parameters
        ----------
        system_base_power : float, optional
            System base power in MVA for per-unit calculations.
            Can be provided as first positional argument or as keyword argument.
            Default is 100.0 MVA if not provided.
        name : str, optional
            Name of the system. If not provided, a default name will be assigned.
        **kwargs
            Additional keyword arguments passed to infrasys.System (e.g., description,
            auto_add_composed_components).

        Examples
        --------
        Various ways to create a system:

        >>> System()  # Uses defaults: name=auto, system_base_power=100.0
        >>> System(200.0)  # Positional: system_base_power=200.0
        >>> System(200.0, name="MySystem")  # Both
        >>> System(name="MySystem")  # Name only
        >>> System(system_base_power=200.0, name="MySystem")  # Both as keywords
        >>> System(name="MySystem", system_base_power=200.0)  # Order doesn't matter

        Notes
        -----
        This method defines the 'system_base' unit in the global Pint registry.
        If you create multiple System instances, the last one's system_base will
        be used for all unit conversions. Existing components will detect the
        change and issue a warning if they access system_base conversions.
        """
        # Pass name and other kwargs to parent
        if name is not None:
            kwargs["name"] = name

        super().__init__(**kwargs)

        # System base power for per-unit calculations (MVA)
        self.base_power = base_power

        # Define or redefine system_base in the shared Pint registry
        # This allows components to convert: device_pu.to('system_base')
        if "system_base" in units.ureg:
            units.ureg.define(f"system_base = {base_power} * MVA")  # overwrite
        else:
            units.ureg.define(f"system_base = {base_power} * MVA")

        logger.debug(
            "Created R2X Core System '{}' with system_base = {} MVA",
            self.name,
            base_power,
        )

    def add_components(self, *components: Component, **kwargs: Any) -> None:
        """Add one or more components to the system and set their _system_base.

        Parameters
        ----------
        *components : Component
            Component(s) to add to the system.
        **kwargs
            Additional keyword arguments passed to parent's add_components.

        Notes
        -----
        If any component is a HasPerUnit model, this method automatically sets
        the component's _system_base attribute for use in system-base per-unit
        display mode.

        Raises
        ------
        ValueError
            If a component already has a different _system_base set.
        """
        # Call parent's add_components first
        super().add_components(*components, **kwargs)

        # Set _system_base on all HasPerUnit components
        for component in components:
            if isinstance(component, units.HasPerUnit):
                existing_base = component._get_system_base()
                if existing_base is not None and existing_base != self.base_power:
                    comp_name = component.name if hasattr(component, "name") else type(component).__name__
                    msg = (
                        f"Component '{comp_name}' already has _system_base={existing_base} MVA "
                        f"but is being added to system with base={self.base_power} MVA. "
                        f"This may indicate the component was previously added to a different system."
                    )
                    raise ValueError(msg)

                component._system_base = self.base_power
                logger.trace(
                    "Set _system_base = {} MVA on component '{}'",
                    self.base_power,
                    component.name if hasattr(component, "name") else type(component).__name__,
                )

    def __str__(self) -> str:
        """Return string representation of the system.

        Returns
        -------
        str
            String showing system name and component count.
        """
        system_str = f"System(name={self.name}"
        num_components = self._components.get_num_components()
        if num_components:
            system_str += f", components={num_components}"
        system_base = self.base_power
        if system_base:
            system_str += f", system_base={system_base}"
        return system_str + ")"

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
        filename: Path | str | None = None,
        overwrite: bool = False,
        indent: int | None = None,
        data: Any = None,
    ) -> None:
        """Serialize system to JSON file or stdout.

        Parameters
        ----------
        filename : Path or str, optional
            Output JSON file path. If None, prints JSON to stdout.
            Note: When writing to stdout, time series are serialized to a temporary
            directory that will be cleaned up automatically.
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
        >>> system.to_json()  # Print to stdout

        See Also
        --------
        from_json : Load system from JSON file
        """
        if filename is None:
            logger.info("Serializing system '{}' to stdout", self.name)
            # Use a temporary directory for time series
            with tempfile.TemporaryDirectory() as tmpdir:
                time_series_dir = Path(tmpdir) / "time_series"
                time_series_dir.mkdir(exist_ok=True)

                # Build the system data dictionary (same as parent class)
                system_data: dict[str, Any] = {
                    "name": self.name,
                    "description": self.description,
                    "uuid": str(self.uuid),
                    "data_format_version": self.data_format_version,
                    "components": [x.model_dump_custom() for x in self._component_mgr.iter_all()],
                    "supplemental_attributes": [
                        x.model_dump_custom() for x in self._supplemental_attr_mgr.iter_all()
                    ],
                    "time_series": {
                        "directory": str(time_series_dir),
                    },
                }
                extra = self.serialize_system_attributes()
                system_data.update(extra)

                if data is None:
                    data = system_data
                else:
                    if "system" not in data:
                        data["system"] = system_data

                # Serialize time series to temporary directory
                backup(self._con, time_series_dir / self.DB_FILENAME)
                self._time_series_mgr.serialize(
                    system_data["time_series"], time_series_dir, db_name=self.DB_FILENAME
                )

                # Serialize to JSON and write to stdout
                if indent is not None:
                    json_bytes = orjson.dumps(data, option=orjson.OPT_INDENT_2)
                else:
                    json_bytes = orjson.dumps(data)

                sys.stdout.buffer.write(json_bytes)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()

                logger.debug("Time series data written to temporary directory (will be cleaned up)")
        else:
            logger.info("Serializing system '{}' to {}", self.name, filename)
            return super().to_json(filename, overwrite=overwrite, indent=indent, data=data)

    @classmethod
    def from_json(
        cls,
        filename: Path | str,
        upgrade_handler: Callable[..., Any] | None = None,
        upgrader: type["DataUpgrader"] | None = None,
        **kwargs: Any,
    ) -> "System":
        """Deserialize system from JSON file.

        Parameters
        ----------
        filename : Path or str
            Input JSON file path.
        upgrade_handler : Callable, optional
            Function to handle data model version upgrades.
        upgrader : type[DataUpgrader], optional
            DataUpgrader subclass to use for system upgrades after deserialization.
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

        With system upgrades:

        >>> from my_plugin.upgrader import MyPluginUpgrader
        >>> system = System.from_json("system.json", upgrader=MyPluginUpgrader)

        See Also
        --------
        to_json : Serialize system to JSON file
        upgrade_data : Phase 1 upgrades (for parser workflow)

        Notes
        -----
        This method applies Phase 2 (SYSTEM) upgrades only. Phase 2 is ONLY for
        cached systems loaded from JSON, NOT for the normal parser workflow.

        If you're building a system from raw data:
        1. Use upgrade_data() first (Phase 1)
        2. Build system with parser
        3. Save with system.to_json()

        If you're loading a cached system:
        1. Use System.from_json(upgrader=...) (Phase 2 applies here)
        """
        logger.info("Deserializing system from {}", filename)
        system: System = super().from_json(filename=filename, upgrade_handler=upgrade_handler, **kwargs)  # type: ignore[assignment]

        # Apply Phase 2 (SYSTEM) upgrades if upgrader is specified
        # This is ONLY for cached systems, not the normal parser workflow
        if upgrader:
            from .upgrader import UpgradeType, apply_upgrades

            # Filter for system upgrades from the upgrader class
            system_steps = [step for step in upgrader.steps if step.upgrade_type == UpgradeType.SYSTEM]

            if system_steps:
                logger.info(
                    "Applying {} system upgrade steps for cached system from upgrader '{}'",
                    len(system_steps),
                    upgrader.__name__,
                )
                upgraded_system, applied_steps = apply_upgrades(
                    system, system_steps, upgrade_type=UpgradeType.SYSTEM
                )
                if applied_steps:
                    logger.info("Applied system upgrades: {}", applied_steps)
                    system = upgraded_system

        # After deserialization, update all HasPerUnit components with system_base
        for component in system.get_components(Component):
            if isinstance(component, units.HasPerUnit):
                component._system_base = system.base_power

        return system

    def serialize_system_attributes(self) -> dict[str, Any]:
        """Serialize R2X-specific system attributes.

        Returns
        -------
        dict[str, Any]
            Dictionary containing system_base_power.
        """
        return {"system_base_power": self.base_power}

    def deserialize_system_attributes(self, data: dict[str, Any]) -> None:
        """Deserialize R2X-specific system attributes.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary containing serialized system attributes.
        """
        if "system_base_power" in data:
            self.base_power = data["system_base_power"]

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
