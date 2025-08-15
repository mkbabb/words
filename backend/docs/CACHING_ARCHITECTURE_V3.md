# Floridify Caching/Metadata/Versioning Architecture v3.0

## Data Models

### Base Versioned Model

```python
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from beanie import Document, PydanticObjectId
import hashlib
import json

from floridify.models.base import BaseMetadata
from floridify.models.dictionary import Language, DictionaryProvider, CorpusType
from floridify.caching.models import CacheNamespace


class StorageType(str, Enum):
    """Backend storage types for content location."""
    MEMORY = "memory"
    CACHE = "cache"  # L2 cache backend (filesystem/s3/redis)
    DATABASE = "database"  # MongoDB inline storage
    S3 = "s3"  # Direct S3 storage


class CompressionType(str, Enum):
    """Compression algorithms for stored content."""
    ZSTD = "zstd"  # Balanced performance/ratio (default)
    LZ4 = "lz4"    # Speed priority for real-time
    GZIP = "gzip"  # Maximum compression for archives


class ContentLocation(BaseModel):
    """Metadata for externally stored content.
    
    Tracks where large content is stored when not inline in MongoDB.
    """
    storage_type: StorageType
    cache_namespace: CacheNamespace | None = None
    cache_key: str | None = None
    path: str | None = None  # filesystem or S3 path
    compression: CompressionType | None = None  # None means no compression
    size_bytes: int
    size_compressed: int | None = None
    checksum: str  # SHA256 hash for integrity


class VersionInfo(BaseModel):
    """Version tracking with semantic versioning and chain management."""
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    data_hash: str  # SHA256 for deduplication
    is_latest: bool = True
    superseded_by: PydanticObjectId | None = None  # Next version in chain
    supersedes: PydanticObjectId | None = None     # Previous version
    dependencies: list[PydanticObjectId] = Field(default_factory=list)


class BaseVersionedData(Document, BaseMetadata):
    """Base class for all versioned data with unified metadata management."""
    
    # Identification
    resource_id: str  # Human-readable identifier
    resource_type: str  # Type discriminator
    namespace: CacheNamespace
    
    # Versioning
    version_info: VersionInfo
    
    # Content storage strategy
    content_location: ContentLocation | None = None  # External storage
    content_inline: dict[str, Any] | None = None    # MongoDB inline (<16MB)
    
    # Metadata and lifecycle
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    ttl: timedelta | None = None
    access_count: int = 0
    last_accessed: datetime | None = None
    
    class Settings:
        name = "versioned_data"
        is_root = True  # Allow inheritance
        indexes = [
            [("resource_id", 1), ("version_info.is_latest", -1)],
            [("namespace", 1), ("resource_type", 1)],
            [("version_info.created_at", -1)],
            "version_info.data_hash"
        ]
    
    def compute_content_hash(self, content: Any) -> str:
        """Compute deterministic hash of content for deduplication."""
        if isinstance(content, dict | list | tuple):
            content_str = json.dumps(content, sort_keys=True, ensure_ascii=True)
        else:
            content_str = str(content)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def should_compress(self) -> bool:
        """Determine if this resource type should be compressed."""
        # Override in subclasses for type-specific logic
        if self.content_inline:
            return False  # Don't compress inline content
        return True  # Default to compression for external storage
```

### Dictionary Data

```python
class Dictionary(BaseVersionedData):
    """Dictionary provider data - typically small, stored inline."""
    
    word: str
    provider: DictionaryProvider
    language: Language = Language.ENGLISH
    
    # Provider-specific fields
    provider_version: str = "1.0.0"
    fetch_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "dictionary")
        data.setdefault("namespace", CacheNamespace.DICTIONARY)
        super().__init__(**data)
    
    def should_compress(self) -> bool:
        """Dictionary data is small enough to skip compression."""
        return False
```

### Corpus Models with Tree Hierarchy

