"""Delta chain management for versioned data.

Handles conversion of full snapshots to delta-compressed versions and
reconstruction of full content from delta chains.
"""

from __future__ import annotations

from typing import Any

from ..utils.logging import get_logger
from .config import DELTA_CONFIG
from .delta import apply_delta, compute_delta
from .models import (
    DELTA_ELIGIBLE_TYPES,
    BaseVersionedData,
    ResourceType,
)
from .version_chains import parse_version

logger = get_logger(__name__)


async def convert_to_delta(
    old_version: BaseVersionedData,
    new_version: BaseVersionedData,
    resource_type: ResourceType,
) -> None:
    """Convert an old version's content from full snapshot to delta.

    The delta stores only the differences needed to reconstruct the old
    version from the new version (which is always a full snapshot).

    Skips conversion if:
    - Resource type is not delta-eligible (binary types)
    - Old version is at a snapshot interval boundary
    - Old version has no inline content
    """
    if resource_type not in DELTA_ELIGIBLE_TYPES:
        return

    # Check if this version should remain a snapshot (every Nth version)
    version_parts = parse_version(old_version.version_info.version)
    version_num = version_parts.patch
    if version_num % DELTA_CONFIG.snapshot_interval == 0:
        logger.debug(f"Keeping v{old_version.version_info.version} as snapshot (interval boundary)")
        return

    # Only convert inline content (external content is too complex for delta)
    old_content = old_version.content_inline
    new_content = new_version.content_inline
    if old_content is None or new_content is None:
        return

    # Compute and store delta
    delta = compute_delta(old_content, new_content)
    if not delta:
        return  # Identical content, nothing to do

    # Replace old version's content with the delta
    collection = BaseVersionedData.get_pymongo_collection()
    await collection.update_one(
        {"_id": old_version.id},
        {
            "$set": {
                "content_inline": delta,
                "version_info.storage_mode": "delta",
                "version_info.delta_base_id": new_version.id,
            }
        },
    )

    logger.debug(
        f"Converted v{old_version.version_info.version} to delta "
        f"(base: v{new_version.version_info.version})"
    )


async def reconstruct_from_delta(
    delta_version: BaseVersionedData,
    resource_type: ResourceType,
    get_model_class: Any,
) -> dict[str, Any] | None:
    """Reconstruct full content for a delta-stored version.

    Walks the delta_base_id chain until hitting a full snapshot,
    then applies deltas in reverse order to reconstruct the target version.

    Args:
        delta_version: The version stored as a delta
        resource_type: Type of resource
        get_model_class: Callable that maps resource_type to model class

    Returns:
        Reconstructed content dict, or None if chain is broken
    """
    model_class = get_model_class(resource_type)

    # Collect delta chain: walk from delta_version toward the nearest snapshot
    chain: list[BaseVersionedData] = [delta_version]
    current = delta_version
    safety = DELTA_CONFIG.max_chain_length

    while current.version_info.storage_mode == "delta" and safety > 0:
        base_id = current.version_info.delta_base_id
        if base_id is None:
            logger.error(
                f"Broken delta chain: v{current.version_info.version} has no delta_base_id"
            )
            return None

        base_version = await model_class.get(base_id)
        if base_version is None:
            logger.error(
                f"Broken delta chain: base {base_id} not found for v{current.version_info.version}"
            )
            return None

        chain.append(base_version)
        current = base_version
        safety -= 1

    if safety <= 0:
        logger.error(
            f"Delta chain exceeded max length ({DELTA_CONFIG.max_chain_length}) "
            f"for {delta_version.resource_id}"
        )
        return None

    # The last element in chain is the snapshot base
    snapshot = chain[-1]
    if snapshot.content_inline is None:
        logger.error(f"Snapshot base v{snapshot.version_info.version} has no inline content")
        return None

    # Apply deltas from snapshot toward the target version
    # chain = [target_delta, ..., intermediate_delta, snapshot]
    # We apply deltas from second-to-last back to first
    chain_length = len(chain) - 1  # Exclude the snapshot itself
    result = dict(snapshot.content_inline)
    for delta_ver in reversed(chain[:-1]):
        if delta_ver.content_inline is None:
            logger.error(f"Delta v{delta_ver.version_info.version} has no content")
            return None
        result = apply_delta(result, delta_ver.content_inline)

    # Auto-resnapshot: if chain was long, save reconstructed as new snapshot
    # to prevent unbounded delta chain traversal on subsequent reads
    if chain_length > 20:
        try:
            delta_version.content_inline = result
            delta_version.version_info.storage_mode = "snapshot"
            delta_version.version_info.delta_base_id = None
            await delta_version.save()
            logger.info(
                f"Auto-resnapshotted v{delta_version.version_info.version} "
                f"(chain was {chain_length} deep)"
            )
        except Exception as e:
            logger.warning(f"Auto-resnapshot failed (non-fatal): {e}")

    return result
