# Floridify - Comprehensive Fix Plan
**Generated**: 2025-10-06
**Status**: Active Development
**Last Updated**: 2025-10-06 by AI Agent Analysis

---

## Executive Summary

Based on comprehensive analysis by 8 parallel research agents, the Floridify system has **4 critical issues** blocking optimal performance:

1. **Semantic index caching broken** → Always rebuilds (5-15 min delay)
2. **Corpus building slow** → 5-10 min (should be 1-2 min)
3. **Benchmark targets failing** → Semantic 100% error, Exact 5.6x over target
4. **API integration issues** → Enum serialization, missing cache layer

**Total Fix Time**: 8-12 hours
**Expected Performance Gain**: 2-3x overall system speedup

---

## Priority Matrix

| Priority | Issue | Impact | Effort | Status |
|----------|-------|--------|--------|--------|
| **P0** | Semantic index binary data not loaded | 🔴 CRITICAL | 1-2h | 🔄 PENDING |
| **P0** | Semantic search 100% failure rate | 🔴 BLOCKING | 1-2h | 🔄 PENDING |
| **P0** | API enum serialization | 🔴 CRITICAL | 30m | 🔄 PENDING |
| **P1** | Corpus aggregation redundancy | 🟡 HIGH | 2-3h | 🔄 PENDING |
| **P1** | Exact search performance | 🟡 HIGH | 1h | ⚠️ VERIFY |
| **P1** | Cache not providing speedup | 🟡 HIGH | 1-2h | 🔄 PENDING |
| **P2** | Multi-core utilization | 🟠 MEDIUM | 2-3h | 🔄 PENDING |
| **P2** | API search caching | 🟠 MEDIUM | 1h | 🔄 PENDING |
| **P3** | Trie/Bloom filter persistence | 🟢 LOW | 1-2h | 🔄 PENDING |

---

# P0: Critical Blockers (Fix Immediately)

## 1. Semantic Index Binary Data Not Loaded ⚠️ CRITICAL

### Problem
**Location**:
- `backend/src/floridify/search/semantic/core.py:221-270`
- `backend/src/floridify/search/semantic/models.py:132-140`

**Issue**: Binary data (embeddings + FAISS index) not populated when loading from versioned storage.

**Impact**:
- Every load from cache **fails silently**
- Triggers full rebuild (5-15 minutes for 100k vocab)
- Cache effectively useless

**Root Cause**:
```python
# semantic/models.py:132-140 (BROKEN)
content = await get_versioned_content(metadata)
index = cls.model_validate(content)
# ❌ binary_data is lost here - model_validate doesn't preserve it
```

### Fix

**File 1**: `backend/src/floridify/search/semantic/models.py` (line 132-140)

```python
# BEFORE (BROKEN):
content = await get_versioned_content(metadata)
if not content:
    return None
index = cls.model_validate(content)
if metadata.id:
    index.index_id = metadata.id
return index

# AFTER (FIXED):
content = await get_versioned_content(metadata)
if not content:
    return None
index = cls.model_validate(content)

# ✅ FIX: Preserve binary_data from external storage
if "binary_data" in content:
    object.__setattr__(index, "binary_data", content["binary_data"])

if metadata.id:
    index.index_id = metadata.id
return index
```

**File 2**: `backend/src/floridify/search/semantic/core.py` (line 221-270)

