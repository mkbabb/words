"""FastAPI application for Floridify dictionary service."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..ai import get_definition_synthesizer, get_openai_connector
from ..caching.core import get_global_cache, shutdown_global_cache
from ..storage.mongodb import get_storage
from ..utils.logging import setup_logging
from .middleware import CacheHeadersMiddleware, LoggingMiddleware
from .middleware.auth import ClerkAuthMiddleware
from .middleware.rate_limiting import RateLimitMiddleware
from .routers import (
    ai,
    audio,
    cache,
    config,
    corpus,
    database,
    definitions,
    examples,
    health,
    images,
    lookup,
    providers,
    search,
    suggestions,
    word_versions,
    wordlist_reviews,
    wordlist_search,
    wordlist_words,
    wordlists,
    words,
    # wotd_main,
    # wotd_ml,
)

# Configure logging from environment
setup_logging(os.getenv("LOG_LEVEL", "INFO"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Initialize database and resources on startup, cleanup on shutdown."""
    # Startup
    try:
        # Warn about auth configuration in production
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production" and not os.getenv("CLERK_DOMAIN"):
            print("⚠️  CLERK_DOMAIN not set — auth middleware will skip JWT validation")

        # Initialize MongoDB storage
        await get_storage()
        print("✅ MongoDB storage initialized successfully")

        # Initialize AI components (singletons)
        get_openai_connector()
        print("✅ OpenAI connector initialized successfully")

        get_definition_synthesizer()
        print("✅ Definition synthesizer initialized successfully")

        # Start background TTL cleanup task (runs every 5 minutes)
        cache = await get_global_cache()
        cache.start_ttl_cleanup_task(interval_seconds=60.0)
        print("✅ Background TTL cleanup task started (interval=60s)")

    except Exception as e:
        print(f"❌ Application initialization failed: {e}")
        raise

    yield

    # Shutdown
    print("🔄 Shutting down...")
    try:
        cache = await get_global_cache()
        await cache.stop_ttl_cleanup_task()
        await shutdown_global_cache()
        print("✅ Cache cleanup task stopped and cache shut down")
    except Exception as e:
        print(f"⚠️ Cache shutdown error: {e}")


# Create FastAPI application
app = FastAPI(
    title="Floridify Dictionary API",
    description="AI-enhanced dictionary with semantic search",
    version="0.1.0",
    lifespan=lifespan,
)

# Add middleware (order matters - CORS should be outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "https://words.babb.dev",
        "https://www.words.babb.dev",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "Accept", "Cache-Control", "If-None-Match"],
    expose_headers=["ETag", "Cache-Control", "X-Process-Time", "X-Request-ID"],
    max_age=3600,  # Cache preflight responses for 1 hour
)
app.add_middleware(CacheHeadersMiddleware)  # Add cache headers before logging
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)  # Rate limiting after auth
app.add_middleware(ClerkAuthMiddleware)  # Auth check (innermost - runs first)

# Register global exception handlers
from .middleware.exception_handlers import register_exception_handlers

register_exception_handlers(app)


# API versioning configuration
API_V1_PREFIX = "/api/v1"

# Include routers with versioned API prefix
app.include_router(lookup, prefix=API_V1_PREFIX, tags=["lookup"])
app.include_router(search, prefix=API_V1_PREFIX, tags=["search"])
# Note: Old synonyms endpoint removed - now handled by /ai/synthesize/synonyms
app.include_router(suggestions, prefix=API_V1_PREFIX, tags=["suggestions"])
app.include_router(ai, prefix=API_V1_PREFIX, tags=["ai"])
app.include_router(definitions, prefix=f"{API_V1_PREFIX}/definitions", tags=["definitions"])
app.include_router(examples, prefix=API_V1_PREFIX, tags=["examples"])
app.include_router(words, prefix=f"{API_V1_PREFIX}/words", tags=["words"])
app.include_router(word_versions, prefix=f"{API_V1_PREFIX}/words", tags=["word-versions"])
app.include_router(audio, prefix=API_V1_PREFIX, tags=["audio"])
app.include_router(images, prefix=f"{API_V1_PREFIX}/images", tags=["images"])

# Wordlist routers
app.include_router(wordlists, prefix=f"{API_V1_PREFIX}/wordlists", tags=["wordlists"])
app.include_router(wordlist_words, prefix=f"{API_V1_PREFIX}/wordlists", tags=["wordlists"])
app.include_router(wordlist_reviews, prefix=f"{API_V1_PREFIX}/wordlists", tags=["wordlists"])
app.include_router(wordlist_search, prefix=f"{API_V1_PREFIX}/wordlists", tags=["wordlists"])

# New comprehensive routers for isomorphism with CLI
app.include_router(database, prefix=API_V1_PREFIX, tags=["database"])
app.include_router(providers, prefix=API_V1_PREFIX, tags=["providers"])
app.include_router(corpus, prefix=API_V1_PREFIX, tags=["corpus"])
app.include_router(cache, prefix=API_V1_PREFIX, tags=["cache"])
app.include_router(config, prefix=API_V1_PREFIX, tags=["config"])

# Health check remains at root for monitoring
app.include_router(health, prefix="", tags=["health"])


@app.get("/api")
async def api_info() -> dict[str, Any]:
    """API version information."""
    return {
        "name": "Floridify Dictionary API",
        "current_version": "v1",
        "versions": {
            "v1": {
                "status": "stable",
                "base_url": "/api/v1",
                "docs_url": "/api/v1/docs",
            },
        },
    }
