# search/

Multi-method search: exact (marisa-trie), prefix, substring (suffix array), fuzzy + phonetic (ffuzzy Rust crate), semantic (FAISS). Cascade with early termination.

## Structure

```
search/
├── engine.py               # Search orchestrator, cascade logic
├── index.py                 # SearchIndex versioned model (links trie+fuzzy+semantic)
├── config.py                # Score thresholds, corpus tiers, Bloom filter params
├── constants.py             # SearchMethod, SearchMode, FuzzySearchMethod enums
├── result.py                # SearchResult, MatchDetail
├── language.py              # LanguageSearch (multi-corpus delegation)
│
├── trie/                    # Exact + prefix search
│   ├── search.py            # TrieSearch (marisa-trie C++ backend)
│   ├── index.py             # TrieIndex (versioned, includes Bloom filter bytes)
│   └── bloom.py             # BloomFilter (xxHash, probabilistic membership)
│
├── fuzzy/                   # Fuzzy + phonetic via ffuzzy Rust crate
│   ├── search.py            # FuzzySearch — thin wrapper around ffuzzy.Index
│   ├── index.py             # FuzzyIndex — versioned, stores ffuzzy blob + pickled suffix array via GridFS
│   ├── candidates.py        # Legacy trigram helpers used by the suffix array substring path
│   ├── suffix_array.py      # SuffixArray (pydivsufsort, O(m log n) substring)
│   └── scoring.py           # Length correction for suffix array candidates
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

## Fuzzy + Phonetic

The entire fuzzy stage is the [`ffuzzy`](https://github.com/mkbabb/ffuzzy) Rust crate, loaded via PyO3 and driven through a ~30-line wrapper at `fuzzy/search.py`. `ffuzzy.Index` fuses five engines behind an adaptive router: SymSpell (k≤2), Levenshtein automaton + FST (scaffolded, search-path stubbed), bounded BK-tree (Damerau-Levenshtein), 3.5-gram trigram, and Double Metaphone with silent-consonant handling.

Candidate generation, signal boosting, length correction, and SIMD DL verification all happen on the Rust side. Python just converts `ffuzzy.SearchHit` to `SearchResult`. Persistence: `FuzzyIndex` stores `ffuzzy.Index.to_bytes()` as an opaque binary blob in GridFS alongside a pickled `SuffixArray` (for substring search, unrelated to fuzzy).

Details: see [`../../../../docs/search.md#fuzzy-search-the-ffuzzy-crate`](../../../../docs/search.md#fuzzy-search-the-ffuzzy-crate) or the `ffuzzy` repo docs directly.

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

Python-level constants in `config.py`: score thresholds, corpus size tiers, Bloom filter error rates. Fuzzy-specific tuning (BK-tree visit cap, trigram cap fractions, signal boosts, adaptive k) lives inside the `ffuzzy` Rust crate and is exposed via `ffuzzy.Index` constructor arguments.

HNSW config via env vars: `FLORIDIFY_USE_HNSW`, `FLORIDIFY_HNSW_M` (default 32), `FLORIDIFY_HNSW_EF_CONSTRUCTION` (200), `FLORIDIFY_HNSW_EF_SEARCH` (64).
