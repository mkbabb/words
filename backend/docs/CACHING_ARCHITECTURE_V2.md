# Floridify Caching/Metadata/Versioning Architecture v2.0

## Executive Summary

This document defines a comprehensive rearchitecture of Floridify's data management system, introducing a unified global caching mechanism with in-memory and disk layers, MongoDB-orchestrated metadata with versioning, intelligent compression, and a tree-based corpus hierarchy with atomic cascading operations.

## 1. Data Models

### 1.1 Base Versioned Model

```python
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from beanie import Document, Indexed
from enum import Enum
import hashlib

class StorageType(str, Enum):
    MEMORY = "memory"
    CACHE = "cache"
    DISK = "disk"
    DATABASE = "database"
    S3 = "s3"

class CompressionType(str, Enum):
    NONE = "none"
    ZSTD = "zstd"      # Balanced performance/ratio
    LZ4 = "lz4"        # Speed priority
    GZIP = "gzip"      # Compatibility

class ContentLocation(BaseModel):
    """Abstraction for content storage location"""
    storage_type: StorageType
    cache_namespace: Optional[str] = None
    cache_key: Optional[str] = None
    path: Optional[str] = None  # For disk/S3
    compression: CompressionType = CompressionType.NONE
    size_bytes: int
    size_compressed: Optional[int] = None
    checksum: str  # SHA256 hash

class VersionInfo(BaseModel):
    """Version metadata with semantic versioning"""
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    data_hash: str
    is_latest: bool = True
    superseded_by: Optional[str] = None  # ObjectId as string
    supersedes: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)  # Related version IDs

class BaseVersionedData(Document):
    """Base class for all versioned data"""
    resource_id: Indexed(str)  # Unique identifier
    resource_type: str
    namespace: str
    version_info: VersionInfo
    content_location: Optional[ContentLocation] = None
    content_inline: Optional[Dict[str, Any]] = None  # For small data
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    ttl: Optional[timedelta] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    class Settings:
        name = "versioned_data"
        indexes = [
            [("resource_id", 1), ("version_info.is_latest", -1)],
            [("namespace", 1), ("resource_type", 1)],
            [("version_info.created_at", -1)]
        ]
```

### 1.2 Dictionary Provider Data

```python
class DictionaryVersionedData(BaseVersionedData):
    """Small enough for MongoDB inline storage"""
    resource_type: Literal["dictionary"] = "dictionary"
    word: str
    provider: str
    language: str = "en"
    
    def should_compress(self) -> bool:
        return False  # Small enough to store inline
```

### 1.3 Corpus Models with Tree Structure

```python
class CorpusType(str, Enum):
    BASE = "base"
    LANGUAGE = "language"
    LITERATURE = "literature"
    COMPOSITE = "composite"

class CorpusVersionedData(BaseVersionedData):
    """Corpus with tree-based hierarchy support"""
    resource_type: Literal["corpus"] = "corpus"
    corpus_type: CorpusType
    
    # Tree structure
    parent_corpus_id: Optional[str] = None  # Parent in hierarchy
    child_corpus_ids: List[str] = Field(default_factory=list)
    is_master: bool = False  # Master corpus aggregates children
    
    # Corpus data
    vocabulary_size: int
    vocabulary_hash: str  # Hash of sorted vocabulary
    source_references: List[str] = Field(default_factory=list)
    
    # Statistics
    word_frequencies: Optional[ContentLocation] = None  # Large, store externally
    metadata_stats: Dict[str, Any] = Field(default_factory=dict)
    
    def should_compress(self) -> bool:
        return self.vocabulary_size > 10000

class LanguageCorpusVersionedData(CorpusVersionedData):
    """Language-level corpus aggregating multiple sources"""
    corpus_type: Literal[CorpusType.LANGUAGE] = CorpusType.LANGUAGE
    language: str
    dialect: Optional[str] = None
    
    # Aggregated from children
    total_documents: int = 0
    total_tokens: int = 0
    unique_sources: List[str] = Field(default_factory=list)

class LiteratureCorpusVersionedData(CorpusVersionedData):
    """Literature-specific corpus"""
    corpus_type: Literal[CorpusType.LITERATURE] = CorpusType.LITERATURE
    
    # FK to LiteratureProviderData
    literature_data_ids: List[str] = Field(default_factory=list)
    
    # Aggregated metadata
    authors: List[str] = Field(default_factory=list)
    time_periods: List[str] = Field(default_factory=list)
    genres: List[str] = Field(default_factory=list)
```

