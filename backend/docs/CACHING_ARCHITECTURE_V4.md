# Floridify Caching/Metadata/Versioning Architecture v4.0

## Data Models

### Core Enums and Configuration

```python
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, TypeVar, Generic
from pydantic import BaseModel, Field
from beanie import Document, PydanticObjectId
import hashlib
import json
import pickle

from floridify.models.base import BaseMetadata
from floridify.models.dictionary import Language, DictionaryProvider, CorpusType
from floridify.caching.models import CacheNamespace, QuantizationType
from floridify.providers.literature.models import LiteratureSource


class ResourceType(str, Enum):
    """Types of versioned resources in the system."""
    DICTIONARY = "dictionary"
    CORPUS = "corpus"
    SEMANTIC = "semantic"
    LITERATURE = "literature"
    TRIE = "trie"
    SEARCH = "search"


class StorageType(str, Enum):
    """Backend storage types for content location."""
    MEMORY = "memory"
    CACHE = "cache"
    DATABASE = "database"
    S3 = "s3"


class CompressionType(str, Enum):
    """Compression algorithms for stored content."""
    ZSTD = "zstd"
    LZ4 = "lz4"
    GZIP = "gzip"


class VersionConfig(BaseModel):
    """Configuration for version operations."""
    
    # Cache control
    force_rebuild: bool = False  # Skip cache, force fresh fetch/rebuild
    use_cache: bool = True      # Whether to check cache first
    
    # Version control
    version: str | None = None  # Fetch specific version (None = latest)
    increment_version: bool = True  # Auto-increment version on save
    
    # Storage options
    ttl: timedelta | None = None
    compression: CompressionType | None = None  # None = auto-select
    
    # Operation metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Content Management

```python
class ContentLocation(BaseModel):
    """Metadata for externally stored content."""
    storage_type: StorageType
    cache_namespace: CacheNamespace | None = None
    cache_key: str | None = None
    path: str | None = None
    compression: CompressionType | None = None
    size_bytes: int
    size_compressed: int | None = None
    checksum: str


class VersionInfo(BaseModel):
    """Version tracking with chain management."""
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    data_hash: str
    is_latest: bool = True
    superseded_by: PydanticObjectId | None = None
    supersedes: PydanticObjectId | None = None
    dependencies: list[PydanticObjectId] = Field(default_factory=list)
```

### Base Versioned Data

```python
T = TypeVar('T', bound='BaseVersionedData')


class BaseVersionedData(Document, BaseMetadata, Generic[T]):
    """Base class for all versioned data with content management."""
    
    # Identification
    resource_id: str
    resource_type: ResourceType
    namespace: CacheNamespace
    
    # Versioning
    version_info: VersionInfo
    
    # Content storage
    content_location: ContentLocation | None = None
    content_inline: dict[str, Any] | None = None
    
    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    ttl: timedelta | None = None
    access_count: int = 0
    last_accessed: datetime | None = None
    
    class Settings:
        name = "versioned_data"
        is_root = True
        indexes = [
            [("resource_id", 1), ("version_info.is_latest", -1)],
            [("namespace", 1), ("resource_type", 1)],
            [("version_info.created_at", -1)],
            "version_info.data_hash"
        ]
    
    async def get_content(self) -> Any | None:
        """Retrieve content whether inline or external.
        
        Provides unified access to content regardless of storage location.
        """
        if self.content_inline is not None:
            return self.content_inline
        
        if self.content_location:
            # Delegate to storage backend to retrieve
            from .storage import load_external_content
            return await load_external_content(self.content_location)
        
        return None
    
    async def set_content(
        self, 
        content: Any,
        force_external: bool = False
    ) -> None:
        """Store content with automatic strategy selection.
        
        Automatically determines inline vs external storage based on size.
        """
        content_str = json.dumps(content, sort_keys=True) if isinstance(content, dict | list) else str(content)
        size_bytes = len(content_str.encode())
        
        # Threshold for external storage (1MB)
        if size_bytes > 1_000_000 or force_external:
            from .storage import store_external_content
            self.content_location = await store_external_content(
                content,
                self.namespace,
                f"{self.resource_type.value}:{self.resource_id}:{self.version_info.version}"
            )
            self.content_inline = None
        else:
            self.content_inline = content
            self.content_location = None
```

### Dictionary Entry

```python
from floridify.models.base import Etymology


