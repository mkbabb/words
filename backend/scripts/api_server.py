#!/usr/bin/env python3
"""
Simple API server for the Floridify frontend.
Provides REST endpoints that interface with the existing backend.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from floridify.core.lookup_pipeline import LookupPipeline
from floridify.core.search_manager import SearchManager
from floridify.models.models import SynthesizedDictionaryEntry
from floridify.storage.mongodb import MongoDBStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Floridify API",
    description="AI-Enhanced Dictionary API",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class ApiResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    timestamp: datetime

class SearchResult(BaseModel):
    word: str
    score: float
    type: str

class SearchResponse(ApiResponse):
    data: List[SearchResult]

class DefinitionResponse(ApiResponse):
    data: Optional[SynthesizedDictionaryEntry]

class SynonymData(BaseModel):
    word: str
    similarity: float
    partOfSpeech: Optional[str] = None

class ThesaurusEntry(BaseModel):
    word: str
    synonyms: List[SynonymData]
    antonyms: List[SynonymData]

class ThesaurusResponse(ApiResponse):
    data: ThesaurusEntry

class SuggestionsResponse(ApiResponse):
    data: List[str]

# Global instances
lookup_pipeline: Optional[LookupPipeline] = None
search_manager: Optional[SearchManager] = None
storage: Optional[MongoDBStorage] = None

async def initialize_services():
    """Initialize the backend services."""
    global lookup_pipeline, search_manager, storage
    
    try:
        # Initialize MongoDB storage
        storage = MongoDBStorage()
        await storage.connect()
        
        # Initialize search manager
        search_manager = SearchManager()
        await search_manager.initialize()
        
        # Initialize lookup pipeline
        lookup_pipeline = LookupPipeline()
        
        logger.info("Services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    await initialize_services()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if storage:
        await storage.disconnect()

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({
        "success": True,
        "data": {"status": "healthy"},
        "timestamp": datetime.now().isoformat()
    })

@app.get("/api/search/word", response_model=SearchResponse)
async def search_word(q: str = Query(..., description="Search query")):
    """Search for words."""
    try:
        if not search_manager:
            raise HTTPException(status_code=500, detail="Search manager not initialized")
        
        # Perform search using the search manager
        results = await search_manager.search(q)
        
        # Convert results to API format
        search_results = []
        for result in results[:10]:  # Limit to top 10 results
            search_results.append(SearchResult(
                word=result.word,
                score=result.score,
                type=result.search_type
            ))
        
        return SearchResponse(
            success=True,
            data=search_results,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lookup/{word}", response_model=DefinitionResponse)
async def get_definition(word: str):
    """Get word definition."""
    try:
        if not lookup_pipeline:
            raise HTTPException(status_code=500, detail="Lookup pipeline not initialized")
        
        # Use the lookup pipeline to get definition
        entry = await lookup_pipeline.lookup(word)
        
        return DefinitionResponse(
            success=True,
            data=entry,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Definition lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/synonyms/{word}", response_model=ThesaurusResponse)
async def get_synonyms(word: str):
    """Get synonyms and antonyms for a word."""
    try:
        if not search_manager:
            raise HTTPException(status_code=500, detail="Search manager not initialized")
        
        # Get semantic similar words
        similar_words = await search_manager.get_similar_words(word, limit=20)
        
        # Convert to synonym format
        synonyms = []
        for similar_word in similar_words:
            synonyms.append(SynonymData(
                word=similar_word.word,
                similarity=similar_word.score,
                partOfSpeech=getattr(similar_word, 'part_of_speech', None)
            ))
        
        # For now, we don't have antonyms in the backend
        # This would need to be implemented in the AI synthesis
        antonyms = []
        
        thesaurus_entry = ThesaurusEntry(
            word=word,
            synonyms=synonyms,
            antonyms=antonyms
        )
        
        return ThesaurusResponse(
            success=True,
            data=thesaurus_entry,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Synonyms lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    prefix: str = Query(..., description="Search prefix"),
    limit: int = Query(10, description="Maximum number of suggestions")
):
    """Get search suggestions."""
    try:
        if not search_manager:
            raise HTTPException(status_code=500, detail="Search manager not initialized")
        
        # Get suggestions from the search manager
        suggestions = await search_manager.get_suggestions(prefix, limit=limit)
        
        return SuggestionsResponse(
            success=True,
            data=suggestions,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        # Return empty suggestions on error
        return SuggestionsResponse(
            success=True,
            data=[],
            timestamp=datetime.now()
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )