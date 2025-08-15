# Unified Versioning System Architecture

## Core Principles
- **Single Source of Truth**: All versioned data flows through `core/versioned.py`
- **Immutable Versions**: Once created, versions are never modified
- **Content Deduplication**: SHA256 hashing prevents duplicate storage
- **Storage Flexibility**: Support for MongoDB, disk, cache, and memory
- **Layered Architecture**: Version layer → Metadata layer → Storage layer

## Layered Data Architecture

### Layer 1: Version Management
**Purpose**: Minimal version tracking and pointer management
**Storage**: MongoDB exclusively
```
VersionedData (MongoDB Document - Lightweight)
├── resource_id: str (unique identifier)
├── resource_type: str (corpus|dictionary|semantic|literature)
├── version_info: VersionInfo
│   ├── version: str (semantic versioning)
│   ├── data_hash: str (SHA256)
│   ├── is_latest: bool
│   └── superseded_by: ObjectId | None
└── metadata_ref: ObjectId → Points to Metadata Document
```

### Layer 2: Metadata Management
**Purpose**: Rich metadata with cache information and relationships
**Storage**: MongoDB with references
```
Metadata Documents (MongoDB - Rich Data)
├── SemanticMetadata
│   ├── cache_key: str (unified cache key)
│   ├── cache_ttl: int | None (seconds)
│   ├── cache_tags: list[str]
│   ├── corpus_ref: ObjectId → CorpusMetadata
│   └── index_stats: SemanticIndexStats
├── CorpusMetadata
│   ├── cache_key: str
│   ├── cache_ttl: int | None
│   ├── cache_tags: list[str]
│   └── corpus_stats: CorpusStats
├── LiteratureMetadata
│   ├── cache_key: str
│   ├── cache_ttl: int | None
│   ├── cache_tags: list[str]
│   ├── corpus_ref: ObjectId | None → CorpusMetadata
│   └── work_info: WorkInfo
└── LanguageMetadata
    ├── cache_key: str
    ├── cache_ttl: int | None
    ├── cache_tags: list[str]
    ├── corpus_ref: ObjectId → CorpusMetadata
    └── language_info: LanguageInfo
```

### Layer 3: Storage Management
**Purpose**: Actual content storage with unified caching
**Locations**: Cache (with NO TTL for persistence), Disk, MongoDB inline
```
Content Storage
├── Cache Storage (Unified Cache Manager)
│   ├── Key Pattern: {type}:{id}:{hash[:8]}:v{version}
│   ├── Compression: zlib/gzip
│   └── TTL: None (persistent disk-like behavior)
├── Disk Storage (File System)
│   ├── Path Pattern: /data/{type}/{id}/{version}/
│   └── Formats: JSON, FAISS, NPY
└── Inline Storage (MongoDB)
    └── For small data only (<16MB)
```

## Specialized Versioned Data Types

### 1. CorpusVersionedData
```python
class CorpusVersionedData(VersionedData):
    # Version layer (minimal)
    resource_type = "corpus"
    metadata_ref: ObjectId → CorpusMetadata
    
class CorpusMetadata(Document):
    # Metadata layer (rich)
    cache_key: str  # corpus:{name}:{hash[:8]}:v{version}
    cache_ttl: None  # No TTL for persistence
    cache_tags: list[str] = ["corpus", "{language}"]
    corpus_stats: CorpusStats
    
    # Storage: Unified cache as persistent disk
    # Content: vocabulary, sources, metadata
```

### 2. SemanticIndexVersionedData
```python
class SemanticIndexVersionedData(VersionedData):
    # Version layer (minimal)
    resource_type = "semantic"
    metadata_ref: ObjectId → SemanticMetadata
    
class SemanticMetadata(Document):
    # Metadata layer (rich)
    cache_key: str  # semantic:{corpus}:{model}:{hash[:8]}:v{version}
    cache_ttl: None  # No TTL for persistence
    cache_tags: list[str] = ["semantic", "{corpus_name}"]
    corpus_ref: ObjectId → CorpusMetadata
    index_stats: SemanticIndexStats
    
    # Storage: Unified cache as persistent disk
    # Content: FAISS index, embeddings, mappings
```

### 3. DictionaryVersionedData
```python
class DictionaryVersionedData(VersionedData):
    # Version layer (minimal)
    resource_type = "dictionary"
    # No metadata_ref - content stored inline
    
    # Content stored inline in MongoDB
    content_inline: DictionaryProviderData
    # No disk storage needed
```

### 4. LiteratureVersionedData
```python
class LiteratureVersionedData(VersionedData):
    # Version layer (minimal)
    resource_type = "literature"
    metadata_ref: ObjectId → LiteratureMetadata
    
class LiteratureMetadata(Document):
    # Metadata layer (rich)
    cache_key: str  # literature:{source}:{work_id}:{hash[:8]}:v{version}
    cache_ttl: None  # No TTL for persistence
    cache_tags: list[str] = ["literature", "{author}"]
    corpus_ref: ObjectId | None → CorpusMetadata
    work_info: WorkInfo
    
    # Storage: Unified cache as persistent disk
    # Content: text, metadata, quality metrics
```