### 1.4 Semantic Index

```python
class SemanticIndexVersionedData(BaseVersionedData):
    """Semantic search indices - always large, disk storage"""
    resource_type: Literal["semantic"] = "semantic"
    
    # FK to corpus
    corpus_id: str  # Must reference a CorpusVersionedData
    corpus_version: str  # Track specific corpus version
    
    # Index properties
    model_name: str
    embedding_dimension: int
    index_type: str = "faiss"  # faiss, annoy, etc.
    quantization: Optional[str] = None  # "float16", "int8", etc.
    
    # Always stored externally due to size
    content_location: ContentLocation  # Required, not optional
    
    # Performance metrics
    build_time_seconds: float
    memory_usage_mb: float
    
    def should_compress(self) -> bool:
        return False  # Already optimized at creation
```

### 1.5 Literature Provider Data

```python
class LiteratureVersionedData(BaseVersionedData):
    """Literature works - almost always large"""
    resource_type: Literal["literature"] = "literature"
    
    # Metadata
    title: str
    authors: List[str]
    publication_year: Optional[int] = None
    source: str  # gutenberg, archive, etc.
    
    # Content management
    text_hash: str
    text_size_bytes: int
    
    # Statistics
    word_count: int
    unique_words: int
    readability_score: Optional[float] = None
    
    def should_compress(self) -> bool:
        return self.text_size_bytes > 1024  # Compress anything > 1KB
```

### 1.6 Trie Index

```python
class TrieIndexVersionedData(BaseVersionedData):
    """Trie indices for fast prefix search"""
    resource_type: Literal["trie"] = "trie"
    
    # Can be built from multiple corpora
    corpus_ids: List[str]  # Source corpora
    
    # Index properties
    node_count: int
    max_depth: int
    supports_fuzzy: bool = False
    
    def should_compress(self) -> bool:
        return self.node_count > 10000
```

### 1.7 Search Index (Composite)

```python
class SearchIndexVersionedData(BaseVersionedData):
    """Composite search index aggregating multiple indices"""
    resource_type: Literal["search"] = "search"
    
    # Component indices
    trie_index_id: Optional[str] = None
    semantic_index_id: Optional[str] = None
    corpus_id: str  # Primary corpus
    
    # Cascading version tracking
    component_versions: Dict[str, str] = Field(default_factory=dict)
    
    # Search configuration
    search_config: Dict[str, Any] = Field(default_factory=dict)
    supported_languages: List[str] = Field(default_factory=list)
```

## 2. Core Classes

### 2.1 Global Cache Manager

