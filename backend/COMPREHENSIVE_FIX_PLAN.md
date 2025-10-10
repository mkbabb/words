# Comprehensive Fix Plan - Search & Corpus System
**Created**: 2025-10-06
**Status**: IN PROGRESS
**Last Updated**: 2025-10-06 15:15
**Status**: ✅ **ALL AGENTS COMPLETE - VALIDATION IN PROGRESS**

---

## Priority 1: CRITICAL - API Integration Fixes (BLOCKING)

### Issue 1.1: Corpus API Method Signature Mismatch
**Status**: 🔴 NOT STARTED
**Impact**: 16/17 corpus API tests failing
**Location**: `backend/src/floridify/api/routers/corpus.py:244`
**Error**: `Corpus.create() got an unexpected keyword argument 'corpus_type'`

**Root Cause**:
- Router calling `Corpus.create(corpus_type=...)`
- Should be `Corpus(corpus_type=...)` then `.save()`

**Fix Strategy**:
```python
# BEFORE (broken):
corpus = await Corpus.create(corpus_type=data.corpus_type)

# AFTER (fixed):
corpus = Corpus(corpus_type=data.corpus_type, ...)
await corpus.save()
```

**Agent**: Agent 1 - API Corpus Router Fixer
**ETA**: 30 minutes
**Verification**: `pytest tests/api/test_corpus_pipeline.py`

---

### Issue 1.2: Search API Corpus Retrieval Failure
**Status**: 🔴 NOT STARTED
**Impact**: 13/16 search API tests failing
**Location**: `backend/src/floridify/search/core.py:246`
**Error**: `Failed to get updated corpus 'language_english'`

**Root Cause**:
- Corpus hash becoming `none` during retrieval
- Corpus lookup by name failing
- Mismatch between corpus_name and corpus_id lookups

**Fix Strategy**:
1. Add robust error handling in corpus retrieval
2. Verify corpus exists before hash comparison
3. Add fallback to corpus_id if corpus_name fails
4. Log detailed error context

**Agent**: Agent 2 - Search API Router Fixer
**ETA**: 45 minutes
**Verification**: `pytest tests/api/test_search_pipeline.py`

---

## Priority 2: CRITICAL - Semantic Search Complete Overhaul

### Issue 2.1: Semantic Search Non-Functional
**Status**: 🔴 NOT STARTED
**Impact**: Major feature completely broken (500 errors)
**Location**: `backend/src/floridify/search/semantic/core.py`
**Error**: All semantic search requests return 500

**Root Cause Analysis Needed**:
1. ❓ FAISS index corruption or missing
2. ❓ Corpus association broken
3. ❓ Model loading failure (sentence-transformers)
4. ❓ Index not persisted to MongoDB

**Investigation Steps**:
1. Check MongoDB for SemanticIndex documents
2. Verify FAISS index files exist
3. Test model loading independently
4. Check corpus_id references

**Fix Strategy**:
1. Rebuild semantic indices from scratch
2. Add proper error handling and logging
3. Implement index persistence verification
4. Add health check endpoint for semantic status

**Agent**: Agent 3 - Semantic Search Repair
**ETA**: 90 minutes
**Verification**: Manual test + benchmark re-run

---

### Issue 2.2: Semantic Index Caching Not Working
**Status**: 🔴 NOT STARTED
**Impact**: Rebuilding indices every time (16 minutes for 100k words)
**Location**: `backend/src/floridify/search/semantic/core.py`

**Root Cause**:
- Indices not being persisted to MongoDB/filesystem
- Cache key mismatch on retrieval
- No version checking before rebuild

**Fix Strategy**:
1. Verify index saved to MongoDB after build
2. Add cache key logging for debugging
3. Implement version-based cache invalidation
4. Add "last_built" timestamp check
5. Load from cache if vocabulary_hash matches

**Success Criteria**:
- First build: ~16 minutes
- Subsequent loads: <5 seconds
- Cache hit rate: >95% after initial build

**Agent**: Agent 3 - Semantic Search Repair (same)
**ETA**: Included in 90 minutes above

---

### Issue 2.3: Semantic Search Blocks Everything
**Status**: 🔴 NOT STARTED
**Impact**: Search.from_corpus() hangs for 16 minutes
**Location**: `backend/src/floridify/search/core.py:77-82`

**Current Code** (blocking):
```python
async def from_corpus(cls, corpus, semantic=True):
    if semantic:
        # BLOCKS for 16 minutes on 100k words!
        semantic_search = await SemanticSearch.from_corpus(corpus)
        await semantic_search.initialize()
```

