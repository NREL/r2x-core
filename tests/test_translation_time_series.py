"""Validate translation of time series metadata between fixture systems."""

from __future__ import annotations

from fixtures.target_system import NodeComponent

from r2x_core import TranslationContext, apply_rules_to_context
from r2x_core.time_series import transfer_time_series_metadata


def test_time_series_transfer_via_fixture_context(context_example: TranslationContext):
    """Translation applies fixture rules and transfers time series metadata."""
    result = apply_rules_to_context(context_example)

    assert result.time_series_transferred > 0

    target_system = context_example.target_system
    node_components = list(target_system.get_components(NodeComponent))
    assert node_components, "Expected translated NodeComponent instances"

    nodes_with_ts = [node for node in node_components if target_system.has_time_series(node)]
    assert nodes_with_ts, "No NodeComponent received time series metadata"

    for node in nodes_with_ts:
        keys = target_system.list_time_series_keys(node)
        assert keys


def test_time_series_transfer_is_idempotent(context_example: TranslationContext):
    """Re-running metadata transfer does not duplicate associations."""
    first_result = apply_rules_to_context(context_example)

    with context_example.target_system.open_time_series_store(mode="r") as store:
        initial_count = store.metadata_conn.execute(
            "SELECT COUNT(*) FROM time_series_associations"
        ).fetchone()[0]

    second_result = transfer_time_series_metadata(context_example)

    with context_example.target_system.open_time_series_store(mode="r") as store:
        final_count = store.metadata_conn.execute("SELECT COUNT(*) FROM time_series_associations").fetchone()[
            0
        ]

    assert first_result.time_series_transferred == initial_count
    assert second_result.transferred == 0
    assert final_count == initial_count
