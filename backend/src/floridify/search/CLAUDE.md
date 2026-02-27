# search/

Multi-method search: exact (marisa-trie), fuzzy (RapidFuzz), semantic (FAISS). Cascade with early termination.

```
search/
├── core.py (897)           # Search orchestrator, cascade logic
├── trie.py (228)           # marisa-trie + Bloom filter (<1ms)
├── fuzzy.py (234)          # RapidFuzz dual-scorer (10-50ms)
├── bloom.py (196)          # Bitarray membership testing
├── language.py (231)       # Multi-corpus orchestration
├── models.py (700)         # SearchResult, SearchIndex, SearchMode
├── constants.py (39)       # SearchMethod/SearchMode enums
└── semantic/               # FAISS vector search (2,213 LOC)
    ├── core.py (1,470)     # SemanticSearch: 7 index types, embeddings
    ├── models.py (480)     # SemanticIndex(Document)
    ├── constants.py (95)   # Model catalog (Qwen3-0.6B, BGE-M3)
    └── config.py (168)     # Index selection by corpus size
```

## Methods

| Method | Time | Structure | Notes |
|--------|------|-----------|-------|
| Exact | <1ms | marisa-trie + Bloom filter | O(m), m = query length |
| Fuzzy | 10-50ms | Signature + length buckets | RapidFuzz WRatio + token_set_ratio |
| Semantic | 50-200ms | FAISS HNSW + Qwen3 1024D | 7 index types by corpus size |

## Cascade (SMART mode)

Exact → if no match → Fuzzy → if <33% high-quality (≥0.7) → Semantic → Deduplicate → Top N.

Early termination: exact match returns immediately. Quality gating: skip semantic if fuzzy suffices.

## FAISS Index Selection

| Corpus | Index | Notes |
|--------|-------|-------|
| <10k | Flat L2 | Brute force |
| 10-50k | IVF-Flat | nlist=4√n |
| 50-100k | INT8 | 30% memory reduction |
| 100-200k | HNSW | M=16, ef=40 |
| 200-500k | IVF-PQ | 75% memory reduction |
| 500k-1M | OPQ+PQ | 16 subquantizers |
| >1M | OPQ+IVF-PQ | Hierarchical |

## Embedding Models

| Model | Dims | MTEB | Use |
|-------|------|------|-----|
| Qwen3-0.6B | 1024 | 64.33 | Default |
| BGE-M3 | 1024 | 66.29 | Multilingual |
| GTE-Qwen2-7B | 4096 | 70.58 | SOTA |
