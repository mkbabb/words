# caching/

3-tier cache. L1 memory (OrderedDict LRU) → L2 disk (DiskCache) → L3 versioned MongoDB (SHA-256 content-addressable). Delta compression via DeepDiff. GridFS for large payloads.

```
caching/
├── core.py                 # GlobalCacheManager: L1 memory + L2 disk
├── manager.py              # VersionedDataManager: L3, SHA-256, version chains
├── config.py               # 14 namespace configs (TTL, compression, limits)
├── decorators.py           # @cached_api_call, @cached_computation, etc.
├── models.py               # CacheNamespace, BaseVersionedData, VersionInfo
├── filesystem.py           # DiskCache backend (10GB limit)
├── gridfs.py               # GridFS large payload storage (4MB chunks)
├── keys.py                 # Deterministic key generation
├── serialize.py            # Content hashing, JSON serialization
├── delta.py                # DeepDiff-based delta versioning
├── compression.py          # ZSTD, LZ4, GZIP
├── validation.py           # Version validation, corruption detection
├── version_chains.py       # Semantic versioning, chain management
└── utils.py                # JSON encoder, namespace normalization, run_in_executor
```

## Tiers

**L1 Memory**: OrderedDict LRU per namespace. O(1) get/set/evict.
**L2 Disk**: DiskCache, 10GB limit, per-namespace TTL + compression.
**L3 Versioned**: Content-addressable MongoDB. SHA-256 hashing deduplicates identical content. Per-resource locking. Version chains: `supersedes` / `superseded_by`. Delta compression for eligible types (DICTIONARY, CORPUS, LANGUAGE, LITERATURE); snapshot every 10 versions.
**GridFS**: Durable storage for content exceeding MongoDB's 16MB BSON limit. 4MB chunks. Content here doesn't expire—survives server restarts and cache eviction.

## Enums

**CacheNamespace**: `DEFAULT`, `DICTIONARY`, `SEARCH`, `CORPUS`, `LANGUAGE`, `SEMANTIC`, `TRIE`, `LITERATURE`, `LEXICON`, `API`, `OPENAI` (stored as `"openai_structured"`), `SCRAPING`, `WOTD`, `WORDLIST`
**ResourceType**: `DICTIONARY`, `CORPUS`, `LANGUAGE`, `SEMANTIC`, `LITERATURE`, `SEARCH`, `TRIE`
**CompressionType**: `ZSTD`, `LZ4`, `GZIP`
**StorageType**: `MEMORY`, `CACHE`, `DATABASE`, `S3`

## 14 Namespaces

| Namespace | Mem Limit | Mem TTL | Disk TTL | Compression |
|-----------|-----------|---------|----------|-------------|
| DEFAULT | 200 | 6h | 1d | None |
| DICTIONARY | 500 | 24h | 7d | None |
| SEARCH | 300 | 1h | 6h | None |
| CORPUS | 100 | 30d | 90d | ZSTD |
| LANGUAGE | 100 | 7d | 30d | ZSTD |
| SEMANTIC | 5 | 7d | 30d | ZSTD |
| TRIE | 50 | 7d | 30d | LZ4 |
| OPENAI | 200 | 24h | 7d | ZSTD |
| LITERATURE | 50 | 30d | 90d | GZIP |
| SCRAPING | 100 | 1h | 24h | ZSTD |
| API | 100 | 1h | 12h | None |
| LEXICON | 100 | 7d | 30d | None |
| WOTD | 50 | 1d | 7d | None |
| WORDLIST | 100 | 1h | 12h | None |

## Decorators

- `@cached_api_call(ttl_hours, key_prefix, ignore_params, include_headers)`—async cache with TTL
- `@cached_api_call_with_dedup(...)`—cache + dedup; first concurrent call executes, others await same future
- `@cached_computation(ttl_hours, key_prefix)`—auto-detects sync/async, delegates to `_async` or `_sync` variant
- `@cached_computation_async(...)`—async-only computation caching
- `@cached_computation_sync(...)`—sync computation caching (creates event loop)
- `@deduplicated`—concurrent call dedup only, no storage

## Delta Versioning

`delta.py`: Pure functions using DeepDiff. `compute_delta(old, new)` → serializable diff. `apply_delta(snapshot, delta)` → reconstruct. `reconstruct_version(snapshot, delta_chain)` → walk chain. Full snapshot kept at version 0 and every 10 versions (`DeltaConfig.snapshot_interval`). Max chain length: 50.
