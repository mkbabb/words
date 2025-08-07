# Implementation Plan: Search Pipeline Performance Optimizations

## Quick Reference: Top 10 Changes for Maximum Impact

### 1. normalize.py - Single-Pass Normalization (3-5x speedup)
```python
# CURRENT (Lines 48-106): 7 string copies, 4 Unicode passes
text = ftfy.fix_text(text)                    # Copy 1
text = unicodedata.normalize("NFC", text)     # Copy 2
text = text.translate(UNICODE_TO_ASCII)       # Copy 3
text = remove_diacritics(text)                # Copy 4
text = contractions.fix(text)                 # Copy 5
text = PUNCTUATION_PATTERN.sub(" ", text)     # Copy 6
text = text.lower()                           # Copy 7

# OPTIMIZED: Single pass with caching
@functools.lru_cache(maxsize=50000)
def normalize_comprehensive_optimized(text: str) -> str:
    if not text:
        return ""
    # Pre-process with ftfy once
    text = ftfy.fix_text(text)
    # Single NFD pass for all Unicode operations
    chars = []
    for char in unicodedata.normalize("NFD", text):
        if unicodedata.category(char) != "Mn":  # Skip combining marks
            ascii_char = UNICODE_TO_ASCII.get(ord(char), char)
            chars.append(ascii_char.lower())
    # Single NFC at the end
    normalized = unicodedata.normalize("NFC", ''.join(chars))
    # Batch regex operations
    return COMBINED_PATTERN.sub(' ', contractions.fix(normalized)).strip()
```

### 2. search/core.py - Remove Async Overhead (2-3x speedup)
```python
# CURRENT (Lines 237-238): Unnecessary async for CPU-bound ops
exact_task = loop.run_in_executor(None, self._search_exact_sync, query)
fuzzy_task = loop.run_in_executor(None, self._search_fuzzy_sync, query, max_results * 2)

# OPTIMIZED: Direct calls with early termination
def _search_cascade_optimized(self, query: str, max_results: int) -> list[SearchResult]:
    # Direct synchronous exact search (typically <1ms)
    exact_results = self._search_exact_sync(query)
    
    # Early return for perfect matches
    if len(exact_results) >= max_results and all(r.score >= 0.99 for r in exact_results[:max_results]):
        return exact_results[:max_results]
    
    # Only parallelize if needed
    with ThreadPoolExecutor(max_workers=2) as executor:
        fuzzy_future = executor.submit(self._search_fuzzy_sync, query, max_results * 2)
        semantic_future = None
        if self.should_semantic_search(query):
            semantic_future = executor.submit(self._search_semantic_sync, query, max_results)
        
        all_results = list(exact_results)
        all_results.extend(fuzzy_future.result(timeout=0.5))
        if semantic_future:
            all_results.extend(semantic_future.result(timeout=2.0))
    
    return self._deduplicate_and_sort(all_results)[:max_results]
```

### 3. semantic/core.py - Fix FAISS Configuration (5x speedup)
```python
# CURRENT (Lines 258-283): Suboptimal for 300k
if vocab_size > 100000:
    nlist = min(4096, vocab_size // 100)  # Only 3000 clusters for 300k!

# OPTIMIZED: Proper configuration for scale
def _build_faiss_index_optimized(self, embeddings: np.ndarray, vocab_size: int):
    dimension = embeddings.shape[1]
    
    if vocab_size >= 300000:
        # IVF with Product Quantization for 300k+ entries
        nlist = 8192  # Optimal cluster count
        m = 32  # PQ subvectors
        nbits = 8  # Bits per subvector
        
        quantizer = faiss.IndexFlatL2(dimension)
        index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, nbits)
        index.train(embeddings)
        index.add(embeddings)
        index.nprobe = 256  # Search 3% of clusters
        
        # Enable GPU if available
        if faiss.get_num_gpus() > 0:
            index = faiss.index_cpu_to_gpu(faiss.StandardGpuResources(), 0, index)
        
        return index
```

### 4. fuzzy.py - Bounded Edit Distance (3x speedup)
```python
# CURRENT (Lines 274-293): Unbounded Levenshtein
distance = Levenshtein.distance(query_lower, candidate_lower)

# OPTIMIZED: Early termination with bounds
def bounded_levenshtein(s1: str, s2: str, max_distance: int = 3) -> int:
    # Early exit for length difference
    if abs(len(s1) - len(s2)) > max_distance:
        return max_distance + 1
    
    # Use polyleven for bounded calculation
    return polyleven.levenshtein(s1, s2, max_distance)

# In search function:
distance = bounded_levenshtein(query_lower, candidate_lower, max_distance=3)
if distance > 3:
    continue  # Skip this candidate
```

