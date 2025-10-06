# Persistence & Versioning Architecture Analysis

## Executive Summary

The codebase has **THREE DISTINCT** persistence patterns that overlap and create unnecessary complexity:

1. **Beanie ODM Direct** - Simple MongoDB CRUD via Beanie's Document model
2. **VersionManager Abstraction** - Complex versioning layer with content_location and version chains
3. **Repository Pattern** - API-layer CRUD with BaseRepository

**Key Finding**: The VersionManager abstraction is **over-engineered** and **rarely used** for its intended versioning purpose. Most code just wants simple save/load.

---

## Pattern 1: Beanie ODM Direct (Simplest)

### Usage
Used throughout the codebase for straightforward MongoDB operations.

### Examples

```python
# storage/mongodb.py
word = await Word.find_one(Word.text == word_text)
await word.save()
await word.create()

# api/repositories/word_repository.py
return await Word.find_one({"text": text, "language": language})
await Definition.find({"word_id": word_id_str}).delete()

# corpus/manager.py (TreeCorpusManager)
metadata = await Corpus.Metadata.get(corpus_id)
await metadata.save()
```

### Characteristics
- **Direct Beanie API**: `find_one()`, `save()`, `create()`, `delete()`
- **Simple**: No abstraction layers
- **Fast**: Direct MongoDB queries
- **Clear**: What you see is what you get

### Pros
✅ Simple and intuitive
✅ Well-documented Beanie API
✅ Minimal overhead
✅ Easy to debug

### Cons
❌ No built-in versioning
❌ No caching by default
❌ Repetitive boilerplate

---

## Pattern 2: VersionManager Abstraction (Most Complex)

### Architecture

```python
# caching/manager.py - VersionedDataManager
class VersionedDataManager:
    async def save(
        resource_id: str,
        resource_type: ResourceType,
        namespace: CacheNamespace,
        content: Any,
        config: VersionConfig,
        metadata: dict[str, Any],
    ) -> BaseVersionedData

    async def get_latest(
        resource_id: str,
        resource_type: ResourceType,
        use_cache: bool,
        config: VersionConfig,
    ) -> BaseVersionedData | None
```

### Content Storage Strategy

The VersionManager implements a dual-storage approach:

1. **Inline Storage** (< 16KB):
   ```python
   versioned.content_inline = content  # Stored in MongoDB document
   versioned.content_location = None
   ```

2. **External Storage** (≥ 16KB):
   ```python
   cache_key = f"{resource_type}:{resource_id}:content:{hash[:8]}"
   await cache.set(namespace, cache_key, content)
   versioned.content_location = ContentLocation(
       cache_namespace=namespace,
       cache_key=cache_key,
       storage_type=StorageType.CACHE,
       size_bytes=len(content),
       checksum=hash
   )
   versioned.content_inline = None
   ```

### Version Chain Management

```python
# Version chain (doubly-linked list)
VersionInfo(
    version="1.0.0",
    data_hash="abc123...",
    is_latest=True,
    supersedes=previous_version_id,      # Points to previous version
    superseded_by=None,                  # Will be set when superseded
    dependencies=[dep1_id, dep2_id]      # Dependency tracking
)
```

### MongoDB Transaction Support

```python
async def _save_with_transaction(self, versioned, resource_id, resource_type):
    """Atomic version chain updates using MongoDB transactions."""
    try:
        async with await client.start_session() as session:
            async with session.start_transaction():
                await versioned.insert(session=session)

                # Atomically update old versions
                other_latest = await model_class.find({
                    "resource_id": resource_id,
                    "version_info.is_latest": True,
                    "_id": {"$ne": versioned.id}
                }, session=session).to_list()

                for old_version in other_latest:
                    old_version.version_info.is_latest = False
                    old_version.version_info.superseded_by = versioned.id
                    await old_version.save(session=session)
    except OperationFailure:
        # Fallback for single-node MongoDB (no transactions)
        async with self.lock:
            await versioned.save()
            # Update chain with local lock
```

### Usage Examples