```python
# BEFORE (BROKEN):
async def _load_from_index(self) -> None:
    if self.index.embeddings:  # ❌ Always None
        embeddings_bytes = base64.b64decode(self.index.embeddings.encode("utf-8"))
        self.sentence_embeddings = pickle.loads(embeddings_bytes)

# AFTER (FIXED):
async def _load_from_index(self) -> None:
    import zlib

    if not self.index:
        logger.warning("No index to load from")
        return

    if self.index.num_embeddings == 0:
        logger.warning(f"Index for '{self.index.corpus_name}' has 0 embeddings, cannot load.")
        return

    if not self.sentence_model:
        self.sentence_model = await self._initialize_optimized_model()

    # ✅ FIX: Load from binary_data (external storage)
    binary_data = getattr(self.index, "binary_data", None)

    if not binary_data:
        logger.error(f"No binary data found for index '{self.index.corpus_name}'")
        raise RuntimeError("Semantic index missing binary data - cache corrupted")

    try:
        # Load compressed embeddings
        if "embeddings" in binary_data:
            embeddings_bytes = base64.b64decode(binary_data["embeddings"].encode("utf-8"))
            decompressed = zlib.decompress(embeddings_bytes)
            self.sentence_embeddings = pickle.loads(decompressed)
            logger.debug(f"Loaded compressed embeddings: {len(decompressed) / 1024 / 1024:.2f}MB")

        # Load compressed FAISS index
        if "index_data" in binary_data:
            index_bytes = base64.b64decode(binary_data["index_data"].encode("utf-8"))
            decompressed = zlib.decompress(index_bytes)
            faiss_data = pickle.loads(decompressed)
            self.sentence_index = faiss.deserialize_index(faiss_data)
            logger.debug(f"Loaded compressed FAISS index: {len(decompressed) / 1024 / 1024:.2f}MB")

    except Exception as e:
        logger.error(f"Failed to load embeddings/index from cache: {e}", exc_info=True)
        self.sentence_embeddings = None
        self.sentence_index = None
        raise RuntimeError(f"Corrupted semantic index for '{self.index.corpus_name}': {e}") from e
```

### Verification

```bash
# Test semantic index loading
cd backend
python -c "
import asyncio
from floridify.search.semantic.core import SemanticSearch
from floridify.corpus.core import Corpus

async def test():
    corpus = await Corpus.get(corpus_name='language_english')

    # Should load from cache in 2-5 seconds (not rebuild in 5-15 min)
    search = await SemanticSearch.from_corpus(corpus, model_name='BAAI/bge-m3')

    print(f'Loaded: {search.index.num_embeddings} embeddings')
    print(f'Cache hit: {search.sentence_embeddings is not None}')

asyncio.run(test())
"
```

**Expected Output**:
```
Loaded: 270000 embeddings
Cache hit: True
Time: 2-5 seconds (not 5-15 minutes)
```

---

## 2. Semantic Search 100% Failure Rate ⚠️ BLOCKING

### Problem
**Location**: `backend/scripts/benchmark_performance.py`

**Issue**: Semantic search returns 100% errors in latest benchmark (Oct 6, 2025)

**Impact**:
- Cannot benchmark semantic search
- Semantic search unusable in production
- BLOCKING all performance validation

**Root Cause**: Likely corrupted semantic indices in MongoDB

### Fix

**Step 1**: Check for corrupted indices

```bash
cd backend
python -c "
from floridify.search.semantic.models import SemanticIndex
import asyncio

async def check():
    indices = await SemanticIndex.Metadata.find_all().to_list()
    for idx in indices:
        print(f'{idx.corpus_name}: {idx.num_embeddings} embeddings')
        if idx.num_embeddings == 0:
            print(f'  ⚠️ CORRUPTED: Deleting {idx.id}')
            await idx.delete()

asyncio.run(check())
"
```

**Step 2**: Rebuild semantic indices

```bash
# Option 1: Use existing rebuild script
python scripts/rebuild_from_scratch.py

# Option 2: Targeted rebuild
python -c "
import asyncio
from floridify.corpus.core import Corpus
from floridify.search.semantic.core import SemanticSearch

async def rebuild():
    corpus = await Corpus.get(corpus_name='language_english')
    print(f'Rebuilding semantic index for {len(corpus.vocabulary):,} words...')

    search = await SemanticSearch.from_corpus(
        corpus,
        model_name='BAAI/bge-m3',
        force_rebuild=True
    )

    print(f'✅ Built: {search.index.num_embeddings:,} embeddings')

asyncio.run(rebuild())
"
```

**Step 3**: Verify semantic search works

```bash
python scripts/benchmark_performance.py
```

**Expected Output**: Semantic search P95 < 10ms (no errors)

---

## 3. API Enum Serialization ⚠️ CRITICAL

### Problem
**Location**: `backend/src/floridify/corpus/manager.py:203-234`

**Issue**: Enum objects saved to MongoDB instead of string values

**Impact**:
- API server won't start
- Pydantic validation error on corpus load
- **Blocks ALL API functionality**

**Error**:
```
Pydantic validation error when loading corpus from MongoDB
- Expected: String values ("en", "lexicon")
- Actual: Enum objects (Language.ENGLISH, CorpusType.LEXICON)
```

### Fix

**File**: `backend/src/floridify/corpus/manager.py` (line 203-234)