```python
from typing import TypeVar, Optional, Dict, Any, List, Tuple
from asyncio import Lock
import asyncio
from collections import OrderedDict
import time

T = TypeVar('T')

class CacheNamespace:
    """Namespace configuration"""
    def __init__(
        self,
        name: str,
        memory_limit: int = 100,
        memory_ttl: Optional[timedelta] = None,
        disk_ttl: Optional[timedelta] = None,
        compression: CompressionType = CompressionType.NONE
    ):
        self.name = name
        self.memory_limit = memory_limit
        self.memory_ttl = memory_ttl
        self.disk_ttl = disk_ttl
        self.compression = compression
        self.memory_cache: OrderedDict = OrderedDict()
        self.lock = Lock()

class GlobalCacheManager:
    """Unified global cache with two-tier architecture"""
    
    def __init__(self, cache_dir: str = "/tmp/floridify_cache"):
        self.namespaces: Dict[str, CacheNamespace] = {}
        self.disk_cache = None  # DiskCache instance
        self.cache_dir = cache_dir
        self._init_disk_cache()
        
    def register_namespace(self, namespace: CacheNamespace) -> None:
        """Register a cache namespace with configuration"""
        self.namespaces[namespace.name] = namespace
    
    async def get(
        self,
        namespace: str,
        key: str,
        loader_func: Optional[callable] = None
    ) -> Optional[T]:
        """Two-tier cache get with optional loader"""
        ns = self.namespaces.get(namespace)
        if not ns:
            return None
            
        # L1: Memory cache
        async with ns.lock:
            if key in ns.memory_cache:
                # LRU: Move to end
                ns.memory_cache.move_to_end(key)
                entry = ns.memory_cache[key]
                
                # Check TTL
                if ns.memory_ttl and self._is_expired(entry, ns.memory_ttl):
                    del ns.memory_cache[key]
                else:
                    return entry['data']
        
        # L2: Disk cache
        disk_key = f"{namespace}:{key}"
        disk_data = await self._get_from_disk(disk_key, ns.disk_ttl)
        
        if disk_data is not None:
            # Promote to memory
            await self._promote_to_memory(ns, key, disk_data)
            return disk_data
            
        # Cache miss - use loader if provided
        if loader_func:
            data = await loader_func()
            if data is not None:
                await self.set(namespace, key, data)
            return data
            
        return None
    
    async def set(
        self,
        namespace: str,
        key: str,
        value: T,
        ttl_override: Optional[timedelta] = None
    ) -> None:
        """Set value in both cache tiers"""
        ns = self.namespaces.get(namespace)
        if not ns:
            return
            
        # Compress if needed
        compressed_value = self._compress_if_needed(value, ns)
        
        # L1: Memory cache
        async with ns.lock:
            # Evict if at limit
            while len(ns.memory_cache) >= ns.memory_limit:
                ns.memory_cache.popitem(last=False)  # LRU eviction
                
            ns.memory_cache[key] = {
                'data': value,
                'timestamp': time.time(),
                'compressed': compressed_value is not None
            }
        
        # L2: Disk cache
        disk_key = f"{namespace}:{key}"
        ttl = ttl_override or ns.disk_ttl
        await self._set_to_disk(disk_key, compressed_value or value, ttl)
    
    async def invalidate(
        self,
        namespace: str,
        key: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> int:
        """Invalidate cache entries"""
        ns = self.namespaces.get(namespace)
        if not ns:
            return 0
            
        count = 0
        
        # Specific key invalidation
        if key:
            async with ns.lock:
                if key in ns.memory_cache:
                    del ns.memory_cache[key]
                    count += 1
            
            disk_key = f"{namespace}:{key}"
            if await self._delete_from_disk(disk_key):
                count += 1
                
        # Pattern-based invalidation
        elif pattern:
            # Memory cache
            async with ns.lock:
                keys_to_delete = [
                    k for k in ns.memory_cache
                    if self._matches_pattern(k, pattern)
                ]
                for k in keys_to_delete:
                    del ns.memory_cache[k]
                    count += 1
            
            # Disk cache
            count += await self._invalidate_disk_pattern(namespace, pattern)
            
        return count
    
    async def get_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Get cache statistics"""
        if namespace:
            ns = self.namespaces.get(namespace)
            if ns:
                return {
                    'namespace': namespace,
                    'memory_items': len(ns.memory_cache),
                    'memory_limit': ns.memory_limit,
                    'memory_ttl': ns.memory_ttl,
                    'disk_ttl': ns.disk_ttl
                }
        else:
            # Global stats
            return {
                'namespaces': list(self.namespaces.keys()),
                'total_memory_items': sum(
                    len(ns.memory_cache) for ns in self.namespaces.values()
                ),
                'disk_size_mb': self._get_disk_size_mb()
            }
    
    # Private helper methods
    def _compress_if_needed(self, value: Any, ns: CacheNamespace) -> Optional[bytes]:
        """Compress value based on namespace configuration"""
        if ns.compression == CompressionType.NONE:
            return None
        return compress_data(value, ns.compression)
    
    def _is_expired(self, entry: Dict, ttl: timedelta) -> bool:
        """Check if cache entry is expired"""
        age = time.time() - entry['timestamp']
        return age > ttl.total_seconds()
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (glob-style)"""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
```

### 2.2 Enhanced Versioned Data Manager

