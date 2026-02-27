# Caching Module - Multi-Tier Storage

3-tier caching (L1 memory, L2 disk, L3 versioned) with content-addressable storage, SHA-256 deduplication.

## Structure

```
caching/
├── core.py              # GlobalCacheManager - L1+L2 two-tier system (549 LOC)
├── manager.py           # VersionedDataManager - L3 versioning (745 LOC)
├── config.py            # 13 namespace configurations (175 LOC)
├── models.py            # Pydantic models, enums (330 LOC)
├── decorators.py        # 5 caching decorators (468 LOC)
├── keys.py              # Cache key generation (213 LOC)
├── serialize.py         # Content hashing, serialization (238 LOC)
├── compression.py       # ZSTD, LZ4, GZIP (68 LOC)
├── filesystem.py        # FilesystemBackend - L2 diskcache (175 LOC)
├── validation.py        # Version validation logic (183 LOC)
├── utils.py             # json_encoder, namespace utils (117 LOC)
└── version_chains.py    # Semantic versioning (143 LOC)
```

**Total**: 3,437 LOC across 13 files

## 3-Tier Architecture

```
Request
  ↓
L1: Memory (OrderedDict LRU, 0.2ms)
  ↓ miss
L2: Filesystem (diskcache, 5ms)
  ↓ miss
L3: Versioned Storage (MongoDB, 50-200ms)
  ↓ miss
Loader Function (AI API, providers, etc.)
```

## L1: Memory Cache

**GlobalCacheManager** (`core.py:549`):

```python
class GlobalCacheManager[T]:
    _namespaces: dict[CacheNamespace, NamespaceConfig]
    # NamespaceConfig contains:
    #   memory_cache: OrderedDict[str, dict]  # {data, timestamp}
    #   lock: asyncio.Lock
    #   stats: CacheStats

    async def get(namespace, key, loader=None) -> Any:
        # 1. L1: Check memory (O(1) OrderedDict lookup)
        if key in ns.memory_cache:
            entry = ns.memory_cache[key]
            if not is_expired(entry, ns.memory_ttl):
                ns.memory_cache.move_to_end(key)  # LRU update O(1)
                return entry["data"]

        # 2. L2: Check filesystem
        cached = await self.backend.get(namespace, key)
        if cached:
            # Promote to L1
            await self._promote_to_memory(namespace, key, cached)
            return cached

        # 3. Call loader if provided
        if loader:
            result = await loader()
            await self.set(namespace, key, result)
            return result

    async def set(namespace, key, value, ttl_override=None):
        # Dual-write: L1 + L2 atomically
        # 1. Add to memory with LRU eviction if at capacity
        # 2. Serialize, optionally compress, store to disk
```

**LRU Eviction** (`core.py:93-121`):
```python
def _evict_lru(ns: NamespaceConfig, count: int = 1):
    """O(1) eviction using OrderedDict.popitem(last=False)"""
    for _ in range(count):
        if len(ns.memory_cache) > 0:
            key, _ = ns.memory_cache.popitem(last=False)  # Remove oldest
            ns.stats = ns.stats.increment_evictions()
```

**Performance**:
- Hit: 0.2-0.5ms (dict lookup + move_to_end)
- Miss: 0.1-0.2ms
- LRU eviction: 0.05-0.1ms (O(1))
- Throughput: 5000-10000 ops/sec per namespace

## L2: Filesystem Cache

**FilesystemBackend** (`filesystem.py:175`):

```python
class FilesystemBackend:
    _cache: diskcache.Cache
    # Config: 10GB limit, LRU eviction, pickle serialization

    async def get(namespace, key) -> Any:
        # Async wrapper via loop.run_in_executor()
        full_key = f"{namespace}:{key}"
        return await async_wrapper(self._cache.get, full_key)

    async def set(namespace, key, value, ttl):
        # Pickle serialize + store with TTL
        full_key = f"{namespace}:{key}"
        await async_wrapper(
            self._cache.set,
            full_key,
            value,
            expire=ttl.total_seconds()
        )
```

