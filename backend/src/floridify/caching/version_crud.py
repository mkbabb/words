"""CRUD operations for version management.

Provides standalone functions for listing, deleting, and pruning
versioned data entries.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from beanie import PydanticObjectId

from ..utils.logging import get_logger
from .core import GlobalCacheManager, get_global_cache
from .filesystem import FilesystemBackend
from .keys import generate_resource_key as _generate_cache_key
from .models import (
    BaseVersionedData,
    CacheNamespace,
    ResourceType,
)

logger = get_logger(__name__)


async def list_versions(
    resource_id: str,
    resource_type: ResourceType,
    get_model_class: Callable[[ResourceType], type[BaseVersionedData]],
) -> list[BaseVersionedData]:
    """List all versions of a resource.

    Args:
        resource_id: Resource identifier
        resource_type: Type of resource
        get_model_class: Callable that maps resource_type to model class

    Returns:
        List of all versioned data objects for the resource
    """
    model_class = get_model_class(resource_type)
    results = await model_class.find(
        {"resource_id": resource_id, "resource_type": resource_type.value}
    ).to_list()
    return results


async def delete_version(
    resource_id: str,
    resource_type: ResourceType,
    version: str,
    get_model_class: Callable[[ResourceType], type[BaseVersionedData]],
    get_namespace: Callable[[ResourceType], CacheNamespace],
    cache: GlobalCacheManager[FilesystemBackend] | None = None,
) -> tuple[bool, GlobalCacheManager[FilesystemBackend] | None]:
    """Delete a specific version.

    Args:
        resource_id: Resource identifier
        resource_type: Type of resource
        version: Version string to delete
        get_model_class: Callable that maps resource_type to model class
        get_namespace: Callable that maps resource_type to cache namespace
        cache: Optional cache manager instance (will be initialized if None)

    Returns:
        Tuple of (success: bool, cache: updated cache instance)
    """
    model_class = get_model_class(resource_type)
    result = await model_class.find_one(
        {
            "resource_id": resource_id,
            "resource_type": resource_type.value,
            "version_info.version": version,
        },
    )

    if result:
        # Update version chain
        if result.version_info.superseded_by:
            next_version = await model_class.get(result.version_info.superseded_by)
            if next_version:
                next_version.version_info.supersedes = result.version_info.supersedes
                await next_version.save()

        if result.version_info.supersedes:
            prev_version = await model_class.get(result.version_info.supersedes)
            if prev_version:
                prev_version.version_info.superseded_by = result.version_info.superseded_by
                if result.version_info.is_latest:
                    prev_version.version_info.is_latest = True
                await prev_version.save()

        await result.delete()

        # Clear cache for both specific version and latest version
        namespace = get_namespace(resource_type)
        if cache is None:
            cache = await get_global_cache()

        # CRITICAL FIX #8: Use consistent hashing for cache keys
        # Clear specific version cache
        version_cache_key = _generate_cache_key(resource_type, resource_id, "v", version)
        await cache.delete(namespace, version_cache_key)

        # Clear latest version cache if this was marked as latest
        if result.version_info.is_latest:
            latest_cache_key = _generate_cache_key(resource_type, resource_id)
            await cache.delete(namespace, latest_cache_key)

        logger.info(f"Deleted {resource_type.value} '{resource_id}' v{version}")
        return True, cache

    return False, cache


async def prune_old_versions(
    max_age_days: int = 90,
    keep_minimum: int = 10,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Delete old non-latest versions older than max_age_days, keeping at least keep_minimum.

    For each (resource_id, resource_type) group, versions are sorted by creation time.
    The latest version is always preserved. Among non-latest versions, those older than
    max_age_days are candidates for deletion, but at least keep_minimum total versions
    (including the latest) are always retained.

    Args:
        max_age_days: Delete non-latest versions older than this many days.
        keep_minimum: Always keep at least this many versions per resource.
        dry_run: If True, return counts without actually deleting.

    Returns:
        Dict with pruning statistics: total_deleted, resources_affected, details.
    """
    from datetime import UTC, datetime, timedelta as td

    cutoff = datetime.now(UTC) - td(days=max_age_days)
    collection = BaseVersionedData.get_pymongo_collection()

    # Find all distinct (resource_id, resource_type) pairs
    pipeline = [
        {"$group": {"_id": {"resource_id": "$resource_id", "resource_type": "$resource_type"}}},
    ]
    groups = await collection.aggregate(pipeline).to_list(length=None)

    total_deleted = 0
    resources_affected = 0
    details: list[dict[str, Any]] = []

    for group in groups:
        resource_id = group["_id"]["resource_id"]
        resource_type = group["_id"]["resource_type"]

        # Get all versions for this resource, sorted newest first
        versions = (
            await collection.find(
                {
                    "resource_id": resource_id,
                    "resource_type": resource_type,
                },
            )
            .sort([("version_info.created_at", -1), ("_id", -1)])
            .to_list(length=None)
        )

        total_versions = len(versions)
        if total_versions <= keep_minimum:
            # Already at or below minimum -- skip entirely
            continue

        # Identify candidates for deletion:
        # - Must NOT be the latest version
        # - Must be older than cutoff
        # - Must leave at least keep_minimum versions remaining
        candidates_to_delete: list[PydanticObjectId] = []
        for version_doc in versions:
            # Never delete the latest version
            vi = version_doc.get("version_info", {})
            if vi.get("is_latest", False):
                continue

            created_at = vi.get("created_at")
            if created_at is not None and created_at < cutoff:
                candidates_to_delete.append(version_doc["_id"])

        # Ensure we keep at least keep_minimum versions
        max_deletable = total_versions - keep_minimum
        if max_deletable <= 0:
            continue

        ids_to_delete = candidates_to_delete[:max_deletable]

        if not ids_to_delete:
            continue

        if not dry_run:
            # Also clean up delta chains: any version that has delta_base_id
            # pointing to a deleted version needs to be handled.
            # For safety, we skip deleting versions that are delta bases for others.
            delta_base_ids = set()
            dependent_cursor = collection.find(
                {"version_info.delta_base_id": {"$in": ids_to_delete}},
                {"version_info.delta_base_id": 1},
            )
            async for dep_doc in dependent_cursor:
                base_id = dep_doc.get("version_info", {}).get("delta_base_id")
                if base_id:
                    delta_base_ids.add(base_id)

            # Remove delta bases from deletion candidates
            safe_ids = [did for did in ids_to_delete if did not in delta_base_ids]

            if safe_ids:
                result = await collection.delete_many({"_id": {"$in": safe_ids}})
                deleted_count = result.deleted_count
            else:
                deleted_count = 0
        else:
            deleted_count = len(ids_to_delete)

        if deleted_count > 0:
            total_deleted += deleted_count
            resources_affected += 1
            details.append(
                {
                    "resource_id": resource_id,
                    "resource_type": resource_type,
                    "versions_before": total_versions,
                    "versions_deleted": deleted_count,
                    "versions_after": total_versions - deleted_count,
                }
            )

    return {
        "total_deleted": total_deleted,
        "resources_affected": resources_affected,
        "max_age_days": max_age_days,
        "keep_minimum": keep_minimum,
        "dry_run": dry_run,
        "details": details,
    }