```python
class VersionedDataManager:
    """Manager for all versioned data operations with tree support"""
    
    def __init__(self, cache_manager: GlobalCacheManager):
        self.cache_manager = cache_manager
        self.operation_lock = Lock()
    
    async def save(
        self,
        resource_id: str,
        resource_type: str,
        namespace: str,
        content: Any,
        metadata: Optional[Dict] = None,
        dependencies: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
        ttl: Optional[timedelta] = None
    ) -> BaseVersionedData:
        """Save versioned data with automatic versioning"""
        
        # Calculate content hash
        content_hash = self._calculate_hash(content)
        
        # Check for existing version with same hash (deduplication)
        existing = await self._find_by_hash(resource_id, content_hash)
        if existing:
            return existing
        
        # Get latest version for increment
        latest = await self.get_latest(resource_id, resource_type)
        new_version = self._increment_version(latest.version_info.version if latest else "0.0.0")
        
        # Determine storage strategy
        storage_location = await self._store_content(
            resource_id, resource_type, content, namespace
        )
        
        # Create versioned data
        model_class = self._get_model_class(resource_type)
        versioned_data = model_class(
            resource_id=resource_id,
            resource_type=resource_type,
            namespace=namespace,
            version_info=VersionInfo(
                version=new_version,
                data_hash=content_hash,
                is_latest=True,
                supersedes=str(latest.id) if latest else None,
                dependencies=dependencies or []
            ),
            content_location=storage_location if storage_location else None,
            content_inline=content if not storage_location else None,
            metadata=metadata or {},
            ttl=ttl
        )
        
        # Atomic update with parent
        async with self.operation_lock:
            # Mark previous as not latest
            if latest:
                latest.version_info.is_latest = False
                latest.version_info.superseded_by = str(versioned_data.id)
                await latest.save()
            
            # Save new version
            await versioned_data.save()
            
            # Update parent if tree structure
            if parent_id and hasattr(versioned_data, 'parent_corpus_id'):
                await self._update_parent_corpus(parent_id, str(versioned_data.id))
        
        # Cache the new version
        cache_key = generate_cache_key(resource_id, resource_type)
        await self.cache_manager.set(namespace, cache_key, versioned_data, ttl)
        
        return versioned_data
    
    async def save_batch(
        self,
        items: List[Tuple[str, str, str, Any, Dict]],
        atomic: bool = True
    ) -> List[BaseVersionedData]:
        """Batch save with optional atomicity"""
        
        if atomic:
            async with self.operation_lock:
                results = []
                try:
                    for resource_id, resource_type, namespace, content, metadata in items:
                        result = await self.save(
                            resource_id, resource_type, namespace, 
                            content, metadata
                        )
                        results.append(result)
                    return results
                except Exception as e:
                    # Rollback on failure
                    for result in results:
                        await result.delete()
                    raise e
        else:
            # Non-atomic batch
            tasks = [
                self.save(resource_id, resource_type, namespace, content, metadata)
                for resource_id, resource_type, namespace, content, metadata in items
            ]
            return await asyncio.gather(*tasks)
    
    async def get_latest(
        self,
        resource_id: str,
        resource_type: str,
        use_cache: bool = True
    ) -> Optional[BaseVersionedData]:
        """Get latest version of a resource"""
        
        if use_cache:
            cache_key = generate_cache_key(resource_id, resource_type)
            cached = await self.cache_manager.get(
                resource_type, cache_key
            )
            if cached:
                return cached
        
        # Query database
        model_class = self._get_model_class(resource_type)
        result = await model_class.find_one(
            model_class.resource_id == resource_id,
            model_class.version_info.is_latest == True
        )
        
        if result and use_cache:
            # Cache the result
            await self.cache_manager.set(
                resource_type, 
                generate_cache_key(resource_id, resource_type),
                result,
                result.ttl
            )
        
        return result
    
    async def cascade_rebuild(
        self,
        resource_id: str,
        resource_type: str
    ) -> Dict[str, List[str]]:
        """Rebuild resource and all dependencies"""
        
        rebuilt = {'direct': [], 'cascaded': []}
        
        # Get the resource
        resource = await self.get_latest(resource_id, resource_type)
        if not resource:
            return rebuilt
        
        # Track what needs rebuilding
        to_rebuild = set()
        visited = set()
        
        async def collect_dependencies(res_id: str, res_type: str):
            if res_id in visited:
                return
            visited.add(res_id)
            
            res = await self.get_latest(res_id, res_type)
            if res and res.version_info.dependencies:
                for dep_id in res.version_info.dependencies:
                    to_rebuild.add(dep_id)
                    # Recursively collect
                    dep_res = await self._get_by_id(dep_id)
                    if dep_res:
                        await collect_dependencies(
                            dep_res.resource_id,
                            dep_res.resource_type
                        )
        
        # Collect all dependencies
        await collect_dependencies(resource_id, resource_type)
        
        # Rebuild in order (leaves first)
        async with self.operation_lock:
            # Increment version of main resource
            new_version = self._increment_version(resource.version_info.version)
            resource.version_info.version = new_version
            await resource.save()
            rebuilt['direct'].append(resource_id)
            
            # Cascade to dependencies
            for dep_id in to_rebuild:
                dep = await self._get_by_id(dep_id)
                if dep:
                    new_dep_version = self._increment_version(dep.version_info.version)
                    dep.version_info.version = new_dep_version
                    await dep.save()
                    rebuilt['cascaded'].append(dep.resource_id)
        
        return rebuilt
    
    async def cleanup_versions(
        self,
        resource_id: str,
        resource_type: str,
        keep_count: int = 5
    ) -> int:
        """Clean up old versions keeping the latest N"""
        
        model_class = self._get_model_class(resource_type)
        
        # Get all versions sorted by creation date
        versions = await model_class.find(
            model_class.resource_id == resource_id
        ).sort(-model_class.version_info.created_at).to_list()
        
        if len(versions) <= keep_count:
            return 0
        
        # Delete old versions
        to_delete = versions[keep_count:]
        deleted_count = 0
        
        for version in to_delete:
            # Clean up storage
            if version.content_location:
                await self._cleanup_storage(version.content_location)
            
            # Invalidate cache
            cache_key = generate_cache_key(
                version.resource_id,
                version.resource_type,
                version.version_info.version
            )
            await self.cache_manager.invalidate(
                version.namespace, cache_key
            )
            
            # Delete from database
            await version.delete()
            deleted_count += 1
        
        return deleted_count
    
    # Tree operations for corpus hierarchy
    async def update_master_corpus(
        self,
        master_id: str,
        child_updates: List[str]
    ) -> CorpusVersionedData:
        """Update master corpus when children change"""
        
        master = await self.get_latest(master_id, "corpus")
        if not master or not isinstance(master, CorpusVersionedData):
            raise ValueError(f"Master corpus {master_id} not found")
        
        # Collect all child vocabularies
        all_vocab = set()
        all_frequencies = {}
        
        for child_id in master.child_corpus_ids:
            child = await self.get_latest(child_id, "corpus")
            if child and isinstance(child, CorpusVersionedData):
                # Load child vocabulary
                child_vocab = await self._load_corpus_vocabulary(child)
                all_vocab.update(child_vocab)
                
                # Aggregate frequencies
                if child.word_frequencies:
                    child_freq = await self._load_content(child.word_frequencies)
                    for word, freq in child_freq.items():
                        all_frequencies[word] = all_frequencies.get(word, 0) + freq
        
        # Create new master version
        new_master_content = {
            'vocabulary': sorted(list(all_vocab)),
            'frequencies': all_frequencies,
            'child_updates': child_updates,
            'update_time': datetime.utcnow()
        }
        
        return await self.save(
            master_id,
            "corpus",
            master.namespace,
            new_master_content,
            metadata={
                'vocabulary_size': len(all_vocab),
                'child_count': len(master.child_corpus_ids)
            },
            dependencies=master.child_corpus_ids
        )
    
    # Private helper methods
    def _get_model_class(self, resource_type: str):
        """Get the appropriate model class for resource type"""
        mapping = {
            'dictionary': DictionaryVersionedData,
            'corpus': CorpusVersionedData,
            'semantic': SemanticIndexVersionedData,
            'literature': LiteratureVersionedData,
            'trie': TrieIndexVersionedData,
            'search': SearchIndexVersionedData
        }
        return mapping.get(resource_type, BaseVersionedData)
    
    def _calculate_hash(self, content: Any) -> str:
        """Calculate SHA256 hash of content"""
        import json
        if isinstance(content, dict):
            content_str = json.dumps(content, sort_keys=True)
        else:
            content_str = str(content)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def _increment_version(self, version: str) -> str:
        """Increment semantic version (patch level)"""
        parts = version.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        return '.'.join(parts)
```

