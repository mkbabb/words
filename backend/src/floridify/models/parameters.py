"""Shared parameter models for CLI and API isomorphism.

This module provides unified parameter models that are used by both the CLI
and REST API to ensure consistent behavior across interfaces. All parameters
are type-safe via Pydantic and support both programmatic usage (API) and
CLI parsing (Click).

Design Principles:
- DRY: Single source of truth for all parameters
- Type Safety: Pydantic validation throughout
- Compatibility: Works with both FastAPI and Click
- Consistency: Same names and defaults everywhere
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from .base import Language
from .dictionary import DictionaryProvider

if TYPE_CHECKING:
    pass


class LookupParams(BaseModel):
    """Shared parameters for word lookup operations.

    Used by:
    - CLI: `floridify lookup <word> [options]`
    - API: `GET /api/v1/lookup/{word}?[params]`
    """

    providers: list[DictionaryProvider] = Field(
        default=[DictionaryProvider.WIKTIONARY],
        description="Dictionary providers to use for lookup",
    )
    languages: list[Language] = Field(
        default=[Language.ENGLISH],
        description="Languages to query",
    )
    force_refresh: bool = Field(
        default=False,
        description="Force refresh from providers, bypass cache",
    )
    no_ai: bool = Field(
        default=False,
        description="Skip AI synthesis, return raw provider data",
    )

    @field_validator("providers", mode="before")
    @classmethod
    def parse_providers(cls, v: Any) -> list[DictionaryProvider]:
        """Parse provider strings to enums."""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    try:
                        result.append(DictionaryProvider(item.lower()))
                    except ValueError:
                        pass  # Skip invalid
                elif isinstance(item, DictionaryProvider):
                    result.append(item)
            return result or [DictionaryProvider.WIKTIONARY]
        return [DictionaryProvider.WIKTIONARY]

    @field_validator("languages", mode="before")
    @classmethod
    def parse_languages(cls, v: Any) -> list[Language]:
        """Parse language strings to enums."""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    try:
                        result.append(Language(item.lower()))
                    except ValueError:
                        pass  # Skip invalid
                elif isinstance(item, Language):
                    result.append(item)
            return result or [Language.ENGLISH]
        return [Language.ENGLISH]


class SearchParams(BaseModel):
    """Shared parameters for search operations.

    Used by:
    - CLI: `floridify search word <query> [options]`
    - API: `GET /api/v1/search?q=<query>&[params]`
    """

    languages: list[Language] = Field(
        default=[Language.ENGLISH],
        description="Languages to search",
    )
    max_results: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )
    min_score: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold",
    )
    mode: str = Field(
        default="smart",
        description="Search mode: smart (cascade), exact, fuzzy, semantic",
    )
    force_rebuild: bool = Field(
        default=False,
        description="Force rebuild of search indices",
    )
    corpus_id: str | None = Field(
        default=None,
        description="Specific corpus ID to search (optional)",
    )
    corpus_name: str | None = Field(
        default=None,
        description="Specific corpus name to search (optional)",
    )

    @field_validator("languages", mode="before")
    @classmethod
    def parse_languages(cls, v: Any) -> list[Language]:
        """Parse language strings to enums."""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    try:
                        result.append(Language(item.lower()))
                    except ValueError:
                        pass
                elif isinstance(item, Language):
                    result.append(item)
            return result or [Language.ENGLISH]
        return [Language.ENGLISH]

    @field_validator("mode", mode="before")
    @classmethod
    def parse_mode(cls, v: Any) -> str:
        """Parse mode string - validates it's a valid search mode."""
        if isinstance(v, str):
            mode = v.lower()
            if mode in ("smart", "exact", "fuzzy", "semantic"):
                return mode
            return "smart"
        # Handle enum if passed
        if hasattr(v, "value"):
            return str(v.value)
        return "smart"


class WordlistCreateParams(BaseModel):
    """Shared parameters for wordlist creation.

    Used by:
    - CLI: `floridify wordlist create <file> [options]`
    - API: `POST /api/v1/wordlists` (JSON body)
    """

    name: str | None = Field(
        default=None,
        description="Wordlist name (auto-generated if not provided)",
    )
    description: str | None = Field(
        default=None,
        description="Wordlist description",
    )
    is_public: bool = Field(
        default=False,
        description="Make wordlist publicly visible",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )
    language: Language = Field(
        default=Language.ENGLISH,
        description="Primary language of wordlist",
    )


class DatabaseStatsParams(BaseModel):
    """Shared parameters for database statistics.

    Used by:
    - CLI: `floridify database stats [options]`
    - API: `GET /api/v1/database/stats?[params]`
    """

    detailed: bool = Field(
        default=False,
        description="Include detailed quality metrics",
    )
    include_provider_coverage: bool = Field(
        default=True,
        description="Include provider coverage analysis",
    )
    include_storage_size: bool = Field(
        default=True,
        description="Calculate estimated storage size",
    )