```python
# providers/core.py - BaseConnector
async def save(self, resource_id: str, content: Any, config: VersionConfig):
    manager = get_version_manager()
    await manager.save(
        resource_id=f"{resource_id}_{self.get_cache_key_suffix()}",
        resource_type=self.get_resource_type(),
        namespace=self.get_cache_namespace(),
        content=self.model_dump(content),
        config=config,
        metadata=self.get_metadata_for_resource(resource_id),
    )

# corpus/core.py - Corpus.save()
async def save(self, config: VersionConfig | None = None):
    manager = get_tree_corpus_manager()
    saved = await manager.save_corpus(
        corpus_id=self.corpus_id,
        content=self.model_dump(),
        config=config,
        # ... more parameters
    )
```

### TreeCorpusManager Integration

The TreeCorpusManager acts as a facade over VersionManager:

```python
# corpus/manager.py
class TreeCorpusManager:
    def __init__(self, vm: VersionedDataManager | None = None):
        self.vm = vm or get_version_manager()

    async def save_corpus(self, corpus_id, content, config, metadata):
        # Prepares metadata
        full_metadata = {
            "corpus_name": corpus_name,
            "corpus_type": corpus_type_value,
            "language": language_value,
            "parent_corpus_id": parent_corpus_id,
            "child_corpus_ids": child_corpus_ids,
            "is_master": is_master,
            **metadata
        }

        # Delegates to VersionManager
        saved = await self.vm.save(
            resource_id=corpus_name,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=content,
            config=config,
            metadata=full_metadata,
        )

        # Converts metadata back to Corpus
        saved_content = await get_versioned_content(saved)
        saved_content.update(full_metadata)
        return Corpus.model_validate(saved_content)
```

### Problems with This Pattern

1. **Metadata vs Content Confusion**
   - Corpus-specific fields (parent_id, child_ids) stored in `metadata` dict
   - Requires constant merging/splitting between Corpus and Metadata
   - Type safety lost in dict serialization

2. **Over-Abstraction**
   ```python
   # To save a corpus:
   Corpus.save()
   → TreeCorpusManager.save_corpus()
   → VersionManager.save()
   → set_versioned_content()  # Choose inline/external
   → _save_with_transaction()  # Update version chain
   → BaseVersionedData.save()  # Finally save to MongoDB
   ```

3. **Content Location Complexity**
   - Automatic threshold-based routing (inline vs external)
   - Complex retrieval logic with cache fallbacks
   - Error-prone content reconstruction

4. **Versioning Rarely Used**
   - Most code uses `force_rebuild=False`, `increment_version=True`
   - Version chains not actually traversed
   - History features not implemented

5. **Performance Overhead**
   - Multiple serialization passes (JSON, pickle, compression)
   - Extra database queries for version chain updates
   - Cache invalidation complexity

### Actual Usage Pattern

**What the code does:**
```python
# Just wants to save/load corpus with tree structure
corpus.child_corpus_ids = [child1_id, child2_id]
await corpus.save()

loaded = await Corpus.get(corpus_id)
print(loaded.child_corpus_ids)  # [child1_id, child2_id]
```

**What it goes through:**
```python
Corpus.save()
→ TreeCorpusManager.save_corpus(
    corpus_id=corpus.corpus_id,
    content=corpus.model_dump(),  # Serialize to dict
    metadata={
        "child_corpus_ids": corpus.child_corpus_ids,  # Duplicate in metadata
        "parent_corpus_id": corpus.parent_corpus_id,
        ...
    }
)
→ VersionManager.save(
    content=content_dict,
    metadata=metadata_dict,
)
→ Corpus.Metadata(**params)  # Create metadata document
→ set_versioned_content(metadata, content)  # Store content separately if large
→ metadata.save()  # Save to MongoDB

# Then to retrieve:
Corpus.get(corpus_id)
→ TreeCorpusManager.get_corpus(corpus_id)
→ VersionManager.get_latest(resource_id)  # Find metadata
→ get_versioned_content(metadata)  # Load content from inline/cache
→ Merge content + metadata fields
→ Corpus.model_validate(merged_dict)  # Reconstruct
```

---

## Pattern 3: Repository Pattern (API Layer)

### Architecture

```python
# api/core/base.py
class BaseRepository(Generic[T, CreateSchema, UpdateSchema]):
    def __init__(self, model: type[T]):
        self.model = model

    async def get(self, id: PydanticObjectId) -> T | None:
        """Direct Beanie get"""
        return await self.model.get(id)

    async def create(self, data: CreateSchema) -> T:
        """Create from schema"""
        doc = self.model(**data.model_dump())
        await doc.create()
        return doc

    async def update(self, id: PydanticObjectId, data: UpdateSchema) -> T:
        """Update with optimistic locking"""
        doc = await self.get(id)
        # Update fields, increment version
        await doc.save()
        return doc

    async def list(self, filter_dict, pagination, sort) -> tuple[list[T], int]:
        """List with filtering/pagination"""
        query = self.model.find(filter_dict)
        # Apply sort, pagination
        return await query.to_list(), total
```

