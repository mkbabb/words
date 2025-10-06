# SOWPODS English Corpus - Semantic Index Verification Report
**Date:** 2025-10-02  
**Corpus:** `english_language_master_sowpods_scrabble_words`  
**Model:** `Alibaba-NLP/gte-Qwen2-1.5B-instruct` (GTE-Qwen2-1.5B, 1536D)

---

## Executive Summary

**STATUS: ⚠️ INDEX NOT BUILT - EMPTY PLACEHOLDERS EXIST**

The semantic index for the 267K SOWPODS English corpus has **NOT been built**. While metadata entries exist in MongoDB, both the corpus vocabulary and semantic embeddings are empty (0 bytes). The system requires a full index build to generate the expected 217K embeddings.

---

## Current Index Status

### MongoDB Metadata (5 documents found)

| Model | Version | Latest | Size | Embeddings | Status |
|-------|---------|--------|------|------------|---------|
| **GTE-Qwen2-1.5B** | 1.0.1 | ✓ Yes | 6.35 MB | **0** | ❌ Empty |
| GTE-Qwen2-1.5B | 1.0.0 | ✗ No | 6.35 MB | **0** | ❌ Empty |
| all-MiniLM-L6-v2 | 1.0.2 | ✓ Yes | 6.35 MB | **0** | ❌ Empty |
| all-MiniLM-L6-v2 | 1.0.1 | ✗ No | 6.35 MB | **0** | ❌ Empty |
| all-MiniLM-L6-v2 | 1.0.0 | ✗ No | 6.35 MB | **0** | ❌ Empty |

**Latest Index (GTE-Qwen2):**
- **Document ID:** `68de7a2df398621993ad3b06`
- **Resource ID:** `english_language_master_sowpods_scrabble_words:semantic:Alibaba-NLP/gte-Qwen2-1.5B-instruct`
- **Content Hash:** `3e83f5c06a72a9d59d32b07db1b1ad7a60c30f53514412f64cd6ca35657a0346`
- **Storage Type:** Filesystem cache (`cache` namespace)
- **Size:** 6,354,731 bytes (metadata structure only, no embeddings)
- **Embeddings:** **0** (expected: 217,172)
- **Index Data:** Empty (expected: FAISS index)

### Filesystem Cache Status

```
Cache Location: /Users/mkbabb/Programming/words/backend/cache/floridify/unified
Total Size: 4.6 MB
Total Entries: 51
```

**SOWPODS Entries:**
```sql
corpus:corpus:english_language_master_sowpods_scrabble_words | 0 bytes
semantic:semantic:english_language_master_sowpods_scrabble_words:semantic:Alibaba-NLP/gte-Qwen2-1.5B-instruct | 0 bytes
```

**Key Finding:** Both corpus and semantic index cache entries are **0 bytes** - they are placeholder entries without actual data.

---

## Expected Configuration

### Corpus Specifications
- **Name:** `english_language_master_sowpods_scrabble_words`
- **Corpus ID:** `68dde4c063a8a94ce1869ae2`
- **Total Vocabulary:** 267,743 words
- **Unique Lemmas:** 217,172 (after lemmatization)
- **Language:** English (en)
- **Type:** LANGUAGE corpus

### Model Configuration (GTE-Qwen2-1.5B-instruct)
- **Dimensions:** 1,536
- **Architecture:** QWEN2-based multilingual transformer
- **MTEB Score:** 67.16 (state-of-the-art)
- **Batch Size:** 24 (optimized for 1536D embeddings)
- **Device:** MPS (Apple Silicon GPU acceleration)
- **Quantization:** INT8 (75% memory reduction, <2% quality loss)

### Expected Index Configuration

Based on corpus size (217K lemmas), the system will automatically select:

**Index Type: OPQ+IVF-PQ** (Optimized Product Quantization with Inverted File)

- **Threshold:** 150K-250K+ embeddings → EXTREME corpus size
- **Strategy:** Maximum compression for massive datasets
- **Compression:** ~97% (1.3 GB baseline → 40-60 MB final)
- **Quality Loss:** ~10-15% (acceptable for semantic search)
- **Search Speed:** 5-10ms per query

**FAISS Parameters (Auto-selected):**
```python
Index Type: OPQ + IVF-PQ
├── nlist: ~3,000-4,000 clusters (based on sqrt(217K) * 2)
├── m: 64 subquantizers (for 1536D embeddings)
├── nbits: 8 bits per subquantizer
├── nprobe: 64-128 clusters searched at query time
└── OPQ: Rotation matrix for improved quantization quality
```

**Memory Calculation:**
```
Baseline (FP32):  217,172 × 1536 × 4 bytes = 1,336 MB (1.3 GB)
Compressed (PQ):  217,172 × 64 subquants × 8 bits / 8 = 13.9 MB
With metadata:    ~40-60 MB total
Compression:      ~3% of baseline (97% reduction)
```

---

## Build Requirements

### Time Estimates (Apple Silicon MPS)

| Stage | Time | Notes |
|-------|------|-------|
| Model Load | 10-30s | One-time download/cache (1.5B params) |
| Embeddings | 30-90 min | 217K lemmas × 1536D on MPS |
| FAISS Training | 5-15 min | OPQ+IVF-PQ cluster training |
| Serialization | 1-2 min | Save to MongoDB + cache |
| **Total** | **45-120 min** | First-time build |

### Storage Requirements

| Component | Size | Location |
|-----------|------|----------|
| Model Weights | ~3 GB | HuggingFace cache (`~/.cache/huggingface/`) |
| FP32 Embeddings | 1.3 GB | Temporary (build phase only) |
| Compressed Index | 40-60 MB | MongoDB + filesystem cache |
| Metadata | ~6 MB | MongoDB (`versioned_data` collection) |

---

## Verification Commands

### 1. Check Current Status
```bash
cd /Users/mkbabb/Programming/words/backend
source .venv/bin/activate
python scripts/check_semantic_index.py
```

**Expected Output:**
```
✗ No semantic index found
To build the semantic index, run:
  python scripts/build_semantic_index.py english_language_master_sowpods_scrabble_words
```

### 2. Build Semantic Index
```bash
python scripts/build_semantic_index.py english_language_master_sowpods_scrabble_words
```

**Build Process:**
1. ✓ Load corpus (267K vocabulary, 217K lemmas)
2. ✓ Load GTE-Qwen2-1.5B model (1536D)
3. 🔄 Detect device (MPS on Apple Silicon)
4. 🔄 Generate embeddings (217K lemmas, 30-90 min)
5. ⏳ Train FAISS index (OPQ+IVF-PQ, 5-15 min)
6. ⏳ Serialize and save to MongoDB
7. ⏳ Run validation test query

### 3. Verify Build Success
```bash
python scripts/check_semantic_index.py
```

**Expected Output (after build):**
```
✓ Semantic index is ready for use

Semantic Index Status
┌────────────────────┬──────────────────────────────────┐
│ Model              │ Alibaba-NLP/gte-Qwen2-1.5B-...  │
│ Index Type         │ OPQ+IVF-PQ                        │
│ Embeddings         │ 217,172                           │
│ Dimension          │ 1536                              │
│ Memory Usage       │ 40-60 MB                          │
│ Build Time         │ 45-120 minutes                    │
│ Device             │ mps                               │
└────────────────────┴──────────────────────────────────┘

Compression: 3% of baseline (1,336 MB → 50 MB)
```

### 4. Test Index Integrity
```bash
python -c "
import asyncio
from floridify.corpus.core import Corpus
from floridify.search.semantic.core import SemanticSearch
from floridify.caching.models import VersionConfig

async def test():
    corpus = await Corpus.get(
        corpus_name='english_language_master_sowpods_scrabble_words',
        config=VersionConfig()
    )
    
    search = await SemanticSearch.from_corpus(
        corpus=corpus,
        model_name='Alibaba-NLP/gte-Qwen2-1.5B-instruct',
        config=VersionConfig()
    )
    
    results = await search.search('hello', max_results=5)
    print(f'Found {len(results)} results for \"hello\"')
    for i, r in enumerate(results, 1):
        print(f'{i}. {r.word} (score: {r.score:.4f})')

asyncio.run(test())
"
```

### 5. Check MongoDB Directly
```bash
mongosh floridify --eval "
db.versioned_data.find({
    resource_type: 'semantic',
    resource_id: /sowpods/
}, {
    resource_id: 1,
    'version_info.version': 1,
    'version_info.is_latest': 1,
    'metadata.num_embeddings': 1,
    'metadata.embedding_dimension': 1
}).pretty()
"
```

### 6. Check Filesystem Cache
```bash
sqlite3 /Users/mkbabb/Programming/words/backend/cache/floridify/unified/cache.db \
    "SELECT key, size FROM cache WHERE key LIKE '%sowpods%semantic%';"
```

**Expected (after build):**
```
semantic:semantic:english_language_master_sowpods_scrabble_words:...|52428800
```
(~50 MB for compressed index)

---

## Performance Benchmarks (Post-Build)

### Search Latency (Expected)
- **Query Embedding:** 5-10ms (cached: <1ms)
- **FAISS Search:** 5-10ms (OPQ+IVF-PQ with nprobe=64)
- **Result Mapping:** 1-2ms
- **Total (cold):** 10-20ms
- **Total (warm):** 1-5ms (with query cache)

### Memory Usage
- **Model (MPS):** ~1.5 GB (shared across queries)
- **Index (RAM):** ~50 MB (loaded on first search)
- **Query Cache:** ~10 MB (100 cached queries)
- **Total:** ~1.6 GB (persistent)

