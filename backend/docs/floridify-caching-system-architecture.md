# Floridify Caching/Metadata/Versioning System Architecture

## Executive Summary

This document synthesizes a comprehensive solution for the Floridify caching, metadata, and versioning system rearchitecture. The design follows KISS and DRY principles while providing powerful features for global caching, versioning, tree-like corpus structures, and atomic operations.

## Current State Analysis

Based on the existing codebase, Floridify already has:

1. **Unified Cache System** (`unified.py`) - Two-tier caching with per-namespace memory limits
2. **Versioned Data Management** (`versioned.py`) - Full versioning with deduplication and storage abstraction  
3. **Base Manager Pattern** (`manager.py`) - Abstract base for resource managers
4. **Compression Support** - Automatic compression with metadata tracking
5. **Model Hierarchy** - Specialized versioned data types for different resource types

The system is well-architected but needs refinement in data models, class hierarchies, and implementation strategy.

## 1. Data Models

### 1.1 Core Versioned Data Models

```python
# Enhanced base model with improved tree relationships
class VersionedData(Document, BaseMetadata):
    """Enhanced base class for all versioned data with tree support."""
    
    # Core identification
    resource_id: str = Field(description="Unique identifier for the resource")
    resource_type: str = Field(description="Type of resource")
    
    # Tree relationships for corpus hierarchy
    parent_id: PydanticObjectId | None = None  # Parent resource
    children_ids: list[PydanticObjectId] = Field(default_factory=list)  # Child resources
    depth_level: int = 0  # Tree depth for efficient queries
    
    # Enhanced versioning with cascading support
    version_info: VersionInfo
    cascade_on_update: bool = False  # Whether updates cascade to children
    
    # Content storage with compression metadata
    content_location: ContentLocation | None = None
    content_inline: dict[str, Any] | None = None
    compression_metadata: CacheMetadata | None = None
    
    # Enhanced metadata and relationships
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    dependencies: list[PydanticObjectId] = Field(default_factory=list)  # Resource dependencies
    
    class Settings:
        name = "versioned_data"
        is_root = True
        indexes = [
            [("resource_id", 1), ("resource_type", 1), ("version_info.is_latest", -1)],
            [("parent_id", 1), ("depth_level", 1)],  # Tree navigation
            [("resource_type", 1), ("depth_level", 1)],  # Type + level queries
            "dependencies",  # Dependency tracking
            "tags",
        ]
```

### 1.2 Specialized Data Models