```python
class CorpusRelationship(str, Enum):
    """Types of corpus relationships in the hierarchy."""
    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    DERIVED = "derived"  # Semantic indices, tries built from this


class Corpus(BaseVersionedData):
    """Corpus with tree-based hierarchy for vocabulary management.
    
    Supports master-child relationships where masters aggregate
    children's vocabularies through set union operations.
    """
    
    corpus_type: CorpusType
    language: Language
    
    # Tree hierarchy
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False  # Masters aggregate children
    
    # Vocabulary data
    vocabulary_size: int
    vocabulary_hash: str  # Hash of sorted unique words
    distinct_words: set[str] = Field(default_factory=set)  # Cached for masters
    
    # Source tracking
    source_references: list[PydanticObjectId] = Field(default_factory=list)
    
    # Statistics (stored externally if large)
    word_frequencies: ContentLocation | None = None
    metadata_stats: dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "corpus")
        data.setdefault("namespace", CacheNamespace.CORPUS)
        super().__init__(**data)
    
    def should_compress(self) -> bool:
        """Compress corpora over 10K words."""
        return self.vocabulary_size > 10_000
    
    async def aggregate_children(self, children: list[Corpus]) -> None:
        """Aggregate vocabulary from child corpora (union operation)."""
        if not self.is_master:
            raise ValueError("Only master corpora can aggregate children")
        
        # Union all child vocabularies
        all_words: set[str] = set()
        total_frequencies: dict[str, int] = {}
        
        for child in children:
            # Add child's vocabulary
            all_words.update(child.distinct_words)
            
            # Aggregate frequencies if available
            if child.word_frequencies:
                # Load frequencies from external storage
                frequencies = await load_content(child.word_frequencies)
                for word, freq in frequencies.items():
                    total_frequencies[word] = total_frequencies.get(word, 0) + freq
        
        # Update master corpus
        self.distinct_words = all_words
        self.vocabulary_size = len(all_words)
        self.vocabulary_hash = self.compute_content_hash(sorted(all_words))
        
        # Store aggregated frequencies externally if large
        if total_frequencies and len(total_frequencies) > 1000:
            self.word_frequencies = await store_content(
                total_frequencies, 
                CompressionType.ZSTD
            )


class LanguageCorpus(Corpus):
    """Language-level corpus aggregating multiple sources."""
    
    dialect: str | None = None
    iso_code: str  # ISO 639-1/639-3 code
    
    # Aggregated statistics
    total_documents: int = 0
    total_tokens: int = 0
    unique_sources: list[str] = Field(default_factory=list)
    
    def __init__(self, **data: Any) -> None:
        data["corpus_type"] = CorpusType.LANGUAGE
        data["is_master"] = True  # Language corpora are always masters
        super().__init__(**data)


class LiteratureCorpus(Corpus):
    """Literature-based corpus with work metadata."""
    
    # References to literature works
    literature_data_ids: list[PydanticObjectId] = Field(default_factory=list)
    
    # Aggregated metadata
    authors: list[str] = Field(default_factory=list)
    time_periods: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    
    def __init__(self, **data: Any) -> None:
        data["corpus_type"] = CorpusType.LITERATURE
        super().__init__(**data)
```

### Semantic Index

```python
class SemanticIndex(BaseVersionedData):
    """FAISS semantic search index - always stored externally."""
    
    # Source corpus reference
    corpus_id: PydanticObjectId
    corpus_version: str  # Track specific version used
    
    # Model configuration
    model_name: str  # e.g., "BGE-M3", "all-MiniLM-L6-v2"
    embedding_dimension: int
    index_type: str = "faiss"
    quantization: str | None = None  # "float16", "int8", etc.
    
    # Required external storage (embeddings are large)
    content_location: ContentLocation  # Never None
    
    # Build metrics
    build_time_seconds: float
    memory_usage_mb: float
    num_vectors: int
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "semantic")
        data.setdefault("namespace", CacheNamespace.SEMANTIC)
        super().__init__(**data)
    
    def should_compress(self) -> bool:
        """Embeddings are already optimized, skip compression."""
        return False
```

### Literature Provider Data

```python
class Literature(BaseVersionedData):
    """Literature work content - typically large texts."""
    
    # Metadata
    title: str
    authors: list[str]
    publication_year: int | None = None
    source: str  # "gutenberg", "archive.org", etc.
    language: Language
    
    # Content tracking
    text_hash: str
    text_size_bytes: int
    
    # Analysis metrics
    word_count: int
    unique_words: int
    readability_score: float | None = None
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "literature")
        data.setdefault("namespace", CacheNamespace.CORPUS)  # Share with corpus
        super().__init__(**data)
    
    def should_compress(self) -> bool:
        """Always compress literature texts."""
        return True
```

### Trie Index

```python
class TrieIndex(BaseVersionedData):
    """Trie index for prefix search across corpora."""
    
    # Source corpora (can be multiple via tree aggregation)
    corpus_ids: list[PydanticObjectId]
    
    # Index properties
    node_count: int
    max_depth: int
    supports_fuzzy: bool = False
    memory_usage_bytes: int
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "trie")
        data.setdefault("namespace", CacheNamespace.TRIE)
        super().__init__(**data)
    
    def should_compress(self) -> bool:
        """Compress large tries."""
        return self.node_count > 10_000
```