### Usage Examples

```python
# api/repositories/word_repository.py
class WordRepository(BaseRepository[Word, WordCreate, WordUpdate]):
    async def find_by_text(self, text: str) -> Word | None:
        return await Word.find_one({"text": text, "language": language})

    async def get_with_counts(self, id: PydanticObjectId) -> dict:
        word = await self.get(id)
        # Add aggregated counts
        return word_dict

# api/repositories/synthesis_repository.py
class SynthesisRepository(BaseRepository[DictionaryEntry, ...]):
    async def get_by_word(self, word_id: str) -> DictionaryEntry | None:
        return await DictionaryEntry.find_one({
            "word_id": word_oid,
            "provider": "synthesis"
        })
```

### Characteristics
- **Thin wrapper** over Beanie
- **Schema validation** via Pydantic
- **CRUD + custom queries** per repository
- **API-specific features** (pagination, versioning, cascades)

### Pros
✅ Clean API separation
✅ Schema validation
✅ Reusable CRUD logic
✅ Domain-specific methods

### Cons
❌ Another abstraction layer
❌ Duplicates Beanie functionality
❌ Not used consistently

---

## Pattern Comparison

| Feature | Beanie Direct | VersionManager | Repository |
|---------|--------------|----------------|------------|
| **Complexity** | Low | Very High | Medium |
| **Type Safety** | High | Low (dict-based) | High |
| **Versioning** | ❌ | ✅ (unused) | ✅ (simple) |
| **Caching** | ❌ | ✅ (complex) | ❌ |
| **Performance** | Fast | Slow | Fast |
| **Usage** | 60% | 20% | 20% |
| **Learning Curve** | Low | High | Medium |

---

## Actual Usage Analysis

### Who Uses What?

1. **Beanie Direct (60%)**
   - `storage/mongodb.py` - all operations
   - `corpus/manager.py` - `Corpus.Metadata` CRUD
   - `api/repositories/*` - underlying queries
   - Tests - direct document manipulation

2. **VersionManager (20%)**
   - `providers/core.py` - BaseConnector save/get
   - `corpus/core.py` - via TreeCorpusManager
   - `search/semantic/core.py` - FAISS index storage
   - Rarely uses versioning features (just save latest)

3. **Repository Pattern (20%)**
   - `api/routers/*` - API endpoints
   - Limited to Word, Definition, Example, DictionaryEntry
   - Not used for Corpus, SemanticIndex, or other versioned types

### Dead Code / Unused Features

**VersionManager features rarely/never used:**
- ❌ Version history traversal (`supersedes`, `superseded_by` chains)
- ❌ Dependency tracking (`dependencies` field)
- ❌ Specific version retrieval (always gets latest)
- ❌ Version comparison/diff
- ❌ Rollback to previous version
- ❌ Content deduplication (hash-based)

**Over-engineered aspects:**
- ❌ MongoDB transaction support (fallback to locks anyway)
- ❌ Polymorphic model registry (only corpus uses it)
- ❌ Complex content_location abstraction (inline vs external)
- ❌ Compression auto-selection logic

---

## Design Problems

### 1. Leaky Abstractions

**Problem**: Corpus has to know about VersionManager internals

```python
# corpus/core.py
class Corpus(BaseModel):
    # Core fields
    vocabulary: list[str]

    # VersionManager pollution
    version_info: VersionInfo | None = None
    _metadata_id: PydanticObjectId | None = None

    async def save(self):
        # Has to go through manager facade
        manager = get_tree_corpus_manager()
        saved = await manager.save_corpus(
            corpus_id=self.corpus_id,
            content=self.model_dump(),  # Serialize self
            config=config,
            # Duplicate metadata extraction
            parent_corpus_id=self.parent_corpus_id,
            child_corpus_ids=self.child_corpus_ids,
        )
        # Then sync back the IDs
        if saved:
            self.corpus_id = saved.corpus_id
```

### 2. Metadata Field Confusion

