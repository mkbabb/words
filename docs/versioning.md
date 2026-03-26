# Versioning & Caching

A content-addressable versioning system backed by a 3-tier cache and delta compression. Identical content is deduplicated via SHA-256 hashing, version chains track history through `supersedes`/`superseded_by` links, and delta compression via DeepDiff keeps storage bounded.

## Table of Contents

1. [Background](#background)
2. [Architecture](#architecture)
3. [L1: Memory Cache](#l1-memory-cache)
4. [L2: Disk Cache](#l2-disk-cache)
5. [L3: Versioned MongoDB](#l3-versioned-mongodb)
6. [GridFS](#gridfs)
7. [Serialization](#serialization)
8. [Decorators](#decorators)
9. [Concurrency](#concurrency)
10. [API Endpoints](#api-endpoints)
11. [Key Files](#key-files)

## Background

### Content-Addressable Storage

Every versioned resource in Floridify is identified by the SHA-256 hash of its serialized content. The serialization is deterministic: `json.dumps(content, sort_keys=True, default=json_encoder)` produces a stable byte string regardless of insertion order, and the encoder handles `PydanticObjectId`, `Enum`, and `datetime` values. The resulting 64-character hex digest serves as both a deduplication key and an integrity check.

The design borrows from Git's object model and IPFS's content identifiers: data is addressed by *what it contains*, not by where it lives. When the lookup pipeline retries a synthesis or a provider fetch returns the same definitions, the system computes the hash, finds the existing version via `_find_by_hash()`, and returns it without creating a duplicate. The pure function [`should_create_new_version()`](../backend/src/floridify/caching/validation.py) decides: if `existing` is not `None` and `content_hash` matches, the result is `(False, "content_match")`. This prevents version inflation from retry logic and concurrent saves of identical data.

### LRU Eviction

The L1 memory cache uses Python's `OrderedDict` as an O(1) LRU structure. On access (`get()`), `move_to_end(key)` promotes the entry to the tail of the ordered sequence. On eviction, `popitem(last=False)` removes and returns the head—the least recently used entry—in constant time. Each namespace maintains its own independent `OrderedDict` with its own `memory_limit`, so a burst of SEARCH entries won't evict long-lived CORPUS data.

The eviction method `_evict_lru()` supports two modes: evict a specific count, or evict until the cache is under its limit (used during `set()`). Every eviction increments the namespace's immutable `CacheStats` counter via `increment_evictions()`, which returns a new frozen `CacheStats` instance—mutations never happen in place.

### Compression

Three algorithms are available, each tuned for different workloads:

| Algorithm | Library | Level | Strength |
|-----------|---------|-------|----------|
| **ZSTD** | `zstandard` | 3 | Dictionary-based compression with a good ratio at fast speed; default for structured JSON (CORPUS, LANGUAGE, OPENAI, SCRAPING, SEMANTIC) |
| **LZ4** | `lz4.frame` | 0 | Block compression optimized for decompression throughput; used for TRIE indices where read latency matters most |
| **GZIP** | `gzip` | 6 | Deflate-based compression with maximum ratio; used for LITERATURE where payloads are large and reads are infrequent |

Compression is applied during L2 writes ([`compress_data()`](../backend/src/floridify/caching/compression.py)) and reversed on L2 reads. Data is first pickled if it isn't already bytes, then compressed. Decompression reverses the pipeline: decompress, then [`safe_pickle_loads()`](../backend/src/floridify/caching/filesystem.py) via `RestrictedUnpickler`. Namespaces without compression (`None`) store pickled or raw data directly.

## Architecture

### 3-Tier Hierarchy

```
                         ┌─────────────────────────────────────────┐
                         │              Read Path                  │
                         │                                         │
  Request ──► L1 Memory ─┤─ hit ──► return                        │
              (OrderedDict│                                        │
               per ns)    │─ miss ──► L2 Disk ─┤─ hit ──► promote │
                         │            (DiskCache │          to L1   │
                         │             10GB LRU) │                  │
                         │                      │─ miss ──► L3 DB  │
                         │                      │  (MongoDB versioned│
                         │                      │   SHA-256 dedup)  │
                         │                      │   └──► promote   │
                         │                      │        to L1+L2  │
                         └─────────────────────────────────────────┘

                         ┌─────────────────────────────────────────┐
                         │              Write Path                 │
                         │                                         │
  Data ──► L1 set() ─────┤─ evict LRU if over limit               │
              + L2 set() ─┤─ compress if namespace configured      │
                         │                                         │
  Versioned ──► L3 save()┤─ SHA-256 hash check                    │
                         │─ version chain update (transaction)     │
                         │─ delta conversion (best-effort)         │
                         │─ L1+L2 cache warm                       │
                         └─────────────────────────────────────────┘
```

### Namespaces

The system defines 14 namespaces, each with independent limits, TTLs, and compression settings ([`config.py`](../backend/src/floridify/caching/config.py)):

| Namespace | Mem Limit | Mem TTL | Disk TTL | Compression | Rationale |
|-----------|-----------|---------|----------|-------------|-----------|
| DEFAULT | 200 | 6h | 1d |—| Catch-all for unclassified data |
| DICTIONARY | 500 | 24h | 7d |—| Highest limit: most frequently accessed resource type |
| SEARCH | 300 | 1h | 6h |—| Short TTL: search results change as indices rebuild |
| CORPUS | 100 | 30d | 90d | ZSTD | Long-lived: vocabulary corpora rarely change |
| LANGUAGE | 100 | 7d | 30d | ZSTD | Language provider data; moderate churn |
| SEMANTIC | 5 | 7d | 30d | ZSTD | Very low limit: each entry is a large FAISS index |
| TRIE | 50 | 7d | 30d | LZ4 | LZ4 for fast decompression on prefix search hot path |
| OPENAI | 200 | 24h | 7d | ZSTD | AI synthesis responses; compressed to save disk |
| LITERATURE | 50 | 30d | 90d | GZIP | Full literary texts; max compression for large payloads |
| SCRAPING | 100 | 1h | 24h | ZSTD | Web scraping results; short TTL, high churn |
| API | 100 | 1h | 12h |—| API response caching; uncompressed for speed |
| LEXICON | 100 | 7d | 30d |—| Lexicon data; moderate retention |
| WOTD | 50 | 1d | 7d |—| Word-of-the-Day; refreshed daily |
| WORDLIST | 100 | 1h | 12h |—| User wordlist data; short TTL for freshness |

### Storage Strategy

Content size determines where data lives in L3:

- **Inline** (< 16KB): Stored directly in the `content_inline` field of the MongoDB document. No GridFS overhead, no separate fetch. The threshold is defined by `INLINE_CONTENT_THRESHOLD_BYTES` in [`search/config.py`](../backend/src/floridify/search/config.py).
- **GridFS** (>= 16KB): Uploaded to GridFS with ZSTD compression. A `ContentLocation` reference is stored in the document instead of the content itself. L1+L2 are warmed with the uncompressed content for fast reads.
- **force_external**: Semantic embeddings and other large binary blobs bypass JSON serialization entirely. Content is pickled directly (no ZSTD, since SEMANTIC data is internally gzip'd) and uploaded to GridFS. This prevents hangs from attempting JSON encoding on multi-hundred-megabyte numpy arrays.

The 16KB threshold balances document size against oplog pressure in replica sets—embedding large blobs inflates the working set and slows replication.

## L1: Memory Cache

[`core.py`](../backend/src/floridify/caching/core.py)—`GlobalCacheManager`

The L1 tier is a per-namespace `OrderedDict` protected by an `asyncio.Lock`. The `get()` flow:

1. Acquire the namespace lock.
2. Check if `key` exists in `memory_cache`.
3. If present, check TTL: compute `time.time() - entry["timestamp"]`. If expired, delete and increment evictions.
4. If valid, call `move_to_end(key)` for LRU promotion, increment hits, return `entry["data"]`.
5. Release the lock. On miss, fall through to L2.

The `set()` flow:

1. Acquire the namespace lock.
2. Call `_evict_lru(ns, count=None)` to evict entries until `len(memory_cache) < memory_limit`. Each eviction calls `popitem(last=False)` and increments the eviction counter.
3. Insert `{data: value, timestamp: time.time()}` at the current key.
4. Release the lock. Write to L2 outside the lock.

`CacheStats` is a frozen Pydantic model with three counters: `hits`, `misses`, `evictions`. Every mutation returns a new instance via `model_copy(update={...})`. This eliminates data races on stat counters without requiring additional locks.

A background cleanup task runs every 300 seconds (5 minutes). `cleanup_expired_entries()` scans all namespaces, identifies entries older than their namespace's `memory_ttl`, and deletes them. The task is started by `start_ttl_cleanup_task()` during application lifespan and cancelled by `stop_ttl_cleanup_task()` on shutdown.

## L2: Disk Cache

[`filesystem.py`](../backend/src/floridify/caching/filesystem.py)—`FilesystemBackend`

The L2 tier wraps the `diskcache` library, configured with:

- **Size limit**: 10GB (`DEFAULT_SIZE_LIMIT = 1024 * 1024 * 1024 * 10`).
- **Eviction policy**: `least-recently-used`.
- **Statistics**: Enabled for hit/miss tracking.
- **Timeout**: 60 seconds for SQLite lock acquisition.

All operations are async via `loop.run_in_executor(None, ...)`, offloading blocking SQLite I/O to the thread pool. The `FilesystemBackend` caches the event loop reference for a 5-10% speedup, detecting loop changes (common in test environments) by comparing `id(loop)`.

Serialization uses pickle for complex types (Pydantic models, ObjectIds, numpy arrays). Simple types (`str`, `int`, `float`, `bool`, `dict`, `list`) pass through to diskcache's native handling. On deserialization, `safe_pickle_loads()` uses `RestrictedUnpickler`, which restricts deserialization to a frozen allowlist of modules:

- Standard library: `builtins`, `collections`, `datetime`, `decimal`, `enum`, `copy`, `copyreg`, `re`, `uuid`
- Pydantic/Beanie: `pydantic`, `pydantic.main`, `beanie`, `beanie.odm`, etc.
- BSON: `bson`, `bson.objectid`, `bson.decimal128`
- NumPy: `numpy`, `numpy.core`, `numpy._core`
- Application: `floridify` (all sub-modules)

Any attempt to unpickle a class from an unlisted module raises `pickle.UnpicklingError`. This prevents arbitrary code execution from tampered cache files—a necessary safeguard since the L2 cache directory is on the local filesystem.

## L3: Versioned MongoDB

[`manager.py`](../backend/src/floridify/caching/manager.py)—`VersionedDataManager`

### Content Hashing

Every save begins with `json.dumps(content, sort_keys=True, default=encode_for_json)` followed by `hashlib.sha256(...).hexdigest()`. The `sort_keys=True` parameter ensures field ordering doesn't affect the hash—`{"a": 1, "b": 2}` and `{"b": 2, "a": 1}` produce identical digests.

The manager then calls `_find_by_hash()`, which queries MongoDB with a compound filter on `resource_id`, `resource_type`, and `version_info.data_hash`. If a matching document exists, `should_create_new_version()` evaluates the match:

- `(False, "content_match")`—identical content, no metadata comparison requested. Reuse existing.
- `(False, "content_and_metadata_match")`—content matches and all `metadata_comparison_fields` are unchanged.
- `(True, "metadata_changed:field1,field2")`—content matches but tracked metadata fields differ. Create new version.
- `(True, "no_existing")`—no version with this hash exists.
- `(True, "force_rebuild")`—`VersionConfig.force_rebuild` overrides deduplication.

This makes saves idempotent: calling `save()` twice with the same content returns the same version without creating a duplicate.

### Version Chains

Versions form a doubly-linked list through `VersionInfo.supersedes` (points to the predecessor's `_id`) and `VersionInfo.superseded_by` (points to the successor's `_id`). The `is_latest` boolean flag marks the current head of the chain.

When a new version is saved, the chain update proceeds atomically:

1. Insert the new document with `is_latest=True` and `supersedes=latest.id`.
2. `update_many` sets `is_latest=False` and `superseded_by=new.id` on all other documents matching `resource_id + resource_type + is_latest=True + _id != new.id`.

This update uses MongoDB transactions when a replica set is available. If transactions aren't supported (standalone deployment), the operation falls back to a non-transactional `update_many` under a local `asyncio.Lock`—safe for single-process deployments.

Version strings follow semantic versioning: `major.minor.patch`. The [`version_chains.py`](../backend/src/floridify/caching/version_chains.py) module provides pure functions for parsing (`parse_version` returns a `VersionParts` named tuple), incrementing (`increment_version` bumps the specified level and resets lower components), and comparing versions.

UUIDs persist across the version chain. The `uuid` field on `BaseVersionedData` is auto-generated for the first version and preserved on all subsequent versions via `constructor_params["uuid"] = latest.uuid`. This ensures stable external references regardless of how many versions exist.

### Delta Compression

For eligible resource types (`DICTIONARY`, `CORPUS`, `LANGUAGE`, `LITERATURE`), old versions are converted from full snapshots to deltas after a new version is saved. Binary types (`SEMANTIC`, `TRIE`, `SEARCH`) are excluded because their content is opaque blobs unsuitable for structural diffing.

The delta pipeline in [`delta_manager.py`](../backend/src/floridify/caching/delta_manager.py):

1. **Check eligibility**: Skip if the old version's patch number falls on a snapshot interval boundary (every 10 versions by default).
2. **Compute delta**: [`compute_delta(old_content, new_content)`](../backend/src/floridify/caching/delta.py) uses DeepDiff to produce a serializable diff. The diff direction is `DeepDiff(new, old)`, meaning `apply_delta(new, delta)` reconstructs `old`.
3. **Store delta**: The old version's `content_inline` is replaced with the delta dict. `version_info.storage_mode` is set to `"delta"` and `version_info.delta_base_id` points to the new version's `_id`.

Reconstruction walks the `delta_base_id` chain until reaching a full snapshot, then applies deltas in reverse order. A safety limit of 50 (`DeltaConfig.max_chain_length`) prevents runaway chain traversal.

**Auto-resnapshot**: When a read reconstructs a version from a chain deeper than 20, the system saves the reconstructed content back as a full snapshot. This bounds worst-case reconstruction cost on subsequent reads without requiring manual intervention.

The snapshot/delta pattern follows from the observation that typically less than 5% of fields change between consecutive AI synthesis versions. Storing only the diff reduces per-version storage from the full document size (often 10-50KB) down to a few hundred bytes.

### Corruption Recovery

When `get_latest()` finds a version with external content that can't be retrieved (GridFS file missing, deserialization failure), the recovery procedure:

1. **Flag the document**: Set `version_info.is_latest=False` and add the tag `corrupt:missing_content` via `$addToSet`.
2. **Purge cache**: Delete the stale L1/L2 entry using the `ContentLocation.cache_key`.
3. **Raise `RuntimeError`**: Signal to the caller that the resource needs rebuilding.

For delta chain corruption (broken `delta_base_id` references, missing snapshot bases), [`reconstruct_from_delta()`](../backend/src/floridify/caching/delta_manager.py) returns `None` and the manager raises `CacheCorruptionError` with the resource type, resource ID, and reason string.

The `CacheCorruptionError` class in [`models.py`](../backend/src/floridify/caching/models.py) extends `RuntimeError` and carries structured fields (`resource_type`, `resource_id`, `reason`) for programmatic handling upstream.

## GridFS

[`gridfs.py`](../backend/src/floridify/caching/gridfs.py)

GridFS provides durable storage for content exceeding the inline threshold. Configuration:

- **Chunk size**: 4MB (`_CHUNK_SIZE = 4 * 1024 * 1024`), vs. the MongoDB default of 255KB. A 400MB SEMANTIC blob produces ~100 chunks instead of ~1,600.
- **Bucket name**: `floridify_blobs`.
- **Singleton**: Lazy initialization via `get_gridfs_bucket()`. The bucket reference is invalidated and recreated when the event loop changes (detected by comparing `id(asyncio.get_running_loop())`).

Content stored in GridFS never expires—it survives server restarts, cache eviction, and process recycling. This makes it suitable for FAISS indices and other binary data that is expensive to regenerate.

The `gridfs_cleanup_stale()` function identifies files not referenced by any `BaseVersionedData` document with `is_latest=True`. It collects all GridFS file IDs, queries for live references via `content_location.path`, and computes the set difference. The function supports:

- **Corpus-scoped cleanup**: Pass `corpus_uuid` to restrict cleanup to files from a specific corpus.
- **Dry-run mode**: `dry_run=True` (the default) returns counts and byte totals without deleting.

The cleanup endpoint is admin-only and defaults to dry-run for safety.

## Serialization

[`serialize.py`](../backend/src/floridify/caching/serialize.py)

### SerializedContent

The `SerializedContent` frozen Pydantic model eliminates double JSON serialization by computing all artifacts in one pass:

```python
serialized = serialize_content(content)
# serialized.json_str    → stable JSON string (sorted keys)
# serialized.json_bytes  → UTF-8 encoded bytes
# serialized.content_hash → SHA-256 hex digest
# serialized.size_bytes  → byte length
```

This model is used by `set_versioned_content()` to decide the storage strategy (inline vs. GridFS) and populate `ContentLocation` metadata without re-serializing.

### Key Generation

[`keys.py`](../backend/src/floridify/caching/keys.py) provides three key generation patterns, all producing 64-character SHA-256 hex digests:

| Function | Input | Used By |
|----------|-------|---------|
| `generate_resource_key(type, id, *qualifiers)` | Colon-joined enum values and strings | Version manager (L3 cache keys) |
| `generate_cache_key(key_parts)` | `str(tuple)` of prepared parts | Decorator-based caching |
| `generate_http_key(method, path, params)` | HTTP method + URL + sorted params | API-level caching |

### Binary Content Estimation

For payloads containing large binary data (e.g., numpy embeddings in `content["binary_data"]`), full JSON serialization would be prohibitively slow. `estimate_binary_size()` computes a CRC32 checksum (~1GB/s throughput) instead of SHA-256 and sums byte lengths directly from the `binary_data` dict values. The returned checksum uses the format `crc32:XXXXXXXX`.

## Decorators

[`decorators.py`](../backend/src/floridify/caching/decorators.py)

Six decorators provide caching and deduplication at the function level, each targeting a different combination of async/sync, storage tiers, and dedup behavior:

| Decorator | Async | Stores | Dedup | Parameters |
|-----------|-------|--------|-------|------------|
| `@cached_api_call` | Yes | L1+L2 | No | `ttl_hours=24`, `key_prefix="api"`, `ignore_params`, `include_headers` |
| `@cached_api_call_with_dedup` | Yes | L1+L2 | Yes | Same as `@cached_api_call` |
| `@cached_computation_async` | Yes | L1+L2 | No | `ttl_hours=168`, `key_prefix="compute"` |
| `@cached_computation_sync` | No | L1+L2 | No | `ttl_hours=168`, `key_prefix="compute"` |
| `@cached_computation` | Auto | L1+L2 | No | `ttl_hours=168`, `key_prefix="compute"` |
| `@deduplicated` | Yes | No | Yes | (none) |

The `key_prefix` parameter maps to a `CacheNamespace` via `NAMESPACE_MAP`. Cache keys are generated from `_efficient_cache_key_parts()`, which extracts the function's module, name, positional args, and keyword args. For kwargs with 3 or fewer entries, sorting is skipped for performance; larger kwarg dicts are sorted for deterministic keys.

**`@cached_api_call_with_dedup`** combines storage-backed caching with future-based deduplication. When the first concurrent call begins, it registers an `asyncio.Future` in the global `_active_calls` dict (keyed by cache key). Subsequent calls with the same key find the existing future and `await` it. The first call's result (or exception) is propagated to all waiters. This prevents duplicate provider fetches when multiple clients request the same word simultaneously.

**`@cached_computation`** auto-detects sync vs. async: it inspects `inspect.iscoroutinefunction(func)` and delegates to `cached_computation_async` or `cached_computation_sync` accordingly. The sync variant creates a temporary event loop to interact with the async cache.

Example usage:

```python
@cached_api_call_with_dedup(ttl_hours=24, key_prefix="dictionary")
async def fetch_from_provider(word: str, provider: str) -> dict:
    ...
```

## Concurrency

### Per-Resource Locking

`VersionedDataManager` uses a `defaultdict(asyncio.Lock)` keyed by `(ResourceType, resource_id)` tuples. This allows concurrent saves of different resources (e.g., saving "cat" and "dog" simultaneously) while serializing writes to the same resource. The approach provides 3-5x throughput improvement over a single global lock.

The lock dict tracks which event loop created it via `_locks_loop_id`. When the event loop changes (common in test environments with per-function loops), the dict is cleared and repopulated. This prevents `RuntimeError: Task ... got Future attached to a different loop`.

### Future-Based Deduplication

The `@deduplicated` and `@cached_api_call_with_dedup` decorators share a global `_active_calls: dict[str, asyncio.Future]` protected by `_active_calls_lock: asyncio.Lock`. The lock is held only for the check-and-register operation; the actual function execution and future awaiting happen outside the lock to avoid blocking unrelated callers.

### Event Loop Awareness

Three components track their event loop to handle loop changes gracefully:

- **GridFS bucket** (`_bucket_loop_id`): Recreated when the loop changes, since `AsyncIOMotorGridFSBucket` is bound to a specific Motor client/loop pair.
- **Per-resource locks** (`_locks_loop_id`): Cleared and recreated because `asyncio.Lock` instances are loop-specific.
- **FilesystemBackend** (`_loop_id`): Cached for performance, refreshed on change.

### Transaction Fallback

`_save_with_transaction()` attempts a MongoDB transaction (requires a replica set) for atomic version chain updates. If transactions aren't available—standalone MongoDB, older server versions, or `OperationFailure`—the method falls back to sequential insert + `update_many` under the per-resource `asyncio.Lock`. The local lock provides equivalent safety for single-process deployments.

## API Endpoints

[`api/routers/cache.py`](../backend/src/floridify/api/routers/cache.py)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/cache/stats` | None | Per-namespace or aggregate stats: entries, hits, misses, evictions, estimated size. Optional `namespace` filter. |
| `POST` | `/cache/clear` | None | Clear a specific namespace or all namespaces. Supports `dry_run` mode. |
| `POST` | `/cache/prune` | None | Delete non-latest versions older than `max_age_days` (default 90), keeping at least `keep_minimum` (default 10) per resource. Preserves delta base versions. Supports `dry_run`. |
| `GET` | `/cache/disk-usage` | None | L2 disk cache volume, item count, hit/miss stats from diskcache. |
| `POST` | `/cache/gridfs/cleanup` | Admin | Find stale GridFS files not referenced by any live versioned data. Optional `corpus_uuid` filter. Defaults to `dry_run=true`. |

The prune endpoint protects delta chain integrity by excluding versions that serve as delta bases for other versions.

## Key Files

| File | Role |
|------|------|
| [`caching/core.py`](../backend/src/floridify/caching/core.py) | `GlobalCacheManager`—L1 memory + L2 disk. `get_versioned_content` / `set_versioned_content` for storage strategy. |
| [`caching/manager.py`](../backend/src/floridify/caching/manager.py) | `VersionedDataManager`—L3 versioned MongoDB. SHA-256 dedup, version chains, delta orchestration. |
| [`caching/config.py`](../backend/src/floridify/caching/config.py) | 14 namespace configs (`NamespaceCacheConfig`), `DeltaConfig`, `RESOURCE_TYPE_MAP`. |
| [`caching/models.py`](../backend/src/floridify/caching/models.py) | `CacheNamespace`, `ResourceType`, `CompressionType`, `StorageType`, `BaseVersionedData`, `VersionInfo`, `ContentLocation`, `VersionConfig`, `CacheCorruptionError`. |
| [`caching/decorators.py`](../backend/src/floridify/caching/decorators.py) | `@cached_api_call`, `@cached_api_call_with_dedup`, `@cached_computation`, `@cached_computation_async`, `@cached_computation_sync`, `@deduplicated`. |
| [`caching/filesystem.py`](../backend/src/floridify/caching/filesystem.py) | `FilesystemBackend`—DiskCache wrapper with `RestrictedUnpickler` security, 10GB LRU. |
| [`caching/keys.py`](../backend/src/floridify/caching/keys.py) | Pure key generation: `generate_resource_key`, `generate_cache_key`, `generate_http_key`. |
| [`caching/serialize.py`](../backend/src/floridify/caching/serialize.py) | `SerializedContent` one-pass model, `compute_content_hash`, `estimate_binary_size` (CRC32). |
| [`caching/delta.py`](../backend/src/floridify/caching/delta.py) | Pure DeepDiff functions: `compute_delta`, `apply_delta`, `reconstruct_version`, `should_keep_as_snapshot`. |
| [`caching/delta_manager.py`](../backend/src/floridify/caching/delta_manager.py) | `convert_to_delta`, `reconstruct_from_delta` with auto-resnapshot at chain depth >20. |
| [`caching/compression.py`](../backend/src/floridify/caching/compression.py) | `compress_data` / `decompress_data` with ZSTD, LZ4, GZIP backends. |
| [`caching/validation.py`](../backend/src/floridify/caching/validation.py) | `should_create_new_version`, `validate_content_match`, `validate_metadata_changed`. |
| [`caching/version_chains.py`](../backend/src/floridify/caching/version_chains.py) | `parse_version`, `increment_version`, `compare_versions`—pure semantic versioning functions. |
| [`caching/version_crud.py`](../backend/src/floridify/caching/version_crud.py) | `list_versions`, `delete_version` (with chain repair), `prune_old_versions`. |
| [`caching/gridfs.py`](../backend/src/floridify/caching/gridfs.py) | GridFS CRUD: `gridfs_put`, `gridfs_get`, `gridfs_delete`, `gridfs_list_files`, `gridfs_cleanup_stale`. |
| [`caching/utils.py`](../backend/src/floridify/caching/utils.py) | `json_encoder`, `normalize_namespace`, `run_in_executor`. |
| [`api/routers/cache.py`](../backend/src/floridify/api/routers/cache.py) | REST endpoints: stats, clear, prune, disk-usage, gridfs/cleanup. |