### Search Index (Composite)

```python
class SearchIndex(BaseVersionedData):
    """Unified search index combining multiple search strategies."""
    
    # Component indices
    trie_index_id: PydanticObjectId | None = None
    semantic_index_id: PydanticObjectId | None = None
    corpus_id: PydanticObjectId  # Primary corpus
    
    # Version tracking for components
    component_versions: dict[str, str] = Field(default_factory=dict)
    
    # Search configuration
    search_config: dict[str, Any] = Field(default_factory=dict)
    supported_languages: list[Language] = Field(default_factory=list)
    max_results: int = 100
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "search")
        data.setdefault("namespace", CacheNamespace.SEARCH)
        super().__init__(**data)
```

## Core Classes

### L2 Cache Backend Abstraction

```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class CacheBackend(Protocol):
    """Protocol for L2 cache backend implementations."""
    
    async def get(self, key: str) -> Any | None:
        """Retrieve value from cache."""
        ...
    
    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Store value in cache with optional TTL."""
        ...
    
    async def delete(self, key: str) -> bool:
        """Remove key from cache."""
        ...
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern, return count deleted."""
        ...
    
    async def get_stats(self) -> dict[str, Any]:
        """Get backend statistics."""
        ...


class FilesystemBackend(CacheBackend):
    """Filesystem backend using diskcache for L2 storage."""
    
    def __init__(self, cache_dir: str, size_limit: int = 10 * 1024**3):
        """Initialize with 10GB default limit."""
        import diskcache as dc
        
        self.cache = dc.Cache(
            directory=cache_dir,
            size_limit=size_limit,
            eviction_policy="least-recently-used",
            statistics=True,
            tag_index=False,  # We handle tags at higher level
            timeout=60
        )
    
    async def get(self, key: str) -> Any | None:
        """Get with async wrapper for diskcache."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.cache.get, key)
    
    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Set with TTL support."""
        loop = asyncio.get_event_loop()
        expire = ttl.total_seconds() if ttl else None
        await loop.run_in_executor(None, self.cache.set, key, value, expire)
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear using diskcache filtering."""
        import fnmatch
        loop = asyncio.get_event_loop()
        
        def clear_matching():
            count = 0
            for key in list(self.cache.iterkeys()):
                if fnmatch.fnmatch(key, pattern):
                    del self.cache[key]
                    count += 1
            return count
        
        return await loop.run_in_executor(None, clear_matching)


class S3Backend(CacheBackend):
    """S3 backend for L2 cache using aioboto3."""
    
    def __init__(self, bucket: str, prefix: str = "cache/"):
        """Initialize S3 backend with bucket and key prefix."""
        import aioboto3
        
        self.bucket = bucket
        self.prefix = prefix
        self.session = aioboto3.Session()
    
    async def get(self, key: str) -> Any | None:
        """Retrieve and decompress from S3."""
        import pickle
        
        async with self.session.client("s3") as s3:
            try:
                response = await s3.get_object(
                    Bucket=self.bucket,
                    Key=f"{self.prefix}{key}"
                )
                data = await response["Body"].read()
                return pickle.loads(data)
            except s3.exceptions.NoSuchKey:
                return None
    
    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Compress and store to S3 with metadata."""
        import pickle
        from datetime import datetime
        
        async with self.session.client("s3") as s3:
            data = pickle.dumps(value)
            
            metadata = {}
            if ttl:
                expiry = datetime.utcnow() + ttl
                metadata["expiry"] = expiry.isoformat()
            
            await s3.put_object(
                Bucket=self.bucket,
                Key=f"{self.prefix}{key}",
                Body=data,
                Metadata=metadata
            )


class RedisBackend(CacheBackend):
    """Redis backend for distributed L2 cache."""
    
    def __init__(self, url: str = "redis://localhost:6379"):
        """Initialize Redis connection pool."""
        import redis.asyncio as redis
        
        self.redis = redis.from_url(url, decode_responses=False)
    
    async def get(self, key: str) -> Any | None:
        """Get and deserialize from Redis."""
        import pickle
        
        data = await self.redis.get(key)
        if data:
            return pickle.loads(data)
        return None
    
    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Serialize and set with TTL."""
        import pickle
        
        data = pickle.dumps(value)
        if ttl:
            await self.redis.setex(key, ttl, data)
        else:
            await self.redis.set(key, data)
    
    async def clear_pattern(self, pattern: str) -> int:
        """Use Redis SCAN to find and delete matching keys."""
        count = 0
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)
            count += 1
        return count


class MongoDBBackend(CacheBackend):
    """MongoDB backend for L2 cache with TTL indexes."""
    
    def __init__(self, collection_name: str = "l2_cache"):
        """Initialize with dedicated cache collection."""
        from motor.motor_asyncio import AsyncIOMotorClient
        
        self.client = AsyncIOMotorClient("mongodb://localhost:27017")
        self.db = self.client.floridify
        self.collection = self.db[collection_name]
        
        # Create TTL index for automatic expiration
        asyncio.create_task(self._ensure_indexes())
    
    async def _ensure_indexes(self):
        """Create indexes including TTL for expiration."""
        await self.collection.create_index("key", unique=True)
        await self.collection.create_index(
            "expires_at", 
            expireAfterSeconds=0  # Use document value
        )
    
    async def get(self, key: str) -> Any | None:
        """Retrieve from MongoDB."""
        doc = await self.collection.find_one({"key": key})
        if doc and "value" in doc:
            return doc["value"]
        return None
    
    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Store with optional TTL."""
        from datetime import datetime
        
        doc = {
            "key": key,
            "value": value,
            "updated_at": datetime.utcnow()
        }
        
        if ttl:
            doc["expires_at"] = datetime.utcnow() + ttl
        
        await self.collection.replace_one(
            {"key": key},
            doc,
            upsert=True
        )
```

