"""Cache management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...caching.core import CacheNamespace, get_global_cache
from ...caching.manager import get_version_manager
from ...models.parameters import CacheClearParams, CacheStatsParams
from ...models.responses import CacheStatsResponse, SuccessResponse
from ...utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def parse_cache_stats_params(
    namespace: str | None = None,
    include_hit_rate: bool = True,
    include_size: bool = True,
) -> CacheStatsParams:
    """Parse cache stats parameters."""
    return CacheStatsParams(
        namespace=namespace,
        include_hit_rate=include_hit_rate,
        include_size=include_size,
    )


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    params: CacheStatsParams = Depends(parse_cache_stats_params),
) -> CacheStatsResponse:
    """Get cache statistics.

    Returns statistics for all cache namespaces or a specific namespace.
    Includes hit rates, miss rates, and size estimates if requested.
    """
    try:
        cache = await get_global_cache()

        if params.namespace:
            # Get stats for specific namespace
            try:
                namespace_enum = CacheNamespace(params.namespace.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid namespace: {params.namespace}"
                )

            namespace_stats = cache.get_stats(namespace_enum)

            hits = namespace_stats.get("hits", 0)
            misses = namespace_stats.get("misses", 0)
            total_requests = hits + misses

            hit_rate = None
            miss_rate = None
            if params.include_hit_rate and total_requests > 0:
                hit_rate = hits / total_requests
                miss_rate = misses / total_requests

            # Rough size estimation (not exact)
            size_bytes = None
            size_human = None
            if params.include_size:
                memory_items = namespace_stats.get("memory_items", 0)
                # Assume ~1KB per item (very rough)
                size_bytes = memory_items * 1024
                size_human = _format_bytes(size_bytes)

            return CacheStatsResponse(
                namespace=params.namespace,
                total_entries=namespace_stats.get("memory_items", 0),
                hit_rate=hit_rate,
                miss_rate=miss_rate,
                size_bytes=size_bytes,
                size_human=size_human,
            )

        else:
            # Get stats for all namespaces
            all_stats = {}
            total_entries = 0
            total_hits = 0
            total_misses = 0

            for namespace in CacheNamespace:
                namespace_stats = cache.get_stats(namespace)
                hits = namespace_stats.get("hits", 0)
                misses = namespace_stats.get("misses", 0)
                memory_items = namespace_stats.get("memory_items", 0)

                total_entries += memory_items
                total_hits += hits
                total_misses += misses

                all_stats[namespace.value] = {
                    "entries": memory_items,
                    "hits": hits,
                    "misses": misses,
                    "evictions": namespace_stats.get("evictions", 0),
                }

            total_requests = total_hits + total_misses
            hit_rate = None
            miss_rate = None
            if params.include_hit_rate and total_requests > 0:
                hit_rate = total_hits / total_requests
                miss_rate = total_misses / total_requests

            # Total size estimation
            size_bytes = None
            size_human = None
            if params.include_size:
                size_bytes = total_entries * 1024  # Rough estimate
                size_human = _format_bytes(size_bytes)

            return CacheStatsResponse(
                namespace=None,
                total_entries=total_entries,
                hit_rate=hit_rate,
                miss_rate=miss_rate,
                size_bytes=size_bytes,
                size_human=size_human,
                by_namespace=all_stats,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {e!s}")


@router.post("/cache/clear", response_model=SuccessResponse)
async def clear_cache(
    params: CacheClearParams,
) -> SuccessResponse:
    """Clear cache entries.

    Supports:
    - Clearing specific namespace
    - Clearing all namespaces
    - Age-based clearing (older than N days)
    - Dry run mode to preview changes
    """
    try:
        cache = await get_global_cache()

        if params.dry_run:
            # Preview mode - just count what would be cleared
            if params.namespace:
                try:
                    namespace_enum = CacheNamespace(params.namespace.lower())
                except ValueError:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid namespace: {params.namespace}"
                    )

                namespace_stats = cache.get_stats(namespace_enum)
                count = namespace_stats.get("memory_items", 0)

                return SuccessResponse(
                    message=f"Would clear {count} entries from {params.namespace} (dry run)",
                    data={"namespace": params.namespace, "count": count, "dry_run": True},
                )
            else:
                # Count all entries
                total_count = 0
                for namespace in CacheNamespace:
                    namespace_stats = cache.get_stats(namespace)
                    total_count += namespace_stats.get("memory_items", 0)

                return SuccessResponse(
                    message=f"Would clear {total_count} total entries from all namespaces (dry run)",
                    data={"count": total_count, "dry_run": True},
                )

        # Actual clearing
        if params.namespace:
            try:
                namespace_enum = CacheNamespace(params.namespace.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid namespace: {params.namespace}"
                )

            await cache.clear_namespace(namespace_enum)
            return SuccessResponse(
                message=f"Cleared cache namespace: {params.namespace}",
                data={"namespace": params.namespace},
            )
        else:
            # Clear all namespaces
            await cache.clear()
            return SuccessResponse(
                message="Cleared all cache namespaces",
                data={"cleared": "all"},
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e!s}")


class VersionPruneParams(BaseModel):
    """Parameters for version pruning."""

    max_age_days: int = Field(
        default=90,
        ge=1,
        le=3650,
        description="Delete non-latest versions older than this many days",
    )
    keep_minimum: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Always keep at least this many versions per resource",
    )
    dry_run: bool = Field(
        default=False,
        description="Preview what would be deleted without making changes",
    )


@router.post("/cache/prune", response_model=SuccessResponse)
async def prune_old_versions(
    params: VersionPruneParams,
) -> SuccessResponse:
    """Prune old non-latest versions from the versioned data store.

    Deletes versions older than max_age_days while always keeping at least
    keep_minimum versions per resource. The latest version is never deleted.
    Delta base versions (referenced by other versions) are also preserved.

    Supports dry_run mode to preview changes before executing.
    """
    try:
        manager = get_version_manager()
        result = await manager.prune_old_versions(
            max_age_days=params.max_age_days,
            keep_minimum=params.keep_minimum,
            dry_run=params.dry_run,
        )

        action = "Would delete" if params.dry_run else "Deleted"
        message = (
            f"{action} {result['total_deleted']} old versions "
            f"across {result['resources_affected']} resources "
            f"(max_age={params.max_age_days}d, keep_min={params.keep_minimum})"
        )
        if params.dry_run:
            message += " (dry run)"

        return SuccessResponse(
            message=message,
            data=result,
        )

    except Exception as e:
        logger.error(f"Failed to prune versions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to prune versions: {e!s}")


class DiskUsageResponse(BaseModel):
    """Response for disk usage endpoint."""

    volume_bytes: int = Field(..., description="Total bytes used by L2 disk cache")
    volume_human: str = Field(..., description="Human-readable size string")
    item_count: int = Field(..., description="Number of items in L2 disk cache")
    hits: int = Field(..., description="L2 cache hits since startup")
    misses: int = Field(..., description="L2 cache misses since startup")


@router.get("/cache/disk-usage", response_model=DiskUsageResponse)
async def get_cache_disk_usage() -> DiskUsageResponse:
    """Get L2 disk cache consumption.

    Returns the total disk space used by the filesystem-backed L2 cache,
    the number of stored items, and basic hit/miss statistics from diskcache.
    """
    try:
        cache = await get_global_cache()
        l2_stats = await cache.l2_backend.get_stats()

        volume = l2_stats.get("size", 0)
        return DiskUsageResponse(
            volume_bytes=volume,
            volume_human=_format_bytes(volume),
            item_count=l2_stats.get("count", 0),
            hits=l2_stats.get("hits", 0),
            misses=l2_stats.get("misses", 0),
        )
    except Exception as e:
        logger.error(f"Failed to get disk usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get disk usage: {e!s}")


def _format_bytes(bytes_count: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"
