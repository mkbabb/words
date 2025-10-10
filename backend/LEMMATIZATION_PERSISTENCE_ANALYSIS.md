# Lemmatization Data Storage and Persistence Analysis

## Executive Summary

Lemmatization data IS properly persisted in the corpus system, stored in versioned content (either `content_inline` or `content_location`), NOT in metadata. However, there are critical bypass paths that could lead to data loss.

## Lemmatization Fields in Corpus Model

**Location**: `/backend/src/floridify/corpus/core.py` (lines 76-78)

```python
lemmatized_vocabulary: list[str] = Field(default_factory=list)
word_to_lemma_indices: dict[int, int] = Field(default_factory=dict)
lemma_to_word_indices: dict[int, list[int]] = Field(default_factory=dict)
```

These fields store:
- `lemmatized_vocabulary`: Unique lemmas in order (e.g., ["run", "cat", "dog"])
- `word_to_lemma_indices`: Maps word index → lemma index (e.g., {0: 0, 1: 0, 2: 1})
- `lemma_to_word_indices`: Maps lemma index → list of word indices (e.g., {0: [0, 1], 1: [2]})

## Creation in _create_unified_indices()

**Location**: `/backend/src/floridify/corpus/core.py` (lines 306-343)

**Process**:
1. **Skip if already created**: Checks `if self.lemmatized_vocabulary:` (line 309)
2. **Lemmatize vocabulary**: `batch_lemmatize(self.vocabulary)` (line 313)
3. **Build unique lemma list**: Deduplicate while preserving order (lines 316-323)
4. **Create mappings**: Build bidirectional index maps (lines 328-338)

**Called by**:
- `Corpus.create()` - Initial corpus creation (line 233)
- `Corpus._rebuild_indices()` - After vocabulary changes (line 298)

## Persistence Flow

### Primary Save Path: corpus.save()

**Location**: `/backend/src/floridify/corpus/core.py` (line 714)

```
corpus.save()
  ↓
manager.save_corpus(content=self.model_dump())  [line 748]
  ↓
vm.save(content=content_dict)  [manager.py line 227]
  ↓
set_versioned_content(versioned, content)  [manager.py line 265]
  ↓
Storage decision:
  - If content < 16KB: content_inline (MongoDB document)
  - If content >= 16KB: content_location (filesystem cache)
```

### Key Functions

#### 1. Corpus.model_dump()
**Location**: `/backend/src/floridify/corpus/core.py` (lines 591-593)

```python
def model_dump(self, **kwargs: Any) -> dict[str, Any]:
    """Dump model to dict, handling special fields."""
    return super().model_dump(exclude={"vocabulary_indices"}, **kwargs)
```

**Includes**: ALL Pydantic fields including lemmatization data
**Excludes**: Only `vocabulary_indices` (deprecated field)

#### 2. set_versioned_content()
**Location**: `/backend/src/floridify/caching/core.py` (lines 490-516)

```python
async def set_versioned_content(versioned_data, content, *, force_external=False):
    content_str = json.dumps(content, sort_keys=True, default=_json_default)
    content_size = len(content_str.encode())
    inline_threshold = 16 * 1024  # 16KB
    
    if not force_external and content_size < inline_threshold:
        versioned_data.content_inline = content  # Store in MongoDB
        versioned_data.content_location = None
    else:
        # Store in filesystem cache
        cache_key = f"{resource_type}:{resource_id}:content:{hash[:8]}"
        await cache.set(namespace, cache_key, content)
        versioned_data.content_location = ContentLocation(...)
        versioned_data.content_inline = None
```

## Retrieval Flow

**Location**: `/backend/src/floridify/corpus/manager.py` (line 325)

```
manager.get_corpus(corpus_id or corpus_name)
  ↓
vm.get_latest(resource_id, ResourceType.CORPUS)  [line 338/345]
  ↓
get_versioned_content(metadata)  [line 357]
  ↓
Content retrieval:
  - If content_inline exists: return directly
  - If content_location exists: fetch from cache
  ↓
Corpus.model_validate(content)  [line 416]
  ↓
Returns Corpus with all fields restored
```

### Key Function: get_versioned_content()
**Location**: `/backend/src/floridify/caching/core.py` (lines 437-478)