```python
class DictionaryProviderData(VersionedData):
    """Enhanced dictionary provider data with caching optimization."""
    
    word_id: PydanticObjectId
    word_text: str
    provider: DictionaryProvider
    language: Language = Language.ENGLISH
    
    # Provider-specific metadata
    api_version: str | None = None
    response_size_bytes: int | None = None
    
    # Cache optimization
    lookup_frequency: int = 0  # Track usage for cache prioritization
    last_accessed: datetime | None = None
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "dictionary")
        super().__init__(**data)

class Corpus(VersionedData):
    """Enhanced corpus with tree hierarchy support."""
    
    corpus_name: str
    language: Language
    corpus_type: CorpusType = CorpusType.LEXICON
    
    # Tree hierarchy for master/child relationships
    is_master_corpus: bool = False
    child_corpora_ids: list[PydanticObjectId] = Field(default_factory=list)
    
    # Vocabulary statistics for cache sizing
    unique_word_count: int = 0
    total_word_count: int = 0
    vocabulary_hash: str | None = None  # For deduplication
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "corpus")
        super().__init__(**data)

class SemanticIndex(VersionedData):
    """Semantic search index with optimized caching."""
    
    corpus_id: PydanticObjectId
    model_name: str = Field(..., description="Sentence transformer model")
    embedding_dimension: int = Field(..., description="Embedding dimensions")
    
    # Index statistics for cache management
    index_size_mb: float | None = None
    query_count: int = 0
    average_query_time_ms: float | None = None
    
    # Quantization support
    quantization_type: QuantizationType = QuantizationType.FLOAT32
    quantization_ratio: float = 1.0
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "semantic")
        super().__init__(**data)

class LiteratureProviderData(VersionedData):
    """Literature corpus data with hierarchy support."""
    
    corpus_id: PydanticObjectId
    author: AuthorInfo
    source: LiteratureSource
    
    # Hierarchy support for author -> work -> chapter structure
    work_hierarchy: dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "literature")
        super().__init__(**data)

class LiteratureCorpus(Corpus):
    """Literature-specific corpus with enhanced metadata."""
    
    author_info: AuthorInfo
    period: str | None = None
    genre: str | None = None
    work_count: int = 0
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("corpus_type", CorpusType.LITERATURE)
        super().__init__(**data)

class LanguageCorpus(Corpus):
    """Language-specific corpus with linguistic metadata."""
    
    dialect: str | None = None
    register: str | None = None  # formal, informal, academic, etc.
    source_types: list[str] = Field(default_factory=list)  # news, literature, web, etc.
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("corpus_type", CorpusType.LANGUAGE)
        super().__init__(**data)

class TrieIndex(VersionedData):
    """Trie index for fast prefix searches."""
    
    corpus_id: PydanticObjectId
    language: Language
    
    # Trie statistics
    node_count: int = 0
    max_depth: int = 0
    compression_enabled: bool = True
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "trie")
        super().__init__(**data)

class SearchIndex(VersionedData):
    """General search index with multiple search method support."""
    
    corpus_id: PydanticObjectId
    search_methods: list[str] = Field(default_factory=list)  # exact, fuzzy, semantic, etc.
    
    # Performance metrics
    index_build_time_seconds: float | None = None
    average_search_time_ms: float | None = None
    
    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "search")
        super().__init__(**data)
```

## 2. Class Hierarchy

### 2.1 Enhanced Cache Manager

```python
class GlobalCacheManager:
    """Global cache manager with namespace support and atomic operations."""
    
    def __init__(self):
        self._unified_cache: UnifiedCache | None = None
        self._namespace_managers: dict[CacheNamespace, VersionedDataManager] = {}
        self._atomic_locks: dict[str, asyncio.Lock] = {}
        self._dependency_graph: dict[str, set[str]] = {}
    
    async def get_cache(self) -> UnifiedCache:
        """Get or create unified cache instance."""
        if self._unified_cache is None:
            self._unified_cache = await get_unified()
        return self._unified_cache
    
    async def get_namespace_manager(
        self, 
        namespace: CacheNamespace
    ) -> VersionedDataManager:
        """Get or create namespace-specific version manager."""
        if namespace not in self._namespace_managers:
            data_class = self._get_data_class_for_namespace(namespace)
            self._namespace_managers[namespace] = VersionedDataManager(
                data_class=data_class,
                cache_namespace=namespace
            )
        return self._namespace_managers[namespace]
    
    async def atomic_operation(
        self,
        operation_id: str,
        operations: list[CacheOperation]
    ) -> list[Any]:
        """Execute multiple cache operations atomically."""
        if operation_id not in self._atomic_locks:
            self._atomic_locks[operation_id] = asyncio.Lock()
        
        async with self._atomic_locks[operation_id]:
            results = []
            rollback_operations = []
            
            try:
                for operation in operations:
                    result = await self._execute_operation(operation)
                    results.append(result)
                    rollback_operations.append(operation.get_rollback())
                
                return results
            except Exception as e:
                # Rollback on failure
                for rollback_op in reversed(rollback_operations):
                    try:
                        await self._execute_operation(rollback_op)
                    except Exception:
                        logger.error(f"Rollback failed for operation: {rollback_op}")
                raise e
    
    async def register_dependency(
        self,
        resource_id: str,
        depends_on: str
    ) -> None:
        """Register a dependency relationship for cascading updates."""
        if depends_on not in self._dependency_graph:
            self._dependency_graph[depends_on] = set()
        self._dependency_graph[depends_on].add(resource_id)
    
    async def cascade_update(
        self,
        root_resource_id: str,
        update_type: str = "invalidate"
    ) -> int:
        """Cascade updates through dependency graph."""
        updated_count = 0
        visited = set()
        
        async def _cascade_recursive(resource_id: str):
            nonlocal updated_count
            if resource_id in visited:
                return
            visited.add(resource_id)
            
            # Update current resource
            if update_type == "invalidate":
                await self._invalidate_resource(resource_id)
            updated_count += 1
            
            # Cascade to dependents
            dependents = self._dependency_graph.get(resource_id, set())
            for dependent in dependents:
                await _cascade_recursive(dependent)
        
        await _cascade_recursive(root_resource_id)
        return updated_count
```

