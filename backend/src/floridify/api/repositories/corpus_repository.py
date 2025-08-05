"""Repository for corpus operations."""

from typing import Any

from pydantic import BaseModel, Field

from ...search.corpus import get_corpus_cache


class CorpusCreate(BaseModel):
    """Schema for creating a corpus."""

    words: list[str] = Field(..., min_length=1, description="Words to include")
    phrases: list[str] = Field(default_factory=list, description="Phrases to include")
    name: str = Field(default="", description="Corpus name")
    ttl_hours: float = Field(default=2.0, gt=0, le=24, description="TTL in hours")


class CorpusSearchParams(BaseModel):
    """Parameters for corpus search."""

    query: str = Field(..., min_length=1, description="Search query")
    max_results: int = Field(default=20, ge=1, le=100, description="Max results")
    min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Min score")
    semantic: bool = Field(default=False, description="Enable semantic search")
    semantic_weight: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Weight for semantic results"
    )


class CorpusRepository:
    """Repository for corpus operations."""

    def __init__(self) -> None:
        self._cache: Any = None

    async def _get_cache(self) -> Any:
        """Get corpus cache instance."""
        if self._cache is None:
            self._cache = await get_corpus_cache()
        return self._cache

    async def create(self, data: CorpusCreate) -> dict[str, Any]:
        """Create a new corpus."""
        cache = await self._get_cache()

        corpus_id = cache.create_corpus(
            words=data.words,
            phrases=data.phrases,
            name=data.name,
            ttl_hours=data.ttl_hours,
        )

        # Get metadata
        metadata = cache.get_corpus_info(corpus_id)
        if not metadata:
            raise ValueError("Failed to create corpus")

        return {
            "corpus_id": corpus_id,
            "name": metadata.name,
            "word_count": metadata.word_count,
            "phrase_count": metadata.phrase_count,
            "created_at": metadata.created_at.isoformat(),
            "expires_at": metadata.expires_at.isoformat(),
        }

    async def get(self, corpus_id: str) -> dict[str, Any] | None:
        """Get corpus metadata."""
        cache = await self._get_cache()
        metadata = cache.get_corpus_info(corpus_id)

        if not metadata:
            return None

        return {
            "corpus_id": metadata.corpus_id,
            "name": metadata.name,
            "created_at": metadata.created_at.isoformat(),
            "expires_at": metadata.expires_at.isoformat(),
            "word_count": metadata.word_count,
            "phrase_count": metadata.phrase_count,
            "search_count": metadata.search_count,
            "last_accessed": metadata.last_accessed.isoformat(),
        }

    async def get_by_name(self, name: str) -> str | None:
        """Get corpus ID by name if it exists."""
        cache = await self._get_cache()
        corpora = cache.list_corpora()

        for corpus in corpora:
            if corpus.name == name:
                corpus_id: str = corpus.corpus_id
                return corpus_id

        return None

    async def search(self, corpus_id: str, params: CorpusSearchParams) -> dict[str, Any]:
        """Search within a corpus."""
        cache = await self._get_cache()

        result = await cache.search_corpus(
            corpus_id=corpus_id,
            query=params.query,
            max_results=params.max_results,
            min_score=params.min_score,
            semantic=params.semantic,
        )
        return dict(result)

    async def list_all(self) -> list[dict[str, Any]]:
        """List all active corpora."""
        cache = await self._get_cache()
        corpora = cache.list_corpora()

        return [
            {
                "corpus_id": corpus.corpus_id,
                "name": corpus.name,
                "created_at": corpus.created_at.isoformat(),
                "expires_at": corpus.expires_at.isoformat(),
                "word_count": corpus.word_count,
                "phrase_count": corpus.phrase_count,
                "search_count": corpus.search_count,
                "last_accessed": corpus.last_accessed.isoformat(),
            }
            for corpus in corpora
        ]

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        cache = await self._get_cache()
        stats = cache.get_stats()
        return dict(stats)

    async def create_from_wordlist(
        self, words: list[str], name: str = "", ttl_hours: float = 2.0
    ) -> str:
        """Create corpus from word list."""
        data = CorpusCreate(
            words=words,
            phrases=[],
            name=name,
            ttl_hours=ttl_hours,
        )

        result = await self.create(data)
        corpus_id: str = result["corpus_id"]
        return corpus_id