### 5. text/normalize.py - Pre-compile Regex (1.5x speedup)
```python
# CURRENT (Line 133): Compiles on every call
text = re.sub(r"[^\w\s\'-]", " ", text)

# OPTIMIZED: Module-level compilation
# At top of file:
FAST_PUNCTUATION_PATTERN = re.compile(r"[^\w\s\'-]")
WHITESPACE_NORMALIZE_PATTERN = re.compile(r"\s+")
COMBINED_CLEANUP_PATTERN = re.compile(r"[^\w\s\'-]+|\s+")

# In function:
text = FAST_PUNCTUATION_PATTERN.sub(" ", text)
text = WHITESPACE_NORMALIZE_PATTERN.sub(" ", text).strip()
```

### 6. corpus/core.py - Dict-based Lookups (2x speedup)
```python
# CURRENT (Lines 217-233): O(n) index lookup
normalized_idx = corpus.vocabulary.index(normalized_word)  # O(n) for 300k!

# OPTIMIZED: O(1) dict lookup
class Corpus:
    def __init__(self):
        self.word_to_index: dict[str, int] = {}
        self.normalized_to_original: dict[int, int] = {}
    
    @classmethod
    def create_optimized(cls, vocabulary: list[str]) -> Corpus:
        corpus = cls()
        
        # Build O(1) lookup structures
        for i, word in enumerate(vocabulary):
            corpus.vocabulary.append(word)
            corpus.word_to_index[word] = i
            
            normalized = normalize_comprehensive(word)
            if normalized != word:
                norm_idx = len(corpus.vocabulary)
                corpus.vocabulary.append(normalized)
                corpus.word_to_index[normalized] = norm_idx
                corpus.normalized_to_original[norm_idx] = i
        
        return corpus
```

### 7. semantic/core.py - Remove Duplicate Embeddings (40% memory)
```python
# CURRENT (Lines 222-232): Creates 2x embeddings
for lemma in vocabulary:
    embedding_vocabulary.append(lemma)
    diacritic_free = normalize_comprehensive(lemma)
    if diacritic_free != lemma:
        embedding_vocabulary.append(diacritic_free)  # Duplicate!

# OPTIMIZED: Single embedding per unique word
def _build_embedding_vocabulary_optimized(self) -> tuple[list[str], dict[int, int]]:
    unique_words = set()
    variant_mapping = {}
    
    for i, lemma in enumerate(self.corpus.lemmatized_vocabulary):
        unique_words.add(lemma)
        # Map variants at query time, not embedding time
        normalized = normalize_comprehensive(lemma)
        if normalized != lemma:
            variant_mapping[normalized] = i
    
    return list(unique_words), variant_mapping
```

### 8. search/core.py - Generator Expressions (30% memory)
```python
# CURRENT: Creates intermediate lists
exact_filtered = [r for r in exact_results if r.score >= min_score_threshold]
fuzzy_filtered = [r for r in fuzzy_results if r.score >= min_score_threshold]
all_results = exact_filtered + fuzzy_filtered + semantic_filtered

# OPTIMIZED: Lazy evaluation with generators
import itertools

def filter_results(results, min_score):
    return (r for r in results if r.score >= min_score)

all_results_gen = itertools.chain(
    filter_results(exact_results, min_score_threshold),
    filter_results(fuzzy_results, min_score_threshold),
    filter_results(semantic_results, min_score_threshold) if semantic_results else []
)

# Only materialize when needed
final_results = list(itertools.islice(all_results_gen, max_results))
```

### 9. trie.py - Memory-Mapped Storage (50% memory)
```python
# CURRENT (Lines 159-167): In-memory trie
self._trie = marisa_trie.Trie(words)

# OPTIMIZED: Memory-mapped for large corpus
import mmap

class MemoryMappedTrie:
    def save(self, path: str):
        self._trie.save(path)
    
    def load_mmap(self, path: str):
        with open(path, 'rb') as f:
            self._mmap = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            self._trie = marisa_trie.Trie().mmap(self._mmap)
```

### 10. fuzzy.py - BK-Tree Implementation (5-10x speedup)
```python
# NEW: Add BK-tree for metric space indexing
class BKTree:
    def __init__(self, words: list[str]):
        self.tree = {}
        for word in words:
            self._add_word(word)
    
    def _add_word(self, word: str):
        node = self.tree
        while True:
            if 'word' not in node:
                node['word'] = word
                break
            
            distance = polyleven.levenshtein(word, node['word'], 3)
            if distance not in node:
                node[distance] = {}
            node = node[distance]
    
    def search(self, query: str, max_distance: int = 2) -> list[tuple[str, int]]:
        results = []
        self._search_node(self.tree, query, max_distance, results)
        return sorted(results, key=lambda x: x[1])[:20]
    
    def _search_node(self, node, query, max_distance, results):
        if 'word' not in node:
            return
        
        distance = polyleven.levenshtein(query, node['word'], max_distance)
        if distance <= max_distance:
            results.append((node['word'], distance))
        
        # Triangle inequality pruning
        for d in range(max(0, distance - max_distance), 
                      min(distance + max_distance + 1, len(node))):
            if d in node and d != 'word':
                self._search_node(node[d], query, max_distance, results)
```