### 2.2 Enhanced Version Manager

```python
class EnhancedVersionManager(VersionedDataManager[T]):
    """Enhanced version manager with tree operations and atomic updates."""
    
    async def save_with_tree_update(
        self,
        resource_id: str,
        content: dict[str, Any],
        resource_type: str,
        parent_id: str | None = None,
        cascade_to_children: bool = False,
        **kwargs: Any
    ) -> T:
        """Save resource with automatic tree relationship updates."""
        
        # Start transaction for atomic tree operations
        async with self._get_database_session() as session:
            async with session.start_transaction():
                # Save the main resource
                versioned_data = await self.save(
                    resource_id=resource_id,
                    content=content,
                    resource_type=resource_type,
                    **kwargs
                )
                
                # Update tree relationships
                if parent_id:
                    await self._update_parent_child_relationship(
                        parent_id, resource_id, session
                    )
                
                # Cascade to children if requested
                if cascade_to_children:
                    await self._cascade_to_children(
                        resource_id, content, session
                    )
                
                return versioned_data
    
    async def get_tree_structure(
        self,
        root_resource_id: str,
        max_depth: int = 10
    ) -> dict[str, Any]:
        """Get complete tree structure starting from root."""
        root = await self.get_latest(root_resource_id)
        if not root:
            return {}
        
        async def _build_tree(resource: T, current_depth: int) -> dict[str, Any]:
            if current_depth >= max_depth:
                return {"resource": resource, "children": []}
            
            children = []
            for child_id in resource.children_ids:
                child = await self.get_latest(str(child_id))
                if child:
                    child_tree = await _build_tree(child, current_depth + 1)
                    children.append(child_tree)
            
            return {"resource": resource, "children": children}
        
        return await _build_tree(root, 0)
    
    async def atomic_multi_save(
        self,
        operations: list[SaveOperation]
    ) -> list[T]:
        """Save multiple resources atomically."""
        results = []
        
        async with self._get_database_session() as session:
            async with session.start_transaction():
                for operation in operations:
                    result = await self._save_single(operation, session)
                    results.append(result)
                
                return results
```

### 2.3 Tree-Based Corpus Manager

