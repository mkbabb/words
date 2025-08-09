"""Semantic search constants."""

# Model Configuration - BGE-M3 for Multilingual Support
DEFAULT_SENTENCE_MODEL = "BAAI/bge-m3"  # 1024D embeddings, 100+ languages, superior cross-language accuracy
SENTENCE_EMBEDDING_DIM = 1024  # Expected dimension for BGE-M3

# FAISS Configuration
L2_DISTANCE_NORMALIZATION = 2  # Divisor for L2 distance to similarity conversion

# BGE-M3 Optimized Quantization Thresholds
SMALL_CORPUS_THRESHOLD = 10000    # IndexFlatL2 (exact search)
MEDIUM_CORPUS_THRESHOLD = 25000   # FP16 Scalar Quantization 
LARGE_CORPUS_THRESHOLD = 50000    # INT8 Scalar Quantization
PQ_CORPUS_THRESHOLD = 50000       # Product Quantization (IVF-PQ)
MASSIVE_CORPUS_THRESHOLD = 200000 # OPQ + IVF-PQ (advanced quantization)

# Batch Processing - Optimized for BGE-M3
DEFAULT_BATCH_SIZE = 32  # Reduced batch size for larger BGE-M3 model (1024D vs 384D)

# Optimization Configuration
USE_ONNX_BACKEND = True  # Enable ONNX backend for 2x speedup
USE_MIXED_PRECISION = True  # Enable FP16 for 1.88x speedup and memory reduction
ENABLE_GPU_ACCELERATION = True  # Enable GPU acceleration when available
MEMORY_MAP_EMBEDDINGS = True  # Use memory-mapped storage for zero-copy access