```python
# BEFORE (BROKEN):
async def save_corpus(...):
    full_metadata = {
        "corpus_type": corpus_type,  # ❌ Enum object
        "language": language,        # ❌ Enum object
        ...
    }

# AFTER (FIXED):
async def save_corpus(...):
    full_metadata = {
        "corpus_type": corpus_type.value if isinstance(corpus_type, CorpusType) else corpus_type,
        "language": language.value if isinstance(language, Language) else language,
        "parent_corpus_id": parent_corpus_id,
        "child_corpus_ids": child_corpus_ids or [],
        "is_master": is_master,
        "vocabulary_size": len(content.get("vocabulary", [])),
        "vocabulary_hash": content.get("vocabulary_hash", ""),
    }
```

**Also check**: All other enum serialization points

```bash
cd backend
grep -r "corpus_type\|language" src/floridify/corpus/ | grep -v ".value"
```

### Verification

```bash
# Restart API server
./scripts/dev --restart-backend

# Check health endpoint
curl http://localhost:8000/health
```

**Expected Output**: `{"status": "healthy", "cache": {...}}`

---

# P1: High Priority (Fix This Week)

## 4. Corpus Aggregation Redundancy ⚠️ HIGH

### Problem
**Location**: `backend/src/floridify/corpus/language/core.py:108`

**Issue**: Vocabulary aggregation runs after **each source** addition (7-10 times for English)

**Impact**:
- Wasted CPU on intermediate aggregations
- O(n²) complexity instead of O(n)
- 5-10 min corpus build (should be 1-2 min)

**Current Flow**:
```python
for source in sources:
    await add_language_source(source)
    await aggregate_vocabularies()  # ❌ Called 7 times for English
```

### Fix

**File**: `backend/src/floridify/corpus/language/core.py`

**Option 1**: Add `aggregate` parameter (recommended)

```python
# Line 65-110 (add_language_source method)
async def add_language_source(
    self,
    source: LanguageSource,
    aggregate: bool = True,  # ✅ NEW parameter
    config: VersionConfig | None = None
) -> None:
    # ... create child corpus ...

    # Only aggregate if requested
    if aggregate:
        await manager.aggregate_vocabularies(self.corpus_id)

# Line 146-228 (create_from_language method)
@classmethod
async def create_from_language(cls, ...):
    # Add all sources WITHOUT aggregation
    tasks = [
        corpus.add_language_source(source, aggregate=False, config=config)
        for source in sources
    ]
    await asyncio.gather(*tasks)

    # ✅ Aggregate ONCE at the end
    await manager.aggregate_vocabularies(corpus.corpus_id, config=config)

    # Reload final corpus
    return await cls.get(corpus_id=corpus.corpus_id, config=VersionConfig(use_cache=False))
```

**Option 2**: Batch aggregation in manager

```python
# backend/src/floridify/corpus/manager.py:545-628
async def aggregate_vocabularies(
    self,
    corpus_id: PydanticObjectId,
    config: VersionConfig | None = None,
    update_parent: bool = True,
) -> list[str]:
    # Get all children in ONE DB query (not recursive)
    children = await self.get_corpora_by_ids(child_ids, config)

    # Merge vocabularies without recursion
    vocabulary = set()
    for child in children:
        vocabulary.update(child.vocabulary)

    return sorted(vocabulary)
```

### Verification

```bash
# Time corpus build
cd backend
time python -c "
import asyncio
from floridify.corpus.language.core import LanguageCorpus
from floridify.corpus.language.models import Language

async def test():
    corpus = await LanguageCorpus.create_from_language(
        Language.ENGLISH,
        force_rebuild=True
    )
    print(f'Built corpus: {len(corpus.vocabulary):,} words')

asyncio.run(test())
"
```

**Expected Output**: Build time 1-2 minutes (down from 5-10 min)

---

## 5. Exact Search Performance ⚠️ VERIFY

### Problem
**Location**: Benchmark shows 5.56ms P95 vs 1.0ms target (5.6x over)

**Status**: ⚠️ **Optimizations already implemented** - need verification

**Optimizations Applied** (from EXACT_SEARCH_OPTIMIZATION_REPORT.md):
- ✅ Bloom filter for negative lookups
- ✅ Removed redundant normalization
- ✅ Inlined hot path functions
- ✅ Removed corpus update from search path

### Fix

**Verification Steps**:

```bash
# 1. Check if Bloom filter is enabled
cd backend
python -c "
from floridify.search.bloom import BloomFilter
print('✅ Bloom filter module exists')
"

# 2. Check if optimizations are in place
grep -A5 "_bloom_filter" src/floridify/search/trie.py

# 3. Run microbenchmark
python scripts/profile_exact_search.py

# 4. Run API benchmark
python scripts/benchmark_performance.py
```

**Expected Results**:
- Bloom filter: ✅ Enabled
- P95 latency: < 1.5ms (down from 5.56ms)

**If not working**: Check git status to ensure optimizations are committed

```bash
git status
git diff src/floridify/search/
```

---

## 6. Cache Not Providing Speedup ⚠️ HIGH

### Problem
**Location**: Benchmark shows cache P95 4.68ms vs 0.5ms target (9.4x over)

**Issue**: Cache should be 10x faster, currently same speed as uncached

**Possible Causes**:
1. Low cache hit rate (<50%)
2. Serialization overhead
3. Async/sync method mismatch

### Fix

**Diagnostic Steps**:

```bash
cd backend

# 1. Check cache hit rate
curl http://localhost:8000/health | jq '.cache'

# 2. Profile cache operations
python -c "
import asyncio
import time
from floridify.caching.core import get_cache_manager

async def test():
    cache = get_cache_manager()

    # Test set/get performance
    data = {'test': 'data' * 1000}

    times = []
    for i in range(100):
        key = f'test_key_{i}'

        start = time.perf_counter()
        await cache.set('SEARCH', key, data)
        result = await cache.get('SEARCH', key)
        duration = (time.perf_counter() - start) * 1000
        times.append(duration)

    avg = sum(times) / len(times)
    p95 = sorted(times)[94]

    print(f'Avg: {avg:.3f}ms, P95: {p95:.3f}ms')
    print(f'Target: <0.5ms, Status: {'✅' if p95 < 0.5 else '❌'}')

asyncio.run(test())
"
```

**Expected Issues & Fixes**:

**Issue 1**: Low cache hit rate
```python
# Check cache stats
stats = cache.get_stats()
print(f"Hit rate: {stats['stats']['hits'] / (stats['stats']['hits'] + stats['stats']['misses']):.1%}")

# If <80%, check cache keys and TTL
```

**Issue 2**: Serialization overhead
```python
# Profile serialization
from floridify.caching.serialization import serialize_value, deserialize_value

data = {'large': 'object' * 10000}
start = time.perf_counter()
serialized = serialize_value(data)
duration = (time.perf_counter() - start) * 1000
print(f"Serialization: {duration:.3f}ms")
```

**Issue 3**: Async/sync mismatch (from CACHE_REPAIR_REPORT.md)
```python
# Check for incorrect awaits
grep -r "await.*get_stats" src/floridify/
```

### Verification

```bash
python scripts/benchmark_performance.py
```

**Expected Output**: Cache P95 < 0.5ms with >90% hit rate

---

# P2: Medium Priority (Fix This Month)

## 7. Multi-Core Utilization ⚠️ MEDIUM

### Problem
**Issue**: Corpus building and semantic indexing not fully utilizing available cores

**Current Utilization**:
- Embedding generation: ✅ 75% of cores (already optimized)
- Corpus normalization: ⚠️ 5000-word threshold (conservative)
- Corpus lemmatization: ⚠️ 10000-word threshold (conservative)
- Signature indexing: ❌ Not parallelized

### Fix

**File 1**: `backend/src/floridify/text/normalize.py:232`

```python
# BEFORE:
min_parallel_size = 5000

# AFTER:
min_parallel_size = 2000  # Lower threshold for earlier parallelization
```

**File 2**: `backend/src/floridify/corpus/core.py:560-589`

Add parallel signature index building:

```python
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict

def _build_signature_index_chunk(args):
    vocabulary, start_idx = args
    sig_buckets = defaultdict(list)
    len_buckets = defaultdict(list)

    for i, word in enumerate(vocabulary):
        idx = start_idx + i
        sig_buckets[get_word_signature(word)].append(idx)
        len_buckets[len(word)].append(idx)

    return sig_buckets, len_buckets

def _build_signature_index(self) -> None:
    import os

    cpu_count = os.cpu_count() or 4
    chunk_size = len(self.vocabulary) // cpu_count

    if len(self.vocabulary) < 10000:
        # Small vocabulary, use sequential
        for idx, word in enumerate(self.vocabulary):
            signature = get_word_signature(word)
            if signature not in self.signature_buckets:
                self.signature_buckets[signature] = []
            self.signature_buckets[signature].append(idx)

            length = len(word)
            if length not in self.length_buckets:
                self.length_buckets[length] = []
            self.length_buckets[length].append(idx)
    else:
        # Large vocabulary, parallelize
        chunks = [
            (self.vocabulary[i:i+chunk_size], i)
            for i in range(0, len(self.vocabulary), chunk_size)
        ]

        with ProcessPoolExecutor() as executor:
            results = executor.map(_build_signature_index_chunk, chunks)

        # Merge results
        for sig_buckets, len_buckets in results:
            for sig, indices in sig_buckets.items():
                if sig not in self.signature_buckets:
                    self.signature_buckets[sig] = []
                self.signature_buckets[sig].extend(indices)
            for length, indices in len_buckets.items():
                if length not in self.length_buckets:
                    self.length_buckets[length] = []
                self.length_buckets[length].extend(indices)
```

### Verification

```bash
# Monitor CPU usage during corpus build
top -pid $(pgrep -f "python.*corpus")

# Should see 80-100% CPU across all cores
```

---

## 8. API Search Caching ⚠️ MEDIUM

### Problem
**Location**: `backend/src/floridify/api/routers/search.py:149-184`

**Issue**: `_cached_search()` function name is misleading - no actual caching

### Fix

```python
# File: backend/src/floridify/api/routers/search.py

from floridify.caching.core import get_cache_manager, CacheNamespace

async def _cached_search(query: str, params: SearchParams) -> SearchResponse:
    """Cached search implementation with actual caching."""

    # Generate cache key
    cache_key = f"search:{query}:{params.mode}:{params.languages}"

    # Check cache
    cache = get_cache_manager()
    cached_result = await cache.get(CacheNamespace.SEARCH, cache_key)

    if cached_result:
        logger.debug(f"Cache hit for query: {query}")
        return SearchResponse.model_validate(cached_result)

    # Cache miss - perform search
    language_search = await get_language_search(languages=params.languages)
    results = await language_search.search_with_mode(
        query=query,
        mode=params.mode,
        max_results=params.max_results,
        min_score=params.min_score,
    )

    response = SearchResponse(
        query=query,
        results=results,
        mode=params.mode,
        total=len(results),
    )

    # Cache result with 1 hour TTL
    await cache.set(
        CacheNamespace.SEARCH,
        cache_key,
        response.model_dump(),
        ttl=3600
    )

    return response
```

### Verification

```bash
# Test cache hit
curl "http://localhost:8000/api/v1/search/words?q=test" -w "\nTime: %{time_total}s\n"
# Should be slower (cache miss)

curl "http://localhost:8000/api/v1/search/words?q=test" -w "\nTime: %{time_total}s\n"
# Should be faster (cache hit)
```

---

# P3: Low Priority (Nice to Have)

## 9. Trie/Bloom Filter Persistence ⚠️ LOW

### Problem
**Issue**: Bloom filter and marisa-trie rebuilt on every load (1-2 seconds)

**Impact**: Minor - initialization time slightly slower

### Fix

**File**: `backend/src/floridify/search/models.py:66-93`

Add persistence fields:

```python
class TrieIndex(BaseModel):
    # ... existing fields ...

    # ✅ NEW: Serialized structures
    trie_binary: bytes | None = None          # Pre-built marisa-trie
    bloom_bits: bytes | None = None           # Serialized bloom filter
    bloom_hash_count: int | None = None
    bloom_bit_count: int | None = None
```

**File**: `backend/src/floridify/search/trie.py:89-104`

```python
# Save trie binary
def _save_trie_binary(self):
    import io
    buffer = io.BytesIO()
    self._trie.save(buffer)
    self.index.trie_binary = buffer.getvalue()

# Load trie from binary
if self.index.trie_binary:
    self._trie = marisa_trie.Trie()
    self._trie.load(io.BytesIO(self.index.trie_binary))
else:
    self._trie = marisa_trie.Trie(self.index.trie_data)
    self._save_trie_binary()
```

**Expected Improvement**: 50-80% faster initialization (1-2s → 200-400ms)

---

# Testing & Verification Plan

## Pre-Implementation Checklist