```python
class TreeCorpusManager(BaseManager[Corpus, CorpusMetadata]):
    """Enhanced corpus manager with tree hierarchy support."""
    
    async def create_master_corpus(
        self,
        name: str,
        description: str | None = None,
        language: Language = Language.ENGLISH
    ) -> CorpusMetadata:
        """Create a master corpus that can have child corpora."""
        
        corpus_data = {
            "corpus_name": name,
            "language": language,
            "corpus_type": CorpusType.LEXICON,
            "is_master_corpus": True,
            "unique_word_count": 0,
            "total_word_count": 0
        }
        
        version_manager = self._get_version_manager()
        versioned_data = await version_manager.save_with_tree_update(
            resource_id=name,
            content=corpus_data,
            resource_type="corpus",
            cascade_to_children=False
        )
        
        # Create metadata
        metadata = CorpusMetadata(
            corpus_id=name,
            name=name,
            description=description,
            language=language
        )
        await metadata.save()
        
        return metadata
    
    async def add_child_corpus(
        self,
        parent_corpus_name: str,
        child_corpus_name: str,
        vocabulary: list[str],
        merge_with_parent: bool = True
    ) -> CorpusMetadata:
        """Add a child corpus to a parent corpus."""
        
        # Load parent corpus
        parent = await self.get(parent_corpus_name)
        if not parent or not getattr(parent, 'is_master_corpus', False):
            raise ValueError(f"Parent corpus {parent_corpus_name} not found or not a master corpus")
        
        # Create child corpus data
        child_data = {
            "corpus_name": child_corpus_name,
            "language": parent.language,
            "corpus_type": parent.corpus_type,
            "is_master_corpus": False,
            "unique_word_count": len(set(vocabulary)),
            "total_word_count": len(vocabulary),
            "vocabulary": vocabulary
        }
        
        # Use atomic operation to update both parent and child
        operations = [
            SaveOperation(
                resource_id=child_corpus_name,
                content=child_data,
                resource_type="corpus",
                parent_id=parent_corpus_name
            )
        ]
        
        if merge_with_parent:
            # Update parent with merged vocabulary
            parent_vocabulary = getattr(parent, 'vocabulary', [])
            merged_vocabulary = list(set(parent_vocabulary + vocabulary))
            parent_data = {
                "vocabulary": merged_vocabulary,
                "unique_word_count": len(set(merged_vocabulary)),
                "total_word_count": len(merged_vocabulary)
            }
            
            operations.append(
                SaveOperation(
                    resource_id=parent_corpus_name,
                    content=parent_data,
                    resource_type="corpus",
                    cascade_to_children=True
                )
            )
        
        version_manager = self._get_version_manager()
        await version_manager.atomic_multi_save(operations)
        
        # Create child metadata
        metadata = CorpusMetadata(
            corpus_id=child_corpus_name,
            name=child_corpus_name,
            language=parent.language
        )
        await metadata.save()
        
        return metadata
    
    async def get_corpus_hierarchy(
        self,
        root_corpus_name: str
    ) -> dict[str, Any]:
        """Get complete corpus hierarchy."""
        version_manager = self._get_version_manager()
        return await version_manager.get_tree_structure(root_corpus_name)
```

## 3. Helper Functions

### 3.1 Cache Key Generation

```python
def generate_cache_key(
    resource_type: str,
    resource_id: str,
    version: str | None = None,
    hash_value: str | None = None,
    namespace: str | None = None
) -> str:
    """Generate standardized cache key with optional namespace."""
    
    # Sanitize inputs
    safe_resource_type = re.sub(r'[^a-zA-Z0-9_]', '_', resource_type)
    safe_resource_id = re.sub(r'[^a-zA-Z0-9_-]', '_', resource_id)
    
    parts = [safe_resource_type, safe_resource_id]
    
    if namespace:
        parts.insert(0, namespace)
    
    if version:
        parts.append(f"v{version}")
    
    if hash_value:
        parts.append(hash_value[:8])
    
    return ":".join(parts)

def generate_tree_cache_key(
    resource_type: str,
    resource_id: str,
    depth_level: int,
    parent_id: str | None = None
) -> str:
    """Generate cache key for tree-structured data."""
    
    base_key = generate_cache_key(resource_type, resource_id)
    tree_parts = [f"depth{depth_level}"]
    
    if parent_id:
        tree_parts.append(f"parent{parent_id[:8]}")
    
    return f"{base_key}:tree:{':'.join(tree_parts)}"
```

### 3.2 Version Incrementing

```python
def increment_version(
    current_version: str,
    increment_type: Literal["major", "minor", "patch"] = "patch"
) -> str:
    """Increment semantic version string."""
    
    try:
        parts = current_version.split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        
        if increment_type == "major":
            return f"{major + 1}.0.0"
        elif increment_type == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"
    
    except (ValueError, IndexError):
        return "1.0.0"

def should_increment_version(
    old_content: dict[str, Any],
    new_content: dict[str, Any],
    threshold: float = 0.1
) -> Literal["major", "minor", "patch"]:
    """Determine version increment type based on content changes."""
    
    # Calculate content similarity
    old_str = json.dumps(old_content, sort_keys=True)
    new_str = json.dumps(new_content, sort_keys=True)
    
    # Simple similarity metric (can be enhanced with proper diff algorithms)
    common_chars = sum(1 for a, b in zip(old_str, new_str) if a == b)
    similarity = common_chars / max(len(old_str), len(new_str))
    
    if similarity < 0.5:
        return "major"
    elif similarity < 0.8:
        return "minor"
    else:
        return "patch"
```