**Features**:
- Library: `diskcache` (pure Python, no C deps)
- Storage: Pickle serialization
- Capacity: 10GB default
- Eviction: LRU policy
- TTL: Per-item expiration
- Performance: 3-8ms (small <1MB), 50-200ms (large 10MB+)

## L3: Versioned Storage

**VersionedDataManager** (`manager.py:745`):

Content-addressable storage with SHA-256 hashing:

```python
class VersionedDataManager:
    _locks: defaultdict[tuple[ResourceType, str], asyncio.Lock]

    async def save(
        resource_id: str,
        resource_type: ResourceType,
        namespace: CacheNamespace,
        content: Any,
        config: VersionConfig,
    ) -> BaseVersionedData:
        # 1. Serialize content
        content_str = json.dumps(content, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        # 2. Deduplication check
        existing = await find_by_content_hash(content_hash)
        if existing and metadata_unchanged:
            return existing  # Reuse

        # 3. Version increment
        latest = await get_latest(resource_id)
        new_version = increment_version(latest.version_info.version)

        # 4. Content storage (inline <16KB, external ≥16KB)
        if len(content_str) < 16384:
            versioned.content_inline = content
        else:
            await global_cache.set_versioned_content(...)
            versioned.content_location = ContentLocation(...)

        # 5. Atomic save with per-resource lock
        async with self._get_lock(resource_type, resource_id):
            await self._save_with_transaction(versioned, resource_id, resource_type)

        return versioned

    async def get_latest(
        resource_id: str,
        resource_type: ResourceType,
        use_cache: bool = True,
    ) -> BaseVersionedData | None:
        # 1. Check GlobalCacheManager
        # 2. Validate external content exists
        # 3. Query MongoDB for is_latest=True
        # 4. Cache result
```

**Key features**:
- **Per-resource locking**: 3-5x throughput vs global lock
- **Content hashing**: SHA-256 for deduplication
- **Version chains**: Doubly-linked (supersedes, superseded_by)
- **Inline vs external**: <16KB inline, ≥16KB external
- **MongoDB transactions**: Atomic save when available

## 13 Cache Namespaces

**Configuration** (`config.py:175`):

| Namespace | Memory Limit | Memory TTL | Disk TTL | Compression |
|-----------|--------------|-----------|----------|-------------|
| DEFAULT | 200 | 6h | 1d | None |
| DICTIONARY | 500 | 24h | 7d | None |
| CORPUS | 100 | 30d | 90d | ZSTD |
| SEMANTIC | 50 | 7d | 30d | None |
| SEARCH | 300 | 1h | 6h | None |
| TRIE | 50 | 7d | 30d | LZ4 |
| LITERATURE | 50 | 30d | 90d | GZIP |
| SCRAPING | 100 | 1h | 24h | ZSTD |
| API | 100 | 1h | 12h | None |
| LANGUAGE | 100 | 7d | 30d | ZSTD |
| OPENAI | 200 | 24h | 7d | ZSTD |
| LEXICON | 100 | 7d | 30d | None |
| WOTD | 50 | 1d | 7d | None |

## Compression

**3 algorithms** (`compression.py:68`):

```python
def compress_data(data: Any, algorithm: CompressionType) -> bytes:
    pickled = pickle.dumps(data)

    if algorithm == CompressionType.ZSTD:
        return zstd.compress(pickled, level=3)  # 500 MB/s, 2-3x ratio
    elif algorithm == CompressionType.LZ4:
        return lz4.frame.compress(pickled)       # 1000+ MB/s, 1.5-2x ratio
    elif algorithm == CompressionType.GZIP:
        return gzip.compress(pickled, compresslevel=6)  # 50 MB/s, 3-4x ratio
```

| Algorithm | Speed | Ratio | Use Case |
|-----------|-------|-------|----------|
| ZSTD (level 3) | 500 MB/s | 2-3x | Default for large data (corpus, embeddings) |
| LZ4 (level 0) | 1000+ MB/s | 1.5-2x | Fast cache (trie indices) |
| GZIP (level 6) | 50 MB/s | 3-4x | Maximum compression (literature) |

## Caching Decorators

**5 decorators** (`decorators.py:468`):