### 2.3 Tree-Based Corpus Manager

```python
class TreeCorpusManager:
    """Manages tree-structured corpus hierarchies"""
    
    def __init__(self, version_manager: VersionedDataManager):
        self.version_manager = version_manager
    
    async def create_corpus_tree(
        self,
        master_name: str,
        children: List[Dict[str, Any]]
    ) -> CorpusVersionedData:
        """Create a corpus tree with master and children"""
        
        # Create child corpora
        child_ids = []
        for child_config in children:
            child = await self.version_manager.save(
                resource_id=child_config['id'],
                resource_type='corpus',
                namespace='corpus',
                content=child_config['content'],
                metadata=child_config.get('metadata', {})
            )
            child_ids.append(str(child.id))
        
        # Create master corpus
        master_content = {
            'vocabulary': [],  # Will be populated from children
            'is_master': True,
            'child_corpus_ids': child_ids
        }
        
        master = await self.version_manager.save(
            resource_id=master_name,
            resource_type='corpus',
            namespace='corpus',
            content=master_content,
            metadata={'corpus_type': 'master'},
            dependencies=child_ids
        )
        
        # Update children with parent reference
        for child_id in child_ids:
            child = await self.version_manager.get_latest(child_id, 'corpus')
            if child and isinstance(child, CorpusVersionedData):
                child.parent_corpus_id = str(master.id)
                await child.save()
        
        # Populate master vocabulary
        await self.version_manager.update_master_corpus(
            master_name, child_ids
        )
        
        return master
    
    async def add_to_corpus_tree(
        self,
        master_id: str,
        new_child: Dict[str, Any]
    ) -> CorpusVersionedData:
        """Add a new child to existing corpus tree"""
        
        master = await self.version_manager.get_latest(master_id, 'corpus')
        if not master or not isinstance(master, CorpusVersionedData):
            raise ValueError(f"Master corpus {master_id} not found")
        
        # Create new child
        child = await self.version_manager.save(
            resource_id=new_child['id'],
            resource_type='corpus',
            namespace='corpus',
            content=new_child['content'],
            metadata=new_child.get('metadata', {}),
            parent_id=master_id
        )
        
        # Update master
        master.child_corpus_ids.append(str(child.id))
        await master.save()
        
        # Update master vocabulary
        return await self.version_manager.update_master_corpus(
            master_id, [str(child.id)]
        )
    
    async def get_corpus_tree(
        self,
        master_id: str,
        include_children: bool = True
    ) -> Dict[str, Any]:
        """Get full corpus tree structure"""
        
        master = await self.version_manager.get_latest(master_id, 'corpus')
        if not master or not isinstance(master, CorpusVersionedData):
            return None
        
        tree = {
            'master': master.dict(),
            'children': []
        }
        
        if include_children:
            for child_id in master.child_corpus_ids:
                child = await self.version_manager.get_latest(child_id, 'corpus')
                if child:
                    tree['children'].append(child.dict())
        
        return tree
```