### 3.3 Compression Selection

```python
def select_compression_type(
    data_size_bytes: int,
    data_type: str,
    performance_priority: bool = False
) -> CompressionType:
    """Select optimal compression type based on data characteristics."""
    
    # For small data, no compression overhead
    if data_size_bytes < 1024:  # 1KB
        return CompressionType.NONE
    
    # For performance-critical scenarios
    if performance_priority:
        if data_size_bytes < 10 * 1024:  # 10KB
            return CompressionType.NONE
        else:
            return CompressionType.ZLIB  # Fast compression
    
    # For large data, prioritize space savings
    if data_size_bytes > 100 * 1024:  # 100KB
        return CompressionType.GZIP  # Better compression ratio
    
    # Default to zlib for balanced performance
    return CompressionType.ZLIB

async def compress_with_metadata(
    data: Any,
    compression_type: CompressionType | None = None
) -> tuple[bytes, CacheMetadata]:
    """Compress data and return with metadata."""
    
    if compression_type is None:
        serialized = pickle.dumps(data)
        compression_type = select_compression_type(
            len(serialized),
            type(data).__name__
        )
    
    compressed_data, metadata = serialize_with_compression(data, compression_type)
    return compressed_data, metadata
```

### 3.4 Cascading Operations

```python
async def cascade_invalidation(
    cache_manager: GlobalCacheManager,
    root_resource_id: str,
    resource_type: str,
    max_depth: int = 5
) -> int:
    """Cascade cache invalidation through resource dependencies."""
    
    invalidated_count = 0
    visited = set()
    
    async def _invalidate_recursive(resource_id: str, current_depth: int):
        nonlocal invalidated_count
        
        if current_depth >= max_depth or resource_id in visited:
            return
        
        visited.add(resource_id)
        
        # Invalidate current resource
        cache = await cache_manager.get_cache()
        namespace = _get_namespace_for_resource_type(resource_type)
        await cache.delete(namespace, resource_id)
        invalidated_count += 1
        
        # Find dependent resources
        dependents = await _find_dependent_resources(resource_id, resource_type)
        
        # Recursively invalidate dependents
        for dependent in dependents:
            await _invalidate_recursive(dependent, current_depth + 1)
    
    await _invalidate_recursive(root_resource_id, 0)
    return invalidated_count

async def cascade_update_tree(
    version_manager: VersionedDataManager,
    root_resource_id: str,
    update_function: Callable[[dict[str, Any]], dict[str, Any]],
    max_depth: int = 5
) -> int:
    """Cascade updates through tree structure."""
    
    updated_count = 0
    
    async def _update_recursive(resource_id: str, current_depth: int):
        nonlocal updated_count
        
        if current_depth >= max_depth:
            return
        
        # Get current resource
        resource = await version_manager.get_latest(resource_id)
        if not resource or not resource.content_inline:
            return
        
        # Apply update function
        updated_content = update_function(resource.content_inline)
        
        # Save updated content
        await version_manager.save(
            resource_id=resource_id,
            content=updated_content,
            resource_type=resource.resource_type
        )
        updated_count += 1
        
        # Update children
        if hasattr(resource, 'children_ids'):
            for child_id in resource.children_ids:
                await _update_recursive(str(child_id), current_depth + 1)
    
    await _update_recursive(root_resource_id, 0)
    return updated_count
```

### 3.5 Cleanup and Retention

