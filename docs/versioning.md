# Versioning & Caching

Content-addressable versioning with 3-tier cache and delta compression. Identical content is deduplicated via SHA-256 hashing; version chains track history with `supersedes`/`superseded_by` links; delta compression via DeepDiff keeps storage bounded.

## Table of Contents

- [3-Tier Cache](#3-tier-cache)
- [Namespaces](#namespaces)
- [Versioning Lifecycle](#versioning-lifecycle)
- [Delta Compression](#delta-compression)
- [Frontend Diffing](#frontend-diffing)
- [Key Files](#key-files)

## 3-Tier Cache

```
Request → L1 Memory → L2 Disk → L3 Versioned MongoDB
```

**L1 Memory** ([`core.py`](../backend/src/floridify/caching/core.py)): `OrderedDict` LRU per namespace. O(1) get/set/evict via `move_to_end()`. Independent limits and TTLs per namespace.

**L2 Disk** ([`filesystem.py`](../backend/src/floridify/caching/filesystem.py)): DiskCache backend, 10GB limit. Per-namespace TTL and optional compression (ZSTD, LZ4, GZIP).

**L3 Versioned MongoDB** ([`manager.py`](../backend/src/floridify/caching/manager.py)): Content-addressable via SHA-256 hashing—identical content reuses versions. `supersedes`/`superseded_by` chains for history. Inline storage for payloads <16KB, GridFS for larger. Per-resource locking prevents concurrent write races.

## Namespaces

13 namespaces with independent limits, TTLs, and compression ([`config.py`](../backend/src/floridify/caching/config.py)):

| Namespace | Mem Limit | Mem TTL | Disk TTL | Compression |
|-----------|-----------|---------|----------|-------------|
| DEFAULT | 200 | 6h | 1d | — |
| DICTIONARY | 500 | 24h | 7d | — |
| SEARCH | 300 | 1h | 6h | — |
| CORPUS | 100 | 30d | 90d | ZSTD |
| LANGUAGE | 100 | 7d | 30d | ZSTD |
| SEMANTIC | 5 | 7d | 30d | ZSTD |
| TRIE | 50 | 7d | 30d | LZ4 |
| OPENAI | 200 | 24h | 7d | ZSTD |
| LITERATURE | 50 | 30d | 90d | GZIP |
| SCRAPING | 100 | 1h | 24h | ZSTD |
| API | 100 | 1h | 12h | — |
| LEXICON | 100 | 7d | 30d | — |
| WOTD | 50 | 1d | 7d | — |

## Versioning Lifecycle

1. **Content Hash**: SHA-256 of the serialized data ([`serialize.py`](../backend/src/floridify/caching/serialize.py)). If the hash matches an existing version, no new version is created.

2. **Version Chain**: New versions link to predecessors via `supersedes`/`superseded_by` fields. [`version_chains.py`](../backend/src/floridify/caching/version_chains.py) manages chain traversal and semantic versioning (major.minor.patch).

3. **Delta or Snapshot**: For eligible resource types (DICTIONARY, CORPUS, LANGUAGE, LITERATURE), versions store a delta against the previous snapshot rather than full content. Full snapshots are kept at version 0 and every 10 versions.

4. **Validation**: [`validation.py`](../backend/src/floridify/caching/validation.py) detects corruption—broken chains, missing snapshots, hash mismatches.

## Delta Compression

[`delta.py`](../backend/src/floridify/caching/delta.py) uses DeepDiff for structural diffs:

```python
compute_delta(old_data, new_data) -> dict    # serializable diff
apply_delta(snapshot, delta) -> dict          # reconstruct version
reconstruct_version(snapshot, delta_chain)    # walk chain from nearest snapshot
```

Configuration ([`DeltaConfig`](../backend/src/floridify/caching/config.py)):
- `snapshot_interval`: full snapshot every 10 versions
- `max_chain_length`: safety limit of 50 deltas before forced snapshot

## Frontend Diffing

The TimeMachine overlay ([`TimeMachineOverlay.vue`](../frontend/src/components/custom/definition/TimeMachineOverlay.vue)) shows version history with inline diffs:

- Word-level LCS diff via [`wordDiff.ts`](../frontend/src/utils/wordDiff.ts) highlights additions and deletions
- [`VersionHistory.vue`](../frontend/src/components/custom/definition/VersionHistory.vue) lists all versions with timestamps
- [`VersionDiffViewer.vue`](../frontend/src/components/custom/definition/VersionDiffViewer.vue) renders side-by-side or inline comparisons
- Version data fetched via [`versions.ts`](../frontend/src/api/versions.ts) API module

## Key Files

| File | Role |
|------|------|
| [`caching/core.py`](../backend/src/floridify/caching/core.py) | `GlobalCacheManager`—L1 memory + L2 disk |
| [`caching/manager.py`](../backend/src/floridify/caching/manager.py) | `VersionedDataManager`—L3, SHA-256, version chains |
| [`caching/config.py`](../backend/src/floridify/caching/config.py) | 13 namespace configs, `DeltaConfig` |
| [`caching/delta.py`](../backend/src/floridify/caching/delta.py) | DeepDiff-based delta versioning |
| [`caching/models.py`](../backend/src/floridify/caching/models.py) | `CacheNamespace`, `BaseVersionedData`, `VersionInfo` |
| [`caching/decorators.py`](../backend/src/floridify/caching/decorators.py) | `@cached_api_call`, `@cached_computation`, `@deduplicated` |
| [`caching/compression.py`](../backend/src/floridify/caching/compression.py) | ZSTD, LZ4, GZIP backends |
| [`caching/serialize.py`](../backend/src/floridify/caching/serialize.py) | Content hashing, JSON serialization |