class DictionaryEntry(BaseVersionedData):
    """Raw data from a dictionary provider with versioning support."""
    
    # Foreign keys to related entities
    word_id: PydanticObjectId  # FK to Word document
    definition_ids: list[PydanticObjectId] = Field(default_factory=list)  # FK to Definition documents
    pronunciation_id: PydanticObjectId | None = None  # FK to Pronunciation document
    
    # Provider information
    provider: DictionaryProvider
    language: Language = Language.ENGLISH
    
    # Etymology and raw data
    etymology: Etymology | None = None
    raw_data: dict[str, Any] | None = None  # Original API response
    
    # Status and timing
    fetch_timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: str | None = None
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.DICTIONARY)
        data.setdefault("namespace", CacheNamespace.DICTIONARY)
        super().__init__(**data)
    
    class Settings:
        # Additional indexes for efficient queries
        indexes = [
            "word_id",
            "provider",
            [("word_id", 1), ("provider", 1)]
        ]
```

### Corpus Models with Tree Hierarchy

```python
class Corpus(BaseVersionedData):
    """Corpus with tree hierarchy for vocabulary management."""
    
    corpus_type: CorpusType
    language: Language
    
    # Tree hierarchy
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False
    
    # Vocabulary (external if large)
    vocabulary_size: int
    vocabulary_hash: str
    vocabulary: ContentLocation | None = None  # External storage for large vocabs
    
    # Statistics (external)
    word_frequencies: ContentLocation | None = None
    metadata_stats: dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.CORPUS)
        data.setdefault("namespace", CacheNamespace.CORPUS)
        super().__init__(**data)
    
    async def get_vocabulary(self) -> set[str]:
        """Retrieve vocabulary whether inline or external."""
        if self.vocabulary:
            from .storage import load_external_content
            vocab_list = await load_external_content(self.vocabulary)
            return set(vocab_list)
        elif self.content_inline and "vocabulary" in self.content_inline:
            return set(self.content_inline["vocabulary"])
        return set()


class LanguageCorpus(Corpus):
    """Language-level master corpus."""
    
    # Aggregated statistics
    total_documents: int = 0
    total_tokens: int = 0
    unique_sources: list[str] = Field(default_factory=list)
    
    def __init__(self, **data: Any) -> None:
        data["corpus_type"] = CorpusType.LANGUAGE
        data["is_master"] = True
        super().__init__(**data)


class LiteratureCorpus(Corpus):
    """Literature-based corpus."""
    
    literature_data_ids: list[PydanticObjectId] = Field(default_factory=list)
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
    """FAISS semantic search index."""
    
    corpus_id: PydanticObjectId
    corpus_version: str
    
    # Model configuration
    model_name: str
    embedding_dimension: int
    index_type: str = "faiss"
    quantization: QuantizationType | None = None
    
    # Always external
    content_location: ContentLocation
    
    # Metrics
    build_time_seconds: float
    memory_usage_mb: float
    num_vectors: int
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.SEMANTIC)
        data.setdefault("namespace", CacheNamespace.SEMANTIC)
        super().__init__(**data)
```

### Literature Data

```python
class Literature(BaseVersionedData):
    """Literature work with external content storage."""
    
    # Metadata
    title: str
    authors: list[str]
    publication_year: int | None = None
    source: LiteratureSource
    language: Language
    
    # Content location (always external for full text)
    content_location: ContentLocation  # The actual text content
    
    # Metrics
    text_hash: str
    text_size_bytes: int
    word_count: int
    unique_words: int
    readability_score: float | None = None
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.LITERATURE)
        data.setdefault("namespace", CacheNamespace.LEXICON)  # Separate namespace
        super().__init__(**data)
```

### Additional Models

```python
class TrieIndex(BaseVersionedData):
    """Trie index for prefix search."""
    
    corpus_ids: list[PydanticObjectId]
    node_count: int
    max_depth: int
    supports_fuzzy: bool = False
    memory_usage_bytes: int
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.TRIE)
        data.setdefault("namespace", CacheNamespace.TRIE)
        super().__init__(**data)


class SearchIndex(BaseVersionedData):
    """Composite search index."""
    
    trie_index_id: PydanticObjectId | None = None
    semantic_index_id: PydanticObjectId | None = None
    corpus_id: PydanticObjectId
    
    # Configuration
    search_config: dict[str, Any] = Field(default_factory=dict)
    supported_languages: list[Language] = Field(default_factory=list)
    max_results: int = 100
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.SEARCH)
        data.setdefault("namespace", CacheNamespace.SEARCH)
        super().__init__(**data)