---

## Testing Strategy

### Unit Tests to Add
```python
# test_performance.py
import time
import numpy as np

def test_normalization_performance():
    texts = ["café", "naïve", "résumé"] * 10000
    
    start = time.perf_counter()
    for text in texts:
        normalize_comprehensive(text)
    old_time = time.perf_counter() - start
    
    start = time.perf_counter()
    for text in texts:
        normalize_comprehensive_optimized(text)
    new_time = time.perf_counter() - start
    
    assert new_time < old_time * 0.5  # At least 2x faster

def test_search_cascade_performance():
    # Test with 300k corpus
    corpus = load_test_corpus(300000)
    search = SearchEngine(corpus)
    
    queries = ["test", "café", "naïve", "search", "performance"] * 20
    
    start = time.perf_counter()
    for query in queries:
        search.search(query)
    
    elapsed = time.perf_counter() - start
    qps = len(queries) / elapsed
    
    assert qps > 500  # Should handle 500+ QPS
```

### Benchmark Script
```python
# benchmark.py
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor

async def benchmark_search_pipeline():
    # Load 300k corpus
    corpus = await load_corpus("english-300k")
    search = SearchPipeline(corpus)
    
    # Test queries
    queries = load_test_queries(1000)
    
    # Measure latencies
    latencies = []
    for query in queries:
        start = time.perf_counter_ns()
        results = await search.search(query)
        latencies.append((time.perf_counter_ns() - start) / 1_000_000)  # ms
    
    print(f"P50: {statistics.quantiles(latencies, n=2)[0]:.2f}ms")
    print(f"P95: {statistics.quantiles(latencies, n=20)[18]:.2f}ms")
    print(f"P99: {statistics.quantiles(latencies, n=100)[98]:.2f}ms")
    
    # Memory usage
    import tracemalloc
    tracemalloc.start()
    
    # Create new instance
    search2 = SearchPipeline(corpus)
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"Memory usage: {current / 1024 / 1024:.1f}MB")
    print(f"Peak memory: {peak / 1024 / 1024:.1f}MB")
```

---

## Monitoring & Rollback

### Feature Flags
```python
# config.py
OPTIMIZATIONS = {
    "single_pass_normalization": True,
    "parallel_search_cascade": True,
    "bk_tree_fuzzy": False,  # Gradual rollout
    "faiss_ivf_pq": True,
    "memory_mapped_indices": False,
    "int8_quantization": False,
}

# Usage
if OPTIMIZATIONS["single_pass_normalization"]:
    result = normalize_comprehensive_optimized(text)
else:
    result = normalize_comprehensive(text)
```

### Performance Metrics
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

search_latency = Histogram('search_latency_ms', 'Search latency in milliseconds',
                          buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000])
cache_hits = Counter('cache_hits_total', 'Total cache hits')
memory_usage = Gauge('memory_usage_bytes', 'Current memory usage')

# Usage
with search_latency.time():
    results = search.search(query)
```

---

## Timeline

### Day 1-2: Critical String Operations
- [ ] Pre-compile all regex patterns
- [ ] Implement single-pass normalization
- [ ] Add normalization caching

### Day 3-4: Search Pipeline
- [ ] Remove async overhead
- [ ] Implement parallel cascade
- [ ] Add early termination logic

### Day 5-6: FAISS Optimization
- [ ] Fix index configuration
- [ ] Remove duplicate embeddings
- [ ] Add INT8 quantization

### Day 7-8: Fuzzy Search
- [ ] Implement bounded edit distance
- [ ] Add BK-tree structure
- [ ] Optimize candidate generation

### Day 9-10: Memory & Testing
- [ ] Convert to generators
- [ ] Add memory mapping
- [ ] Comprehensive benchmarking
- [ ] Load testing with 300k corpus

---

## Success Metrics

### Must Achieve
- [ ] 5x search speedup (3.4ms → 0.7ms)
- [ ] 50% memory reduction (2.3GB → 1.15GB)
- [ ] 500+ QPS throughput
- [ ] Zero accuracy regression

### Stretch Goals
- [ ] 10x search speedup (3.4ms → 0.34ms)
- [ ] 75% memory reduction (2.3GB → 575MB)
- [ ] 1000+ QPS throughput
- [ ] GPU acceleration working