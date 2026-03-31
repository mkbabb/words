"""Search-only FastAPI application.

Initializes MongoDB (read-only for corpus polling) and SearchEngineManager.
Does NOT initialize AI connector, TTS, lookup pipeline, CRUD, or user management.
Same Python package as the main app — just a thinner entry point.
"""

import os
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..api.middleware import CacheHeadersMiddleware, LoggingMiddleware
from ..api.middleware.rate_limiting import RateLimitMiddleware
from ..api.routers.search import router as search_router
from ..caching.core import get_global_cache, shutdown_global_cache
from ..core.search_pipeline import get_search_engine_manager
from ..storage.mongodb import get_storage
from ..utils.logging import get_logger, setup_logging

setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

_start_time = time.perf_counter()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Startup: MongoDB + search engine only."""
    try:
        await get_storage()
        logger.info("MongoDB storage initialized")

        cache = await get_global_cache()
        cache.start_ttl_cleanup_task(interval_seconds=60.0)
        logger.info("Cache TTL cleanup started")

        manager = get_search_engine_manager()
        await manager.start_background_init()
        logger.info("Search engine initialization started in background")

    except Exception as e:
        logger.error(f"Search service initialization failed: {e}")
        raise

    yield

    try:
        cache = await get_global_cache()
        await cache.stop_ttl_cleanup_task()
        await shutdown_global_cache()
    except Exception as e:
        logger.warning(f"Cache shutdown error: {e}")


app = FastAPI(
    title="Floridify Search Service",
    description="Standalone search cascade (trie, fuzzy, semantic)",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Internal service — nginx handles external CORS
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_middleware(CacheHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Mount search routes
API_V1_PREFIX = "/api/v1"
app.include_router(search_router, prefix=API_V1_PREFIX, tags=["search"])

# Health check
health_router = APIRouter()


@health_router.get("/health")
async def health_check() -> dict[str, Any]:
    """Search service health check."""
    manager = get_search_engine_manager()
    engine_ready = manager._engine is not None

    return {
        "status": "healthy" if engine_ready else "initializing",
        "service": "search",
        "search_engine": "ready" if engine_ready else "loading",
        "uptime_seconds": round(time.perf_counter() - _start_time, 1),
    }


app.include_router(health_router, tags=["health"])
