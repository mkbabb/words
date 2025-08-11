# WOTD ML Pipeline - Semantic Preference Learning

**Word of the Day Machine Learning System**: Learns user preferences through semantic ID compression and DSL generation.

## Architecture Overview

**Pipeline**: Synthetic Corpus → BGE Embeddings → Semantic Encoder → DSL Fine-tuning → Inference
**Goal**: Convert user word preferences into semantic IDs for personalized word generation

## Four-Stage Training Pipeline

### Stage 1: Synthetic Corpus Generation
- **Input**: Style/Complexity/Era combinations
- **Process**: OpenAI generates semantically coherent word collections
- **Output**: 12 corpora × 100 words = 1200 training words
- **Purpose**: Create diverse, balanced training data

### Stage 2: BGE Embedding Extraction  
- **Input**: Word collections from Stage 1
- **Process**: BAAI/bge-m3 model creates 1024D preference vectors
- **Output**: Dense embeddings representing semantic preferences
- **Purpose**: Convert words to numerical preference space

### Stage 3: Semantic Encoder Training
- **Input**: 1024D preference vectors from Stage 2
- **Process**: Residual Vector Quantization (RVQ) compresses to 4-tuple IDs
- **Output**: Semantic IDs `[style, complexity, era, variation]`
- **Purpose**: Discrete semantic space for efficient preference matching

### Stage 4: DSL Fine-tuning
- **Input**: Semantic IDs and corpus mappings from Stage 3
- **Process**: LoRA fine-tuning of Phi-3.5 for DSL generation
- **Output**: Model that generates words from semantic ID patterns
- **Purpose**: Convert semantic preferences back to natural language

## Key Components

### Semantic ID System
- **Format**: `(style: int, complexity: int, era: int, variation: int)`  
- **Range**: Each dimension 0-31 (5 bits × 4 = 20-bit preference space)
- **Compression**: 1024D → 4D discrete representation
- **Reversibility**: IDs can reconstruct preference vectors via codebook lookup
- **Authorship**: Influences training data generation but not semantic ID dimensions

### Preference Vector Architecture
- **Model**: BAAI/bge-m3 (matches semantic search for consistency)
- **Dimension**: 1024D dense vectors
- **Normalization**: L2 normalized for cosine similarity
- **Caching**: Unified cache system for performance

### Training Components

1. **`SyntheticGenerator`**: OpenAI-powered corpus creation
2. **`BGEEmbedder`**: Embedding extraction and caching  
3. **`SemanticEncoder`**: RVQ-based preference compression
4. **`DSLTrainer`**: LoRA fine-tuning for generation
5. **`WOTDTrainer`**: Orchestrates complete pipeline

## Usage Patterns

### Training
```python
config = TrainingConfig()  # Uses constants for reproducibility
trainer = WOTDTrainer(config)
results = await trainer.train_complete_pipeline()
```

### Inference
```python
semantic_id = (2, 1, 3, 0)  # Classical, beautiful, modernist
words = await generate_words_from_id(semantic_id)
```

### Storage
- **Cache**: Embeddings and semantic IDs (unified system)
- **MongoDB**: Persistent corpora and training results
- **Models**: PyTorch checkpoints for deployment

## Performance Characteristics

- **Training Time**: ~10 minutes on CPU (1200 words)
- **Memory Usage**: <2GB peak (BGE + RVQ + LoRA)
- **Inference Speed**: <100ms per word generation
- **Storage**: ~50MB models + ~10MB corpora cache

## Dependencies

- **BGE-M3**: 1024D multilingual embeddings
- **Phi-3.5**: Microsoft's efficient language model  
- **PyTorch**: Deep learning framework
- **OpenAI API**: Synthetic corpus generation
- **MongoDB**: Persistent storage
- **FAISS**: Optional similarity search acceleration