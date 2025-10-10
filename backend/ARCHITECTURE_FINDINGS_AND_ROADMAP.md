# Technical Debt & Fixes

## What Was Broken (Now Fixed)

**Index Persistence**
- Cache updated before database write completed → Fixed: moved cache update after DB transaction
- All failures were silent → Fixed: added RuntimeError with context
- SemanticIndex stored data twice (400MB each) → Fixed: removed inline storage, kept external only
- No verification after saves → Fixed: all saves now verify retrieval

## What's Still Broken

### 1. Providers Fail on First Error

**Current code** (`providers/literature/sources.py`):
```python
for provider in [gutenberg, wikisource, archive_org]:
    result = await provider.get_text(title)  # First failure kills entire lookup
    if result:
        return result
```

**Fix needed**: Try all providers
```python
for provider in [gutenberg, wikisource, archive_org]:
    try:
        result = await provider.get_text(title)
        if result:
            return result
    except Exception as e:
        logger.warning(f"{provider} failed: {e}")
        continue
return None  # All failed
```

### 2. No Cascade Deletion Anywhere

**Current state** - All MongoDB models lack cascade:
```python
async def delete_corpus(corpus_id: str):
    await Corpus.find_one({"_id": corpus_id}).delete()
    # SearchIndex, TrieIndex, SemanticIndex remain forever

async def delete_search_index(index_id: str):
    await SearchIndex.find_one({"_id": index_id}).delete()
    # Referenced TrieIndex, SemanticIndex remain

async def delete_provider(provider_id: str):
    await Provider.find_one({"_id": provider_id}).delete()
    # Cached results remain
```

**Fix needed** - Add to all Document classes:
```python
class Corpus(Document):
    async def delete(self):
        # Delete dependent indices first
        await SearchIndex.find({"corpus_id": self.id}).delete()
        await TrieIndex.find({"corpus_id": self.id}).delete()
        await SemanticIndex.find({"corpus_id": self.id}).delete()
        await super().delete()

class SearchIndex(Document):
    async def delete(self):
        # Clean up references
        if self.trie_index_id:
            await TrieIndex.find_one({"_id": self.trie_index_id}).delete()
        if self.semantic_index_id:
            await SemanticIndex.find_one({"_id": self.semantic_index_id}).delete()
        await super().delete()
```

### 3. Semantic Search Blocks Everything

**Current code** (`search/core.py`):
```python
async def from_corpus(cls, corpus, semantic=True):
    if semantic:
        # Blocks for 16 minutes on 100k words!
        semantic_search = await SemanticSearch.from_corpus(corpus)
        await semantic_search.initialize()
    return cls(corpus=corpus, semantic_search=semantic_search)
```

**Fix needed**: Non-blocking with status check
```python
class Search:
    def __init__(self, corpus):
        self.corpus = corpus
        self.semantic_enabled = False
        self.semantic_ready = False
        self.semantic_task = None

    async def enable_semantic(self):
        """Start semantic building in background"""
        self.semantic_enabled = True
        self.semantic_task = asyncio.create_task(self._build_semantic())

    async def _build_semantic(self):
        self.semantic_search = await SemanticSearch.from_corpus(self.corpus)
        await self.semantic_search.initialize()
        self.semantic_ready = True

    def is_semantic_ready(self) -> bool:
        return self.semantic_enabled and self.semantic_ready

    async def search(self, query: str):
        results = await self.exact_search(query)
        if not results:
            results = await self.fuzzy_search(query)
        if not results and self.is_semantic_ready():
            results = await self.semantic_search.search(query)
        return results
```

### 4. API Missing Half the Features

**Backend has** (`corpus/language/core.py`):
```python
class LanguageCorpus:
    async def build_from_language(language: Language)
    async def aggregate_from_sources()
    async def validate_vocabulary()
```

**API missing** (`api/routers/corpus.py`):
```python
# Only has:
@router.get("/corpus/{corpus_id}")
# Missing: POST /corpus/build, POST /corpus/aggregate, POST /corpus/validate
```

### 5. No MongoDB Indices

**Current state**: No indices defined
```python
class Corpus(Document):
    corpus_name: str  # Queried constantly, no index
    vocabulary_hash: str  # Queried constantly, no index
```

**Fix needed**: Add indices
```python
class Corpus(Document):
    corpus_name: str
    vocabulary_hash: str

    class Settings:
        indexes = [
            IndexModel([("corpus_name", 1)], unique=True),
            IndexModel([("vocabulary_hash", 1)]),
            IndexModel([("corpus_id", 1), ("version_info.is_latest", 1)])
        ]
```

## Patterns Not Followed

### Missing Inner Metadata

**SearchIndex, TrieIndex lack Metadata**:
```python
class SearchIndex(BaseModel):
    # No inner Metadata class
```

**Should have**:
```python
class SearchIndex(BaseModel):
    class Metadata(BaseVersionedData):
        default_resource_type = ResourceType.SEARCH
        default_namespace = CacheNamespace.SEARCH
```

### Inconsistent Returns

**Some save methods return None**:
```python
async def save(self):
    await db.save(self)
    # Nothing returned
```

**Should return ID**:
```python
async def save(self) -> str:
    await db.save(self)
    return str(self.id)
```

## Code That Needs Deletion

```python
# utils/deprecated.py - 500 lines of unused functions
# models/legacy.py - old models still imported
# api/v1/ - entire folder of old endpoints
# search/experimental/ - failed experiments
```

## Performance Problems

1. **Semantic index blocks Search creation**: 16 minutes for 100k words
   - Fix: Make it non-blocking with status check

2. **MongoDB fetches entire documents**:
   - Fix: Add `.project()` to queries

3. **Cache not warmed after build**:
   - Fix: Pre-populate L1 cache after index creation

## Testing Gaps

- No test for cascade deletion on any model
- No test for provider failure handling
- No test for semantic search readiness check
- No test for concurrent operations

## Priority Fixes

1. **Cascade deletion** - Add to all Document classes
2. **Non-blocking semantic** - Add background task + status check
3. **Provider failures** - Add try/except to all provider loops
4. **MongoDB indices** - Add index definitions to all Document classes
5. **API completeness** - Add missing endpoints for existing backend methods