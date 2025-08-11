"""WOTD training and model constants."""

from typing import Literal

# Embedding Models - Independent WOTD configuration
EmbeddingModel = Literal["BAAI/bge-m3", "sentence-transformers/all-MiniLM-L6-v2"]

# BGE-M3: 1024D, 100+ languages, cross-lingual support
BGE_M3_MODEL: EmbeddingModel = "BAAI/bge-m3"
MINI_LM_MODEL: EmbeddingModel = "sentence-transformers/all-MiniLM-L6-v2"

# Model dimensions mapping
MODEL_DIMENSIONS = {
    BGE_M3_MODEL: 1024,
    MINI_LM_MODEL: 384,
}

# Default embedding model - BGE-M3 for multilingual and semantic richness
DEFAULT_EMBEDDING_MODEL: EmbeddingModel = BGE_M3_MODEL
DEFAULT_EMBEDDING_DIM = MODEL_DIMENSIONS[BGE_M3_MODEL]  # 1024

# Language Models for DSL generation
LanguageModel = Literal["microsoft/Phi-3.5-mini-instruct", "microsoft/Phi-3-mini-instruct"]
DEFAULT_LANGUAGE_MODEL: LanguageModel = "microsoft/Phi-3.5-mini-instruct"

# Training Corpus Configuration
DEFAULT_WORDS_PER_CORPUS = 100  # Words per semantic corpus
DEFAULT_NUM_CORPORA = 12        # Total corpora for complete coverage
MIN_CORPUS_SIZE = 25            # Minimum viable corpus size
MAX_CORPUS_SIZE = 500           # Maximum efficient corpus size

# BGE Embedding Configuration
NORMALIZE_EMBEDDINGS = True     # L2 normalization for similarity
EMBEDDING_BATCH_SIZE = 32       # BGE-M3 optimal batch size
EMBEDDING_DEVICE = "cpu"        # Default to CPU for reliability

# Semantic Encoder (RVQ) Configuration
RVQ_NUM_LEVELS = 4              # Residual quantization levels
RVQ_CODEBOOK_SIZE = 32          # Codebook size per level
RVQ_ENCODER_EPOCHS = 200        # Training epochs for RVQ
RVQ_ENCODER_LR = 1e-3           # Learning rate for RVQ

# Language Model (LoRA) Configuration  
LM_MAX_LENGTH = 512             # Maximum sequence length
LM_EPOCHS = 10                  # Fine-tuning epochs
LM_LEARNING_RATE = 2e-5         # LoRA learning rate
LORA_RANK = 16                  # LoRA rank (adaptation dimension)
LORA_ALPHA = 32                 # LoRA scaling parameter
LORA_DROPOUT = 0.1              # LoRA dropout rate

# Semantic ID System
SEMANTIC_ID_DIMENSIONS = 4      # [style, complexity, era, variation]
MAX_SEMANTIC_VARIATIONS = 8     # Maximum variations per style/complexity/era

# Training Performance
DEFAULT_BATCH_SIZE = 16         # Default training batch size
GRADIENT_ACCUMULATION = 2       # Steps before optimizer update
WARMUP_RATIO = 0.1              # Learning rate warmup ratio
WEIGHT_DECAY = 0.01             # L2 regularization

# File Extensions
MODEL_EXTENSION = ".pt"         # PyTorch model extension
CONFIG_EXTENSION = ".json"      # Configuration file extension
CHECKPOINT_EXTENSION = ".ckpt"  # Training checkpoint extension

# Memory Optimization
USE_GRADIENT_CHECKPOINTING = True  # Trade compute for memory
ENABLE_MIXED_PRECISION = True      # FP16 training
DATALOADER_WORKERS = 4             # Parallel data loading
PIN_MEMORY = True                  # Pin memory for GPU transfer