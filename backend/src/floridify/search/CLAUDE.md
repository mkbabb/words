# search/

Multi-method search: exact (marisa-trie), prefix, substring (suffix array), fuzzy (BK-tree + phonetic + trigram), semantic (FAISS). Cascade with early termination.

## Structure

```
search/
├── engine.py               # Search orchestrator, cascade logic
├── index.py                 # SearchIndex versioned model (links trie+fuzzy+semantic)
├── config.py                # All tunable constants (thresholds, budgets, boosts)
├── constants.py             # SearchMethod, SearchMode, FuzzySearchMethod enums
├── result.py                # SearchResult, MatchDetail
├── language.py              # LanguageSearch (multi-corpus delegation)
│
├── trie/                    # Exact + prefix search
│   ├── search.py            # TrieSearch (marisa-trie C++ backend)
│   ├── index.py             # TrieIndex (versioned, includes Bloom filter bytes)
│   └── bloom.py             # BloomFilter (xxHash, probabilistic membership)
│
├── fuzzy/                   # Multi-strategy fuzzy matching
│   ├── search.py            # FuzzySearch (candidate aggregation pipeline)
│   ├── index.py             # FuzzyIndex (versioned, bundles BK+phonetic+suffix)
│   ├── candidates.py        # Trigram inverted index + length buckets
│   ├── bk_tree.py           # BKTree (Damerau-Levenshtein, adaptive k)
│   ├── suffix_array.py      # SuffixArray (pydivsufsort, O(m log n) substring)
│   └── scoring.py           # Length correction, frequency heuristics
│
├── phonetic/                # Multilingual phonetic matching
│   ├── index.py             # PhoneticIndex (composite + per-word codes)
│   ├── encoder.py           # PhoneticEncoder (ICU normalization + jellyfish Metaphone)
│   └── constants.py         # ICU transliteration rules (CLDR-sourced)
│
└── semantic/                # FAISS vector search
    ├── search.py            # SemanticSearch (from_corpus, query caching)
    ├── index.py             # SemanticIndex (versioned, binary data in GridFS)
    ├── constants.py         # Model catalog (Qwen3-0.6B), FAISS thresholds, HNSW config
    ├── encoder.py           # SemanticEncoder (text → embeddings)
    ├── embedding.py         # Model loading/caching, worker functions
    ├── builder.py           # SemanticEmbeddingBuilder (vocab → embeddings)
    ├── index_builder.py     # FAISS index construction (5-tier by corpus size)
    ├── persistence.py       # GridFS save/load for binary data
    └── query_cache.py       # LRU query embedding cache
```

## Enums

**SearchMethod**: `EXACT`, `PREFIX`, `SUBSTRING`, `FUZZY`, `SEMANTIC`, `AUTO`
**SearchMode**: `SMART`, `EXACT`, `FUZZY`, `SEMANTIC`
**FuzzySearchMethod**: `RAPIDFUZZ`, `JARO_WINKLER`, `SOUNDEX`, `LEVENSHTEIN`, `METAPHONE`, `AUTO`

## Cascade (SMART mode)

Exact → Prefix → Substring (if query >= 3 chars) → Fuzzy → if <33% high-quality (>=0.7) → Semantic → Deduplicate → Top N.

Early termination: exact+prefix fill max_results. Quality gating: skip semantic if fuzzy suffices.

## Fuzzy Pipeline

Multi-strategy candidate aggregation:
1. **BK-tree**: Damerau-Levenshtein with adaptive k (2-5 based on query length), cascading expansion, time-budgeted
2. **Phonetic**: ICU cross-linguistic normalization → jellyfish Metaphone, composite + per-word inverted index
3. **Trigram overlap**: Structured numpy arrays with 8-bit positional + next-char masks ("3.5-gram" precision)
4. **Per-word decomposition**: Multi-word queries search each word independently

Signal-based score boosting: phonetic match (1.08x), close edit distance (1.02x), multi-strategy (1.03x).

## FAISS Index Selection

5 tiers selected by corpus size (thresholds in `config.py`):

| Corpus Size | Index | Notes |
|-------------|-------|-------|
| <10k | IndexFlatL2 | Brute-force exact search |
| 10k–50k | IVF-Flat | nlist=max(64, sqrt(n)), nprobe=nlist/4 |
| 50k–100k | ScalarQuantizer INT8 | 4x compression |
| 100k–200k | HNSW or IVF-PQ | HNSW default (M, efConstruction, efSearch from env) |
| >200k | OPQ+IVF-PQ | OPQ rotation + product quantization |

## Configuration

All tunable constants in `config.py`: score thresholds, corpus size tiers, candidate budgets, BK-tree time limits, signal boost factors, trigram parameters, Bloom filter error rates.

HNSW config via env vars: `FLORIDIFY_USE_HNSW`, `FLORIDIFY_HNSW_M` (default 32), `FLORIDIFY_HNSW_EF_CONSTRUCTION` (200), `FLORIDIFY_HNSW_EF_SEARCH` (64).
