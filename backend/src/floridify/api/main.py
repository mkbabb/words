"""FastAPI application for Floridify dictionary service."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..utils.logging import setup_logging
from .middleware import LoggingMiddleware, CacheHeadersMiddleware
from .routers import corpus, facts, health, lookup, search, suggestions, synonyms

# Configure logging for the application
setup_logging("DEBUG")

# Create FastAPI application
app = FastAPI(
    title="Floridify Dictionary API",
    description="AI-enhanced dictionary with semantic search",
    version="0.1.0",
    root_path="/api",  # Proper proxy awareness for nginx
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

# Include routers - clean paths, versioning handled by nginx/deployment
app.include_router(lookup.router, prefix="", tags=["lookup"])
app.include_router(search.router, prefix="", tags=["search"])
app.include_router(corpus.router, prefix="", tags=["corpus"])
app.include_router(synonyms.router, prefix="", tags=["synonyms"])
app.include_router(suggestions.router, prefix="", tags=["suggestions"])
app.include_router(facts.router, prefix="", tags=["facts"])
app.include_router(health.router, prefix="", tags=["health"])