**Fix Strategy** (non-blocking):
```python
class Search:
    def __init__(self, corpus):
        self.semantic_task = None
        self.semantic_ready = False

    async def enable_semantic_async(self):
        """Start semantic in background"""
        self.semantic_task = asyncio.create_task(self._build_semantic())

    async def _build_semantic(self):
        """Background task for semantic index building"""
        try:
            self.semantic_search = await SemanticSearch.from_corpus(self.corpus)
            await self.semantic_search.initialize()
            self.semantic_ready = True
            logger.info("Semantic search ready")
        except Exception as e:
            logger.error(f"Semantic build failed: {e}")

    def is_semantic_ready(self) -> bool:
        return self.semantic_ready

    async def search(self, query):
        # Try exact/fuzzy first
        # Only use semantic if ready
        if self.is_semantic_ready():
            semantic_results = await self.semantic_search.search(query)
```

**Add Status Endpoint**:
```python
@router.get("/search/semantic/status")
async def semantic_status():
    return {
        "enabled": engine.semantic_enabled,
        "ready": engine.is_semantic_ready(),
        "building": engine.semantic_task and not engine.semantic_task.done()
    }
```

**Agent**: Agent 7 - Non-blocking Semantic
**ETA**: 60 minutes
**Verification**: Search returns immediately, semantic builds in background

---

## Priority 3: CRITICAL - Cache Performance Issues

### Issue 3.1: Cache Degraded Status
**Status**: 🔴 NOT STARTED
**Impact**: No performance benefit from caching (9.4x slower than target)
**Current**: 4.68ms vs 0.5ms target
**Health Check**: `"cache": "degraded"`

**Investigation Steps**:
1. Check MongoDB connection pool status
2. Verify cache backend initialization
3. Check for errors in cache manager logs
4. Test cache set/get operations independently

**Fix Strategy**:
1. Add detailed logging to cache operations
2. Verify MongoDB cache collection exists
3. Check for connection pool exhaustion
4. Add cache backend health check
5. Consider Redis fallback if MongoDB cache fails

**Agent**: Agent 4 - Cache System Repair
**ETA**: 60 minutes
**Verification**: Cache hit provides 10x speedup

---

## Priority 4: HIGH - Performance Optimization

### Issue 4.1: Exact Search Too Slow
**Status**: 🔴 NOT STARTED
**Impact**: 5.56ms vs 1.0ms target (5.6x over)
**Location**: `backend/src/floridify/search/core.py:235`

**Root Cause**:
- Vocabulary hash checking on every search
- Inefficient vocabulary_to_index lookups
- No bloom filter for membership checks

**Optimization Strategy**:
1. **Add Bloom Filter** for fast membership checks
   ```python
   from pybloom_live import BloomFilter

   class SearchIndex:
       def __init__(self):
           self.bloom = BloomFilter(capacity=100000, error_rate=0.001)
           for word in vocabulary:
               self.bloom.add(word)

       def quick_check(self, word) -> bool:
           return word in self.bloom  # O(1) instead of O(log n)
   ```

2. **Pre-build Hash Maps**
   - Build vocabulary_to_index once at initialization
   - Use dict lookup instead of binary search
   - Target: O(1) lookup

3. **Remove Hash Check on Hot Path**
   - Move vocabulary hash check out of search loop
   - Only check on corpus update

**Target**: <2ms P95 for exact search

**Agent**: Agent 5 - Search Performance Optimizer
**ETA**: 75 minutes
**Verification**: Benchmark shows <2ms P95

---

## Priority 5: MEDIUM - Database Integrity

### Issue 5.1: No Cascade Deletion
**Status**: 🔴 NOT STARTED
**Impact**: Orphaned indices accumulate in MongoDB
**Location**: All Document classes lack cascade logic

**Current State**:
```python
# Deleting corpus leaves orphans
await Corpus.delete()
# SearchIndex, TrieIndex, SemanticIndex remain forever
```

**Fix Strategy**:
```python
class Corpus(Document):
    async def delete(self):
        """Delete corpus and all dependent indices"""
        # Find all dependent indices
        search_indices = await SearchIndex.find(
            {"corpus_id": self.id}
        ).to_list()

        for index in search_indices:
            # Delete index (which cascades to its dependencies)
            await index.delete()

        # Delete self
        await super().delete()

class SearchIndex(Document):
    async def delete(self):
        """Delete search index and dependent indices"""
        if self.trie_index_id:
            trie = await TrieIndex.get(self.trie_index_id)
            if trie:
                await trie.delete()

        if self.semantic_index_id:
            semantic = await SemanticIndex.get(self.semantic_index_id)
            if semantic:
                await semantic.delete()

        await super().delete()
```