### Global Cache Manager

```python
from collections import OrderedDict
from typing import TypeVar, Generic
import asyncio
import time

T = TypeVar('T')


class NamespaceConfig:
    """Configuration for a cache namespace."""
    
    def __init__(
        self,
        name: CacheNamespace,
        memory_limit: int = 100,
        memory_ttl: timedelta | None = None,
        disk_ttl: timedelta | None = None,
        compression: CompressionType | None = None
    ):
        self.name = name
        self.memory_limit = memory_limit
        self.memory_ttl = memory_ttl
        self.disk_ttl = disk_ttl
        self.compression = compression
        self.memory_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.lock = asyncio.Lock()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}


class GlobalCacheManager:
    """Two-tier cache with pluggable L2 backends.
    
    L1: In-memory LRU cache per namespace
    L2: Pluggable backend (filesystem, S3, Redis, MongoDB)
    """
    
    def __init__(self, l2_backend: CacheBackend):
        """Initialize with chosen L2 backend."""
        self.namespaces: dict[CacheNamespace, NamespaceConfig] = {}
        self.l2_backend = l2_backend
        self._init_default_namespaces()
    
    def _init_default_namespaces(self):
        """Initialize standard namespaces with optimized configs."""
        configs = [
            # Small, frequently accessed
            NamespaceConfig(
                CacheNamespace.DICTIONARY,
                memory_limit=500,
                memory_ttl=timedelta(hours=24),
                disk_ttl=timedelta(days=7)
            ),
            # Large, less frequent
            NamespaceConfig(
                CacheNamespace.CORPUS,
                memory_limit=100,
                memory_ttl=timedelta(days=30),
                disk_ttl=timedelta(days=90),
                compression=CompressionType.ZSTD
            ),
            # Embeddings - no compression
            NamespaceConfig(
                CacheNamespace.SEMANTIC,
                memory_limit=50,
                memory_ttl=timedelta(days=7),
                disk_ttl=timedelta(days=30)
            ),
            # Search results - short TTL
            NamespaceConfig(
                CacheNamespace.SEARCH,
                memory_limit=300,
                memory_ttl=timedelta(hours=1),
                disk_ttl=timedelta(hours=6)
            ),
            # Trie indices
            NamespaceConfig(
                CacheNamespace.TRIE,
                memory_limit=50,
                memory_ttl=timedelta(days=7),
                disk_ttl=timedelta(days=30),
                compression=CompressionType.LZ4
            ),
        ]
        
        for config in configs:
            self.namespaces[config.name] = config
    
    async def get(
        self,
        namespace: CacheNamespace,
        key: str,
        loader: callable | None = None
    ) -> Any | None:
        """Two-tier get with optional loader function.
        
        Flow: L1 (memory) -> L2 (backend) -> loader() -> store in both
        """
        ns = self.namespaces.get(namespace)
        if not ns:
            return None
        
        # L1: Check memory cache
        async with ns.lock:
            if key in ns.memory_cache:
                # LRU: move to end
                ns.memory_cache.move_to_end(key)
                entry = ns.memory_cache[key]
                
                # Check TTL
                if ns.memory_ttl:
                    age = time.time() - entry["timestamp"]
                    if age > ns.memory_ttl.total_seconds():
                        del ns.memory_cache[key]
                        ns.stats["evictions"] += 1
                    else:
                        ns.stats["hits"] += 1
                        return entry["data"]
                else:
                    ns.stats["hits"] += 1
                    return entry["data"]
        
        # L2: Check backend cache
        backend_key = f"{namespace.value}:{key}"
        data = await self.l2_backend.get(backend_key)
        
        if data is not None:
            # Decompress if needed
            if ns.compression and isinstance(data, bytes):
                data = decompress_data(data, ns.compression)
            
            # Promote to L1
            await self._promote_to_memory(ns, key, data)
            return data
        
        ns.stats["misses"] += 1
        
        # Cache miss - use loader if provided
        if loader:
            data = await loader()
            if data is not None:
                await self.set(namespace, key, data)
            return data
        
        return None
    
    async def set(
        self,
        namespace: CacheNamespace,
        key: str,
        value: Any,
        ttl_override: timedelta | None = None
    ) -> None:
        """Store in both cache tiers with compression."""
        ns = self.namespaces.get(namespace)
        if not ns:
            return
        
        # L1: Store in memory
        async with ns.lock:
            # Evict LRU if at limit
            while len(ns.memory_cache) >= ns.memory_limit:
                evicted_key, _ = ns.memory_cache.popitem(last=False)
                ns.stats["evictions"] += 1
            
            ns.memory_cache[key] = {
                "data": value,
                "timestamp": time.time()
            }
        
        # L2: Store in backend with compression
        backend_key = f"{namespace.value}:{key}"
        ttl = ttl_override or ns.disk_ttl
        
        # Compress if configured
        if ns.compression:
            value = compress_data(value, ns.compression)
        
        await self.l2_backend.set(backend_key, value, ttl)
    
    async def invalidate(
        self,
        namespace: CacheNamespace,
        key: str | None = None,
        pattern: str | None = None
    ) -> int:
        """Invalidate by key or pattern in both tiers."""
        ns = self.namespaces.get(namespace)
        if not ns:
            return 0
        
        count = 0
        
        if key:
            # Specific key invalidation
            async with ns.lock:
                if key in ns.memory_cache:
                    del ns.memory_cache[key]
                    count += 1
            
            backend_key = f"{namespace.value}:{key}"
            if await self.l2_backend.delete(backend_key):
                count += 1
        
        elif pattern:
            # Pattern invalidation
            import fnmatch
            
            # L1: Memory cache
            async with ns.lock:
                keys_to_delete = [
                    k for k in ns.memory_cache
                    if fnmatch.fnmatch(k, pattern)
                ]
                for k in keys_to_delete:
                    del ns.memory_cache[k]
                    count += 1
            
            # L2: Backend cache
            backend_pattern = f"{namespace.value}:{pattern}"
            count += await self.l2_backend.clear_pattern(backend_pattern)
        
        return count
    
    async def _promote_to_memory(
        self,
        ns: NamespaceConfig,
        key: str,
        data: Any
    ) -> None:
        """Promote L2 hit to L1 memory cache."""
        async with ns.lock:
            # Evict if needed
            while len(ns.memory_cache) >= ns.memory_limit:
                ns.memory_cache.popitem(last=False)
                ns.stats["evictions"] += 1
            
            ns.memory_cache[key] = {
                "data": data,
                "timestamp": time.time()
            }
```

