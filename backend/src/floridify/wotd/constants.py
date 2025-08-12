"""WOTD training and model constants."""

from typing import Literal

# Embedding Models
EmbeddingModel = Literal[
    "Alibaba-NLP/gte-Qwen2-7B-instruct",
    "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
    "Salesforce/SFR-Embedding-2_R",
    "intfloat/multilingual-e5-large-instruct",
    "intfloat/e5-mistral-7b-instruct",
]

# State-of-the-art models (2024-2025)
GTE_QWEN2_7B: EmbeddingModel = "Alibaba-NLP/gte-Qwen2-7B-instruct"  # SOTA 4096D
GTE_QWEN2_1B: EmbeddingModel = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"  # Lighter 4096D
SFR_EMBEDDING_2: EmbeddingModel = "Salesforce/SFR-Embedding-2_R"  # Research license
E5_MULTILINGUAL: EmbeddingModel = "intfloat/multilingual-e5-large-instruct"  # 1024D
E5_MISTRAL_7B: EmbeddingModel = "intfloat/e5-mistral-7b-instruct"  # 4096D

# Model dimensions mapping with Matryoshka support
MODEL_DIMENSIONS = {
    "Alibaba-NLP/gte-Qwen2-7B-instruct": 4096,  # Supports elastic dimensions: 256, 512, 1024, 2048, 4096
    "Alibaba-NLP/gte-Qwen2-1.5B-instruct": 4096,  # Lighter but same dimensionality
    "Salesforce/SFR-Embedding-2_R": 4096,  # Top MTEB performance
    "intfloat/multilingual-e5-large-instruct": 1024,  # Efficient multilingual
    "intfloat/e5-mistral-7b-instruct": 4096,  # Large E5 variant
    "sentence-transformers/all-MiniLM-L6-v2": 384,  # Lightweight testing model
}

# Matryoshka/Elastic dimension support
MATRYOSHKA_MODELS = {
    "Alibaba-NLP/gte-Qwen2-7B-instruct": [256, 512, 1024, 2048, 4096],
    "Alibaba-NLP/gte-Qwen2-1.5B-instruct": [256, 512, 1024, 2048, 4096],
    "Salesforce/SFR-Embedding-2_R": [512, 1024, 2048, 4096],
}

# Default embedding model - GTE-Qwen2 for SOTA performance
DEFAULT_EMBEDDING_MODEL: EmbeddingModel = GTE_QWEN2_1B  # Balance of quality and speed
DEFAULT_EMBEDDING_DIM = MODEL_DIMENSIONS[DEFAULT_EMBEDDING_MODEL]  # 4096

# Language Models for DSL generation
LanguageModel = Literal[
    "microsoft/Phi-4",
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
    "mistralai/Mistral-Nemo-Instruct-2407",
]

# State-of-the-art models (2024-2025)
PHI_4: LanguageModel = "microsoft/Phi-4"  # 14B, 128K context
QWEN_25_7B: LanguageModel = "Qwen/Qwen2.5-7B-Instruct"  # SOTA 7B
QWEN_25_3B: LanguageModel = "Qwen/Qwen2.5-3B-Instruct"  # Efficient 3B
MISTRAL_NEMO: LanguageModel = "mistralai/Mistral-Nemo-Instruct-2407"  # 12B, 128K

DEFAULT_LANGUAGE_MODEL: LanguageModel = QWEN_25_7B  # Best quality/performance

# Training Corpus Configuration
DEFAULT_WORDS_PER_CORPUS = 100  # Words per semantic corpus
DEFAULT_NUM_CORPORA = 12  # Total corpora for complete coverage
MIN_CORPUS_SIZE = 25  # Minimum viable corpus size
MAX_CORPUS_SIZE = 500  # Maximum efficient corpus size

# BGE Embedding Configuration
NORMALIZE_EMBEDDINGS = True  # L2 normalization for similarity
EMBEDDING_BATCH_SIZE = 32  # BGE-M3 optimal batch size
EMBEDDING_DEVICE = "cpu"  # Default to CPU for reliability

# Semantic Encoder Configuration - RVQ and FSQ options
RVQ_NUM_LEVELS = 4  # Residual quantization levels
RVQ_CODEBOOK_SIZE = 32  # Codebook size per level
RVQ_ENCODER_EPOCHS = 200  # Training epochs for RVQ
RVQ_ENCODER_LR = 1e-3  # Learning rate for RVQ

# Finite Scalar Quantization (FSQ) - simpler alternative to RVQ
FSQ_LATENT_DIM = 4  # Number of latent dimensions (matches semantic levels)
FSQ_LEVELS_PER_DIM = [8, 8, 8, 5]  # Quantization levels per dimension
FSQ_USE_L2_NORM = True  # L2 normalize before quantization

# Hierarchical encoding options
USE_FSQ = False  # Use FSQ instead of RVQ (experimental)
USE_HIERARCHICAL_VQ = False  # Use multi-level VQ (experimental)

# Language Model (LoRA) Configuration
LM_MAX_LENGTH = 512  # Maximum sequence length
LM_EPOCHS = 10  # Fine-tuning epochs
LM_LEARNING_RATE = 2e-5  # LoRA learning rate
LORA_RANK = 16  # LoRA rank (adaptation dimension)
LORA_ALPHA = 32  # LoRA scaling parameter
LORA_DROPOUT = 0.1  # LoRA dropout rate

# Semantic ID System
SEMANTIC_ID_DIMENSIONS = 4  # [style, complexity, era, variation]
MAX_SEMANTIC_VARIATIONS = 8  # Maximum variations per style/complexity/era

# Training Performance
DEFAULT_BATCH_SIZE = 16  # Default training batch size
GRADIENT_ACCUMULATION = 2  # Steps before optimizer update
WARMUP_RATIO = 0.1  # Learning rate warmup ratio
WEIGHT_DECAY = 0.01  # L2 regularization

# File Extensions
MODEL_EXTENSION = ".pt"  # PyTorch model extension
CONFIG_EXTENSION = ".json"  # Configuration file extension
CHECKPOINT_EXTENSION = ".ckpt"  # Training checkpoint extension

# Memory Optimization
USE_GRADIENT_CHECKPOINTING = True  # Trade compute for memory
ENABLE_MIXED_PRECISION = True  # FP16 training
DATALOADER_WORKERS = 4  # Parallel data loading
PIN_MEMORY = True  # Pin memory for GPU transfer

# Quantization Configuration
USE_INT8_EMBEDDINGS = False  # Quantize embeddings to int8
USE_BINARY_EMBEDDINGS = False  # Binary quantization (experimental)
USE_PRODUCT_QUANTIZATION = False  # PQ for FAISS indices
PQ_SUBVECTORS = 64  # Number of PQ subvectors
PQ_BITS = 8  # Bits per PQ code

# Matryoshka Configuration
MATRYOSHKA_TRAINING = True  # Train with dimension dropout
MATRYOSHKA_MIN_DIM = 256  # Minimum dimension for training
MATRYOSHKA_DROPOUT_SCHEDULE = [0.0, 0.1, 0.2, 0.3]  # Dropout per level

# Model Context Windows
MODEL_CONTEXT_WINDOWS = {
    PHI_4: 131072,  # 128K
    QWEN_25_7B: 32768,  # 32K
    QWEN_25_3B: 32768,  # 32K
    MISTRAL_NEMO: 131072,  # 128K
}