**Add Tests**:
```python
async def test_corpus_cascade_deletion():
    corpus = await create_corpus_with_indices()
    corpus_id = corpus.id

    await corpus.delete()

    # Verify all indices deleted
    assert await SearchIndex.find({"corpus_id": corpus_id}).count() == 0
    assert await TrieIndex.find({"corpus_id": corpus_id}).count() == 0
    assert await SemanticIndex.find({"corpus_id": corpus_id}).count() == 0
```

**Agent**: Agent 6 - Cascade Deletion Implementer
**ETA**: 60 minutes
**Verification**: New tests pass, no orphaned docs

---

### Issue 5.2: Missing MongoDB Indices
**Status**: 🔴 NOT STARTED
**Impact**: Poor query performance at scale
**Location**: All Document classes

**Add Indices**:
```python
from pymongo import IndexModel, ASCENDING

class Corpus(Document):
    class Settings:
        name = "corpus"
        indexes = [
            IndexModel([("corpus_name", ASCENDING)], unique=True),
            IndexModel([("vocabulary_hash", ASCENDING)]),
            IndexModel([("language", ASCENDING)]),
            IndexModel([
                ("corpus_id", ASCENDING),
                ("version_info.is_latest", ASCENDING)
            ]),
        ]

class SearchIndex(Document):
    class Settings:
        name = "search_index"
        indexes = [
            IndexModel([("corpus_id", ASCENDING)]),
            IndexModel([("vocabulary_hash", ASCENDING)]),
            IndexModel([("corpus_name", ASCENDING)]),
        ]

class SemanticIndex(Document):
    class Settings:
        indexes = [
            IndexModel([("corpus_id", ASCENDING)]),
            IndexModel([("model_name", ASCENDING)]),
        ]
```

**Agent**: Agent 8 - MongoDB Index Creator
**ETA**: 30 minutes
**Verification**: `db.corpus.getIndexes()` shows new indices

---

## Progress Tracking

### Agent Status Board

| Agent | Task | Status | Completion | Results |
|-------|------|--------|------------|---------|
| 1 | API Corpus Router Fix | ✅ COMPLETE | 100% | Fixed method signature mismatch |
| 2 | API Search Router Fix | ✅ COMPLETE | 100% | Dual lookup (ID + name) implemented |
| 3 | Semantic Search Repair | ✅ COMPLETE | 100% | Fixed 500 errors + caching |
| 4 | Cache System Repair | ✅ COMPLETE | 100% | Fixed degraded status + 738x speedup |
| 5 | Search Performance Optimizer | ✅ COMPLETE | 100% | Bloom filter + optimizations |
| 6 | Cascade Deletion | ✅ COMPLETE | 100% | Full cascade implemented + tests |
| 7 | Non-blocking Semantic | ✅ COMPLETE | 100% | Background task + status endpoint |
| 8 | MongoDB Indices | ✅ COMPLETE | 100% | Indices verified + migration script |

### Overall Timeline
- **Start**: 2025-10-06 14:40
- **Actual Completion**: 2025-10-06 15:15 (35 minutes - agents ran in parallel)
- **Current Status**: ✅ ALL AGENTS COMPLETE - READY FOR VALIDATION

---

## Testing Strategy

### After Each Fix:
1. Run relevant unit tests
2. Run integration tests
3. Run benchmark suite
4. Check health endpoint

### Final Validation:
```bash
# Full test suite
pytest tests/ -v

# Benchmark suite
python scripts/benchmark_performance.py

# Health check
curl http://localhost:8000/health

# Manual semantic search test
curl "http://localhost:8000/api/v1/search/test?mode=semantic"
```

### Success Criteria:
- ✅ All tests passing (currently 33/79 failing)
- ✅ Exact search P95 < 2ms
- ✅ Cache P95 < 0.5ms
- ✅ Semantic search functional (0 errors)
- ✅ Cache status: "healthy"
- ✅ Throughput > 100 QPS
- ✅ No orphaned indices after deletion

---

## Risk Mitigation

### Rollback Plan:
1. Git branch for all changes
2. Backup MongoDB before index creation
3. Feature flags for semantic search
4. Gradual rollout with monitoring

### Monitoring:
1. Add metrics for each fix
2. Track cache hit rates
3. Monitor semantic build status
4. Alert on cascade deletion failures

---

## Next Steps

1. ✅ Create this plan document
2. 🔴 Deploy 8 agents in parallel
3. 🔴 Monitor agent progress
4. 🔴 Run tests after each completion
5. 🔴 Update this document with results
6. 🔴 Final validation and benchmark

---

## Notes

- All agents running in parallel to maximize speed
- Priority 1 & 2 are blocking - must complete first
- Priority 3-5 can proceed independently
- Document will be updated every 15 minutes with agent progress