### Throughput (Concurrent Queries)
- **Single Query:** 50-100 QPS
- **Batch (10):** 200-400 QPS (MPS parallelization)

---

## Build Optimization Recommendations

### 1. Use HNSW for Faster Search (Optional)
If search speed is more important than memory:

```bash
# Edit constants before building
vim /Users/mkbabb/Programming/words/backend/src/floridify/search/semantic/constants.py
```

Change:
```python
USE_HNSW = True  # Enable HNSW (default: True)
HNSW_M = 32      # Connections per node (higher = faster, more memory)
HNSW_EF_SEARCH = 64  # Query-time search depth (tunable)
```

**HNSW vs IVF-PQ:**
| Metric | HNSW | IVF-PQ |
|--------|------|--------|
| Memory | ~450 MB | ~50 MB |
| Search Speed | 2-3ms | 5-10ms |
| Quality Loss | ~2-3% | ~10-15% |
| Build Time | 20-40 min | 10-20 min |

### 2. Monitor Build Progress
```bash
# Run build in background and monitor logs
python scripts/build_semantic_index.py english_language_master_sowpods_scrabble_words \
    2>&1 | tee semantic_build.log &

# Monitor progress
tail -f semantic_build.log | grep -E "embeddings|FAISS|Saved"
```

### 3. Verify System Resources
```bash
# Check available memory (need ~4 GB free)
vm_stat | grep "Pages free" | awk '{print $3 * 4096 / 1024 / 1024 " MB"}'

# Check MPS availability (Apple Silicon only)
python -c "import torch; print(f'MPS Available: {torch.backends.mps.is_available()}')"

# Check HuggingFace cache space (need ~3 GB)
du -sh ~/.cache/huggingface/hub
```

---

## Troubleshooting

### Issue: "No semantic index found"
**Cause:** Index has never been built  
**Solution:** Run build command above

### Issue: "Failed to load content"
**Cause:** Corpus vocabulary is empty (0 bytes in cache)  
**Solution:** Rebuild corpus first, then semantic index

### Issue: Build times out or crashes
**Cause:** Insufficient memory or MPS issues  
**Solutions:**
1. Close memory-intensive applications
2. Use CPU instead: `FLORIDIFY_USE_GPU=false python scripts/build_semantic_index.py ...`
3. Reduce batch size: Edit `constants.py` → `MODEL_BATCH_SIZES["GTE_QWEN2_MODEL"] = 12`

### Issue: Embeddings count is 0 after build
**Cause:** Corpus lemmatized_vocabulary is empty  
**Solution:**
```bash
# Check corpus status
python scripts/check_semantic_index.py

# Rebuild corpus if needed
python scripts/rebuild_corpus.py english_language_master_sowpods_scrabble_words
```

---

## Next Steps

1. **Run Build:** Execute `python scripts/build_semantic_index.py english_language_master_sowpods_scrabble_words`
2. **Monitor Progress:** Watch for "✅ Semantic embeddings complete" message
3. **Verify:** Run check script to confirm 217,172 embeddings
4. **Test:** Perform sample searches to validate quality
5. **Benchmark:** Measure search latency and adjust FAISS parameters if needed

---

## Technical Details

### Index Selection Logic
```python
def _build_optimized_index(dimension: int, vocab_size: int):
    if vocab_size <= 5000:
        return "IndexFlatL2"  # Exact search, no compression
    elif vocab_size <= 15000:
        return "IVF-Flat"  # 3-5x speedup, minimal loss
    elif vocab_size <= 40000:
        return "IVF-PQ"  # High compression
    elif vocab_size <= 150000:
        return "HNSW" if USE_HNSW else "IVF-PQ"
    else:
        return "OPQ+IVF-PQ"  # Maximum compression (217K → this path)
```

### Compression Breakdown
```
Original: 217,172 lemmas × 1536 dims × 4 bytes = 1,336 MB

OPQ+IVF-PQ Compression:
  1. OPQ rotation: Pre-process for better quantization
  2. Product Quantization: 64 subquantizers × 8 bits = 512 bits/vector
  3. Compression ratio: 512 / (1536 × 32) = 1.04% of original
  4. With metadata/clusters: ~40-60 MB final
  5. Total compression: 97-99%
```

---

**Report Generated:** 2025-10-02 10:50:00  
**Script:** `/Users/mkbabb/Programming/words/backend/scripts/check_semantic_index.py`  
**Source Files:**
- `/Users/mkbabb/Programming/words/backend/src/floridify/search/semantic/core.py`
- `/Users/mkbabb/Programming/words/backend/src/floridify/search/semantic/models.py`
- `/Users/mkbabb/Programming/words/backend/src/floridify/search/semantic/constants.py`