## Storage Strategy

### MongoDB-Stored (Full Content)
- DictionaryVersionedData: Complete definition data
- All metadata for disk-stored content

### Disk-Stored (Content Only)
- CorpusVersionedData: Large vocabulary lists
- SemanticIndexVersionedData: FAISS indices and embeddings

### Cache Strategy
| Data Type | Cache Location | TTL | Compression |
|-----------|---------------|-----|-------------|
| Dictionary | Redis/Memory | 24h | Yes |
| Corpus | Memory | 1h | Yes |
| Semantic | Memory (FAISS) | No TTL | No |

## Version Management Flow

1. **Create Version**
   ```python
   manager = VersionedDataManager[CorpusVersionedData]()
   await manager.save(
       resource_id="sophocles_corpus",
       content={"vocabulary": unique_words, ...},
       storage_type=StorageType.DISK
   )
   ```

2. **Retrieve Latest**
   ```python
   data = await manager.get_latest("sophocles_corpus")
   content = await manager.get_content(data)
   ```

3. **Version Chain**
   - New versions automatically supersede previous
   - Previous versions marked as `is_latest=False`
   - Chain maintained via `superseded_by` references

## Migration Path

### Remove
- `providers/literature/versioned.py` → Use `models/versioned.py`
- `providers/versioning.py` → Use `core/versioned.py`
- All connector-specific versioning → Use `VersionedDataManager`
- Legacy cache parameters → Use unified caching

### Consolidate
- All versioning through `VersionedDataManager`
- All hashing through `VersionedData.compute_hash()`
- All storage through `ContentLocation` abstraction

## Manager Instances

### Core Version Manager (`core/versioned.py`)
```python
class VersionedDataManager[T: VersionedData]:
    """Base generic manager for all versioned data types"""
    - get_latest(resource_id, resource_type) → T
    - save(resource_id, content, storage_type) → T
    - load_content(versioned_data) → dict
    - cleanup_old_versions(resource_id, keep_count)
```

### Specialized Manager Instances

#### 1. DictionaryProviderManager (`providers/dictionary/manager.py`)
```python
class DictionaryProviderManager:
    version_manager: VersionedDataManager[DictionaryVersionedData]
    providers: dict[DictionaryProvider, DictionaryConnector]
    - fetch_definitions(word, providers) → dict[Provider, Data]
    - get_cached_or_fetch(word, provider) → DictionaryProviderData
```

#### 2. LiteratureProviderManager (`providers/literature/manager.py`)
```python
class LiteratureProviderManager:
    version_manager: VersionedDataManager[LiteratureVersionedData]
    providers: dict[LiteratureSource, LiteratureConnector]
    - download_work(source_id, provider) → LiteratureMetadata
    - search_works(query, providers) → list[WorkInfo]
```

#### 3. SemanticSearchManager (`search/semantic/manager.py`)
```python
class SemanticSearchManager:
    version_manager: VersionedDataManager[SemanticIndexVersionedData]
    indices: dict[str, SemanticSearch]
    - create_index(corpus_name, model) → SemanticMetadata
    - search(query, top_k) → list[SearchResult]
```

#### 4. CorpusManager (`corpus/manager.py`)
```python
class CorpusManager:
    version_manager: VersionedDataManager[CorpusVersionedData]
    corpora: dict[str, Corpus]
    - create_corpus(name, sources) → CorpusMetadata
    - get_corpus(name) → Corpus
```

#### 5. LanguageCorpusManager (`corpus/manager.py`)
```python
class LanguageCorpusManager(CorpusManager):
    language_loaders: dict[Language, LanguageLoader]
    - load_language_corpus(language) → LanguageMetadata
    - update_from_sources(language, sources) → LanguageMetadata
```

#### 6. LiteratureCorpusManager (`corpus/manager.py`)
```python
class LiteratureCorpusManager(CorpusManager):
    literature_manager: LiteratureProviderManager
    - create_author_corpus(author) → CorpusMetadata
    - create_period_corpus(period) → CorpusMetadata
```

### Manager Factory Functions
```python
# Singleton access patterns in core/versioned.py
def get_dictionary_manager() → DictionaryProviderManager
def get_literature_manager() → LiteratureProviderManager
def get_semantic_manager() → SemanticSearchManager
def get_corpus_manager() → CorpusManager
def get_language_corpus_manager() → LanguageCorpusManager
def get_literature_corpus_manager() → LiteratureCorpusManager
```

## Implementation Checklist
- [x] Base VersionedData model
- [x] VersionedDataManager centralization
- [x] CorpusVersionedData implementation
- [x] SemanticIndexVersionedData implementation
- [x] DictionaryVersionedData implementation
- [ ] Remove legacy versioning code (providers/versioned.py)
- [ ] Implement Manager Factory Functions
- [ ] Create specialized manager classes
- [ ] Update metadata models with cache keys
- [ ] Implement disk storage for corpus/semantic
- [ ] Implement cache layer with NO TTL for persistence
- [ ] Update all connectors to use managers
- [ ] Add version increment logic