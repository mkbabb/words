# search/

Multi-method search: exact (marisa-trie), fuzzy (RapidFuzz), semantic (FAISS). Cascade with early termination.

```
search/
├── core.py (897)           # Search orchestrator, cascade logic
├── trie.py (228)           # marisa-trie + Bloom filter
├── fuzzy.py (234)          # RapidFuzz dual-scorer
├── bloom.py (196)          # Bitarray membership testing
├── language.py (240)       # Multi-corpus orchestration
├── models.py (705)         # SearchResult, TrieIndex, SearchIndex
├── constants.py (39)       # SearchMethod, SearchMode, FuzzySearchMethod enums
├── utils.py (206)          # Length correction, default frequency heuristics
└── semantic/               # FAISS vector search (2,045 LOC)
    ├── core.py (1,470)     # SemanticSearch: index building, embeddings
    ├── models.py (480)     # SemanticIndex(Document)
    └── constants.py (95)   # Model catalog, FAISS thresholds, HNSW config
```

## Enums

**SearchMethod**: `EXACT`, `PREFIX`, `FUZZY`, `SEMANTIC`, `AUTO`
**SearchMode**: `SMART`, `EXACT`, `FUZZY`, `SEMANTIC`
**FuzzySearchMethod**: `RAPIDFUZZ`, `JARO_WINKLER`, `SOUNDEX`, `LEVENSHTEIN`, `METAPHONE`, `AUTO`

## Cascade (SMART mode)

Exact -> if no match -> Fuzzy -> if <33% high-quality (>=0.7) -> Semantic -> Deduplicate -> Top N.

Early termination: exact match returns immediately. Quality gating: skip semantic if fuzzy suffices.

## FAISS Index Selection

5 tiers selected by corpus size (thresholds in `semantic/constants.py`):

| Corpus Size | Index | Notes |
|-------------|-------|-------|
| <10k | IndexFlatL2 | Brute-force exact search |
| 10k–50k | IVF-Flat | nlist=max(64, sqrt(n)), nprobe=nlist/4 |
| 50k–100k | ScalarQuantizer INT8 | 4x compression |
| 100k–200k | HNSW or IVF-PQ | HNSW default (M, efConstruction, efSearch from env); IVF-PQ fallback |
| >200k | OPQ+IVF-PQ | OPQ rotation + product quantization |

HNSW config via env vars: `FLORIDIFY_USE_HNSW`, `FLORIDIFY_HNSW_M` (default 32), `FLORIDIFY_HNSW_EF_CONSTRUCTION` (200), `FLORIDIFY_HNSW_EF_SEARCH` (64).

## Embedding Models

Defined in `semantic/constants.py`. Default: `Qwen/Qwen3-Embedding-0.6B`.

| Model | Dims | MTEB | Batch Size |
|-------|------|------|------------|
| Qwen3-Embedding-0.6B | 1024 (MRL: 32–1024) | 64.33 | 128 |
| Qwen3-Embedding-4B | 2560 (MRL: 32–2560) | 69.45 | 16 |
| Qwen3-Embedding-8B | 4096 (MRL: 32–4096) | 70.58 | 8 |
| BAAI/bge-m3 | 1024 | 66.29 | 64 |
| all-MiniLM-L6-v2 | 384 | — | 128 |
| gte-Qwen2-1.5B-instruct | 1536 | 67.16 | 24 |

Qwen3 models support Matryoshka Representation Learning (MRL)—any dimension from min to max.
