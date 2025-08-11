"""Semantic search constants."""

from typing import Literal

# Supported Models
SemanticModel = Literal["BAAI/bge-m3", "sentence-transformers/all-MiniLM-L6-v2"]

# Model Configurations
BGE_M3_MODEL: SemanticModel = "BAAI/bge-m3"  # 1024D, 100+ languages, cross-lingual
MINI_LM_MODEL: SemanticModel = "sentence-transformers/all-MiniLM-L6-v2"  # 384D, English-only, fast

# Default model - BGE-M3 for multilingual support
DEFAULT_SENTENCE_MODEL: SemanticModel = "BAAI/bge-m3"

# Model dimensions
MODEL_DIMENSIONS = {
    BGE_M3_MODEL: 1024,
    MINI_LM_MODEL: 384,
}

# FAISS Configuration
L2_DISTANCE_NORMALIZATION = 2  # Divisor for L2 distance to similarity conversion

# BGE-M3 Optimized Quantization Thresholds
SMALL_CORPUS_THRESHOLD = 10000  # IndexFlatL2 (exact search)
MEDIUM_CORPUS_THRESHOLD = 25000  # FP16 Scalar Quantization
LARGE_CORPUS_THRESHOLD = 50000  # INT8 Scalar Quantization
PQ_CORPUS_THRESHOLD = 50000  # Product Quantization (IVF-PQ)
MASSIVE_CORPUS_THRESHOLD = 250000  # OPQ + IVF-PQ (advanced quantization)

# Batch Processing - Model-aware
MODEL_BATCH_SIZES = {
    BGE_M3_MODEL: 32,  # Smaller batch for 1024D embeddings
    MINI_LM_MODEL: 64,  # Larger batch for 384D embeddings
}
DEFAULT_BATCH_SIZE = 32

# Optimization Configuration
USE_ONNX_BACKEND = True  # Enable ONNX backend for 2x speedup
USE_MIXED_PRECISION = True  # Enable FP16 for 1.88x speedup and memory reduction
ENABLE_GPU_ACCELERATION = True  # Enable GPU acceleration when available
MEMORY_MAP_EMBEDDINGS = True  # Use memory-mapped storage for zero-copy access