```python
async def cleanup_expired_versions(
    version_manager: VersionedDataManager,
    resource_type: str | None = None,
    retention_days: int = 30,
    keep_count: int = 5
) -> int:
    """Clean up expired versions while maintaining retention policy."""
    
    cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
    deleted_count = 0
    
    # Build query
    query = {"version_info.created_at": {"$lt": cutoff_date}}
    if resource_type:
        query["resource_type"] = resource_type
    
    # Find old versions
    old_versions = await version_manager.data_class.find(query).to_list()
    
    # Group by resource_id to maintain keep_count
    resource_versions = {}
    for version in old_versions:
        resource_id = version.resource_id
        if resource_id not in resource_versions:
            resource_versions[resource_id] = []
        resource_versions[resource_id].append(version)
    
    # Clean up each resource's versions
    for resource_id, versions in resource_versions.items():
        # Sort by creation date (newest first)
        versions.sort(key=lambda v: v.version_info.created_at, reverse=True)
        
        # Keep the most recent versions
        to_delete = versions[keep_count:]
        
        for version in to_delete:
            await version_manager._cleanup_version(version)
            deleted_count += 1
    
    return deleted_count

async def cleanup_orphaned_cache_entries(
    cache_manager: GlobalCacheManager,
    namespace: CacheNamespace
) -> int:
    """Clean up cache entries that no longer have corresponding database records."""
    
    cache = await cache_manager.get_cache()
    version_manager = await cache_manager.get_namespace_manager(namespace)
    
    # This would require implementing cache key enumeration
    # For now, we'll use namespace invalidation as a simple approach
    return await cache.invalidate_namespace(namespace.value)

class RetentionPolicy:
    """Policy class for managing data retention."""
    
    def __init__(
        self,
        default_retention_days: int = 30,
        version_keep_count: int = 5,
        high_frequency_retention_days: int = 90,
        frequency_threshold: int = 10
    ):
        self.default_retention_days = default_retention_days
        self.version_keep_count = version_keep_count
        self.high_frequency_retention_days = high_frequency_retention_days
        self.frequency_threshold = frequency_threshold
    
    def get_retention_days(self, access_frequency: int) -> int:
        """Get retention days based on access frequency."""
        if access_frequency >= self.frequency_threshold:
            return self.high_frequency_retention_days
        return self.default_retention_days
    
    async def apply_policy(
        self,
        version_manager: VersionedDataManager,
        resource_type: str | None = None
    ) -> int:
        """Apply retention policy to resources."""
        total_deleted = 0
        
        # Apply different retention for high-frequency resources
        high_freq_query = {
            "metadata.lookup_frequency": {"$gte": self.frequency_threshold}
        }
        if resource_type:
            high_freq_query["resource_type"] = resource_type
        
        # Clean high-frequency resources with longer retention
        total_deleted += await cleanup_expired_versions(
            version_manager,
            retention_days=self.high_frequency_retention_days,
            keep_count=self.version_keep_count + 2  # Keep more versions for frequently accessed
        )
        
        # Clean regular resources with standard retention
        low_freq_query = {
            "$or": [
                {"metadata.lookup_frequency": {"$lt": self.frequency_threshold}},
                {"metadata.lookup_frequency": {"$exists": False}}
            ]
        }
        if resource_type:
            low_freq_query["resource_type"] = resource_type
        
        total_deleted += await cleanup_expired_versions(
            version_manager,
            retention_days=self.default_retention_days,
            keep_count=self.version_keep_count
        )
        
        return total_deleted
```

## 4. Implementation Plan

### Phase 1: Core Infrastructure Enhancement (No Dependencies)

**Objectives**: Enhance existing unified cache and versioning systems

**Tasks**:
1. **Enhance Data Models**
   - Add tree relationship fields to `VersionedData`
   - Create specialized data classes for each resource type
   - Add compression metadata tracking
   - Implement dependency tracking fields

2. **Extend Cache Backend**
   - Add atomic operation support to `UnifiedCache`
   - Implement dependency graph tracking
   - Add tree-aware cache key generation
   - Enhance statistics and monitoring

3. **Upgrade Version Manager**
   - Add tree operation methods (`save_with_tree_update`, `get_tree_structure`)
   - Implement atomic multi-save operations
   - Add cascading update support
   - Enhance cleanup with retention policies

**Deliverables**:
- Enhanced `VersionedData` base class with tree support
- Updated `UnifiedCache` with atomic operations
- Extended `VersionedDataManager` with tree methods
- Comprehensive test suite for core functionality

**Risk Mitigation**:
- All changes are additive to existing models
- Backward compatibility maintained through optional fields
- Gradual rollout with feature flags