```python
async def get_versioned_content(versioned_data) -> dict[str, Any] | None:
    # Inline content takes precedence
    if versioned_data.content_inline is not None:
        return versioned_data.content_inline  # Direct return
    
    # External content
    if versioned_data.content_location:
        location = versioned_data.content_location
        if location.cache_key and location.cache_namespace:
            cache = await get_global_cache()
            cached_content = await cache.get(namespace, location.cache_key)
            return cached_content if isinstance(cached_content, dict) else None
    
    return None  # ⚠️ Returns None if cache miss!
```

## Corpus.Metadata Structure

**Location**: `/backend/src/floridify/corpus/core.py` (lines 115-143)

```python
class Metadata(BaseVersionedData):
    # Identification
    corpus_name: str = ""
    corpus_type: CorpusType = CorpusType.LEXICON
    language: Language = Language.ENGLISH
    
    # Tree structure
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False
    
    # Vocabulary metadata (NOT the actual data)
    vocabulary_size: int = 0
    vocabulary_hash: str = ""
    
    # Storage configuration
    content_location: ContentLocation | None = None
```

**Key Point**: Metadata does NOT contain:
- vocabulary
- vocabulary_to_index
- lemmatized_vocabulary
- word_to_lemma_indices
- lemma_to_word_indices
- signature_buckets
- length_buckets

These are in the versioned content!

## Storage Location Summary

### Versioned Content (where lemmatization lives)
- **Small corpora (< 16KB)**: `content_inline` in MongoDB document
- **Large corpora (>= 16KB)**: `content_location` pointing to cache file
- **Includes**: All vocabulary, indices, lemmatization data

### Metadata Document (BaseVersionedData in MongoDB)
- **Always in MongoDB**: Document in `versioned_data` collection
- **Contains**: Identification, tree structure, version info, content pointer
- **Does NOT contain**: Actual vocabulary or lemmatization data

## Critical Gaps and Issues

### 1. Bypass Path: save_corpus_simple()
**Location**: `/backend/src/floridify/corpus/manager.py` (lines 40-79)

```python
async def save_corpus_simple(self, corpus: Corpus, config=None):
    # Get or create metadata
    metadata = await Corpus.Metadata.get(corpus.corpus_id) or Corpus.Metadata(...)
    
    # Store content directly ⚠️
    content = corpus.model_dump(mode="json")
    metadata.content = content  # ⚠️ BYPASSES set_versioned_content!
    
    # Save to MongoDB
    await metadata.save()  # ⚠️ BYPASSES version manager!
```

**Problem**: Sets `metadata.content` directly, bypassing:
- `set_versioned_content()` storage logic
- Version manager save flow
- Content size threshold checks

**Result**: Large corpus data may be stored incorrectly

### 2. Bypass Path: save_metadata()
**Location**: `/backend/src/floridify/corpus/manager.py` (lines 81-102)

```python
async def save_metadata(self, metadata: Corpus.Metadata):
    """Save a Corpus.Metadata object directly to MongoDB.
    
    This bypasses all corpus logic and directly saves the metadata.
    Used for low-level operations and tests.
    """
    await metadata.save()  # ⚠️ BYPASSES version manager!
```

**Problem**: Direct metadata save without content validation

**Risk**: Metadata could be saved without corresponding content

### 3. Cache Eviction Risk
**Location**: `/backend/src/floridify/caching/core.py` (line 476)

```python
async def get_versioned_content(versioned_data):
    if versioned_data.content_location:
        cached_content = await cache.get(namespace, location.cache_key)
        return cached_content if isinstance(cached_content, dict) else None
    
    return None  # ⚠️ Returns None on cache miss!
```

**Problem**: If external cache is evicted:
- `get_versioned_content()` returns `None`
- Corpus reconstruction fails
- Lemmatization data is lost

**No fallback**: No mechanism to regenerate from vocabulary

### 4. Rebuild Guard
**Location**: `/backend/src/floridify/corpus/core.py` (line 309)

```python
async def _create_unified_indices(self):
    # Skip if already created
    if self.lemmatized_vocabulary:
        return
```

**Problem**: If loaded corpus has empty lemmatization but non-empty vocabulary:
- Guard passes (empty list is falsy)
- Indices would be rebuilt
- But if vocabulary is missing, nothing happens

## Correct Usage Patterns

