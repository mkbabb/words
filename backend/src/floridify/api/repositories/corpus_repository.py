"""Repository for corpus operations."""

from typing import Any

from pydantic import BaseModel, Field

from ...search.core import SearchEngine
from ...search.corpus.manager import get_corpus_manager


class CorpusCreate(BaseModel):
    """Schema for creating a corpus."""

    vocabulary: list[str] = Field(..., min_length=1, description="Vocabulary to include")
    name: str = Field(default="", description="Corpus name")


class CorpusSearchParams(BaseModel):
    """Parameters for corpus search."""

    query: str = Field(..., min_length=1, description="Search query")
    max_results: int = Field(default=20, ge=1, le=100, description="Max results")
    min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Min score")
    semantic: bool = Field(default=False, description="Enable semantic search")


class CorpusRepository:
    """Repository for corpus operations."""

    def __init__(self) -> None:
        self._manager = get_corpus_manager()

    async def create(self, data: CorpusCreate) -> dict[str, Any]:
        """Create a new corpus."""
        corpus = await self._manager.create_corpus(
            corpus_name=data.name,
            vocabulary=data.vocabulary,
        )

        return {
            "corpus_name": corpus.corpus_name,
            "vocabulary_size": len(corpus.vocabulary),
            "vocabulary_hash": corpus.vocabulary_hash,
            "metadata": corpus.metadata,
        }

    async def get(self, corpus_name: str) -> dict[str, Any] | None:
        """Get corpus metadata."""
        metadata = await self._manager.get_corpus_metadata(corpus_name)
        
        if not metadata:
            return None

        return {
            "corpus_name": metadata.corpus_name,
            "vocabulary_hash": metadata.vocabulary_hash,
            "vocabulary_stats": metadata.vocabulary_stats,
            "metadata": metadata.metadata,
        }

    async def search(self, corpus_name: str, params: CorpusSearchParams) -> dict[str, Any]:
        """Search within a corpus."""
        # Create search engine for this corpus
        search_engine = SearchEngine(
            corpus_name=corpus_name,
            min_score=params.min_score,
            semantic=params.semantic,
        )
        
        await search_engine.initialize()

        # Perform search
        results = await search_engine.search(
            query=params.query,
            max_results=params.max_results,
            min_score=params.min_score,
            semantic=params.semantic,
        )

        return {
            "results": [
                {
                    "word": result.word,
                    "score": result.score,
                    "method": result.method.value,
                }
                for result in results
            ],
            "metadata": {
                "corpus_name": corpus_name,
                "query": params.query,
                "result_count": len(results),
                "semantic_enabled": params.semantic,
            },
        }

    async def create_from_wordlist(
        self, vocabulary: list[str], name: str = ""
    ) -> str:
        """Create corpus from vocabulary list."""
        data = CorpusCreate(
            vocabulary=vocabulary,
            name=name,
        )

        result = await self.create(data)
        corpus_name: str = result["corpus_name"]
        return corpus_name