### Phase 2: Specialized Managers and Operations (Depends on Phase 1)

**Objectives**: Implement specialized resource managers and advanced operations

**Tasks**:
1. **Implement Specialized Managers**
   - Create `GlobalCacheManager` with namespace coordination
   - Implement `TreeCorpusManager` for hierarchical corpus operations
   - Create specialized managers for Dictionary, Semantic, and Literature data
   - Add atomic operation classes and interfaces

2. **Advanced Cache Operations**
   - Implement cascading invalidation algorithms
   - Add intelligent compression selection
   - Create retention policy engine
   - Add performance monitoring and optimization

3. **Helper Function Library**
   - Cache key generation utilities
   - Version incrementing logic
   - Tree traversal algorithms
   - Cleanup and maintenance functions

**Deliverables**:
- `GlobalCacheManager` with full namespace support
- Specialized resource managers with tree operations
- Atomic operation framework
- Complete helper function library

**Dependencies**: Phase 1 completion
**Risk Mitigation**: Incremental testing with existing data

### Phase 3: Tree Structure and Corpus Hierarchy (Depends on Phase 2)

**Objectives**: Implement full tree-like corpus structure with master/child relationships

**Tasks**:
1. **Tree Structure Implementation**
   - Create master/child corpus relationships
   - Implement tree traversal and updates
   - Add depth-aware querying
   - Create tree visualization tools

2. **Corpus Management Enhancement**
   - Implement hierarchical vocabulary management
   - Add automatic vocabulary merging/splitting
   - Create corpus composition tools
   - Add bulk corpus operations

3. **Advanced Search Integration**
   - Tree-aware semantic search
   - Hierarchical corpus indexing
   - Cross-corpus search capabilities
   - Performance optimization for tree queries

**Deliverables**:
- Complete tree-based corpus hierarchy
- Master/child corpus management tools
- Tree-aware search capabilities
- Performance benchmarks and optimization

**Dependencies**: Phase 2 completion
**Risk Mitigation**: Parallel development with existing corpus system

### Phase 4: Migration and Optimization (Depends on Phase 3)

**Objectives**: Migrate existing data and optimize performance

**Tasks**:
1. **Data Migration**
   - Create migration scripts for existing data
   - Implement gradual migration strategy
   - Add data validation and integrity checks
   - Create rollback procedures

2. **Performance Optimization**
   - Optimize cache hit rates with intelligent prefetching
   - Implement background maintenance tasks
   - Add performance monitoring dashboards
   - Tune compression and quantization settings

3. **Production Deployment**
   - Create deployment automation
   - Implement monitoring and alerting
   - Add operational documentation
   - Conduct load testing

**Deliverables**:
- Complete data migration tools
- Production-ready optimized system
- Monitoring and operational tools
- Performance benchmarks and SLA metrics

**Dependencies**: Phase 3 completion
**Risk Mitigation**: Blue-green deployment with rollback capability

### Testing Strategy

**Unit Testing**:
- Individual function testing with pytest
- Mock-based testing for external dependencies
- Property-based testing for cache operations
- Performance testing for critical paths

**Integration Testing**:
- End-to-end workflow testing
- Cross-namespace operation testing
- Tree operation integrity testing
- Atomic operation rollback testing

**Performance Testing**:
- Cache hit rate optimization
- Memory usage profiling
- Compression ratio validation
- Tree traversal performance

**Migration Testing**:
- Data integrity validation
- Performance regression testing
- Rollback procedure validation
- Production load simulation

## Conclusion

This architecture provides a comprehensive, scalable solution for Floridify's caching, metadata, and versioning needs. The design emphasizes:

1. **Simplicity**: Building on existing proven patterns
2. **Performance**: Optimized caching with intelligent compression
3. **Flexibility**: Tree structures support complex hierarchies
4. **Reliability**: Atomic operations ensure data consistency
5. **Maintainability**: Clear separation of concerns and comprehensive testing

The phased implementation approach ensures smooth deployment while minimizing risk to existing functionality. The system is designed to scale with Floridify's growing data needs while maintaining excellent performance characteristics.