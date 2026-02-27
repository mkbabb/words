# caching/

3-tier cache. L1 memory (0.2ms) → L2 disk (5ms) → L3 versioned MongoDB (50-200ms). SHA-256 dedup.

```
caching/
├── core.py (636)           # GlobalCacheManager: L1 memory + L2 disk
├── manager.py (1,052)      # VersionedDataManager: L3, SHA-256, version chains
├── config.py (188)         # 13 namespace configs (TTL, compression, limits)
├── decorators.py (466)     # @cached_api_call, @cached_computation, etc.
├── models.py (359)         # CacheNamespace, BaseVersionedData, VersionInfo
├── filesystem.py (241)     # DiskCache backend (10GB limit)
├── keys.py (213)           # Deterministic key generation
├── serialize.py (240)      # Content hashing, JSON serialization
├── compression.py (69)     # ZSTD (2-3x), LZ4 (1.5-2x), GZIP (3-4x)
├── validation.py (183)     # Version validation, corruption detection
└── version_chains.py (143) # Semantic versioning, chain management
```

## Tiers

**L1 Memory**: OrderedDict LRU per namespace. O(1) get/set/evict. 0.2ms hit.
**L2 Disk**: DiskCache, 10GB limit, per-namespace TTL + compression. 5ms hit.
**L3 Versioned**: Content-addressable MongoDB. SHA-256 hashing deduplicates identical content. Per-resource locking (3-5x throughput). Version chains: `supersedes` ↔ `superseded_by`. Inline <16KB, external ≥16KB.

## 13 Namespaces

| Namespace | Mem Limit | Mem TTL | Disk TTL | Compression |
|-----------|-----------|---------|----------|-------------|
| DICTIONARY | 500 | 24h | 7d | None |
| SEMANTIC | 50 | 7d | 30d | None |
| SEARCH | 300 | 1h | 6h | None |
| CORPUS | 100 | 30d | 90d | ZSTD |
| OPENAI | 200 | 24h | 7d | ZSTD |
| LITERATURE | 50 | 30d | 90d | GZIP |
| API | 100 | 1h | 12h | None |
| + 6 more | ... | ... | ... | ... |

## Decorators

- `@cached_api_call` — cache with TTL
- `@cached_api_call_with_dedup` — first concurrent call executes, others wait
- `@cached_computation` — cache computation results
- `@deduplicated` — pure dedup, no storage
- `@cache_result` — sync function caching
