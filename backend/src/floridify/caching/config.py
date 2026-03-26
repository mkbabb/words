"""Centralized caching configuration - Immutable data structures.

Single source of truth for all caching configuration.
All configuration uses frozen Pydantic models for immutability.
"""

from datetime import timedelta

from pydantic import BaseModel, ConfigDict

from .models import CacheNamespace, CompressionType, ResourceType


class DeltaConfig(BaseModel):
    """Immutable configuration for delta-based version storage.

    Controls when full snapshots are kept versus delta-compressed versions.
    """

    model_config = ConfigDict(frozen=True)

    snapshot_interval: int = 10  # Full snapshot every N versions
    max_chain_length: int = 50  # Safety limit on delta chain traversal
    enabled: bool = True


DELTA_CONFIG = DeltaConfig()


class NamespaceCacheConfig(BaseModel):
    """Immutable configuration for a cache namespace.

    Defines memory limits, TTLs, and compression settings for each namespace.
    Frozen Pydantic model ensures configuration cannot be mutated after creation.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    namespace: CacheNamespace
    memory_limit: int  # Maximum number of entries in L1 (memory) cache
    memory_ttl: timedelta  # Time-to-live for L1 cache entries
    disk_ttl: timedelta | None  # Time-to-live for L2 (disk) cache entries
    compression: CompressionType | None = None  # Optional compression algorithm


# All 13 namespace configurations - complete coverage, no partial mappings
DEFAULT_CONFIGS: dict[CacheNamespace, NamespaceCacheConfig] = {
    CacheNamespace.DEFAULT: NamespaceCacheConfig(
        namespace=CacheNamespace.DEFAULT,
        memory_limit=200,
        memory_ttl=timedelta(hours=6),
        disk_ttl=timedelta(days=1),
    ),
    CacheNamespace.DICTIONARY: NamespaceCacheConfig(
        namespace=CacheNamespace.DICTIONARY,
        memory_limit=500,
        memory_ttl=timedelta(hours=24),
        disk_ttl=timedelta(days=7),
    ),
    CacheNamespace.CORPUS: NamespaceCacheConfig(
        namespace=CacheNamespace.CORPUS,
        memory_limit=100,
        memory_ttl=timedelta(days=30),
        disk_ttl=timedelta(days=90),
        compression=CompressionType.ZSTD,
    ),
    CacheNamespace.SEMANTIC: NamespaceCacheConfig(
        namespace=CacheNamespace.SEMANTIC,
        memory_limit=5,
        memory_ttl=timedelta(days=7),
        disk_ttl=timedelta(days=30),
        compression=CompressionType.ZSTD,
    ),
    CacheNamespace.SEARCH: NamespaceCacheConfig(
        namespace=CacheNamespace.SEARCH,
        memory_limit=300,
        memory_ttl=timedelta(hours=1),
        disk_ttl=timedelta(hours=6),
    ),
    CacheNamespace.TRIE: NamespaceCacheConfig(
        namespace=CacheNamespace.TRIE,
        memory_limit=50,
        memory_ttl=timedelta(days=7),
        disk_ttl=timedelta(days=30),
        compression=CompressionType.LZ4,
    ),
    CacheNamespace.LITERATURE: NamespaceCacheConfig(
        namespace=CacheNamespace.LITERATURE,
        memory_limit=50,
        memory_ttl=timedelta(days=30),
        disk_ttl=timedelta(days=90),
        compression=CompressionType.GZIP,
    ),
    CacheNamespace.SCRAPING: NamespaceCacheConfig(
        namespace=CacheNamespace.SCRAPING,
        memory_limit=100,
        memory_ttl=timedelta(hours=1),
        disk_ttl=timedelta(hours=24),
        compression=CompressionType.ZSTD,
    ),
    CacheNamespace.LANGUAGE: NamespaceCacheConfig(
        namespace=CacheNamespace.LANGUAGE,
        memory_limit=100,
        memory_ttl=timedelta(days=7),
        disk_ttl=timedelta(days=30),
        compression=CompressionType.ZSTD,
    ),
    CacheNamespace.OPENAI: NamespaceCacheConfig(
        namespace=CacheNamespace.OPENAI,
        memory_limit=200,
        memory_ttl=timedelta(hours=24),
        disk_ttl=timedelta(days=7),
        compression=CompressionType.ZSTD,
    ),
    CacheNamespace.WOTD: NamespaceCacheConfig(
        namespace=CacheNamespace.WOTD,
        memory_limit=50,
        memory_ttl=timedelta(days=1),
        disk_ttl=timedelta(days=7),
    ),
    CacheNamespace.API: NamespaceCacheConfig(
        namespace=CacheNamespace.API,
        memory_limit=100,
        memory_ttl=timedelta(hours=1),
        disk_ttl=timedelta(hours=12),
    ),
    CacheNamespace.LEXICON: NamespaceCacheConfig(
        namespace=CacheNamespace.LEXICON,
        memory_limit=100,
        memory_ttl=timedelta(days=7),
        disk_ttl=timedelta(days=30),
    ),
    CacheNamespace.WORDLIST: NamespaceCacheConfig(
        namespace=CacheNamespace.WORDLIST,
        memory_limit=100,
        memory_ttl=timedelta(hours=1),
        disk_ttl=timedelta(hours=12),
    ),
}

# String -> CacheNamespace mapping (all 13 namespaces)
NAMESPACE_MAP: dict[str, CacheNamespace] = {
    "default": CacheNamespace.DEFAULT,
    "dictionary": CacheNamespace.DICTIONARY,
    "corpus": CacheNamespace.CORPUS,
    "semantic": CacheNamespace.SEMANTIC,
    "search": CacheNamespace.SEARCH,
    "trie": CacheNamespace.TRIE,
    "literature": CacheNamespace.LITERATURE,
    "scraping": CacheNamespace.SCRAPING,
    "api": CacheNamespace.API,
    "language": CacheNamespace.LANGUAGE,
    "openai": CacheNamespace.OPENAI,
    "lexicon": CacheNamespace.LEXICON,
    "wotd": CacheNamespace.WOTD,
    "wordlist": CacheNamespace.WORDLIST,
}

# ResourceType -> CacheNamespace mapping (all 7 resource types)
RESOURCE_TYPE_MAP: dict[ResourceType, CacheNamespace] = {
    ResourceType.DICTIONARY: CacheNamespace.DICTIONARY,
    ResourceType.CORPUS: CacheNamespace.CORPUS,
    ResourceType.LANGUAGE: CacheNamespace.LANGUAGE,
    ResourceType.SEMANTIC: CacheNamespace.SEMANTIC,
    ResourceType.LITERATURE: CacheNamespace.LITERATURE,
    ResourceType.TRIE: CacheNamespace.TRIE,
    ResourceType.SEARCH: CacheNamespace.SEARCH,
}


def validate_namespace(name: str) -> CacheNamespace:
    """Validate and convert string to CacheNamespace enum.

    Pure validation function - no side effects.

    Args:
        name: String namespace name

    Returns:
        Corresponding CacheNamespace enum

    Raises:
        ValueError: If namespace name is unknown

    Examples:
        >>> validate_namespace("dictionary")
        <CacheNamespace.DICTIONARY: 'dictionary'>
        >>> validate_namespace("compute")  # Legacy alias
        <CacheNamespace.SEARCH: 'search'>
        >>> validate_namespace("invalid")
        Traceback (most recent call last):
            ...
        ValueError: Unknown namespace: invalid
    """
    if name not in NAMESPACE_MAP:
        valid_names = ", ".join(sorted(NAMESPACE_MAP.keys()))
        raise ValueError(f"Unknown namespace: {name}. Valid namespaces are: {valid_names}")
    return NAMESPACE_MAP[name]
