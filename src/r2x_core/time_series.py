"""Time series utils."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, NamedTuple, cast
from uuid import UUID

from loguru import logger

if TYPE_CHECKING:
    from .translation_rules import TranslationContext


class TransferStats(NamedTuple):
    """Class that represents the transfer status of time series."""

    transferred: int
    updated: int
    children_remapped: int


def transfer_time_series_metadata(context: TranslationContext) -> TransferStats:
    """Transfer time series metadata for target system."""
    uuid_map = context.target_system._component_mgr._components_by_uuid

    logger.info(f"Transferring time series metadata for {len(uuid_map)} components")

    with (
        context.source_system.open_time_series_store(mode="r") as src_store,
        context.target_system.open_time_series_store(mode="a") as tgt_store,
    ):
        src_metadata = src_store.metadata_conn
        tgt_metadata = tgt_store.metadata_conn
        src_associations = context.source_system._component_mgr._associations._con

        uuid_to_type = {str(uuid): type(comp).__name__ for uuid, comp in uuid_map.items()}

        tgt_metadata.execute("CREATE TEMP TABLE target_components (uuid TEXT PRIMARY KEY, type TEXT)")
        tgt_metadata.executemany("INSERT INTO target_components VALUES (?, ?)", list(uuid_to_type.items()))

        child_parent_rows = src_associations.execute("""
            SELECT component_uuid, attached_component_uuid
            FROM component_associations
        """).fetchall()

        child_remapping = [
            (child_uuid, parent_uuid, type(uuid_map[UUID(parent_uuid)]).__name__)
            for child_uuid, parent_uuid in child_parent_rows
            if parent_uuid in uuid_to_type
        ]

        # Always create child_mapping table (even if empty) to avoid SQL errors
        tgt_metadata.execute(
            "CREATE TEMP TABLE child_mapping (child_uuid TEXT, parent_uuid TEXT, parent_type TEXT)"
        )
        if child_remapping:
            tgt_metadata.executemany("INSERT INTO child_mapping VALUES (?, ?, ?)", child_remapping)

        src_rows = src_metadata.execute("SELECT * FROM time_series_associations").fetchall()

        if src_rows:
            placeholders = ",".join(["?"] * len(src_rows[0]))
            tgt_metadata.executemany(
                f"INSERT OR IGNORE INTO time_series_associations VALUES ({placeholders})", src_rows
            )
            transferred = len(src_rows)
        else:
            transferred = 0

        result = tgt_metadata.execute("""
            WITH owner_resolution AS (
                SELECT
                    ts.owner_uuid as original_uuid,
                    COALESCE(tc_direct.uuid, cm.parent_uuid) as resolved_uuid,
                    COALESCE(tc_direct.type, cm.parent_type) as resolved_type
                FROM time_series_associations ts
                LEFT JOIN target_components tc_direct ON ts.owner_uuid = tc_direct.uuid
                LEFT JOIN child_mapping cm ON ts.owner_uuid = cm.child_uuid
                WHERE tc_direct.uuid IS NOT NULL OR cm.parent_uuid IS NOT NULL
            )
            UPDATE time_series_associations
            SET
                owner_uuid = (SELECT resolved_uuid FROM owner_resolution WHERE original_uuid = time_series_associations.owner_uuid),
                owner_type = (SELECT resolved_type FROM owner_resolution WHERE original_uuid = time_series_associations.owner_uuid)
            WHERE owner_uuid IN (SELECT original_uuid FROM owner_resolution)
        """)

        updated = result.rowcount
        children_remapped = len(child_remapping) if child_remapping else 0

    # We need to rebuild the time series to have the objects in memory.
    loader = cast(
        Callable[[], None],
        context.target_system._time_series_mgr._metadata_store._load_metadata_into_memory,
    )
    loader()

    logger.info(
        f"Time series metadata: {transferred} transferred, {updated} updated, {children_remapped} children remapped"
    )

    return TransferStats(transferred=transferred, updated=updated, children_remapped=children_remapped)