### Enhanced Version Manager

```python
class VersionedDataManager:
    """Manages versioned data with tree support and atomic operations."""
    
    def __init__(self, cache_manager: GlobalCacheManager):
        self.cache = cache_manager
        self.lock = asyncio.Lock()
    
    async def save(
        self,
        resource_id: str,
        resource_type: str,
        namespace: CacheNamespace,
        content: Any,
        metadata: dict[str, Any] | None = None,
        dependencies: list[PydanticObjectId] | None = None,
        parent_id: PydanticObjectId | None = None,
        ttl: timedelta | None = None
    ) -> BaseVersionedData:
        """Save with automatic versioning and deduplication.
        
        Handles version chains, content storage strategy, and caching.
        """
        # Compute content hash for deduplication
        content_hash = hashlib.sha256(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()
        
        # Check for duplicate content
        existing = await self._find_by_hash(resource_id, content_hash)
        if existing:
            return existing
        
        # Get latest version for increment
        latest = await self.get_latest(resource_id, resource_type)
        new_version = self._increment_version(
            latest.version_info.version if latest else "0.0.0"
        )
        
        # Determine storage strategy based on size
        content_size = len(json.dumps(content))
        storage_location = None
        content_inline = None
        
        if content_size > 1_000_000:  # >1MB goes external
            storage_location = await self._store_external(
                resource_id, resource_type, content, namespace
            )
        else:
            content_inline = content
        
        # Create versioned data instance
        model_class = self._get_model_class(resource_type)
        versioned = model_class(
            resource_id=resource_id,
            namespace=namespace,
            version_info=VersionInfo(
                version=new_version,
                data_hash=content_hash,
                is_latest=True,
                supersedes=latest.id if latest else None,
                dependencies=dependencies or []
            ),
            content_location=storage_location,
            content_inline=content_inline,
            metadata=metadata or {},
            ttl=ttl
        )
        
        # Atomic update with version chain
        async with self.lock:
            # Mark previous as old
            if latest:
                latest.version_info.is_latest = False
                latest.version_info.superseded_by = versioned.id
                await latest.save()
            
            # Save new version
            await versioned.save()
            
            # Update parent if tree structure
            if parent_id and isinstance(versioned, Corpus):
                await self._update_parent_corpus(parent_id, versioned.id)
        
        # Cache the new version
        cache_key = f"{resource_type}:{resource_id}"
        await self.cache.set(namespace, cache_key, versioned, ttl)
        
        return versioned
    
    async def get_latest(
        self,
        resource_id: str,
        resource_type: str,
        use_cache: bool = True
    ) -> BaseVersionedData | None:
        """Get latest version with caching."""
        namespace = self._get_namespace(resource_type)
        
        if use_cache:
            cache_key = f"{resource_type}:{resource_id}"
            cached = await self.cache.get(namespace, cache_key)
            if cached:
                return cached
        
        # Query database
        model_class = self._get_model_class(resource_type)
        result = await model_class.find_one(
            model_class.resource_id == resource_id,
            model_class.version_info.is_latest == True
        )
        
        if result and use_cache:
            cache_key = f"{resource_type}:{resource_id}"
            await self.cache.set(namespace, cache_key, result, result.ttl)
        
        return result
    
    async def cascade_rebuild(
        self,
        resource_id: str,
        resource_type: str
    ) -> dict[str, list[str]]:
        """Rebuild resource and cascade to dependencies.
        
        Intelligently handles tree structures and avoids duplicate rebuilds.
        """
        rebuilt = {"direct": [], "cascaded": []}
        visited: set[str] = set()
        
        async def rebuild_recursive(res_id: str, res_type: str):
            """Recursively rebuild with cycle detection."""
            key = f"{res_type}:{res_id}"
            if key in visited:
                return
            visited.add(key)
            
            resource = await self.get_latest(res_id, res_type)
            if not resource:
                return
            
            # Increment version
            new_version = self._increment_version(resource.version_info.version)
            resource.version_info.version = new_version
            resource.version_info.created_at = datetime.utcnow()
            await resource.save()
            
            if res_id == resource_id:
                rebuilt["direct"].append(res_id)
            else:
                rebuilt["cascaded"].append(res_id)
            
            # Cascade to dependencies
            for dep_id in resource.version_info.dependencies:
                dep = await BaseVersionedData.get(dep_id)
                if dep:
                    await rebuild_recursive(dep.resource_id, dep.resource_type)
            
            # Handle tree structures for corpora
            if isinstance(resource, Corpus) and resource.child_corpus_ids:
                for child_id in resource.child_corpus_ids:
                    child = await Corpus.get(child_id)
                    if child:
                        await rebuild_recursive(child.resource_id, "corpus")
        
        async with self.lock:
            await rebuild_recursive(resource_id, resource_type)
        
        return rebuilt
    
    async def cleanup_versions(
        self,
        resource_id: str,
        resource_type: str,
        keep_count: int = 5
    ) -> int:
        """Clean old versions, keeping latest N."""
        model_class = self._get_model_class(resource_type)
        
        # Get all versions sorted newest first
        versions = await model_class.find(
            model_class.resource_id == resource_id
        ).sort(-model_class.version_info.created_at).to_list()
        
        if len(versions) <= keep_count:
            return 0
        
        # Delete old versions
        to_delete = versions[keep_count:]
        deleted = 0
        
        for version in to_delete:
            # Clean external storage
            if version.content_location:
                await self._cleanup_storage(version.content_location)
            
            # Invalidate cache
            namespace = version.namespace
            cache_key = f"{version.resource_type}:{version.resource_id}:v{version.version_info.version}"
            await self.cache.invalidate(namespace, key=cache_key)
            
            # Delete from database
            await version.delete()
            deleted += 1
        
        return deleted
    
    def _get_model_class(self, resource_type: str) -> type[BaseVersionedData]:
        """Map resource type to model class."""
        mapping = {
            "dictionary": Dictionary,
            "corpus": Corpus,
            "language_corpus": LanguageCorpus,
            "literature_corpus": LiteratureCorpus,
            "semantic": SemanticIndex,
            "literature": Literature,
            "trie": TrieIndex,
            "search": SearchIndex
        }
        return mapping.get(resource_type, BaseVersionedData)
    
    def _get_namespace(self, resource_type: str) -> CacheNamespace:
        """Map resource type to cache namespace."""
        mapping = {
            "dictionary": CacheNamespace.DICTIONARY,
            "corpus": CacheNamespace.CORPUS,
            "semantic": CacheNamespace.SEMANTIC,
            "literature": CacheNamespace.CORPUS,
            "trie": CacheNamespace.TRIE,
            "search": CacheNamespace.SEARCH
        }
        return mapping.get(resource_type, CacheNamespace.DEFAULT)
    
    def _increment_version(self, version: str) -> str:
        """Increment patch version (1.2.3 -> 1.2.4)."""
        major, minor, patch = version.split(".")
        return f"{major}.{minor}.{int(patch) + 1}"
```

