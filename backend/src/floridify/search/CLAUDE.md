# Search Module - Multi-Method Search Engine

High-performance search combining exact (marisa-trie), fuzzy (RapidFuzz), semantic (FAISS) with intelligent cascade.

## Structure

```
search/
├── core.py              # Search class - multi-method orchestrator (1,382 LOC)
├── models.py            # SearchResult, SearchMode, SearchIndex (446 LOC)
├── exact/
│   └── core.py         # TrieSearch - marisa-trie + Bloom filter (442 LOC)
├── fuzzy/
│   ├── core.py         # FuzzySearch - RapidFuzz dual-scorer (628 LOC)
│   └── signature.py    # Word signatures for bucketing (172 LOC)
├── semantic/
│   ├── core.py         # SemanticSearch - FAISS indices (1,382 LOC)
│   ├── models.py       # SemanticIndex, embedding config (446 LOC)
│   ├── constants.py    # Model catalog, index strategies (246 LOC)
│   └── config.py       # FAISS index selection logic (168 LOC)
└── language.py          # LanguageSearch - cross-corpus orchestrator (420 LOC)
```

**Total**: 4,582 LOC across 13 files

## Search Methods

**Exact Search** (`exact/core.py:442` - marisa-trie + Bloom Filter)

```python
class TrieSearch:
    trie: marisa_trie.Trie              # Sorted vocabulary
    bloom: BloomFilter                   # False positive filter
    vocabulary_to_index: dict[str, int]  # O(1) lookup

    def search(query: str) -> list[SearchResult]:
        # 1. Bloom filter check (30-50% speedup on negative queries)
        if query not in self.bloom:
            return []

        # 2. Trie exact match - O(m) where m = query length
        if query in self.trie:
            return [SearchResult(word=query, score=1.0, method="exact")]

        return []
```

**Performance**: <1ms, O(m) complexity
**Bloom filter**: Adaptive error rates (0.001-0.01) based on corpus size

**Fuzzy Search** (`fuzzy/core.py:628` - RapidFuzz Dual-Scorer)

```python
class FuzzySearch:
    signature_buckets: dict[str, list[int]]  # Signature → word indices
    length_buckets: dict[int, list[int]]     # Length → word indices

    def search(query: str, max_results: int, min_score: float) -> list[SearchResult]:
        # 1. Candidate selection via signatures + length
        candidates = self._get_candidates(query)

        # 2. Dual-scorer matching
        for word in candidates:
            wratio_score = fuzz.WRatio(query, word) / 100.0      # General similarity
            token_set_score = fuzz.token_set_ratio(query, word) / 100.0  # Phrase-aware

            # 3. Length-aware correction
            final_score = (wratio_score + token_set_score) / 2
            final_score *= length_correction_factor(len(query), len(word))

        # 4. Sort by score, limit to max_results
        return sorted(results, key=lambda r: r.score, reverse=True)[:max_results]
```

**Performance**: 10-50ms
**Signatures**: Consonant-based (`perspicacious` → `prsp`) for bucketing
**Dual scoring**: WRatio (general) + token_set_ratio (multi-word phrases)

**Semantic Search** (`semantic/core.py:1,382` - FAISS + Embeddings)

```python
class SemanticSearch:
    index: faiss.Index                   # FAISS index (IVF, HNSW, etc.)
    vocabulary: list[str]                # Indexed words
    model: SentenceTransformer          # Embedding model

    async def search(query: str, max_results: int, min_score: float) -> list[SearchResult]:
        # 1. Embed query
        query_embedding = self.model.encode(query)  # 1024D or 4096D vector

        # 2. FAISS search
        distances, indices = self.index.search(query_embedding, k=max_results)

        # 3. Convert L2 distance → cosine similarity
        scores = [1 / (1 + distance) for distance in distances]

        # 4. Filter by min_score
        return [
            SearchResult(word=self.vocabulary[idx], score=score, method="semantic")
            for idx, score in zip(indices, scores)
            if score >= min_score
        ]
```

**Performance**: 50-200ms (100-200ms cold, <1ms cached)
**Embedding models**: Qwen3-0.6B (1024D), BGE-M3 (1024D), GTE-Qwen2 (4096D)
**FAISS index types**: 7 strategies selected by corpus size

## Search Cascade

**Smart Mode** - Intelligent multi-method cascade:

```python
async def _smart_search_cascade(query, max_results, min_score, semantic):
    # 1. Exact (< 1ms)
    exact = self.search_exact(query)
    if exact:
        return exact  # Perfect match → return immediately

    # 2. Fuzzy (10-50ms)
    fuzzy = self.search_fuzzy(query, max_results, min_score)

    # 3. Semantic (50-200ms) with quality-based gating
    if semantic and self._semantic_ready:
        high_quality = [r for r in fuzzy if r.score >= 0.7]
        if len(high_quality) >= max_results // 3:
            logger.debug("Skipping semantic: high-quality fuzzy matches")
        else:
            semantic_results = await self.search_semantic(query, max_results, min_score)
            # Merge and deduplicate
            all_results = fuzzy + semantic_results
            return deduplicate_and_sort(all_results, max_results)

    return fuzzy[:max_results]
```

