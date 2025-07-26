"""FastAPI application for Floridify dictionary service."""

from __future__ import annotations
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..storage.mongodb import get_storage
from ..utils.logging import setup_logging
from .middleware import CacheHeadersMiddleware, LoggingMiddleware
from .routers import (
    ai,
    audio,
    batch,
    corpus,
    definitions,
    examples,
    facts,
    health,
    lookup,
    search,
    suggestions,
    words,
)

# Configure logging for the application
setup_logging("DEBUG")


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Initialize database and resources on startup, cleanup on shutdown."""
    # Startup
    try:
        storage = await get_storage()
        print("✅ MongoDB storage initialized successfully")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    print("🔄 Shutting down...")


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
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["ETag", "Cache-Control", "X-Process-Time", "X-Request-ID"],
)
app.add_middleware(CacheHeadersMiddleware)  # Add cache headers before logging
app.add_middleware(LoggingMiddleware)

# API versioning configuration
API_V1_PREFIX = "/api/v1"

# Include routers with versioned API prefix
app.include_router(lookup.router, prefix=API_V1_PREFIX, tags=["lookup"])
app.include_router(search.router, prefix=API_V1_PREFIX, tags=["search"])
app.include_router(corpus.router, prefix=API_V1_PREFIX, tags=["corpus"])
# Old synonyms endpoint removed - now handled by /ai/synthesize/synonyms
app.include_router(suggestions.router, prefix=API_V1_PREFIX, tags=["suggestions"])
app.include_router(ai.router, prefix=API_V1_PREFIX, tags=["ai"])
app.include_router(facts.router, prefix=API_V1_PREFIX, tags=["facts"])
app.include_router(definitions.router, prefix=f"{API_V1_PREFIX}/definitions", tags=["definitions"])
app.include_router(examples.router, prefix=API_V1_PREFIX, tags=["examples"])
app.include_router(batch.router, prefix=f"{API_V1_PREFIX}/batch", tags=["batch"])
app.include_router(words.router, prefix=f"{API_V1_PREFIX}/words", tags=["words"])
app.include_router(audio.router, prefix=API_V1_PREFIX, tags=["audio"])

# Health check remains at root for monitoring
app.include_router(health.router, prefix="", tags=["health"])


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
            }
        },
    }
