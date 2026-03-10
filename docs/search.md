# Search

4-method cascade with early termination and quality gating. Exact match via marisa-trie, prefix via trie traversal, fuzzy via RapidFuzz dual-scorer, semantic via FAISS HNSW with Qwen3-0.6B embeddings.

## Table of Contents

- [Cascade](#cascade)
- [Search Methods](#search-methods)
- [Quality Gate](#quality-gate)
- [FAISS Index Selection](#faiss-index-selection)
- [Hot-Reload](#hot-reload)
- [Dedup & Ranking](#dedup--ranking)
- [Key Files](#key-files)

## Cascade

In SMART mode ([`Search`](../backend/src/floridify/search/core.py)), methods run in order with early termination:

```
Query → Exact → if no match → Prefix → if no match → Fuzzy
  → if <33% high-quality → Semantic → Deduplicate → Top N
```

Exact match terminates immediately. Other modes (`EXACT`, `FUZZY`, `SEMANTIC`) bypass the cascade and run a single method.

## Search Methods

| Method | Implementation | Notes |
|--------|---------------|-------|
| Exact | [`TrieSearch`](../backend/src/floridify/search/trie.py) + [`BloomFilter`](../backend/src/floridify/search/bloom.py) | marisa-trie O(m) lookup, Bloom filter for fast negative |
| Prefix | [`TrieSearch`](../backend/src/floridify/search/trie.py) | Trie prefix traversal |
| Fuzzy | [`FuzzySearch`](../backend/src/floridify/search/fuzzy.py) | RapidFuzz dual-scorer: `WRatio` + `token_set_ratio`, length-aware scoring |
| Semantic | [`SemanticSearch`](../backend/src/floridify/search/semantic/core.py) | FAISS HNSW, Qwen3-0.6B embeddings (1024D) |

## Quality Gate

Before falling through to semantic search, the cascade checks whether fuzzy results are sufficient. If ≥33% of fuzzy results score ≥0.7, semantic search is skipped. This prevents expensive embedding computation when fuzzy matching already found good candidates.

## FAISS Index Selection

5 tiers selected by corpus size ([`semantic/constants.py`](../backend/src/floridify/search/semantic/constants.py)):

| Corpus Size | Index | Notes |
|-------------|-------|-------|
| <10k | `IndexFlatL2` | Brute-force exact search |
| 10k–50k | `IVF-Flat` | `nlist=max(64, sqrt(n))`, `nprobe=nlist/4` |
| 50k–100k | `ScalarQuantizer` INT8 | 4x compression |
| 100k–200k | HNSW | `M=32`, `efConstruction=200`, `efSearch=64` (configurable via env) |
| >200k | `OPQ+IVF-PQ` | OPQ rotation + product quantization |

HNSW config via environment variables: `FLORIDIFY_USE_HNSW`, `FLORIDIFY_HNSW_M`, `FLORIDIFY_HNSW_EF_CONSTRUCTION`, `FLORIDIFY_HNSW_EF_SEARCH`.

**Embedding model**: Default `Qwen/Qwen3-Embedding-0.6B` (1024D, supports Matryoshka dimensions 32–1024). Model catalog in [`semantic/constants.py`](../backend/src/floridify/search/semantic/constants.py) includes Qwen3-4B, Qwen3-8B, BAAI/bge-m3, all-MiniLM-L6-v2, gte-Qwen2-1.5B.

## Hot-Reload

[`SearchEngineManager`](../backend/src/floridify/core/search_pipeline.py) polls `vocabulary_hash` every 30 seconds. When the hash changes (new words added to corpus), it rebuilds the search index in the background and performs an atomic swap of the `Search` instance. No downtime during reindex.

## Dedup & Ranking

When multiple methods return the same word, [`METHOD_PRIORITY`](../backend/src/floridify/search/core.py) determines which result to keep:

```python
METHOD_PRIORITY = {EXACT: 4, PREFIX: 3, SEMANTIC: 2, FUZZY: 1}
METHOD_SORT_BONUS = {EXACT: 0.03, PREFIX: 0.02, SEMANTIC: 0.01, FUZZY: 0.0}
```

Sort bonuses are tiebreakers only—a fuzzy match at 0.95 still beats a semantic match at 0.80.

## Key Files

| File | Role |
|------|------|
| [`search/core.py`](../backend/src/floridify/search/core.py) | `Search`—orchestrator, cascade logic, dedup |
| [`search/trie.py`](../backend/src/floridify/search/trie.py) | marisa-trie exact + prefix search |
| [`search/fuzzy.py`](../backend/src/floridify/search/fuzzy.py) | RapidFuzz dual-scorer |
| [`search/bloom.py`](../backend/src/floridify/search/bloom.py) | Bloom filter for fast negative membership test |
| [`search/result.py`](../backend/src/floridify/search/result.py) | `SearchResult` model |
| [`search/search_index.py`](../backend/src/floridify/search/search_index.py) | `SearchIndex`—vocabulary + trie + semantic index |
| [`search/trie_index.py`](../backend/src/floridify/search/trie_index.py) | `TrieIndex` document model |
| [`search/semantic/core.py`](../backend/src/floridify/search/semantic/core.py) | `SemanticSearch`—FAISS index building, embedding |
| [`search/semantic/constants.py`](../backend/src/floridify/search/semantic/constants.py) | Model catalog, FAISS thresholds, HNSW config |
| [`search/language.py`](../backend/src/floridify/search/language.py) | Multi-corpus orchestration across languages |
| [`core/search_pipeline.py`](../backend/src/floridify/core/search_pipeline.py) | `SearchEngineManager`—hot-reload, atomic swap |
