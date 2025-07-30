"""Health check endpoints."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...caching.cache_manager import get_cache_manager
from ...constants import Language
from ...core.search_pipeline import get_search_engine
from ...storage.mongodb import _ensure_initialized, get_storage
from ...utils.logging import get_logger
logger = get_logger(__name__)
router = APIRouter()

# Track service start time
_start_time = time.perf_counter()


class HealthCheckResponse(BaseModel):
    """Response for health check endpoints."""
    
    status: str = Field(..., description="Service status")
    version: str | None = Field(None, description="API version")
    services: dict[str, str] = Field(default_factory=dict, description="Sub-service statuses")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Performance metrics")
    timestamp: str = Field(..., description="Check timestamp")
    
    @property
    def is_healthy(self) -> bool:
        """Check if all services are healthy."""
        return self.status == "healthy" and all(
            status == "healthy" for status in self.services.values()
        )


# Use the standardized HealthCheckResponse from core but extend if needed
class HealthResponse(HealthCheckResponse):
    """Extended health check response with specific service details."""
    
    database: str = Field(..., description="Database connection status")
    search_engine: str = Field(..., description="Search engine status")
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")
    uptime_seconds: int = Field(..., ge=0, description="Service uptime in seconds")
    connection_pool: dict[str, Any] = Field(
        default_factory=dict, description="MongoDB connection pool stats"
    )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Get service health status.

    Returns status of all major components:
    - Database connectivity
    - Search engine initialization
    - Cache system performance
    - Service uptime
    """
    # Check database and get connection pool stats
    database_status = "disconnected"
    connection_pool_stats = {}
    try:
        await _ensure_initialized()
        storage = await get_storage()

        # Check connection health
        if await storage.ensure_healthy_connection():
            database_status = "connected"
        else:
            database_status = "unhealthy"

        # Get connection pool statistics
        connection_pool_stats = storage.get_connection_pool_stats()

    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        connection_pool_stats = {"status": "error", "error": str(e)}

    # Check search engine
    search_status = "uninitialized"
    try:
        search_engine = await get_search_engine([Language.ENGLISH])
        if search_engine._initialized:
            search_status = "initialized"
    except Exception as e:
        logger.warning(f"Search engine health check failed: {e}")

    # Check cache system
    cache_hit_rate = 0.0
    try:
        cache_manager = get_cache_manager()
        stats = cache_manager.get_stats()

        # Calculate hit rate from memory entries vs expired entries
        memory_entries = stats.get("memory_entries", 0)
        expired_entries = stats.get("expired_memory_entries", 0)

        if memory_entries > 0:
            cache_hit_rate = max(0.0, (memory_entries - expired_entries) / memory_entries)
    except Exception as e:
        logger.warning(f"Cache health check failed: {e}")

    # Calculate uptime
    uptime_seconds = int(time.perf_counter() - _start_time)

    # Determine overall status
    overall_status = "healthy"
    if database_status != "connected" or search_status != "initialized":
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version="0.1.0",  # Version from pyproject.toml
        timestamp=datetime.utcnow().isoformat(),
        services={
            "database": database_status,
            "search_engine": search_status,
            "cache": "healthy" if cache_hit_rate > 0 else "degraded",
        },
        metrics={
            "cache_hit_rate": cache_hit_rate,
            "uptime_seconds": uptime_seconds,
        },
        database=database_status,
        search_engine=search_status,
        cache_hit_rate=cache_hit_rate,
        uptime_seconds=uptime_seconds,
        connection_pool=connection_pool_stats,
    )