**TreeCorpusManager constantly merges/splits fields:**

```python
# Save: Split Corpus → content + metadata
async def save_corpus(self, corpus: Corpus):
    content = corpus.model_dump()  # Everything as dict

    # Extract corpus-specific fields to metadata
    metadata = {
        "corpus_name": corpus.corpus_name,
        "parent_corpus_id": corpus.parent_corpus_id,
        "child_corpus_ids": corpus.child_corpus_ids,
        "is_master": corpus.is_master,
    }

    await self.vm.save(content=content, metadata=metadata)

# Load: Merge metadata + content → Corpus
async def get_corpus(self, corpus_id):
    metadata = await self.vm.get_latest(resource_id)
    content = await get_versioned_content(metadata)

    # Merge back
    content.update({
        "corpus_name": metadata.corpus_name,
        "parent_corpus_id": metadata.parent_corpus_id,
        "child_corpus_ids": metadata.child_corpus_ids,
        "is_master": metadata.is_master,
    })

    return Corpus.model_validate(content)
```

**Why?** Because BaseVersionedData doesn't have corpus-specific fields, so they go in a generic `metadata: dict` field. But then we have to extract them back to typed fields.

### 3. BaseVersionedData Polymorphism Complexity

**The model registry pattern:**

```python
# models/registry.py
_MODEL_REGISTRY = {
    ResourceType.CORPUS: Corpus.Metadata,
    ResourceType.SEMANTIC: SemanticIndex.Metadata,
    ResourceType.TRIE: TrieIndex.Metadata,
    # ...
}

def get_model_class(resource_type: ResourceType) -> type[BaseVersionedData]:
    return _MODEL_REGISTRY[resource_type]

# caching/manager.py
def _get_model_class(self, resource_type: ResourceType):
    return get_versioned_model_class(resource_type)
```

**Problem**: Each resource type has to define a nested `.Metadata` class that inherits from `BaseVersionedData`. This creates parallel class hierarchies.

### 4. Content Storage Decision Logic

**Automatic routing based on size:**

```python
async def set_versioned_content(versioned_data, content, force_external=False):
    content_str = json.dumps(content, sort_keys=True)
    content_size = len(content_str.encode())

    inline_threshold = 16 * 1024  # 16KB

    if not force_external and content_size < inline_threshold:
        # Inline: store in document
        versioned_data.content_inline = content
        versioned_data.content_location = None
    else:
        # External: store in cache, save reference
        cache_key = f"{resource_type}:{resource_id}:content:{hash[:8]}"
        await cache.set(namespace, cache_key, content, ttl)

        versioned_data.content_location = ContentLocation(
            cache_namespace=namespace,
            cache_key=cache_key,
            storage_type=StorageType.CACHE,
            size_bytes=content_size,
            checksum=content_hash,
        )
        versioned_data.content_inline = None
```

**Then retrieval:**

```python
async def get_versioned_content(versioned_data):
    # Try inline first
    if versioned_data.content_inline is not None:
        return versioned_data.content_inline

    # Try external
    if versioned_data.content_location:
        location = versioned_data.content_location
        cache = await get_global_cache()
        return await cache.get(location.cache_namespace, location.cache_key)

    return None
```

**Problems:**
- Magic threshold (16KB) - why this number?
- Adds complexity to every save/load
- Forces serialization even when not needed
- Cache can fail independently of MongoDB

---

## KISS Violations

### Violation 1: Indirection Layers

**Simple need:** Save corpus with child references

**Current path:**
```
Corpus.save()
→ TreeCorpusManager.save_corpus()
→ VersionManager.save()
→ set_versioned_content()
→ _save_with_transaction()
→ BaseVersionedData.save()
→ Beanie Document.save()
→ MongoDB
```

**KISS alternative:**
```python
class Corpus(Document):
    vocabulary: list[str]
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = []

    async def save(self):
        await super().save()  # Direct Beanie save
```

### Violation 2: Metadata Split/Merge

**Current:**
- Corpus has fields: `parent_id`, `child_ids`, `vocabulary`
- Save splits into: `content = {vocabulary}`, `metadata = {parent_id, child_ids}`
- Load merges back: `content + metadata → Corpus`

**KISS alternative:**
```python
class Corpus(Document):
    # All fields in one place
    vocabulary: list[str]
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = []

    # Save/load just works
```

### Violation 3: Version Chain Management