class DatabaseCleanupParams(BaseModel):
    """Shared parameters for database cleanup.

    Used by:
    - CLI: `floridify database cleanup [options]`
    - API: `POST /api/v1/database/cleanup` (JSON body)
    """

    dry_run: bool = Field(
        default=False,
        description="Show what would be cleaned without making changes",
    )
    older_than_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Remove entries older than N days",
    )
    remove_orphaned_words: bool = Field(
        default=True,
        description="Remove words with no provider data",
    )
    remove_orphaned_definitions: bool = Field(
        default=True,
        description="Remove definitions with no word",
    )


class ConfigGetParams(BaseModel):
    """Shared parameters for configuration retrieval.

    Used by:
    - CLI: `floridify config get <key> [options]`
    - API: `GET /api/v1/config/{key}?[params]`
    """

    section: str = Field(
        default="general",
        description="Configuration section",
    )
    show_keys: bool = Field(
        default=False,
        description="Show API keys (otherwise masked)",
    )


class ConfigSetParams(BaseModel):
    """Shared parameters for configuration updates.

    Used by:
    - CLI: `floridify config set <key> <value> [options]`
    - API: `PATCH /api/v1/config/{key}` (JSON body)
    """

    section: str = Field(
        default="general",
        description="Configuration section",
    )
    value: str | int | float | bool = Field(
        ...,
        description="Value to set",
    )


class ProviderStatusParams(BaseModel):
    """Shared parameters for provider status.

    Used by:
    - CLI: `floridify scrape status [session_id]`
    - API: `GET /api/v1/providers/status?[params]`
    """

    provider: DictionaryProvider | None = Field(
        default=None,
        description="Specific provider to check (all if not specified)",
    )
    include_rate_limits: bool = Field(
        default=True,
        description="Include rate limit information",
    )
    include_cache_stats: bool = Field(
        default=True,
        description="Include cache statistics",
    )


class CorpusCreateParams(BaseModel):
    """Shared parameters for corpus creation.

    Used by:
    - CLI: `floridify corpus create <name> [options]`
    - API: `POST /api/v1/corpus` (JSON body)
    """

    name: str = Field(
        ...,
        description="Corpus name",
    )
    language: Language = Field(
        default=Language.ENGLISH,
        description="Primary language",
    )
    source_type: str = Field(
        default="custom",
        description="Source type: custom, language, literature, wordlist",
    )
    description: str | None = Field(
        default=None,
        description="Corpus description",
    )
    vocabulary: list[str] = Field(
        default_factory=list,
        description="Initial vocabulary words",
    )
    enable_semantic: bool = Field(
        default=False,
        description="Enable semantic search for this corpus",
    )


class CorpusListParams(BaseModel):
    """Shared parameters for listing corpora.

    Used by:
    - CLI: `floridify corpus list [options]`
    - API: `GET /api/v1/corpus?[params]`
    """

    language: Language | None = Field(
        default=None,
        description="Filter by language",
    )
    source_type: str | None = Field(
        default=None,
        description="Filter by source type",
    )
    include_stats: bool = Field(
        default=True,
        description="Include vocabulary statistics",
    )


class CacheStatsParams(BaseModel):
    """Shared parameters for cache statistics.

    Used by:
    - CLI: `floridify cache stats [options]`
    - API: `GET /api/v1/cache/stats?[params]`
    """

    namespace: str | None = Field(
        default=None,
        description="Specific cache namespace (all if not specified)",
    )
    include_hit_rate: bool = Field(
        default=True,
        description="Calculate cache hit rates",
    )
    include_size: bool = Field(
        default=True,
        description="Include storage size estimates",
    )


class CacheClearParams(BaseModel):
    """Shared parameters for cache clearing.

    Used by:
    - CLI: `floridify cache clear [options]`
    - API: `POST /api/v1/cache/clear` (JSON body)
    """

    namespace: str | None = Field(
        default=None,
        description="Specific cache namespace to clear (all if not specified)",
    )
    older_than_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Only clear entries older than N days",
    )
    dry_run: bool = Field(
        default=False,
        description="Show what would be cleared without making changes",
    )


class PaginationParams(BaseModel):
    """Shared parameters for pagination.

    Used by both CLI and API for listing operations.
    """

    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of items to return",
    )


class SortParams(BaseModel):
    """Shared parameters for sorting.

    Used by both CLI and API for listing operations.
    """

    sort_by: str | None = Field(
        default=None,
        description="Field to sort by",
    )
    sort_order: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order: asc or desc",
    )


# Alias mappings for backward compatibility
PARAMETER_ALIASES: dict[str, str] = {
    # Old names -> New names
    "force": "force_refresh",
    "provider": "providers",  # Note: singular -> plural
    "language": "languages",  # Note: singular -> plural
    "semantic": "mode",  # Maps to SearchMode.SEMANTIC
}


def resolve_parameter_alias(name: str) -> str:
    """Resolve parameter alias to canonical name."""
    return PARAMETER_ALIASES.get(name, name)