## 3. Helper Functions

### 3.1 Cache Key Generation

```python
def generate_cache_key(
    resource_id: str,
    resource_type: str,
    version: Optional[str] = None,
    **kwargs
) -> str:
    """Generate consistent cache keys"""
    
    parts = [resource_type, resource_id]
    
    if version:
        parts.append(f"v{version}")
    
    # Add any additional parameters
    for key, value in sorted(kwargs.items()):
        if value is not None:
            parts.append(f"{key}:{value}")
    
    return ":".join(parts)

def generate_tree_cache_key(
    master_id: str,
    child_ids: List[str],
    operation: str = "aggregate"
) -> str:
    """Generate cache key for tree operations"""
    
    # Sort child IDs for consistency
    sorted_children = sorted(child_ids)
    children_hash = hashlib.md5(
        ":".join(sorted_children).encode()
    ).hexdigest()[:8]
    
    return f"tree:{master_id}:{operation}:{children_hash}"
```

### 3.2 Compression Utilities

```python
import zstandard as zstd
import lz4.frame
import gzip
import pickle
import json
import msgspec

def compress_data(
    data: Any,
    compression_type: CompressionType
) -> bytes:
    """Compress data with specified algorithm"""
    
    # Serialize first
    if isinstance(data, (dict, list)):
        serialized = msgspec.json.encode(data)
    else:
        serialized = pickle.dumps(data)
    
    # Apply compression
    if compression_type == CompressionType.ZSTD:
        cctx = zstd.ZstdCompressor(level=3)
        return cctx.compress(serialized)
    
    elif compression_type == CompressionType.LZ4:
        return lz4.frame.compress(serialized)
    
    elif compression_type == CompressionType.GZIP:
        return gzip.compress(serialized, compresslevel=6)
    
    else:  # NONE
        return serialized

def decompress_data(
    compressed: bytes,
    compression_type: CompressionType,
    expected_type: Optional[type] = None
) -> Any:
    """Decompress data with specified algorithm"""
    
    # Decompress
    if compression_type == CompressionType.ZSTD:
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed)
    
    elif compression_type == CompressionType.LZ4:
        decompressed = lz4.frame.decompress(compressed)
    
    elif compression_type == CompressionType.GZIP:
        decompressed = gzip.decompress(compressed)
    
    else:  # NONE
        decompressed = compressed
    
    # Deserialize
    try:
        # Try msgspec first (fastest)
        if expected_type:
            return msgspec.json.decode(decompressed, type=expected_type)
        else:
            return msgspec.json.decode(decompressed)
    except:
        # Fall back to pickle
        return pickle.loads(decompressed)

def select_compression(
    data: Any,
    size_bytes: int
) -> CompressionType:
    """Intelligently select compression based on data characteristics"""
    
    # No compression for small data
    if size_bytes < 1024:
        return CompressionType.NONE
    
    # Fast compression for real-time data
    if isinstance(data, dict) and 'real_time' in data:
        return CompressionType.LZ4
    
    # Balanced compression for most data
    if size_bytes < 1_000_000:  # < 1MB
        return CompressionType.ZSTD
    
    # Maximum compression for large data
    return CompressionType.GZIP
```