```

## Core Infrastructure

### Filesystem Cache Backend

```python
import asyncio
import diskcache as dc
from pathlib import Path


class FilesystemBackend:
    """Filesystem backend using diskcache for L2 storage.
    
    Optimized for performance with minimal serialization overhead.
    """
    
    def __init__(self, cache_dir: str, size_limit: int = 10 * 1024**3):
        """Initialize with 10GB default limit."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache = dc.Cache(
            directory=str(self.cache_dir),
            size_limit=size_limit,
            eviction_policy="least-recently-used",
            statistics=True,
            tag_index=False,
            timeout=60
        )
    
    async def get(self, key: str) -> Any | None:
        """Get with minimal deserialization overhead."""
        loop = asyncio.get_event_loop()
        
        def _get():
            data = self.cache.get(key)
            if data is None:
                return None
            
            # For bytes, attempt pickle deserialization (most performant)
            if isinstance(data, bytes):
                # Check for pickle magic bytes (protocol 4 or 5)
                if data[:2] in (b'\x80\x04', b'\x80\x05'):
                    return pickle.loads(data)
                # Otherwise it's likely compressed or JSON
            
            return data
        
        return await loop.run_in_executor(None, _get)
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: timedelta | None = None
    ) -> None:
        """Set with optimized serialization."""
        loop = asyncio.get_event_loop()
        
        def _set():
            # Serialize complex types with pickle for performance
            # Only use raw value for simple types already supported by diskcache
            if isinstance(value, (str, int, float, bool, type(None))):
                data = value
            elif isinstance(value, (dict, list)):
                # Keep JSON types as-is for diskcache's native handling
                data = value
            else:
                # Use pickle for all complex objects (Pydantic models, etc.)
                data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            
            expire = ttl.total_seconds() if ttl else None
            self.cache.set(key, data, expire=expire)
        
        await loop.run_in_executor(None, _set)
    
    async def delete(self, key: str) -> bool:
        """Remove key from cache."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.cache.delete, key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: key in self.cache)
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        import fnmatch
        loop = asyncio.get_event_loop()
        
        def _clear():
            count = 0
            for key in list(self.cache.iterkeys()):
                if fnmatch.fnmatch(key, pattern):
                    del self.cache[key]
                    count += 1
            return count
        
        return await loop.run_in_executor(None, _clear)
```

### Global Cache Manager

```python
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
        self.memory_cache: dict[str, dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}


