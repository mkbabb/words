"""FastAPI application for Floridify dictionary service."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..utils import setup_logging
from .middleware import LoggingMiddleware
from .routers import corpus, facts, health, lookup, search, suggestions, synonyms

# Configure logging for the application
setup_logging("DEBUG")
logging.getLogger("floridify").setLevel(logging.DEBUG)

# Create FastAPI application
app = FastAPI(
    title="Floridify Dictionary API",
    description="AI-enhanced dictionary with semantic search",
    version="0.1.0",
)

# Add middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(lookup.router, prefix="/api/v1", tags=["lookup"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])  
app.include_router(corpus.router, prefix="/api/v1", tags=["corpus"])
app.include_router(synonyms.router, prefix="/api/v1", tags=["synonyms"])
app.include_router(suggestions.router, prefix="/api/v1", tags=["suggestions"])
app.include_router(facts.router, prefix="/api/v1", tags=["facts"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])