### 3.3 Cascading Operations

```python
async def cascade_operation(
    version_manager: VersionedDataManager,
    root_id: str,
    root_type: str,
    operation: callable,
    visited: Optional[set] = None
) -> Dict[str, Any]:
    """Execute operation with intelligent cascading"""
    
    if visited is None:
        visited = set()
    
    if root_id in visited:
        return {'skipped': root_id, 'reason': 'already_visited'}
    
    visited.add(root_id)
    results = {'root': root_id, 'cascaded': []}
    
    # Get the root resource
    root = await version_manager.get_latest(root_id, root_type)
    if not root:
        return {'error': f'Resource {root_id} not found'}
    
    # Execute operation on root
    try:
        result = await operation(root)
        results['result'] = result
    except Exception as e:
        results['error'] = str(e)
        return results
    
    # Cascade to dependencies
    if root.version_info.dependencies:
        for dep_id in root.version_info.dependencies:
            dep_result = await cascade_operation(
                version_manager,
                dep_id,
                root_type,  # Assume same type for now
                operation,
                visited
            )
            results['cascaded'].append(dep_result)
    
    # Special handling for tree structures
    if hasattr(root, 'child_corpus_ids') and root.child_corpus_ids:
        for child_id in root.child_corpus_ids:
            child_result = await cascade_operation(
                version_manager,
                child_id,
                'corpus',
                operation,
                visited
            )
            results['cascaded'].append(child_result)
    
    return results

async def atomic_multi_operation(
    version_manager: VersionedDataManager,
    operations: List[Tuple[str, str, callable]],
    rollback_on_failure: bool = True
) -> Dict[str, Any]:
    """Execute multiple operations atomically"""
    
    results = []
    rollback_stack = []
    
    async with version_manager.operation_lock:
        try:
            for resource_id, resource_type, operation in operations:
                # Save current state for rollback
                if rollback_on_failure:
                    current = await version_manager.get_latest(
                        resource_id, resource_type
                    )
                    if current:
                        rollback_stack.append(current.dict())
                
                # Execute operation
                result = await operation(resource_id, resource_type)
                results.append({
                    'resource_id': resource_id,
                    'resource_type': resource_type,
                    'success': True,
                    'result': result
                })
                
        except Exception as e:
            # Rollback if requested
            if rollback_on_failure:
                for saved_state in reversed(rollback_stack):
                    # Restore previous state
                    model_class = version_manager._get_model_class(
                        saved_state['resource_type']
                    )
                    restored = model_class(**saved_state)
                    await restored.save()
            
            return {
                'success': False,
                'error': str(e),
                'partial_results': results,
                'rolled_back': rollback_on_failure
            }
    
    return {
        'success': True,
        'results': results
    }
```

### 3.4 Cleanup and Retention

