"""FastAPI application for Floridify dictionary service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..ai import get_definition_synthesizer, get_openai_connector
from ..constants import Language
from ..search.language import get_language_search
from ..storage.mongodb import get_storage
from ..text.processor import get_text_processor
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
    images,
    lookup,
    search,
    suggestions,
    synth_entries,
    word_of_the_day,
    words,
    wordlists,
)

# Configure logging for the application
setup_logging("DEBUG")


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Initialize database and resources on startup, cleanup on shutdown."""
    # Startup
    try:
        # Initialize MongoDB storage
        storage = await get_storage()
        print("✅ MongoDB storage initialized successfully")
        
        # Initialize language search engine (singleton)
        language_search = await get_language_search([Language.ENGLISH])
        print("✅ Language search engine initialized successfully")
        
        # Initialize text processor (singleton)
        text_processor = get_text_processor()
        print("✅ Text processor initialized successfully")
        
        # Initialize AI components (singletons)
        ai_connector = get_openai_connector()
        print("✅ OpenAI connector initialized successfully")
        
        definition_synthesizer = get_definition_synthesizer()
        print("✅ Definition synthesizer initialized successfully")
        
    except Exception as e:
        print(f"❌ Application initialization failed: {e}")
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
app.include_router(wordlists.router, prefix=f"{API_V1_PREFIX}/wordlists", tags=["wordlists"])
app.include_router(word_of_the_day.router, prefix=f"{API_V1_PREFIX}/word-of-day", tags=["word-of-day"])
app.include_router(audio.router, prefix=API_V1_PREFIX, tags=["audio"])
app.include_router(images.router, prefix=f"{API_V1_PREFIX}/images", tags=["images"])
app.include_router(synth_entries.router, prefix=f"{API_V1_PREFIX}/synth-entries", tags=["synth-entries"])

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