## Helper Functions

### Compression Utilities

```python
import zstandard as zstd
import lz4.frame
import gzip
import pickle
import msgspec


def compress_data(data: Any, compression: CompressionType) -> bytes:
    """Compress data with specified algorithm.
    
    Uses msgspec for JSON serialization (fastest) with fallback to pickle.
    """
    # Serialize
    try:
        serialized = msgspec.json.encode(data)
    except (TypeError, ValueError):
        serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    
    # Compress
    if compression == CompressionType.ZSTD:
        cctx = zstd.ZstdCompressor(level=3)  # Balanced
        return cctx.compress(serialized)
    elif compression == CompressionType.LZ4:
        return lz4.frame.compress(serialized, compression_level=0)  # Fastest
    elif compression == CompressionType.GZIP:
        return gzip.compress(serialized, compresslevel=6)
    
    return serialized  # Should not reach here


def decompress_data(compressed: bytes, compression: CompressionType) -> Any:
    """Decompress and deserialize data."""
    # Decompress
    if compression == CompressionType.ZSTD:
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed)
    elif compression == CompressionType.LZ4:
        decompressed = lz4.frame.decompress(compressed)
    elif compression == CompressionType.GZIP:
        decompressed = gzip.decompress(compressed)
    else:
        decompressed = compressed
    
    # Deserialize
    try:
        return msgspec.json.decode(decompressed)
    except (TypeError, ValueError):
        return pickle.loads(decompressed)


def select_compression(
    data_type: str,
    size_bytes: int,
    is_realtime: bool = False
) -> CompressionType | None:
    """Select optimal compression based on data characteristics.
    
    Returns None for no compression (small data or pre-optimized).
    """
    # No compression for small data
    if size_bytes < 1024:
        return None
    
    # No compression for embeddings (already optimized)
    if data_type in ["semantic", "embeddings"]:
        return None
    
    # Fast compression for real-time
    if is_realtime or data_type in ["api", "search"]:
        return CompressionType.LZ4
    
    # Balanced for medium data
    if size_bytes < 10_000_000:  # <10MB
        return CompressionType.ZSTD
    
    # Maximum compression for large data
    return CompressionType.GZIP
```