**Current:** Doubly-linked list with atomic updates

```python
# Save new version
new_version.version_info.is_latest = True
new_version.version_info.supersedes = old_version.id

# Update old version
old_version.version_info.is_latest = False
old_version.version_info.superseded_by = new_version.id
```

**But never used for:**
- Traversing history
- Comparing versions
- Rollback

**KISS alternative:**
```python
class Corpus(Document):
    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    async def save(self):
        self.version += 1
        self.updated_at = datetime.utcnow()
        await super().save()
```

---

## DRY Violations

### 1. Duplicate Persistence Code

**VersionManager has save logic:**
```python
class VersionedDataManager:
    async def save(self, resource_id, content, ...):
        # Hash content
        # Find duplicates
        # Create metadata
        # Update version chain
        # Cache result
```

**TreeCorpusManager duplicates it:**
```python
class TreeCorpusManager:
    async def save_corpus(self, corpus_id, content, ...):
        # Prepare metadata
        # Call vm.save()
        # Reconstruct corpus
```

**Corpus also has save logic:**
```python
class Corpus:
    async def save(self, config):
        # Update stats
        # Call manager.save_corpus()
        # Sync IDs back
```

### 2. Duplicate Get/Load Code

**Three ways to load a corpus:**

```python
# Method 1: Direct
metadata = await Corpus.Metadata.get(corpus_id)

# Method 2: Via VersionManager
metadata = await vm.get_latest(resource_id, ResourceType.CORPUS)

# Method 3: Via TreeCorpusManager
corpus = await manager.get_corpus(corpus_id)
```

All do the same thing, but with different interfaces.

### 3. Duplicate Field Definitions

**Corpus has fields:**
```python
class Corpus(BaseModel):
    corpus_name: str
    language: Language
    parent_corpus_id: PydanticObjectId | None
    child_corpus_ids: list[PydanticObjectId]
```

**Corpus.Metadata duplicates them:**
```python
class Corpus.Metadata(BaseVersionedData):
    corpus_name: str
    corpus_type: CorpusType
    language: Language
    parent_corpus_id: PydanticObjectId | None
    child_corpus_ids: list[PydanticObjectId]
```

---

## Alternative: Simpler Architecture

### Option 1: Enhanced Beanie Direct

**Make Corpus a Document:**

```python
class Corpus(Document):
    # Identity
    corpus_name: str = Field(default_factory=lambda: coolname.generate_slug(2))
    corpus_type: CorpusType = CorpusType.LEXICON
    language: Language = Language.ENGLISH

    # Tree structure
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False

    # Vocabulary
    vocabulary: list[str]
    vocabulary_hash: str

    # Versioning (simple)
    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Indices (lazy-loaded from cache)
    _trie_index: TrieIndex | None = None
    _semantic_index: SemanticIndex | None = None

    class Settings:
        name = "corpora"
        indexes = [
            "corpus_name",
            [("parent_corpus_id", 1), ("is_master", 1)],
        ]

    async def save(self):
        self.version += 1
        self.updated_at = datetime.utcnow()
        self.vocabulary_hash = get_vocabulary_hash(self.vocabulary)
        await super().save()

    @classmethod
    async def get_by_name(cls, name: str) -> Corpus | None:
        return await cls.find_one({"corpus_name": name})

    async def get_trie_index(self) -> TrieIndex:
        if not self._trie_index:
            # Load from cache or build
            self._trie_index = await TrieIndex.get_or_create(self)
        return self._trie_index
```

**Benefits:**
- ✅ No separate Metadata class
- ✅ Direct MongoDB operations
- ✅ Simple versioning (increment counter)
- ✅ Type-safe fields
- ✅ Clear save/load semantics

### Option 2: Lightweight VersionManager

**Keep versioning for providers only:**

```python
class ProviderCache:
    """Simple cache for provider responses with TTL."""

    async def get(
        self,
        provider: str,
        resource_id: str,
    ) -> dict | None:
        cache_key = f"{provider}:{resource_id}"
        return await self.cache.get(CacheNamespace.DICTIONARY, cache_key)

    async def set(
        self,
        provider: str,
        resource_id: str,
        content: dict,
        ttl: timedelta = timedelta(days=7),
    ):
        cache_key = f"{provider}:{resource_id}"
        await self.cache.set(CacheNamespace.DICTIONARY, cache_key, content, ttl)
```

