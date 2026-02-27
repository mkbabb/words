"""Semantic search constants."""

from __future__ import annotations

import os
from typing import Literal

# Supported Models
SemanticModel = Literal[
    "BAAI/bge-m3",
    "sentence-transformers/all-MiniLM-L6-v2",
    "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
    # Latest Qwen3-Embedding models (2025) with Matryoshka support
    "Qwen/Qwen3-Embedding-8B",  # 8B params, #1 MTEB, 32-4096D MRL
    "Qwen/Qwen3-Embedding-4B",  # 4B params, balanced, 32-2560D MRL
    "Qwen/Qwen3-Embedding-0.6B",  # 0.6B params, lightweight, 32-1024D MRL
]

# Model Configurations
BGE_M3_MODEL: SemanticModel = "BAAI/bge-m3"  # 1024D, 100+ languages, cross-lingual
MINI_LM_MODEL: SemanticModel = "sentence-transformers/all-MiniLM-L6-v2"  # 384D, English-only, fast
GTE_QWEN2_MODEL: SemanticModel = (
    "Alibaba-NLP/gte-Qwen2-1.5B-instruct"  # 1536D, QWEN2-based, multilingual, 67.16 MTEB
)

# Latest Qwen3-Embedding models (October 2025) - State-of-the-art
QWEN3_8B_MODEL: SemanticModel = "Qwen/Qwen3-Embedding-8B"  # 8B, MTEB #1: 70.58, max 4096D
QWEN3_4B_MODEL: SemanticModel = "Qwen/Qwen3-Embedding-4B"  # 4B, MTEB: 69.45, max 2560D
QWEN3_0_6B_MODEL: SemanticModel = "Qwen/Qwen3-Embedding-0.6B"  # 0.6B, MTEB: 64.33, max 1024D

# Default model - Qwen3-0.6B for balanced performance and multilingual support
# 0.6B parameters, MTEB: 64.33, excellent cross-lingual capabilities
DEFAULT_SENTENCE_MODEL: SemanticModel = QWEN3_0_6B_MODEL

# Model dimensions (using default/max dimensions)
MODEL_DIMENSIONS = {
    BGE_M3_MODEL: 1024,
    MINI_LM_MODEL: 384,
    GTE_QWEN2_MODEL: 1536,
    QWEN3_8B_MODEL: 4096,  # Matryoshka: 32-4096
    QWEN3_4B_MODEL: 2560,  # Matryoshka: 32-2560
    QWEN3_0_6B_MODEL: 1024,  # Matryoshka: 32-1024
}

# Matryoshka dimension support for Qwen3 models
# Can use any dimension from min to max for flexible performance/memory tradeoff
MATRYOSHKA_DIMENSIONS = {
    QWEN3_8B_MODEL: [32, 64, 128, 256, 512, 1024, 2048, 4096],
    QWEN3_4B_MODEL: [32, 64, 128, 256, 512, 1024, 2048, 2560],
    QWEN3_0_6B_MODEL: [32, 64, 128, 256, 512, 1024],
}

# FAISS Configuration
L2_DISTANCE_NORMALIZATION = 2  # Divisor for L2 distance to similarity conversion

# Corpus Size Thresholds - Optimized for 1024D BGE-M3 and large corpora
SMALL_CORPUS_THRESHOLD = 10000  # IndexFlatL2 (exact search, fast for <10k)
MEDIUM_CORPUS_THRESHOLD = 50000  # IVF-Flat (3-5x speedup, good accuracy)
LARGE_CORPUS_THRESHOLD = 100000  # IVF-PQ (balanced speed/accuracy)
PQ_CORPUS_THRESHOLD = 100000  # Product Quantization threshold
MASSIVE_CORPUS_THRESHOLD = 200000  # OPQ+IVF-PQ (for 200k+ lemmas)

# Batch Processing - Model-aware
# Profiled on Apple Silicon M4 Max: larger batches give significant speedup
# for small models (0.6B: batch=128 is 42% faster than batch=32)
MODEL_BATCH_SIZES = {
    BGE_M3_MODEL: 64,  # 1024D embeddings
    MINI_LM_MODEL: 128,  # 384D embeddings (lightweight)
    GTE_QWEN2_MODEL: 24,  # 1536D embeddings (memory-heavy)
    QWEN3_8B_MODEL: 8,   # 8B model, 4096D embeddings
    QWEN3_4B_MODEL: 16,  # 4B model, 2560D embeddings
    QWEN3_0_6B_MODEL: 128,  # 0.6B model, 1024D — profiled optimal for M-series
}
DEFAULT_BATCH_SIZE = 32

# Optimization Configuration
ENABLE_GPU_ACCELERATION = True  # Enable GPU acceleration when available
MEMORY_MAP_EMBEDDINGS = True  # Use memory-mapped storage for zero-copy access

# Quantization Configuration
USE_QUANTIZATION = True  # Enable embedding quantization for speed/memory
QUANTIZATION_PRECISION: Literal["float32", "int8", "uint8", "binary", "ubinary"] = "int8"
# Precision levels:
# - float32: No quantization (baseline)
# - int8: 75% memory reduction, ~2-3x speedup, <2% quality loss [RECOMMENDED]
# - uint8: 75% memory reduction, ~2-3x speedup, <2% quality loss
# - binary: 97% memory reduction, ~10x speedup, ~5-10% quality loss
# - ubinary: 97% memory reduction, ~10x speedup, ~5-10% quality loss

# HNSW Configuration (Hierarchical Navigable Small World)
# Can be overridden via environment variables or config file
USE_HNSW = os.getenv("FLORIDIFY_USE_HNSW", "true").lower() == "true"
HNSW_M = int(os.getenv("FLORIDIFY_HNSW_M", "32"))
HNSW_EF_CONSTRUCTION = int(os.getenv("FLORIDIFY_HNSW_EF_CONSTRUCTION", "200"))
HNSW_EF_SEARCH = int(os.getenv("FLORIDIFY_HNSW_EF_SEARCH", "64"))