**Early termination**: Exact match → skip fuzzy/semantic
**Quality gating**: Skip semantic if fuzzy found ≥33% high-quality (≥0.7) results
**Deduplication**: Method priority: Exact > Semantic > Fuzzy

## FAISS Index Selection

**7 index types** by corpus size (`semantic/config.py:168`):

| Corpus Size | Index Type | Config | Search Time | Memory |
|-------------|-----------|--------|-------------|--------|
| <10k | Flat L2 | Brute force | 5-10ms | Low |
| 10-50k | IVF-Flat | nlist=100 | 20-50ms | Medium |
| 50-100k | INT8 | 8-bit quant | 30-70ms | Low (30% reduction) |
| 100-200k | HNSW | M=16, ef=40 | 10-30ms | High |
| 200-500k | IVF-PQ | m=8, 8-bit | 40-100ms | Low (75% reduction) |
| 500k-1M | OPQ+PQ | 16 subq | 50-150ms | Very Low |
| >1M | OPQ+IVF-PQ | Hierarchical | 60-200ms | Very Low |

**nlist formula**: `int(4 * sqrt(n))`  where n = vocabulary size
**PQ subquantizers**: m=8 (50-100k), m=16 (100-200k), m=32 (>500k)

## Embedding Models

**3 model options** (`semantic/constants.py:246`):

| Model | Dimensions | MTEB Score | Speed | Use Case |
|-------|-----------|-----------|-------|----------|
| Qwen3-0.6B | 1024 | 64.33 | Fast | Default |
| BGE-M3 | 1024 | 66.29 | Fast | Multilingual (100+ languages) |
| GTE-Qwen2-7B | 4096 | 70.58 | Slow | SOTA quality |

**Batch embedding**: 32-128 batch size for corpus indexing
**Caching**: Vocabulary hash-based model cache isolation

## Performance Characteristics

| Method | Time | Data Structure | Complexity |
|--------|------|----------------|------------|
| Exact | <1ms | marisa-trie | O(m) where m = query length |
| Bloom filter | <0.1ms | Bitarray | O(k) where k = hash functions |
| Fuzzy | 10-50ms | Signature buckets | O(c×n) where c = candidates, n = corpus |
| Semantic (cold) | 100-200ms | FAISS + embeddings | O(log n) for HNSW |
| Semantic (cached) | <1ms | Cache hit | O(1) |
| Smart cascade | 10-150ms | Adaptive | Early termination on exact match |

**Candidate selection** (fuzzy):
- Signature matching: ~10% of corpus
- Length filtering: ±2 characters
- Combined: ~3-5% of corpus (1000-5000 words for 100k corpus)

## LanguageSearch

**Cross-corpus orchestration** (`language.py:420`):

```python
class LanguageSearch:
    engines: dict[Language, Search]  # Per-language search engines

    async def search(
        query: str,
        languages: list[Language],
        max_results: int,
        mode: SearchMode,
    ) -> list[SearchResult]:
        # 1. Parallel search across languages
        results_by_language = await asyncio.gather(*[
            self.engines[lang].search_with_mode(query, mode)
            for lang in languages
        ])

        # 2. Merge and sort by score
        all_results = [r for lang_results in results_by_language for r in lang_results]
        all_results.sort(key=lambda r: r.score, reverse=True)

        return all_results[:max_results]
```

## Search Models

**SearchResult** (`models.py:446`):
```python
class SearchResult(BaseModel):
    word: str
    score: float           # 0.0-1.0
    method: str           # "exact", "fuzzy", "semantic"
    language: Language
    metadata: dict | None  # corpus_id, index, etc.
```

**SearchMode** (`models.py:446`):
```python
class SearchMode(Enum):
    SMART = "smart"       # Cascade with early termination
    EXACT = "exact"       # marisa-trie only
    FUZZY = "fuzzy"       # RapidFuzz only
    SEMANTIC = "semantic" # FAISS only
```

**SearchIndex** (`models.py:446` - MongoDB Document):
```python
class SearchIndex(Document):
    corpus_id: PydanticObjectId
    trie_index_id: PydanticObjectId | None
    semantic_index_id: PydanticObjectId | None
    created_at: datetime
    vocabulary_size: int
```

## Memory Usage

**100k word corpus**:
- Trie index: ~15MB (compressed)
- Bloom filter: ~1MB (0.01 error rate)
- Fuzzy indices: ~10MB (signatures + length buckets)
- Semantic embeddings: ~400MB (1024D float32)
- FAISS index: ~50MB (HNSW) to ~400MB (Flat)
- **Total**: ~440MB (with semantic), ~26MB (without semantic)

**Compression** (via caching):
- Trie: 50-60% reduction with gzip
- FAISS: 30-40% reduction with ZSTD
- **Compressed total**: ~150-200MB

## Design Patterns

- **Strategy** - Pluggable search methods (exact, fuzzy, semantic)
- **Cascade** - Sequential fallback with early termination
- **Singleton** - LanguageSearch per language
- **Factory** - SemanticIndex.get_or_create() for model/index creation
- **Adapter** - Wraps marisa-trie, RapidFuzz, FAISS with unified interface
- **Composite** - SearchIndex aggregates Trie + Semantic indices
