"""Semantic search constants."""

# Model Configuration
DEFAULT_SENTENCE_MODEL = "all-MiniLM-L6-v2"  # 384D embeddings, fast and accurate
SENTENCE_EMBEDDING_DIM = 384  # Expected dimension for all-MiniLM-L6-v2

# FAISS Configuration
L2_DISTANCE_NORMALIZATION = 2  # Divisor for L2 distance to similarity conversion

# Batch Processing
DEFAULT_BATCH_SIZE = 64  # Default batch size for embedding generation

# Optimization Configuration
USE_ONNX_BACKEND = True  # Enable ONNX backend for 2x speedup
USE_MIXED_PRECISION = True  # Enable FP16 for 1.88x speedup and memory reduction
ENABLE_GPU_ACCELERATION = True  # Enable GPU acceleration when available
MEMORY_MAP_EMBEDDINGS = True  # Use memory-mapped storage for zero-copy access
