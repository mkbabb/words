"""Cache management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...caching.core import CacheNamespace, get_global_cache
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


def _format_bytes(bytes_count: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"
