"""Database administration endpoints (read-only for API security)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...models.parameters import DatabaseStatsParams
from ...models.responses import DatabaseStatsResponse, HealthResponse
from ...storage.mongodb import get_storage
from ...utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def parse_database_stats_params(
    detailed: bool = False,
    include_provider_coverage: bool = True,
    include_storage_size: bool = True,
) -> DatabaseStatsParams:
    """Parse database stats parameters."""
    return DatabaseStatsParams(
        detailed=detailed,
        include_provider_coverage=include_provider_coverage,
        include_storage_size=include_storage_size,
    )


@router.get("/database/stats", response_model=DatabaseStatsResponse)
async def get_database_stats(
    params: DatabaseStatsParams = Depends(parse_database_stats_params),
) -> DatabaseStatsResponse:
    """Get database statistics (read-only).

    Returns comprehensive database statistics including:
    - Total counts for all collections
    - Provider coverage (if enabled)
    - Quality metrics (if detailed mode enabled)
    - Storage size estimates (if enabled)

    Note: Write operations (backup, cleanup, clear) are CLI-only for security.
    """
    try:
        # Ensure storage is initialized
        await get_storage()

        # Get basic counts
        from ...models.dictionary import Definition, DictionaryEntry, Word

        word_count = await Word.count()
        definition_count = await Definition.count()
        entry_count = await DictionaryEntry.count()

        overview = {
            "total_words": word_count,
            "total_definitions": definition_count,
            "total_entries": entry_count,
        }

        # Provider coverage
        provider_coverage = None
        if params.include_provider_coverage:
            # Aggregate definitions by provider
            from ...models.dictionary import Definition

            pipeline = [
                {"$group": {"_id": "$provider", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
            provider_results = []
            async for result in Definition.aggregate(pipeline):
                provider_results.append(result)
            provider_coverage = {
                str(result["_id"]): result["count"]
                for result in provider_results
                if result.get("_id")
            }

        # Quality metrics
        quality_metrics = None
        if params.detailed:
            # Calculate quality metrics
            words_with_definitions = await Word.find(
                {"definition_ids": {"$exists": True, "$ne": []}}
            ).count()

            quality_metrics = {
                "words_with_definitions": words_with_definitions,
                "words_with_definitions_pct": (
                    (words_with_definitions / word_count * 100) if word_count > 0 else 0
                ),
                "avg_definitions_per_word": (
                    definition_count / word_count if word_count > 0 else 0
                ),
            }

        # Storage size (estimation)
        storage_size = None
        if params.include_storage_size:
            # Rough estimation based on document counts
            # Average sizes: Word ~0.5KB, Definition ~2KB, Entry ~5KB
            estimated_bytes = (word_count * 500) + (definition_count * 2000) + (entry_count * 5000)
            estimated_mb = estimated_bytes / (1024 * 1024)

            storage_size = {
                "estimated_bytes": estimated_bytes,
                "estimated_mb": f"{estimated_mb:.2f}",
                "note": "Rough estimation based on average document sizes",
            }

        return DatabaseStatsResponse(
            overview=overview,
            provider_coverage=provider_coverage,
            quality_metrics=quality_metrics,
            storage_size=storage_size,
        )

    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {e!s}")


@router.get("/database/health", response_model=HealthResponse)
async def get_database_health() -> HealthResponse:
    """Check database connection health."""
    try:
        # Ensure storage is initialized
        await get_storage()

        # Simple ping to check connection
        from ...models.dictionary import Word

        count = await Word.count()

        components = {
            "mongodb": {
                "status": "healthy",
                "connected": True,
                "collections_accessible": True,
                "sample_count": count,
            }
        }

        return HealthResponse(
            status="healthy",
            components=components,
        )

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        components = {
            "mongodb": {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }
        }
        return HealthResponse(
            status="unhealthy",
            components=components,
        )
