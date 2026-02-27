"""Shared response models for CLI and API isomorphism.

This module provides unified response models that are used by both the CLI
(when using --json flag) and REST API to ensure consistent data structures
across interfaces.

Design Principles:
- Uniform Structure: Same fields and nesting everywhere
- Type Safety: Full Pydantic validation
- CLI Compatibility: Works with Rich for pretty printing and JSON for scripting
- API Compatibility: Valid FastAPI response models
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field

from .base import Language

if TYPE_CHECKING:
    pass

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model with standard metadata."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2025-01-15T10:30:00Z",
                "version": "v1",
            }
        }
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response generation time",
    )
    version: str = Field(
        default="v1",
        description="API/CLI version",
    )


class SuccessResponse(BaseResponse):
    """Standard success response."""

    status: str = Field(default="success", description="Status indicator")
    message: str = Field(..., description="Success message")
    data: dict[str, Any] | None = Field(None, description="Optional result data")


class ErrorResponse(BaseResponse):
    """Standard error response."""

    status: str = Field(default="error", description="Status indicator")
    error: str = Field(..., description="Error message")
    details: list[dict[str, str]] | None = Field(
        None,
        description="Detailed error information",
    )
    code: str | None = Field(None, description="Error code")


class ListResponse[T](BaseResponse):
    """Standard paginated list response."""

    items: list[T] = Field(..., description="Result items")
    total: int = Field(..., description="Total number of items")
    offset: int = Field(default=0, description="Pagination offset")
    limit: int = Field(default=20, description="Pagination limit")
    has_more: bool = Field(..., description="More items available")

    @property
    def count(self) -> int:
        """Number of items in this response."""
        return len(self.items)


class LookupResponse(BaseResponse):
    """Response for word lookup operations.

    Used by:
    - CLI: `floridify lookup <word> --json`
    - API: `GET /api/v1/lookup/{word}`
    """

    word: str = Field(..., description="The word that was looked up")
    id: str | None = Field(None, description="Entry ID")
    last_updated: datetime | None = Field(None, description="Last update time")
    model_info: dict[str, Any] | None = Field(
        None,
        description="AI model information",
    )
    pronunciation: dict[str, Any] | None = Field(
        None,
        description="Pronunciation data",
    )
    etymology: dict[str, Any] | None = Field(None, description="Etymology data")
    images: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Related images",
    )
    definitions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Word definitions",
    )
    providers_used: list[str] = Field(
        default_factory=list,
        description="Providers consulted",
    )
    cache_hit: bool = Field(default=False, description="Was result cached")


class SearchResponse(BaseResponse):
    """Response for search operations.

    Used by:
    - CLI: `floridify search word <query> --json`
    - API: `GET /api/v1/search?q=<query>`
    """

    query: str = Field(..., description="Original search query")
    results: list[Any] = Field(
        ..., description="Search results"
    )  # SearchResult from ..search.models
    total_found: int = Field(..., description="Total matches")
    languages: list[Language] = Field(..., description="Languages searched")
    mode: str = Field(..., description="Search mode used")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Search metadata (timing, etc)",
    )

    @property
    def has_results(self) -> bool:
        """Check if search found results."""
        return len(self.results) > 0


class WordlistResponse(BaseResponse):
    """Response for wordlist operations.

    Used by:
    - CLI: `floridify wordlist show <name> --json`
    - API: `GET /api/v1/wordlists/{id}`
    """

    id: str = Field(..., description="Wordlist ID")
    name: str = Field(..., description="Wordlist name")
    description: str | None = Field(None, description="Description")
    language: Language = Field(..., description="Primary language")
    word_count: int = Field(..., description="Total words")
    unique_word_count: int = Field(..., description="Unique words")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    tags: list[str] = Field(default_factory=list, description="Tags")
    is_public: bool = Field(default=False, description="Public visibility")
    top_words: list[dict[str, Any]] | None = Field(
        None,
        description="Most frequent words",
    )


class DatabaseStatsResponse(BaseResponse):
    """Response for database statistics.

    Used by:
    - CLI: `floridify database stats --json`
    - API: `GET /api/v1/database/stats`
    """

    overview: dict[str, int] = Field(..., description="Total counts")
    provider_coverage: dict[str, int] | None = Field(
        None,
        description="Counts per provider",
    )
    quality_metrics: dict[str, Any] | None = Field(
        None,
        description="Quality metrics",
    )
    storage_size: dict[str, str] | None = Field(
        None,
        description="Storage size estimates",
    )


class ProviderStatusResponse(BaseResponse):
    """Response for provider status.

    Used by:
    - CLI: `floridify scrape status --json`
    - API: `GET /api/v1/providers/status`
    """

    provider: str = Field(..., description="Provider name")
    available: bool = Field(..., description="Provider availability")
    rate_limit: dict[str, Any] | None = Field(
        None,
        description="Rate limit information",
    )
    cache_stats: dict[str, Any] | None = Field(
        None,
        description="Cache statistics",
    )
    last_request: datetime | None = Field(None, description="Last request time")
    error_rate: float | None = Field(None, description="Recent error rate")


class CorpusResponse(BaseResponse):
    """Response for corpus operations.

    Used by:
    - CLI: `floridify corpus stats <name> --json`
    - API: `GET /api/v1/corpus/{id}`
    """

    id: str = Field(..., description="Corpus ID")
    name: str = Field(..., description="Corpus name")
    language: Language = Field(..., description="Primary language")
    corpus_type: str = Field(..., description="Corpus type")
    vocabulary_size: int = Field(..., description="Total vocabulary")
    unique_words: int = Field(..., description="Unique words")
    has_semantic: bool = Field(default=False, description="Has semantic index")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    description: str | None = Field(None, description="Description")
    statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional statistics",
    )

    @computed_field
    @property
    def search_count(self) -> int:
        """Number of searches performed on this corpus."""
        return self.statistics.get("search_count", 0) if self.statistics else 0

    @computed_field
    @property
    def last_accessed(self) -> datetime | None:
        """Last time this corpus was accessed for search."""
        if self.statistics and "last_accessed" in self.statistics:
            return self.statistics["last_accessed"]
        return None


class CacheStatsResponse(BaseResponse):
    """Response for cache statistics.

    Used by:
    - CLI: `floridify cache stats --json`
    - API: `GET /api/v1/cache/stats`
    """

    namespace: str | None = Field(None, description="Cache namespace")
    total_entries: int = Field(..., description="Total cached entries")
    hit_rate: float | None = Field(None, description="Cache hit rate")
    miss_rate: float | None = Field(None, description="Cache miss rate")
    size_bytes: int | None = Field(None, description="Total size in bytes")
    size_human: str | None = Field(None, description="Human-readable size")
    by_namespace: dict[str, dict[str, Any]] | None = Field(
        None,
        description="Stats per namespace",
    )


class ConfigResponse(BaseResponse):
    """Response for configuration operations.

    Used by:
    - CLI: `floridify config show --json`
    - API: `GET /api/v1/config`
    """

    sections: dict[str, dict[str, Any]] = Field(
        ...,
        description="Configuration sections",
    )
    masked_keys: list[str] | None = Field(
        None,
        description="Keys that are masked",
    )


class IndexRebuildResponse(BaseResponse):
    """Response for search index rebuild.

    Used by:
    - CLI: `floridify search rebuild --json`
    - API: `POST /api/v1/search/rebuild`
    """

    status: str = Field(..., description="Rebuild status")
    languages: list[Language] = Field(..., description="Languages rebuilt")
    corpus_types: list[str] = Field(..., description="Corpus types rebuilt")
    statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="Index statistics",
    )
    total_time_seconds: float = Field(..., description="Total rebuild time")
    semantic_build_time_seconds: float = Field(
        default=0.0,
        description="Semantic index build time",
    )
    caches_cleared: dict[str, int] = Field(
        default_factory=dict,
        description="Caches cleared",
    )
    vocabulary_quality: dict[str, Any] = Field(
        default_factory=dict,
        description="Quality metrics",
    )


class BatchOperationResponse(BaseResponse):
    """Response for batch operations.

    Used by both CLI and API for bulk operations.
    """

    operation: str = Field(..., description="Operation type")
    total_items: int = Field(..., description="Total items processed")
    successful: int = Field(..., description="Successful operations")
    failed: int = Field(..., description="Failed operations")
    skipped: int = Field(default=0, description="Skipped items")
    errors: list[dict[str, str]] = Field(
        default_factory=list,
        description="Error details",
    )
    duration_seconds: float = Field(..., description="Total duration")


class AnkiExportResponse(BaseResponse):
    """Response for Anki export operations.

    Used by:
    - CLI: `floridify anki export <wordlist> --json`
    - API: `POST /api/v1/anki/export`
    """

    wordlist_id: str = Field(..., description="Source wordlist ID")
    wordlist_name: str = Field(..., description="Source wordlist name")
    deck_name: str = Field(..., description="Generated deck name")
    cards_generated: int = Field(..., description="Number of cards created")
    cards_failed: int = Field(default=0, description="Number of cards that failed to export")
    file_path: str | None = Field(None, description="Output file path (CLI)")
    download_url: str | None = Field(None, description="Download URL (API)")
    card_types: list[str] = Field(..., description="Card types included")
    export_format: str = Field(default="apkg", description="Export format")


class HealthResponse(BaseResponse):
    """Response for health check.

    Used by:
    - CLI: `floridify health --json`
    - API: `GET /health`
    """

    status: str = Field(..., description="Overall health status")
    components: dict[str, dict[str, Any]] = Field(
        ...,
        description="Component health status",
    )
    uptime_seconds: float | None = Field(None, description="Uptime")


# ============================================================================
# VERSION HISTORY RESPONSE MODELS
# ============================================================================


class VersionSummary(BaseModel):
    """Summary of a single version in the version chain."""

    version: str = Field(..., description="Semantic version string (e.g. 1.0.3)")
    created_at: datetime = Field(..., description="When this version was created")
    data_hash: str = Field(..., description="SHA-256 content hash")
    storage_mode: str = Field(
        default="snapshot",
        description="Storage mode: 'snapshot' (full content) or 'delta' (compressed diff)",
    )
    is_latest: bool = Field(default=False, description="Whether this is the current version")


class VersionHistoryResponse(BaseResponse):
    """Response for version history of a resource."""

    resource_id: str = Field(..., description="Resource identifier")
    total_versions: int = Field(..., description="Total number of versions")
    versions: list[VersionSummary] = Field(..., description="Version summaries, newest first")


class VersionDiffResponse(BaseResponse):
    """Response for diff between two versions."""

    from_version: str = Field(..., description="Source version for diff")
    to_version: str = Field(..., description="Target version for diff")
    changes: dict[str, Any] = Field(
        default_factory=dict,
        description="Categorized changes (values_changed, items_added, items_removed, etc.)",
    )


# Type aliases for common generic responses
WordListResponse = ListResponse[dict[str, Any]]
DefinitionListResponse = ListResponse[dict[str, Any]]
ProviderListResponse = ListResponse[ProviderStatusResponse]
CorpusListResponse = ListResponse[CorpusResponse]
