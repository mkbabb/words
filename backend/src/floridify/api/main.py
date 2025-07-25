"""FastAPI application for Floridify dictionary service."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..utils.logging import setup_logging
from .middleware import CacheHeadersMiddleware, LoggingMiddleware
from .routers import (
    atomic_updates,
    batch,
    corpus,
    definitions,
    examples,
    facts,
    health,
    lookup,
    search,
    suggestions,
    synonyms,
    words,
)

# Configure logging for the application
setup_logging("DEBUG")

# Create FastAPI application
app = FastAPI(
    title="Floridify Dictionary API",
    description="AI-enhanced dictionary with semantic search",
    version="0.1.0",
)

# Add middleware (order matters - CORS should be outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:8080",
        "https://words.babb.dev",
        "https://www.words.babb.dev"
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
app.include_router(synonyms.router, prefix=API_V1_PREFIX, tags=["synonyms"])
app.include_router(suggestions.router, prefix=API_V1_PREFIX, tags=["suggestions"])
app.include_router(facts.router, prefix=API_V1_PREFIX, tags=["facts"])
app.include_router(definitions.router, prefix=f"{API_V1_PREFIX}/definitions", tags=["definitions"])
app.include_router(examples.router, prefix=API_V1_PREFIX, tags=["examples"])
app.include_router(batch.router, prefix=f"{API_V1_PREFIX}/batch", tags=["batch"])
app.include_router(atomic_updates.router, prefix=f"{API_V1_PREFIX}/atomic", tags=["atomic"])
app.include_router(words.router, prefix=f"{API_V1_PREFIX}/words", tags=["words"])

# Health check remains at root for monitoring
app.include_router(health.router, prefix="", tags=["health"])


@app.get("/api")
async def api_info():
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