### Tree Corpus Operations

```python
class TreeCorpusManager:
    """Manages corpus trees with automatic aggregation."""
    
    def __init__(self, version_manager: VersionedDataManager):
        self.vm = version_manager
    
    async def create_tree(
        self,
        master_name: str,
        language: Language,
        children: list[dict[str, Any]]
    ) -> Corpus:
        """Create corpus tree with master and children.
        
        Automatically aggregates vocabularies via set union.
        """
        # Create child corpora
        child_ids: list[PydanticObjectId] = []
        
        for child_config in children:
            child = await self.vm.save(
                resource_id=child_config["id"],
                resource_type="corpus",
                namespace=CacheNamespace.CORPUS,
                content=child_config["content"],
                metadata=child_config.get("metadata", {})
            )
            child_ids.append(child.id)
        
        # Create master corpus
        master = Corpus(
            resource_id=master_name,
            corpus_type=CorpusType.LANGUAGE,
            language=language,
            is_master=True,
            child_corpus_ids=child_ids,
            vocabulary_size=0,  # Will be updated
            vocabulary_hash=""   # Will be updated
        )
        
        # Load and aggregate children
        children_corpora = []
        for child_id in child_ids:
            child = await Corpus.get(child_id)
            if child:
                child.parent_corpus_id = master.id
                await child.save()
                children_corpora.append(child)
        
        # Aggregate vocabularies
        await master.aggregate_children(children_corpora)
        
        # Save master with dependencies
        return await self.vm.save(
            resource_id=master_name,
            resource_type="corpus",
            namespace=CacheNamespace.CORPUS,
            content={"vocabulary": list(master.distinct_words)},
            metadata={
                "corpus_type": "master",
                "child_count": len(child_ids),
                "vocabulary_size": master.vocabulary_size
            },
            dependencies=child_ids
        )
    
    async def add_child(
        self,
        master_id: str,
        child_config: dict[str, Any]
    ) -> Corpus:
        """Add child to existing tree and update master."""
        master = await self.vm.get_latest(master_id, "corpus")
        if not master or not isinstance(master, Corpus):
            raise ValueError(f"Master corpus {master_id} not found")
        
        if not master.is_master:
            raise ValueError(f"Corpus {master_id} is not a master")
        
        # Create child
        child = await self.vm.save(
            resource_id=child_config["id"],
            resource_type="corpus",
            namespace=CacheNamespace.CORPUS,
            content=child_config["content"],
            metadata=child_config.get("metadata", {}),
            parent_id=master.id
        )
        
        # Update master
        master.child_corpus_ids.append(child.id)
        
        # Re-aggregate with new child
        all_children = []
        for cid in master.child_corpus_ids:
            c = await Corpus.get(cid)
            if c:
                all_children.append(c)
        
        await master.aggregate_children(all_children)
        await master.save()
        
        # Invalidate master cache
        await self.vm.cache.invalidate(
            CacheNamespace.CORPUS,
            key=f"corpus:{master_id}"
        )
        
        return master
```

