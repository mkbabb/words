"""Pydantic models for search endpoints."""

from typing import Any

from pydantic import BaseModel, Field

from ....models.base import Language


class RebuildIndexRequest(BaseModel):
    """Request for rebuilding search index — per-corpus or language-level."""

    corpus_name: str | None = Field(
        None, description="Target corpus by name (e.g. 'language_english', 'wordlist_69b73006...')"
    )
    corpus_uuid: str | None = Field(None, description="Target corpus by UUID")
    languages: list[Language] = Field(
        default=[Language.ENGLISH], description="Languages (used when no corpus specified)"
    )
    components: list[str] = Field(
        default=["all"], description="Components to rebuild: 'trie', 'semantic', 'all'"
    )
    clear_caches: bool = Field(default=True, description="Clear L1/L2/L3 caches for target")
    clean_gridfs: bool = Field(default=False, description="Delete stale GridFS entries")


class RebuildIndexResponse(BaseModel):
    """Response for index rebuild operation."""

    status: str
    message: str
    corpus_name: str
    corpus_uuid: str | None = None
    components_rebuilt: list[str]
    vocabulary_size: int = 0
    caches_cleared: dict[str, int] = Field(default_factory=dict)
    gridfs_cleaned: int = 0
    total_time_seconds: float
    semantic_info: dict[str, Any] = Field(default_factory=dict)


class SemanticStatusResponse(BaseModel):
    """Response model for semantic search status."""

    enabled: bool = Field(..., description="Whether semantic search is enabled")
    ready: bool = Field(..., description="Whether semantic search is ready to use")
    building: bool = Field(..., description="Whether semantic search is currently building")
    languages: list[Language] = Field(..., description="Languages configured")
    model_name: str | None = Field(None, description="Semantic model being used")
    vocabulary_size: int = Field(0, description="Number of words in vocabulary")
    message: str = Field(..., description="Human-readable status message")


class HotReloadStatusResponse(BaseModel):
    """Response for hot-reload status."""

    engine_loaded: bool = Field(..., description="Whether a search engine is currently loaded")
    initializing: bool = Field(False, description="Whether background init is in progress")
    init_error: str | None = Field(None, description="Error from last init attempt")
    semantic_enabled: bool = Field(True, description="Whether semantic search is enabled")
    last_check_seconds_ago: float | None = Field(
        None, description="Seconds since last corpus change check"
    )
    check_interval: float = Field(..., description="Interval between corpus change checks")
    corpus_fingerprint: dict[str, Any] | None = Field(
        None, description="Current corpus fingerprint (name, hash, version)"
    )
    languages: list[str] | None = Field(None, description="Currently loaded languages")
