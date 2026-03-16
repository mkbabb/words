"""Pydantic models for search endpoints."""

from typing import Any

from pydantic import BaseModel, Field

from ....models.base import Language


class RebuildIndexRequest(BaseModel):
    """Enhanced request for rebuilding search index with unified corpus management."""

    # Language and source options
    languages: list[Language] = Field(
        default=[Language.ENGLISH],
        description="Languages to rebuild (defaults to English)",
    )
    force_download: bool = Field(default=True, description="Force re-download of lexicon sources")

    # Unified corpus management options
    corpus_types: list[str] = Field(
        default=["language_search"],
        description="Corpus types to rebuild: 'language_search', 'wordlist', 'wordlist_names', 'custom'",
    )
    rebuild_all_corpora: bool = Field(default=False, description="Rebuild all corpus types")

    # Semantic search options
    rebuild_semantic: bool = Field(default=True, description="Rebuild semantic search indices")
    semantic_force_rebuild: bool = Field(
        default=False,
        description="Force rebuild semantic even if cached",
    )
    quantization_type: str = Field(
        default="binary",
        description="Quantization method: 'binary', 'scalar', 'none'",
    )
    auto_semantic_small_corpora: bool = Field(
        default=True,
        description="Auto-enable semantic for small corpora (<10k words)",
    )

    # Cache management options
    clear_existing_cache: bool = Field(
        default=False,
        description="Clear all existing caches before rebuild",
    )
    clear_semantic_cache: bool = Field(default=False, description="Clear only semantic caches")
    clear_lexicon_cache: bool = Field(default=False, description="Clear only lexicon caches")

    # Performance options
    enable_lemmatization_cache: bool = Field(
        default=True,
        description="Enable lemmatization memoization",
    )
    batch_size: int = Field(default=1000, ge=100, le=5000, description="Batch size for processing")

    # Validation options
    validate_vocabulary: bool = Field(default=True, description="Validate vocabulary quality")
    min_word_length: int = Field(default=2, ge=1, le=10, description="Minimum word length")
    max_word_length: int = Field(default=50, ge=10, le=100, description="Maximum word length")


class RebuildIndexResponse(BaseModel):
    """Enhanced response for index rebuild operation with unified corpus management."""

    status: str = Field(..., description="Rebuild status")
    languages: list[Language] = Field(..., description="Languages rebuilt")
    statistics: dict[str, Any] = Field(default_factory=dict, description="Index statistics")
    message: str = Field(..., description="Status message")

    # Performance metrics
    total_time_seconds: float = Field(..., description="Total rebuild time in seconds")
    semantic_build_time_seconds: float = Field(default=0.0, description="Semantic index build time")
    vocabulary_optimization_ratio: float = Field(
        default=1.0,
        description="Vocabulary reduction ratio",
    )

    # Unified corpus management results
    corpus_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Corpus rebuild results by type",
    )
    corpus_manager_stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Corpus manager statistics",
    )

    # Cache management results
    caches_cleared: dict[str, int] = Field(
        default_factory=dict,
        description="Caches cleared counts",
    )
    compression_stats: dict[str, float] = Field(
        default_factory=dict,
        description="Compression statistics",
    )

    # Quality metrics
    vocabulary_quality: dict[str, Any] = Field(
        default_factory=dict,
        description="Vocabulary validation results",
    )
    lemmatization_stats: dict[str, int] = Field(
        default_factory=dict,
        description="Lemmatization cache statistics",
    )


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