### Atomic Operations

```python
async def atomic_multi_save(
    version_manager: VersionedDataManager,
    operations: list[tuple[str, str, CacheNamespace, Any, dict]],
    rollback_on_failure: bool = True
) -> list[BaseVersionedData] | None:
    """Execute multiple save operations atomically.
    
    All succeed or all fail (with rollback).
    """
    saved: list[BaseVersionedData] = []
    
    async with version_manager.lock:
        try:
            for resource_id, resource_type, namespace, content, metadata in operations:
                result = await version_manager.save(
                    resource_id=resource_id,
                    resource_type=resource_type,
                    namespace=namespace,
                    content=content,
                    metadata=metadata
                )
                saved.append(result)
            
            return saved
            
        except Exception as e:
            if rollback_on_failure:
                # Delete all saved items
                for item in saved:
                    await item.delete()
                return None
            raise


async def cascade_operation(
    version_manager: VersionedDataManager,
    root_id: str,
    root_type: str,
    operation: callable
) -> dict[str, Any]:
    """Execute operation with intelligent cascading.
    
    Avoids duplicate operations through visited tracking.
    """
    visited: set[str] = set()
    results = {"root": root_id, "cascaded": []}
    
    async def process(res_id: str, res_type: str):
        key = f"{res_type}:{res_id}"
        if key in visited:
            return
        visited.add(key)
        
        resource = await version_manager.get_latest(res_id, res_type)
        if not resource:
            return
        
        # Execute operation
        result = await operation(resource)
        results["cascaded"].append({
            "id": res_id,
            "type": res_type,
            "result": result
        })
        
        # Process dependencies
        for dep_id in resource.version_info.dependencies:
            dep = await BaseVersionedData.get(dep_id)
            if dep:
                await process(dep.resource_id, dep.resource_type)
        
        # Process tree children
        if isinstance(resource, Corpus):
            for child_id in resource.child_corpus_ids:
                child = await Corpus.get(child_id)
                if child:
                    await process(child.resource_id, "corpus")
    
    await process(root_id, root_type)
    return results
```

## Implementation Phases

### Phase 1: Core Infrastructure
- Implement base models with proper enum usage
- Create L2 backend abstractions
- Build GlobalCacheManager with pluggable backends
- Implement VersionedDataManager core

### Phase 2: Tree Structures
- Implement Corpus hierarchy with parent-child relationships
- Build aggregation logic for vocabulary unions
- Create TreeCorpusManager for tree operations
- Add cascading update support

### Phase 3: Storage Backends
- Implement FilesystemBackend with diskcache
- Add S3Backend for cloud storage
- Create RedisBackend for distributed caching
- Build MongoDBBackend for unified storage

### Phase 4: Advanced Features
- Atomic multi-resource operations
- Intelligent compression selection
- Pattern-based cache invalidation
- Cleanup and retention policies