```python
@cached_api_call(ttl_hours=24.0, key_prefix="openai")
async def get_ai_synthesis(word: str) -> dict:
    """Cache API call with 24h TTL"""
    return await openai_connector.synthesize(word)

@cached_api_call_with_dedup(ttl_hours=24.0)
async def expensive_lookup(word: str) -> Definition:
    """Prevent duplicate concurrent calls - only first executes"""
    return await lookup_pipeline(word)

@cached_computation(ttl_hours=1.0, namespace=CacheNamespace.SEARCH)
async def compute_search_results(query: str) -> list:
    """Cache computation results"""
    return await search_engine.search(query)

@deduplicated
async def process_large_file(path: str) -> Result:
    """Pure deduplication (no cache storage)"""
    return await heavy_processing(path)

@cache_result(ttl=timedelta(hours=6))
def expensive_sync_function(arg: str) -> str:
    """Sync function caching"""
    return compute(arg)
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| L1 hit | 0.2-0.5ms | O(1) dict lookup + move_to_end |
| L1 miss | 0.1-0.2ms | O(1) dict lookup |
| L2 hit (small) | 3-8ms | Disk read + pickle deserialize |
| L2 hit (large) | 50-200ms | Disk read + decompression |
| L3 versioned save | 50-500ms | Serialize + MongoDB + version chain |
| L3 get latest | 50-200ms | Cache check + MongoDB query |
| LRU eviction | 0.05-0.1ms | O(1) popitem |
| Content hash | 1-5ms | JSON serialize + SHA-256 |
| Compression (ZSTD) | 200ms/100MB | 500 MB/s throughput |

**Cascade performance**:
- L1 hit: <1ms
- L2 hit: ~5ms
- MongoDB hit: ~50-100ms
- Cold load with AI: 2-5 seconds

## Versioning

**Semantic versioning** (`version_chains.py:143`):

```python
def increment_version(current: str, increment_type: str = "patch") -> str:
    """Increment version: 1.0.0 → 1.0.1 (patch)"""
    major, minor, patch = parse_version(current)

    if increment_type == "major":
        return f"{major + 1}.0.0"
    elif increment_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"
```

**Version chain** (MongoDB documents):
```
Previous ←→ Current ←→ Next (newest)
↑                      ↑
is_latest=False        is_latest=True
supersedes            superseded_by
```

## Content-Addressable Storage

**Deduplication via SHA-256** (`serialize.py:238`):

```python
def serialize_content(content: Any) -> SerializedContent:
    """Single-pass serialization + hashing"""
    json_str = json.dumps(content, sort_keys=True, default=encode_for_json)
    content_hash = hashlib.sha256(json_str.encode()).hexdigest()
    size_bytes = len(json_str.encode())

    return SerializedContent(
        json_str=json_str,
        content_hash=content_hash,
        size_bytes=size_bytes,
    )
```

**Benefits**:
- Identical content reuses existing version
- Checksums verify integrity
- Distributed compatibility (content can move between nodes)

## Design Patterns

- **Functional** - Pure functions, immutable config (@dataclass(frozen=True))
- **Layered** - L1 → L2 → L3 cascade with promotion
- **Singleton** - Global cache manager via get_global_cache()
- **Context Manager** - Async cleanup for cache sessions
- **LRU** - O(1) OrderedDict-based eviction
- **Content-Addressable** - SHA-256 hashing for deduplication
- **Per-Resource Locking** - Fine-grained concurrency control
- **Async-First** - All I/O operations async

## Memory Usage

**100k word corpus**:
- L1 memory: ~5-10KB per namespace
- L2 disk: ~150-200MB compressed (50-60% reduction)
- L3 versioned: ~50-100MB (deduplicated)
- FAISS indices: ~400MB uncompressed
- **Total with semantic**: ~440MB
- **Total compressed**: ~150-200MB

## Concurrency

| Scenario | Throughput |
|----------|-----------|
| Single resource saves | 5-10 /sec |
| Multiple resources (per-resource locks) | 50-100 /sec |
| Cache hits only (L1) | 10,000+ /sec |
| Versioned saves | 20-30 /sec |