- [ ] Backup current database
- [ ] Create test branch: `git checkout -b fix/semantic-corpus-performance`
- [ ] Run baseline benchmarks
- [ ] Document current state

## Implementation Order

1. **Day 1** (P0 Critical):
   - [ ] Fix semantic binary data loading
   - [ ] Rebuild semantic indices
   - [ ] Fix API enum serialization
   - [ ] Verify API starts successfully
   - [ ] Run benchmarks - semantic should work

2. **Day 2** (P1 High Priority):
   - [ ] Fix corpus aggregation
   - [ ] Verify exact search optimizations
   - [ ] Debug cache performance
   - [ ] Run benchmarks - should meet most targets

3. **Day 3** (P2 Medium Priority):
   - [ ] Optimize multi-core utilization
   - [ ] Add API search caching
   - [ ] Run final benchmarks

4. **Day 4** (P3 Low Priority - Optional):
   - [ ] Add trie/bloom persistence
   - [ ] Performance testing
   - [ ] Documentation updates

## Benchmark Target Validation

After all P0-P1 fixes:

```bash
cd backend
python scripts/benchmark_performance.py
```

**Expected Results**:
- ✅ Exact: P95 < 1.5ms (target: 1.0ms)
- ✅ Fuzzy: P95 < 5.0ms
- ✅ Semantic: P95 < 10.0ms (and working!)
- ✅ Cache: P95 < 0.5ms
- ✅ Combined: P95 < 10.0ms
- ✅ Concurrent: P95 < 15.0ms (close to 10.0ms target)

## Linting & Code Quality

```bash
# Run after each fix
cd backend
ruff check src/ --fix
ruff format src/
mypy src/
```

## Success Criteria

### Minimum Acceptable (P0-P1):
- [ ] API server starts without errors
- [ ] Semantic search works (no errors)
- [ ] Semantic indices load from cache (2-5s, not 5-15min)
- [ ] Corpus builds in 1-3 minutes (down from 5-10min)
- [ ] Benchmark P95 targets met for critical searches

### Optimal (P0-P2):
- [ ] All benchmark targets met
- [ ] Multi-core utilization >75%
- [ ] Cache hit rate >90%
- [ ] No failing tests

---

# Monitoring & Rollback Plan

## Monitoring Points

```bash
# 1. Check semantic index status
curl http://localhost:8000/api/v1/search/semantic/status

# 2. Check cache statistics
curl http://localhost:8000/health | jq '.cache'

# 3. Monitor corpus build progress
tail -f backend/logs/corpus_build.log

# 4. Watch benchmark results
watch -n 30 'python scripts/benchmark_performance.py --quick'
```

## Rollback Plan

```bash
# If critical issues occur:
git stash
git checkout main
./scripts/dev --restart-all

# Restore database from backup
mongorestore --db floridify backup/floridify_YYYYMMDD
```

---

# Progress Tracking

**Last Updated**: 2025-10-06
**Completed**: 0/9 items
**In Progress**: Synthesis & planning
**Next Action**: Fix P0 Critical items

## Update Log

| Date | Item | Status | Notes |
|------|------|--------|-------|
| 2025-10-06 | Initial plan created | ✅ DONE | Comprehensive analysis by 8 agents |
| ... | ... | ... | ... |

---

# References

## Agent Research Reports

1. **Semantic Index System** - Binary data loading, caching, versioning
2. **Corpus Building Performance** - Multi-core, aggregation, bottlenecks
3. **Complete Search Pipeline** - All indices, persistence, integration
4. **API Integration Issues** - Enum serialization, caching, endpoints
5. **Trie Index Implementation** - Persistence, versioning, performance
6. **Cache System Architecture** - Two-tier caching, compression, serialization
7. **MongoDB Storage Patterns** - Indices, cascade deletion, query optimization
8. **Benchmark Requirements** - Performance quotas, targets, current status

## Key Files

- `/backend/src/floridify/search/semantic/core.py` - Semantic search engine
- `/backend/src/floridify/search/semantic/models.py` - SemanticIndex model
- `/backend/src/floridify/corpus/language/core.py` - Language corpus
- `/backend/src/floridify/corpus/manager.py` - Corpus manager
- `/backend/src/floridify/api/routers/search.py` - Search API endpoints
- `/backend/scripts/benchmark_performance.py` - Performance benchmarks

---

**END OF FIX PLAN**
