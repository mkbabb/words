"""Semantic search constants."""

from __future__ import annotations

import os
from typing import Literal

# Supported Models
SemanticModel = Literal[
    "BAAI/bge-m3",
    "sentence-transformers/all-MiniLM-L6-v2",
    "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
]

# Model Configurations
BGE_M3_MODEL: SemanticModel = "BAAI/bge-m3"  # 1024D, 100+ languages, cross-lingual
MINI_LM_MODEL: SemanticModel = "sentence-transformers/all-MiniLM-L6-v2"  # 384D, English-only, fast
GTE_QWEN2_MODEL: SemanticModel = (
    "Alibaba-NLP/gte-Qwen2-1.5B-instruct"  # 1536D, QWEN2-based, multilingual, 67.16 MTEB
)

# Default model - GTE-Qwen2 for best QWEN-based multilingual support
DEFAULT_SENTENCE_MODEL: SemanticModel = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"

# Model dimensions
MODEL_DIMENSIONS = {
    BGE_M3_MODEL: 1024,
    MINI_LM_MODEL: 384,
    GTE_QWEN2_MODEL: 1536,
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
MODEL_BATCH_SIZES = {
    BGE_M3_MODEL: 32,  # Smaller batch for 1024D embeddings
    MINI_LM_MODEL: 64,  # Larger batch for 384D embeddings
    GTE_QWEN2_MODEL: 24,  # Smaller batch for 1536D embeddings
}
DEFAULT_BATCH_SIZE = 24

# Optimization Configuration
USE_ONNX_BACKEND = False  # Disable ONNX backend (macOS compatibility issue)
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