### Save
```python
# ✅ CORRECT: Use corpus.save()
corpus = await Corpus.create(vocabulary=words)
await corpus.save()  # Uses version manager + set_versioned_content

# ✅ CORRECT: Use manager.save_corpus() with corpus object
await manager.save_corpus(corpus=corpus)

# ❌ WRONG: Use save_corpus_simple
await manager.save_corpus_simple(corpus)  # Bypasses version manager

# ❌ WRONG: Save metadata directly
metadata = Corpus.Metadata(...)
await metadata.save()  # No content stored!
```

### Update
```python
# ✅ CORRECT: Use manager.update_corpus()
await manager.update_corpus(
    corpus_id=corpus.corpus_id,
    content={"vocabulary": new_vocab}
)

# ✅ CORRECT: Modify and save
corpus.vocabulary.extend(new_words)
await corpus._rebuild_indices()
await corpus.save()
```

### Retrieve
```python
# ✅ CORRECT: Use manager.get_corpus()
corpus = await manager.get_corpus(corpus_id=id)
# Returns full Corpus with lemmatization

# ✅ CORRECT: Use Corpus.get()
corpus = await Corpus.get(corpus_id=id)
# Also uses manager.get_corpus() internally

# ❌ WRONG: Get metadata directly
metadata = await Corpus.Metadata.get(id)
# Only has metadata, no content!
```

## Recommendations

### Immediate Fixes

1. **Remove or fix save_corpus_simple()**
   - Either remove entirely
   - Or make it use `set_versioned_content()`

2. **Add cache persistence validation**
   - Check if external content exists before save
   - Log warnings on cache misses
   - Add cache warming on startup

3. **Add content validation on get_corpus()**
   ```python
   content = await get_versioned_content(metadata)
   if not content:
       # Try to regenerate from vocabulary if possible
       # Or raise error with recovery instructions
   ```

4. **Document bypass functions clearly**
   - Mark `save_metadata()` as dangerous
   - Add warnings in docstrings
   - Consider removing if unused

### Long-term Improvements

1. **Eliminate inline vs external complexity**
   - Always store in cache with reference
   - MongoDB only has metadata + pointer
   - Simpler consistency model

2. **Add automatic index rebuild**
   - Detect missing lemmatization on load
   - Rebuild from vocabulary if needed
   - Log warning for manual review

3. **Add integrity checks**
   - Validate content_location points to existing cache
   - Check content_inline is not too large
   - Verify lemmatization matches vocabulary size

4. **Cache redundancy**
   - Store critical content in both MongoDB and cache
   - Use MongoDB as fallback for cache misses
   - Periodic cache validation job

## Testing Recommendations

```python
# Test lemmatization persistence
async def test_lemma_persistence():
    # Create corpus with lemmatization
    corpus = await Corpus.create(vocabulary=["running", "runs", "cats"])
    assert len(corpus.lemmatized_vocabulary) > 0
    
    # Save and clear from memory
    await corpus.save()
    corpus_id = corpus.corpus_id
    del corpus
    
    # Reload from storage
    loaded = await Corpus.get(corpus_id=corpus_id)
    
    # Verify lemmatization restored
    assert loaded.lemmatized_vocabulary == ["run", "cat"]
    assert loaded.word_to_lemma_indices == {0: 0, 1: 0, 2: 1}
    assert loaded.lemma_to_word_indices == {0: [0, 1], 1: [2]}

# Test cache eviction recovery
async def test_cache_eviction():
    corpus = await Corpus.create(vocabulary=large_vocab)
    await corpus.save()
    
    # Simulate cache eviction
    cache = await get_global_cache()
    await cache.clear_namespace(CacheNamespace.CORPUS)
    
    # Try to reload
    loaded = await Corpus.get(corpus_id=corpus.corpus_id)
    
    # Should either succeed with regeneration or fail gracefully
    assert loaded is not None or "clear error message"
```

## Conclusion

**Lemmatization data IS persisted** via the version manager's content storage mechanism. It's stored in `content_inline` (small corpora) or `content_location` (large corpora), NOT in the metadata document.

**Critical risks**:
1. `save_corpus_simple()` bypasses version manager
2. Cache eviction can lose large corpus data
3. No automatic regeneration on data loss

**Action items**:
1. Fix or remove bypass functions
2. Add cache validation and fallbacks
3. Implement automatic index rebuild on load
4. Add comprehensive persistence tests
