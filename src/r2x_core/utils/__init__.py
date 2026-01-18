"""Utils for r2x-core."""

from ._component import components_to_records, export_components_to_csv
from ._rules import (
    _as_attr_source,
    _build_target_fields,
    _create_target_component,
    _evaluate_rule_filter,
    _make_attr_getter,
    _resolve_component_type,
    _sort_rules_by_dependencies,
    build_component_kwargs,
)
from ._system import _iter_system_components
from ._upgrader import (
    UpgradeStep,
    UpgradeType,
    run_upgrade_step,
    shall_we_upgrade,
)
from .file_operations import audit_file, backup_folder, resolve_glob_pattern
from .overrides import override_dictionary
from .parser import create_component
from .validation import (
    filter_kwargs_by_signatures,
    filter_valid_kwargs,
    validate_file_extension,
    validate_glob_pattern,
)

__all__ = [
    "UpgradeStep",
    "UpgradeType",
    "_as_attr_source",
    "_build_target_fields",
    "_create_target_component",
    "_evaluate_rule_filter",
    "_iter_system_components",
    "_make_attr_getter",
    "_resolve_component_type",
    "_sort_rules_by_dependencies",
    "audit_file",
    "backup_folder",
    "build_component_kwargs",
    "components_to_records",
    "create_component",
    "export_components_to_csv",
    "filter_kwargs_by_signatures",
    "filter_valid_kwargs",
    "override_dictionary",
    "resolve_glob_pattern",
    "run_upgrade_step",
    "shall_we_upgrade",
    "validate_file_extension",
    "validate_glob_pattern",
]