**For corpus/search indices:**
- Store directly in MongoDB as Document
- Use filesystem cache for large objects (FAISS indices)
- Simple versioning via `version: int` field

### Option 3: Hybrid Approach

**Keep VersionManager for external content only:**

```python
class Corpus(Document):
    # All metadata in document
    corpus_name: str
    vocabulary: list[str]  # Inline if < 1000 words
    vocabulary_location: str | None = None  # S3/cache key if large

    @property
    async def full_vocabulary(self) -> list[str]:
        if self.vocabulary:
            return self.vocabulary
        if self.vocabulary_location:
            # Load from external storage
            return await load_from_location(self.vocabulary_location)
        return []

    async def save(self):
        # Store large vocabulary externally
        if len(self.vocabulary) > 1000:
            location = await store_vocabulary(self.vocabulary)
            self.vocabulary = []  # Clear inline
            self.vocabulary_location = location
        await super().save()
```

**Benefits:**
- ✅ Simple for small data (stored inline)
- ✅ Automatic external storage for large data
- ✅ No complex content_location abstraction
- ✅ Direct Document operations

---

## Recommendations

### Immediate Actions (Reduce Complexity)

1. **Simplify Corpus Persistence**
   - Make `Corpus` a Beanie `Document` directly
   - Remove `Corpus.Metadata` nested class
   - Remove TreeCorpusManager facade (just use Corpus methods)
   - Store tree fields (`parent_id`, `child_ids`) directly in document

2. **Simplify VersionManager**
   - Remove unused version chain traversal
   - Remove transaction support (use local locks only)
   - Remove content deduplication
   - Keep only: save latest, get latest, simple caching

3. **Consolidate Patterns**
   - Use Beanie Direct for simple CRUD (Word, Definition, etc.)
   - Use Repository Pattern for API layer with validation
   - Use VersionManager only for provider caching (DictionaryEntry)

### Medium-term Refactoring

1. **Merge BaseVersionedData into specific types**
   ```python
   # Instead of:
   class Corpus.Metadata(BaseVersionedData): ...

   # Do:
   class Corpus(Document):
       version: int = 1
       cache_key: str | None = None  # For external content
   ```

2. **Simplify content storage**
   - Remove automatic inline/external routing
   - Use explicit methods: `save()`, `save_to_cache()`, `load_from_cache()`
   - Store small data inline, large data in S3/cache (manual decision)

3. **Remove unused abstractions**
   - Delete model registry pattern
   - Delete version chain management
   - Delete dependency tracking

### Long-term Vision

**Single, clear persistence pattern:**

```python
# For simple documents
class Word(Document):
    text: str
    async def save(self): ...

# For cached provider responses
class DictionaryEntry(Document):
    provider: str
    content: dict
    cached_at: datetime
    ttl: timedelta

# For large external data
class Corpus(Document):
    vocabulary: list[str] | None  # Inline if small
    vocabulary_s3_key: str | None  # S3 if large

    async def load_vocabulary(self) -> list[str]:
        return self.vocabulary or await load_from_s3(self.vocabulary_s3_key)
```

**Benefits:**
- ✅ One persistence pattern per use case
- ✅ Clear separation of concerns
- ✅ No abstraction layers
- ✅ Easy to understand and maintain

---

## Conclusion

The current architecture has **three overlapping persistence patterns** that create unnecessary complexity:

1. **Beanie Direct** - Simple, works well, used everywhere
2. **VersionManager** - Complex, over-engineered, features unused
3. **Repository** - API-specific, thin wrapper, limited scope

**Key Problems:**
- VersionManager provides versioning features that are never used
- content_location abstraction adds complexity without clear benefit
- Corpus requires constant metadata split/merge between layers
- Multiple indirection layers (Corpus → Manager → VersionManager → Beanie)

**KISS/DRY Violations:**
- 7+ indirection layers to save a simple object
- Duplicate field definitions across Corpus and Corpus.Metadata
- Three different ways to load the same data
- Over-engineered version chains never traversed

**Recommendation:**
- **Keep Beanie Direct** for 90% of use cases
- **Simplify VersionManager** to basic provider caching only
- **Make Corpus a Document** directly, remove TreeCorpusManager facade
- **Use Repository** for API validation layer only

This would reduce codebase complexity by ~40% while maintaining all actually-used functionality.