class GlobalCacheManager:
    """Two-tier cache: L1 memory + L2 filesystem.
    
    Optimized for minimal serialization overhead.
    """
    
    def __init__(self, l2_backend: FilesystemBackend):
        self.namespaces: dict[CacheNamespace, NamespaceConfig] = {}
        self.l2_backend = l2_backend
        self._init_default_namespaces()
    
    def _init_default_namespaces(self):
        """Initialize namespaces with optimized configs."""
        configs = [
            NamespaceConfig(
                CacheNamespace.DICTIONARY,
                memory_limit=500,
                memory_ttl=timedelta(hours=24),
                disk_ttl=timedelta(days=7)
            ),
            NamespaceConfig(
                CacheNamespace.CORPUS,
                memory_limit=100,
                memory_ttl=timedelta(days=30),
                disk_ttl=timedelta(days=90),
                compression=CompressionType.ZSTD
            ),
            NamespaceConfig(
                CacheNamespace.SEMANTIC,
                memory_limit=50,
                memory_ttl=timedelta(days=7),
                disk_ttl=timedelta(days=30)
            ),
            NamespaceConfig(
                CacheNamespace.SEARCH,
                memory_limit=300,
                memory_ttl=timedelta(hours=1),
                disk_ttl=timedelta(hours=6)
            ),
            NamespaceConfig(
                CacheNamespace.TRIE,
                memory_limit=50,
                memory_ttl=timedelta(days=7),
                disk_ttl=timedelta(days=30),
                compression=CompressionType.LZ4
            ),
            NamespaceConfig(
                CacheNamespace.LEXICON,  # For literature
                memory_limit=50,
                memory_ttl=timedelta(days=30),
                disk_ttl=timedelta(days=90),
                compression=CompressionType.GZIP
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
        """Two-tier get with optional loader."""
        ns = self.namespaces.get(namespace)
        if not ns:
            return None
        
        # L1: Memory cache
        async with ns.lock:
            if key in ns.memory_cache:
                entry = ns.memory_cache[key]
                
                # Check TTL
                if ns.memory_ttl:
                    import time
                    age = time.time() - entry["timestamp"]
                    if age > ns.memory_ttl.total_seconds():
                        del ns.memory_cache[key]
                        ns.stats["evictions"] += 1
                    else:
                        # Move to end for LRU (dict preserves order)
                        del ns.memory_cache[key]
                        ns.memory_cache[key] = entry
                        ns.stats["hits"] += 1
                        return entry["data"]
                else:
                    ns.stats["hits"] += 1
                    return entry["data"]
        
        # L2: Filesystem cache
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
        
        # Cache miss - use loader
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
        """Store in both tiers efficiently."""
        ns = self.namespaces.get(namespace)
        if not ns:
            return
        
        # L1: Memory cache
        import time
        async with ns.lock:
            # LRU eviction
            while len(ns.memory_cache) >= ns.memory_limit:
                # Remove first item (oldest)
                first_key = next(iter(ns.memory_cache))
                del ns.memory_cache[first_key]
                ns.stats["evictions"] += 1
            
            ns.memory_cache[key] = {
                "data": value,
                "timestamp": time.time()
            }
        
        # L2: Filesystem with compression
        backend_key = f"{namespace.value}:{key}"
        ttl = ttl_override or ns.disk_ttl
        
        # Compress if configured
        store_value = value
        if ns.compression:
            store_value = compress_data(value, ns.compression)
        
        await self.l2_backend.set(backend_key, store_value, ttl)
```

### Versioned Data Manager

```python
T = TypeVar('T', bound=BaseVersionedData)


class VersionedDataManager:
    """Manages versioned data with proper typing and performance optimization."""
    
    def __init__(self, cache_manager: GlobalCacheManager):
        self.cache = cache_manager
        self.lock = asyncio.Lock()
    
    async def save(
        self,
        resource_id: str,
        resource_type: ResourceType,
        namespace: CacheNamespace,
        content: Any,
        config: VersionConfig = VersionConfig(),
        metadata: dict[str, Any] | None = None,
        dependencies: list[PydanticObjectId] | None = None,
        parent_id: PydanticObjectId | None = None
    ) -> BaseVersionedData:
        """Save with versioning and optimal serialization."""
        
        # Single serialization with sorted keys
        content_str = json.dumps(content, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        
        # Check for duplicate
        if not config.force_rebuild:
            existing = await self._find_by_hash(resource_id, content_hash)
            if existing:
                return existing
        
        # Get latest for version increment
        latest = None
        if config.increment_version:
            latest = await self.get_latest(
                resource_id, 
                resource_type,
                use_cache=not config.force_rebuild
            )
        
        new_version = config.version or (
            self._increment_version(latest.version_info.version) 
            if latest and config.increment_version 
            else "1.0.0"
        )
        
        # Create versioned instance
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
            metadata={**config.metadata, **(metadata or {})},
            ttl=config.ttl
        )
        
        # Set content with automatic storage strategy
        await versioned.set_content(content)
        
        # Atomic save with version chain update
        async with self.lock:
            if latest and config.increment_version:
                latest.version_info.is_latest = False
                latest.version_info.superseded_by = versioned.id
                await latest.save()
            
            await versioned.save()
            
            # Handle tree structures via TreeCorpusManager
            if parent_id and isinstance(versioned, Corpus):
                from .tree_manager import tree_corpus_manager
                await tree_corpus_manager.update_parent(parent_id, versioned.id)
        
        # Cache if enabled
        if config.use_cache:
            cache_key = f"{resource_type.value}:{resource_id}"
            await self.cache.set(namespace, cache_key, versioned, config.ttl)
        
        return versioned
    
    async def get_latest(
        self,
        resource_id: str,
        resource_type: ResourceType,
        use_cache: bool = True,
        config: VersionConfig = VersionConfig()
    ) -> T | None:
        """Get latest version with proper typing."""
        namespace = self._get_namespace(resource_type)
        
        # Check cache unless forced
        if use_cache and not config.force_rebuild:
            cache_key = f"{resource_type.value}:{resource_id}"
            
            # Handle specific version request
            if config.version:
                cache_key = f"{cache_key}:v{config.version}"
            
            cached = await self.cache.get(namespace, cache_key)
            if cached:
                return cached
        
        # Query database
        model_class = self._get_model_class(resource_type)
        
        if config.version:
            # Get specific version
            result = await model_class.find_one(
                model_class.resource_id == resource_id,
                model_class.version_info.version == config.version
            )
        else:
            # Get latest
            result = await model_class.find_one(
                model_class.resource_id == resource_id,
                model_class.version_info.is_latest == True
            )
        
        # Cache result
        if result and use_cache:
            cache_key = f"{resource_type.value}:{resource_id}"
            if config.version:
                cache_key = f"{cache_key}:v{config.version}"
            await self.cache.set(namespace, cache_key, result, result.ttl)
        
        return result
    
    def _get_model_class(self, resource_type: ResourceType) -> type[BaseVersionedData]:
        """Map resource type enum to model class."""
        mapping = {
            ResourceType.DICTIONARY: DictionaryEntry,
            ResourceType.CORPUS: Corpus,
            ResourceType.SEMANTIC: SemanticIndex,
            ResourceType.LITERATURE: Literature,
            ResourceType.TRIE: TrieIndex,
            ResourceType.SEARCH: SearchIndex
        }
        return mapping[resource_type]
    
    def _get_namespace(self, resource_type: ResourceType) -> CacheNamespace:
        """Map resource type enum to namespace."""
        mapping = {
            ResourceType.DICTIONARY: CacheNamespace.DICTIONARY,
            ResourceType.CORPUS: CacheNamespace.CORPUS,
            ResourceType.SEMANTIC: CacheNamespace.SEMANTIC,
            ResourceType.LITERATURE: CacheNamespace.LEXICON,
            ResourceType.TRIE: CacheNamespace.TRIE,
            ResourceType.SEARCH: CacheNamespace.SEARCH
        }
        return mapping[resource_type]
    
    def _increment_version(self, version: str) -> str:
        """Increment patch version."""
        major, minor, patch = version.split(".")
        return f"{major}.{minor}.{int(patch) + 1}"
```

### Tree Corpus Manager

```python
class TreeCorpusManager:
    """Manages corpus trees with automatic vocabulary aggregation."""
    
    def __init__(self, version_manager: VersionedDataManager):
        self.vm = version_manager
    
    async def create_tree(
        self,
        master_name: str,
        language: Language,
        children: list[dict[str, Any]],
        config: VersionConfig = VersionConfig()
    ) -> Corpus:
        """Create corpus tree with master and children."""
        child_ids: list[PydanticObjectId] = []
        
        # Create children
        for child_config in children:
            child = await self.vm.save(
                resource_id=child_config["id"],
                resource_type=ResourceType.CORPUS,
                namespace=CacheNamespace.CORPUS,
                content=child_config["content"],
                config=config,
                metadata=child_config.get("metadata", {})
            )
            child_ids.append(child.id)
        
        # Create master
        master = await self.vm.save(
            resource_id=master_name,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"vocabulary": []},  # Will be aggregated
            config=config,
            metadata={
                "corpus_type": CorpusType.LANGUAGE.value,
                "is_master": True,
                "language": language.value
            },
            dependencies=child_ids
        )
        
        # Aggregate vocabularies
        await self.aggregate_vocabularies(master.id, child_ids)
        
        return master
    
    async def aggregate_vocabularies(
        self,
        master_id: PydanticObjectId,
        child_ids: list[PydanticObjectId]
    ) -> None:
        """Aggregate child vocabularies into master via set union."""
        master = await Corpus.get(master_id)
        if not master or not master.is_master:
            return
        
        all_vocab: set[str] = set()
        
        for child_id in child_ids:
            child = await Corpus.get(child_id)
            if child:
                vocab = await child.get_vocabulary()
                all_vocab.update(vocab)
        
        # Update master
        master.vocabulary_size = len(all_vocab)
        master.vocabulary_hash = hashlib.sha256(
            "".join(sorted(all_vocab)).encode()
        ).hexdigest()
        
        # Store vocabulary externally if large
        if len(all_vocab) > 10_000:
            from .storage import store_external_content
            master.vocabulary = await store_external_content(
                sorted(list(all_vocab)),
                master.namespace,
                f"corpus:{master.resource_id}:vocab"
            )
        else:
            master.content_inline = {"vocabulary": sorted(list(all_vocab))}
        
        await master.save()
    
    async def update_parent(
        self,
        parent_id: PydanticObjectId,
        child_id: PydanticObjectId
    ) -> None:
        """Update parent when child is added."""
        parent = await Corpus.get(parent_id)
        child = await Corpus.get(child_id)
        
        if parent and child:
            parent.child_corpus_ids.append(child_id)
            child.parent_corpus_id = parent_id
            
            await parent.save()
            await child.save()
            
            if parent.is_master:
                await self.aggregate_vocabularies(
                    parent_id,
                    parent.child_corpus_ids
                )
```

## Helper Functions

### Storage Operations

```python
async def load_external_content(location: ContentLocation) -> Any:
    """Load content from external storage location.
    
    Handles decompression and deserialization efficiently.
    """
    if location.storage_type == StorageType.CACHE:
        # Load from cache backend
        from .cache import global_cache
        backend_key = f"{location.cache_namespace}:{location.cache_key}"
        data = await global_cache.l2_backend.get(backend_key)
    
    elif location.storage_type == StorageType.S3:
        # Load from S3 (implement when needed)
        raise NotImplementedError("S3 backend not yet implemented")
    
    else:
        raise ValueError(f"Unsupported storage type: {location.storage_type}")
    
    # Decompress if needed
    if location.compression and isinstance(data, bytes):
        data = decompress_data(data, location.compression)
    
    # Deserialize based on content type hint
    if isinstance(data, bytes):
        # Check pickle magic bytes for fast path
        if len(data) >= 2 and data[:2] in (b'\x80\x04', b'\x80\x05'):
            return pickle.loads(data)
        # Otherwise assume JSON
        return json.loads(data.decode('utf-8'))
    
    return data


async def store_external_content(
    content: Any,
    namespace: CacheNamespace,
    key: str,
    compression: CompressionType | None = None
) -> ContentLocation:
    """Store content externally with optimal serialization.
    
    Returns ContentLocation metadata for retrieval.
    """
    # Serialize efficiently based on type
    if isinstance(content, BaseModel):
        # Pydantic models: use model_dump for dict conversion
        serialized = json.dumps(content.model_dump(), sort_keys=True).encode()
    elif isinstance(content, (dict, list)):
        # JSON-serializable types
        serialized = json.dumps(content, sort_keys=True).encode()
    else:
        # Everything else: use pickle (fastest for complex objects)
        serialized = pickle.dumps(content, protocol=pickle.HIGHEST_PROTOCOL)
    
    size_bytes = len(serialized)
    
    # Auto-select compression if not specified
    if compression is None:
        if size_bytes < 1024:
            compression = None
        elif size_bytes < 10_000_000:
            compression = CompressionType.ZSTD
        else:
            compression = CompressionType.GZIP
    
    # Compress
    compressed = compress_data(serialized, compression) if compression else serialized
    
    # Store in cache backend
    from .cache import global_cache
    backend_key = f"{namespace.value}:{key}"
    await global_cache.l2_backend.set(backend_key, compressed)
    
    return ContentLocation(
        storage_type=StorageType.CACHE,
        cache_namespace=namespace,
        cache_key=key,
        compression=compression,
        size_bytes=size_bytes,
        size_compressed=len(compressed) if compression else None,
        checksum=hashlib.sha256(serialized).hexdigest()
    )
```

### Compression Utilities

```python
import zstandard as zstd
import lz4.frame
import gzip


def compress_data(data: bytes, compression: CompressionType) -> bytes:
    """Compress data with specified algorithm."""
    if compression == CompressionType.ZSTD:
        cctx = zstd.ZstdCompressor(level=3)
        return cctx.compress(data)
    elif compression == CompressionType.LZ4:
        return lz4.frame.compress(data, compression_level=0)
    elif compression == CompressionType.GZIP:
        return gzip.compress(data, compresslevel=6)
    return data


def decompress_data(data: bytes, compression: CompressionType) -> bytes:
    """Decompress data."""
    if compression == CompressionType.ZSTD:
        dctx = zstd.ZstdDecompressor()
        return dctx.decompress(data)
    elif compression == CompressionType.LZ4:
        return lz4.frame.decompress(data)
    elif compression == CompressionType.GZIP:
        return gzip.decompress(data)
    return data
```

## Global Instance

```python
# Initialize global instances for use throughout application
cache_dir = "/tmp/floridify_cache"
l2_backend = FilesystemBackend(cache_dir)
global_cache = GlobalCacheManager(l2_backend)
version_manager = VersionedDataManager(global_cache)
tree_corpus_manager = TreeCorpusManager(version_manager)
```