```python
async def cleanup_namespace(
    cache_manager: GlobalCacheManager,
    version_manager: VersionedDataManager,
    namespace: str,
    retention_policy: Dict[str, int]
) -> Dict[str, int]:
    """Clean up a namespace with retention policy"""
    
    cleanup_stats = {
        'cache_invalidated': 0,
        'versions_deleted': 0,
        'storage_freed_mb': 0
    }
    
    # Get all resource types in namespace
    resource_types = retention_policy.keys()
    
    for resource_type in resource_types:
        keep_count = retention_policy[resource_type]
        
        # Find all resources of this type
        model_class = version_manager._get_model_class(resource_type)
        resources = await model_class.find(
            model_class.namespace == namespace
        ).distinct('resource_id')
        
        # Clean up each resource
        for resource_id in resources:
            deleted = await version_manager.cleanup_versions(
                resource_id,
                resource_type,
                keep_count
            )
            cleanup_stats['versions_deleted'] += deleted
    
    # Clean up cache
    invalidated = await cache_manager.invalidate(namespace, pattern="*")
    cleanup_stats['cache_invalidated'] = invalidated
    
    # Calculate freed storage
    # (Implementation depends on storage backend)
    
    return cleanup_stats

def get_default_retention_policy() -> Dict[str, int]:
    """Get default retention counts by resource type"""
    return {
        'dictionary': 5,
        'corpus': 3,
        'semantic': 5,
        'literature': 3,
        'trie': 5,
        'search': 10
    }

async def scheduled_cleanup(
    cache_manager: GlobalCacheManager,
    version_manager: VersionedDataManager,
    interval_hours: int = 24
):
    """Scheduled cleanup task"""
    
    while True:
        await asyncio.sleep(interval_hours * 3600)
        
        try:
            # Clean up each namespace
            for namespace in cache_manager.namespaces.keys():
                await cleanup_namespace(
                    cache_manager,
                    version_manager,
                    namespace,
                    get_default_retention_policy()
                )
        except Exception as e:
            # Log error but don't stop scheduler
            print(f"Cleanup error: {e}")
```

## 4. Implementation Plan

### Phase 1: Foundation (Core Infrastructure)
**Objective**: Establish base architecture without breaking existing functionality

1. **Create new models module** (`models/v2/`)
   - Implement `BaseVersionedData` and all specialized models
   - Add tree structure support for corpus hierarchy
   - Define storage abstractions

2. **Implement GlobalCacheManager**
   - Two-tier cache with namespace support
   - Memory LRU + disk persistence
   - Pattern-based invalidation

3. **Build VersionedDataManager**
   - Save/retrieve with deduplication
   - Version chain management
   - Tree operations for corpus

**Testing**: Unit tests for all new components
**Risk Mitigation**: Run parallel to existing system

### Phase 2: Migration Layer
**Objective**: Create compatibility bridge between old and new systems

1. **Adapter classes**
   - Map old manager interfaces to new
   - Data migration utilities
   - Backwards compatibility layer

2. **Gradual migration**
   - Start with DictionaryProviderData (smallest)
   - Move to Corpus and tree structures
   - Finally migrate large indices

3. **Validation**
   - Data integrity checks
   - Performance benchmarks
   - A/B testing with old system

**Testing**: Integration tests with existing codebase
**Risk Mitigation**: Rollback capabilities at each step

### Phase 3: Advanced Features
**Objective**: Implement sophisticated capabilities

1. **Tree corpus management**
   - Master/child relationships
   - Automatic vocabulary aggregation
   - Cascading updates

2. **Atomic operations**
   - Multi-resource transactions
   - Rollback support
   - Dependency tracking

3. **Performance optimization**
   - Intelligent compression selection
   - Parallel batch operations
   - Cache warming strategies

**Testing**: Load testing and performance profiling
**Risk Mitigation**: Feature flags for gradual rollout

### Phase 4: Production Deployment
**Objective**: Complete migration and optimize

1. **Final migration**
   - Migrate remaining components
   - Remove old system code
   - Update all dependencies

2. **Monitoring and optimization**
   - Cache hit rate monitoring
   - Storage usage analytics
   - Performance tuning

3. **Documentation**
   - API documentation
   - Migration guide
   - Best practices

**Testing**: Full system integration tests
**Risk Mitigation**: Staged rollout with monitoring

## 5. Performance Considerations

### Expected Performance Characteristics

- **Cache Hit Rates**: 80-90% for hot data
- **Compression Ratios**: 3-10x for text, 2-5x for structured data
- **Version Deduplication**: 20-40% storage savings
- **Tree Operations**: O(log n) for updates, O(1) for lookups
- **Batch Operations**: 10-100x speedup over sequential

### Optimization Strategies

1. **Cache Warming**: Pre-populate frequently accessed items
2. **Compression Tuning**: Algorithm selection based on data type
3. **Index Optimization**: MongoDB compound indices for common queries
4. **Parallel Processing**: Async operations for independent resources
5. **Memory Management**: Adaptive limits based on usage patterns

## Conclusion

This architecture provides a robust, performant, and elegant solution for Floridify's data management needs. It builds upon the existing excellent foundation while adding sophisticated tree structures, atomic operations, and intelligent caching. The phased implementation plan ensures minimal disruption while delivering immediate benefits at each stage.