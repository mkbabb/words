# Word-of-the-Day (WOTD) Semantic Encoding Pipeline

## Abstract

The WOTD system implements a sophisticated semantic encoding pipeline that transforms natural language into discrete, interpretable semantic representations. By combining state-of-the-art embedding models with advanced quantization techniques, the system enables controllable text generation through preference vector formulation. This document presents the theoretical foundations and implementation details of the pipeline, designed for senior software engineers with mathematical backgrounds.

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Embedding Architecture](#embedding-architecture)
3. [Semantic Encoding Methods](#semantic-encoding-methods)
4. [Training Pipeline](#training-pipeline)
5. [Mathematical Foundations](#mathematical-foundations)
6. [Implementation Details](#implementation-details)

## Core Concepts

### 1. Semantic Representation Theory

The fundamental premise of this system is that natural language can be decomposed into discrete semantic attributes that capture style, complexity, temporal context, and variation. We represent each word or phrase as a 4-tuple semantic ID:

```
SemanticID = (style, complexity, era, variation)
```

Where each component is a discrete integer value representing:

- **Style** (0-7): Literary genre or register (formal, casual, technical, poetic)
- **Complexity** (0-7): Linguistic sophistication level
- **Era** (0-7): Temporal or cultural context
- **Variation** (0-4): Fine-grained distinctions within the same semantic category

### 2. Preference Vector Formulation

The system generates synthetic training data by sampling from a preference space defined by these semantic attributes. Each preference vector guides the generation of contextually appropriate word lists, creating a self-supervised learning signal for downstream tasks

## Embedding Architecture

### Matryoshka Embeddings

Matryoshka embeddings (Kusupati et al., 2022) are hierarchical representations where information is organized by importance in decreasing dimensions. Like Russian nesting dolls, each subset of dimensions forms a complete (though lower-fidelity) representation.

#### Mathematical Foundation

Given an embedding vector **e** ∈ ℝ^d, Matryoshka training ensures that for any truncation dimension m < d:

```
e_m = e[0:m]  # First m dimensions
```

The truncated embedding e_m preserves semantic similarity relationships:

```
sim(e₁[0:m], e₂[0:m]) ≈ sim(e₁, e₂)
```

#### Implementation

```python
def apply_matryoshka(embeddings: torch.Tensor, target_dim: int) -> torch.Tensor:
    """
    Truncates embeddings to target dimension while preserving semantic information.
    The model must be trained with Matryoshka loss for this to be effective.

    After truncation, re-normalization is critical for maintaining cosine similarity.
    """
    truncated = embeddings[..., :target_dim]
    return F.normalize(truncated, p=2, dim=-1)  # L2 normalization
```

### Embedding Modes

#### 1. Full Mode

Uses complete d-dimensional embeddings (typically 4096D for GTE-Qwen2). Maximum fidelity but highest computational cost.

#### 2. Elastic Mode

Leverages Matryoshka properties to use reduced dimensions (e.g., 256D, 512D, 1024D) with minimal performance degradation. Enables dynamic compute-accuracy tradeoffs.

#### 3. Binary Quantization

Reduces each dimension to a single bit through sign function:

```python
binary = sign(embedding) = {+1 if x > 0, -1 if x ≤ 0}
```

**Properties:**

- 32x memory reduction (float32 → 1 bit)
- ~90% similarity preservation for many tasks
- Enables ultra-fast Hamming distance computation

#### 4. INT8 Quantization

Scales embeddings to 8-bit integer range:

```python
scale = 127.0 / max(|embedding|)
quantized = round(embedding * scale).clip(-128, 127)
```

**Properties:**

- 4x memory reduction
- ~98% similarity preservation
- Hardware-accelerated on modern CPUs/GPUs

### L2 Normalization

L2 (Euclidean) normalization transforms vectors to unit length:

```
normalized = v / ||v||₂ = v / sqrt(Σvᵢ²)
```

**Purpose:**

- Makes cosine similarity equivalent to dot product
- Ensures embeddings lie on unit hypersphere
- Stabilizes training and similarity computations
- Critical after Matryoshka truncation to maintain similarity relationships

## Semantic Encoding Methods

### 1. Finite Scalar Quantization (FSQ)

FSQ directly quantizes continuous embeddings into discrete codes without using codebooks. Each dimension is independently quantized to a fixed number of levels.

#### Mathematical Formulation

Given latent vector **z** ∈ ℝ^L and quantization levels **l** = [l₁, l₂, ..., l_L]:

```
For each dimension i:
    scaled_i = (z_i - min_i) / (max_i - min_i)  # Scale to [0, 1]
    quantized_i = round(scaled_i * (l_i - 1))   # Quantize to l_i levels
    dequantized_i = quantized_i / (l_i - 1) * (max_i - min_i) + min_i
```

### 2. Hierarchical Vector Quantization (HVQ)

HVQ performs multi-level quantization, creating a hierarchy of increasingly fine-grained representations.

#### Architecture

```
Level 0: Coarse quantization (8 codes) → Style
Level 1: Medium quantization (8 codes) → Complexity
Level 2: Fine quantization (8 codes)   → Era
Level 3: Ultra-fine (5 codes)          → Variation
```

Each level refines the previous level's representation:

```python
residual_0 = input
for level in range(num_levels):
    quantized_l, index_l = quantize(residual_l)
    residual_{l+1} = residual_l - quantized_l
```

## Training Pipeline

### Stage 1: Synthetic Data Generation

The system generates training corpora by sampling semantic IDs and prompting language models:

```python
def generate_corpus(style: int, complexity: int, era: int, author: str) -> WOTDCorpus:
    """
    Generates word lists matching semantic attributes.

    Process:
    1. Format semantic ID as readable string (e.g., "[3,2,1,0]")
    2. Create contextual prompt with examples
    3. Query LLM (GPT-4/Qwen) for appropriate words
    4. Validate and store results

    The prompt engineering uses few-shot learning with style/complexity/era
    descriptions to guide coherent word generation.
    """
```

**Sampling Strategy:**

- 3 style levels × 2 complexity levels × 2 era levels = 12 combinations
- 100 words per combination = 1200 total training examples
- Optional authorship influence (Shakespeare, Hemingway, etc.) for style variation

### Stage 2: Embedding Extraction

Compute multi-modal embeddings for generated words:

```python
def extract_embeddings(corpus: WOTDCorpus) -> torch.Tensor:
    """
    Encodes words using sentence transformers.

    GTE-Qwen2 uses bi-encoder architecture:
    - Self-attention over token embeddings
    - Mean pooling with attention weights
    - Layer normalization
    - Matryoshka-compatible output

    The model produces 4096-dimensional embeddings that can be
    truncated to smaller dimensions while preserving semantics.
    """
```

**Supported Models:**

- **GTE-Qwen2** (Alibaba): 4096D with Matryoshka support, MTEB score 67.3
- **E5-Multilingual** (Microsoft): 1024D efficient alternative
- **SFR-Embedding-2** (Salesforce): 4096D research model

### Stage 3: Encoder Training

Train the semantic encoder to map embeddings to target semantic IDs:

```python
def train_encoder(embeddings: torch.Tensor, semantic_ids: list[SemanticID]):
    """
    Optimizes encoder parameters to minimize:

    L_total = L_reconstruction + λ₁*L_commitment + λ₂*L_entropy

    Where:
    - L_reconstruction: MSE between input and decoded output
    - L_commitment: Forces encoder output close to quantized values
    - L_entropy: Encourages uniform codebook usage

    FSQ eliminates commitment loss through direct quantization,
    while HVQ uses hierarchical residual learning.
    """
```

**Training Details:**

- Optimizer: AdamW with weight decay 0.01
- Learning rate: 1e-4 with cosine annealing
- Batch size: 32 (gradient accumulation if needed)
- Epochs: 10-20 typically sufficient

### Stage 4: Encoder-Decoder Architecture

The semantic encoder uses a symmetric encoder-decoder structure to learn meaningful representations:

#### Encoder (Projection Network)
```python
self.projection = nn.Sequential(
    nn.Linear(input_dim, 512),       # Compress from embedding space (4096D → 512D)
    nn.LayerNorm(512),               # Normalize activations (stabilizes training) 
    nn.GELU(),                       # Smooth activation (better gradients than ReLU)
    nn.Linear(512, 256),             # Further compression (512D → 256D)
    nn.LayerNorm(256),               # Second normalization layer
    nn.GELU(),                       # Non-linearity
    nn.Linear(256, latent_dim),      # Final projection to semantic space (256D → 4D)
)
```

#### Decoder (Reconstruction Network)
```python
self.decoder = nn.Sequential(
    nn.Linear(latent_dim, 256),      # Project from semantic space (4D → 256D)
    nn.LayerNorm(256),               # Normalize activations
    nn.GELU(),                       # Smooth activation
    nn.Linear(256, 512),             # Expand representation (256D → 512D)
    nn.LayerNorm(512),               # Second normalization
    nn.GELU(),                       # Non-linearity
    nn.Linear(512, input_dim),       # Reconstruct original dimension (512D → 4096D)
)
```

**Architectural Design Principles:**

1. **Symmetric Bottleneck**: The encoder compresses information through progressively smaller dimensions (4096→512→256→4), while the decoder reverses this process (4→256→512→4096).

2. **Information Bottleneck**: The 4D latent space forces the model to learn only the most essential semantic features, discarding noise and redundancy.

3. **Residual-like Flow**: Each layer maintains information flow while adding non-linearity, similar to ResNet but with dimension changes.

**Component Deep Dive:**

1. **Linear Layers**: Affine transformations that learn feature mappings
    ```
    y = Wx + b
    ```
    - W: learnable weight matrix (input_dim × output_dim)
    - b: learnable bias vector (output_dim,)
    - Performs matrix multiplication followed by bias addition

2. **LayerNorm**: Normalizes features across the layer dimension
    ```
    y = γ * (x - μ) / σ + β
    ```
    - μ: mean of features across the layer dimension
    - σ: standard deviation across the layer dimension  
    - γ, β: learned scale and shift parameters
    - **Benefits**: Stabilizes training by preventing internal covariate shift, enables higher learning rates, reduces sensitivity to initialization

3. **GELU (Gaussian Error Linear Unit)**: Smooth activation function
    ```
    GELU(x) = x * Φ(x)  where Φ is the CDF of standard normal
    ```
    - **Approximation**: `x * σ(1.702 * x)` where σ is sigmoid
    - **Properties**: Continuously differentiable, better gradient flow than ReLU, incorporates stochastic regularization
    - **Advantages**: Smoother gradient landscape, better performance in transformer architectures

4. **Progressive Dimensionality Reduction**: 
    ```
    4096D → 512D (8x compression)
    512D → 256D (2x compression) 
    256D → 4D (64x compression)
    Total: 1024x compression ratio
    ```

**Training Dynamics:**

The encoder-decoder is trained end-to-end with reconstruction loss:
```python
reconstruction_loss = MSE(decoder(quantize(encoder(x))), x)
```

The quantization step (FSQ/HVQ) introduces discrete bottleneck while maintaining gradient flow through straight-through estimation.

### Stage 5: Language Model Fine-tuning

Fine-tune language models with semantic control:

```python
def train_language_model(model: AutoModelForCausalLM, data: list[tuple[SemanticID, str]]):
    """
    Conditions generation on semantic IDs using prefix tuning:

    Input: "[style,complexity,era,variation] Generate words: ..."
    Output: "word1, word2, word3, ..."

    Loss: Cross-entropy over token predictions
    Optimization: AdamW with cosine scheduling

    LoRA (Low-Rank Adaptation) reduces trainable parameters by 99%
    while maintaining generation quality.
    """
```

**Supported Models:**

- **Qwen-2.5-7B**: SOTA 7B model, 32K context
- **Phi-4**: 14B reasoning model, 128K context
- **Mistral Nemo**: 12B Apache-licensed, 128K context

## Literature Training Pipeline

### Overview

The literature training mode extends the synthetic data approach by extracting vocabulary from real literary works and augmenting it with AI-generated variations. This provides a foundation in actual language use while maintaining the benefits of controlled synthetic data generation.

### Architecture

```
Literary Texts → Word Extraction → AI Augmentation → Embedding → Semantic Encoding
```

#### Stage 1: Literature Corpus Extraction

```python
async def extract_literature_corpus(author: str) -> WOTDCorpus:
    """
    Extract meaningful vocabulary from literary works:
    
    1. Download texts from Project Gutenberg
    2. Tokenize and filter meaningful words
    3. Apply frequency-based filtering
    4. Remove common/uninteresting words
    5. Create tagged corpus with author metadata
    """
```

**Supported Authors:**
- **Shakespeare**: Complete works, 500+ unique meaningful words
- **Virginia Woolf**: Major novels and essays
- **Extensible**: Framework supports adding new authors

**Filtering Pipeline:**
1. **Tokenization**: Split text into individual words using NLTK
2. **Basic Filtering**: Remove stop words, punctuation, short words (<4 chars)
3. **Frequency Analysis**: Keep words appearing 3-50+ times (goldilocks zone)
4. **Heuristic Filtering**: Remove names, very long compounds, irregular patterns
5. **Semantic Tagging**: Assign style/complexity/era based on author and context

#### Stage 2: AI Augmentation

```python
async def augment_corpus_with_ai(corpus: WOTDCorpus, author: str) -> dict[str, WOTDCorpus]:
    """
    Generate semantic variations using OpenAI connector:
    
    Variations:
    - Style shifts: poetic → formal, dramatic → technical  
    - Complexity: complex → simple, archaic → modern
    - Era transformations: shakespearean → contemporary
    - Thematic variations: maintain essence, change expression
    """
```

**Augmentation Strategy:**
- **Base Corpus**: Original author vocabulary (e.g., Shakespeare's 200 most significant words)
- **Style Variations**: Generate formal, casual, technical variants
- **Complexity Shifts**: Create simplified and sophisticated versions  
- **Era Translations**: Modernize archaic language, contemporize historical terms
- **Result**: 5-8x multiplication of training data with semantic diversity

#### Stage 3: Preference Vector Generation

Literature corpora are embedded using the same pipeline as synthetic data:

```python
preference_vector = embedder.encode_corpus(literature_corpus)
semantic_id = encoder.encode(preference_vector)
```

**Key Differences from Synthetic Training:**
- **Real-world Foundation**: Based on actual literary usage patterns
- **Author Signatures**: Captures distinctive vocabulary characteristics
- **Temporal Grounding**: Reflects genuine historical language evolution
- **AI Enhancement**: Maintains authenticity while adding systematic variations

### Usage Examples

#### CLI Training

```bash
# Train on Shakespeare and Woolf with full models
floridify wotd-ml literature --authors Shakespeare Woolf

# Lightweight local training
floridify wotd-ml literature --authors Shakespeare --lightweight

# Without AI augmentation (pure literature)
floridify wotd-ml literature --no-augment --max-words 100
```

#### Programmatic API

```python
from floridify.wotd.trainer import train_from_literature

# Train with default settings
results = await train_from_literature(
    authors=["Shakespeare", "Woolf"],
    use_lightweight_model=True,
    augment_with_ai=True
)

print(f"Generated {len(results.semantic_ids)} semantic IDs")
print(f"Training completed in {results.duration_seconds:.2f}s")
```

### Semantic ID Interpretation

Literature training generates semantic IDs that capture author-specific characteristics:

```python
# Example output for Shakespeare corpus
shakespeare_semantic_id = (2, 3, 0, 1)  # [poetic, complex, shakespearean, variation_1]

# Example output for Woolf corpus  
woolf_semantic_id = (1, 2, 6, 0)        # [modern, complex, modernist, variation_0]
```

**Interpretation Framework:**
- **Style**: 0=formal, 1=casual, 2=poetic, 3=dramatic, 4=archaic, 5=regional, 6=technical, 7=experimental
- **Complexity**: 0=simple, 1=basic, 2=intermediate, 3=advanced, 4=erudite, 5=ornate, 6=dense, 7=esoteric  
- **Era**: 0=ancient, 1=medieval, 2=renaissance, 3=enlightenment, 4=romantic, 5=victorian, 6=modernist, 7=contemporary
- **Variation**: 0-4 for fine-grained distinctions within categories

### Local Deployment

The literature-trained models can be deployed locally using the lightweight inference server:

```bash
# Start local server with literature models
python -m floridify.wotd.deployment.local --model-dir ./models/wotd/literature_shakespeare_woolf

# Generate words using trained semantic IDs
curl -X POST http://localhost:8888/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "[2,3,0,1] Generate Shakespearean words:", "num_words": 10}'

# Encode new text to semantic IDs
curl -X POST http://localhost:8888/encode \
  -H "Content-Type: application/json" \
  -d '{"text": "thy noble spirit doth shine eternal"}'
```

### Performance Characteristics

**Training Speed:**
- Literature extraction: ~30s per author (cached after first run)
- AI augmentation: ~2-3min per author (5 variations × 30s each)
- Embedding computation: ~1-2min for 1000 words
- Encoder training: ~5-10min for 100 epochs
- **Total**: ~10-15min for Shakespeare + Woolf with augmentation

**Model Performance:**
- **Lightweight Mode**: Uses 384D embeddings (all-MiniLM-L6-v2)
- **Full Mode**: Uses 4096D embeddings (GTE-Qwen2-7B)
- **Memory Usage**: ~500MB (lightweight) to ~2GB (full)
- **Inference Speed**: <50ms per request locally

## Implementation Details

### Configuration

```python
# Embedding Models
GTE_QWEN2_7B = "Alibaba-NLP/gte-Qwen2-7B-instruct"      # 4096D, SOTA
GTE_QWEN2_1B = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"    # 4096D, efficient

# Matryoshka Dimensions
MATRYOSHKA_DIMS = {
    GTE_QWEN2_7B: [256, 512, 768, 1024, 2048, 4096],
    GTE_QWEN2_1B: [256, 512, 768, 1024, 2048, 4096],
}

# FSQ Configuration
FSQ_LEVELS = [8, 8, 8, 5]  # Total: 8*8*8*5 = 2560 unique codes
FSQ_LATENT_DIM = 4          # Matches semantic ID components

# Semantic ID Structure
# (style: 0-7, complexity: 0-7, era: 0-7, variation: 0-4)
# Total preference space: 2560 unique combinations
```

### Core Classes

1. **`Embedder`**: Multi-model embedding extraction
    - Supports GTE-Qwen2, E5, SFR models
    - Implements Matryoshka truncation
    - Binary and INT8 quantization
    - Hierarchical encoding modes

2. **`FSQEncoder`**: Finite Scalar Quantization
    - Direct quantization without codebooks
    - Interpretable semantic ID generation
    - Straight-through gradient estimation

3. **`HierarchicalVQEncoder`**: Multi-level VQ
    - Hierarchical residual quantization
    - Progressive refinement
    - Suitable for complex semantic structures

4. **`WOTDTrainer`**: Training orchestration
    - Manages all pipeline stages
    - Handles data generation, embedding, encoding, fine-tuning
    - Checkpointing and recovery

5. **`DSLTrainer`**: Language model fine-tuning
    - LoRA parameter-efficient training
    - Semantic ID conditioning
    - Custom data collation

### Usage Examples

#### Basic Encoding

```python
from floridify.wotd import UnifiedSemanticEncoder, Embedder
from floridify.wotd.embeddings import EmbeddingMode

# Initialize components
embedder = Embedder(model_name="Alibaba-NLP/gte-Qwen2-1.5B-instruct")
encoder = UnifiedSemanticEncoder(input_dim=4096, encoding_type="fsq")

# Encode text to semantic ID
text = "ephemeral"
embedding = embedder.embed(text, mode=EmbeddingMode.FULL)
semantic_id = encoder.encode(embedding)  # Returns (style, complexity, era, variation)
print(f"Semantic ID for '{text}': {semantic_id}")
```

#### Training Pipeline

```python
from floridify.wotd import WOTDTrainer, TrainingConfig

config = TrainingConfig(
    embedding_model="Alibaba-NLP/gte-Qwen2-1.5B-instruct",
    language_model="Qwen/Qwen2.5-7B-Instruct",
    encoder_type="fsq",
    epochs=10,
    learning_rate=1e-4,
)

trainer = WOTDTrainer(config)
await trainer.train_complete_pipeline()
```

#### Matryoshka Embeddings

```python
# Generate multi-resolution embeddings
hierarchy = await embedder.encode_hierarchical(
    texts=["luminous", "ethereal", "transcendent"],
    hierarchy_dims=[256, 512, 1024, 2048, 4096]
)

# Access different resolutions
coarse_embeddings = hierarchy[256]   # Fast, lower quality
fine_embeddings = hierarchy[4096]    # Slow, highest quality
```

#### CLI Usage

```bash
# Train complete pipeline
floridify wotd-ml train \
    --embedding-model gte-qwen2-1b \
    --language-model qwen-2.5-7b \
    --encoder fsq \
    --epochs 10

# Generate synthetic training data
floridify wotd-ml generate \
    --words 100 \
    --styles 3 \
    --complexities 2

# Benchmark encoding performance
floridify wotd-ml benchmark \
    --samples 1000 \
    --modes full,elastic,binary

# System information
floridify wotd-ml info
```

#### Inference

```python
from floridify.wotd.inference import SemanticGenerator

generator = SemanticGenerator(model_path="path/to/finetuned/model")

# Generate from semantic ID
semantic_id = (2, 1, 3, 0)  # (style=2, complexity=1, era=3, variation=0)
words = await generator.generate_from_id(
    semantic_id,
    num_words=10,
    temperature=0.7
)

# Decode semantic ID meaning
attributes = generator.decode_semantic_id(semantic_id)
# Returns: {"style": "formal", "complexity": "simple", "era": "modern", "variation": "base"}
```

## Mathematical Foundations

### Vector Quantization Objective

The VQ-VAE objective combines reconstruction and commitment losses:

```
L = ||x - decoder(quantize(encoder(x)))||² + β||sg[z] - e||² + γ||z - sg[e]||²
```

Where:

- `sg[]` is the stop-gradient operator (prevents gradient flow)
- `z` is encoder output (continuous latent representation)
- `e` is quantized embedding (discrete codebook entry)
- `β` weights encoder commitment (typically 0.25)
- `γ` weights codebook commitment (typically 1.0)

### Straight-Through Estimator

Enables gradient flow through discrete quantization:

```python
# Forward pass: use quantized values
z_quantized = z + (quantized - z).detach()

# Backward pass: gradients flow through z
# This works because (quantized - z).detach() has zero gradient
```

### Information Bottleneck

The semantic ID acts as an information bottleneck, forcing the model to learn compressed representations:

```
I(X; Z) - βI(Z; Y)
```

Where:

- `I(X; Z)`: Mutual information between input and encoding (minimize)
- `I(Z; Y)`: Mutual information between encoding and target (maximize)
- `β`: Trade-off parameter

## Key Technologies

### Embedding Models

- **GTE-Qwen2** (Alibaba): SOTA 4096D embeddings with elastic dimensions
- **E5-Multilingual** (Microsoft): Efficient 1024D alternative
- **SFR-Embedding-2** (Salesforce): Research option with top MTEB scores

### Language Models

- **Qwen-2.5** (Alibaba): SOTA 7B model, 32K context
- **Phi-4** (Microsoft): 14B reasoning-focused, 128K context
- **Mistral Nemo** (Mistral/NVIDIA): 12B Apache-licensed, 128K context

### Encoding Methods

- **FSQ**: Finite Scalar Quantization for interpretable codes
- **Hierarchical VQ**: Multi-level neural codec approach
- **Matryoshka**: Hierarchical embeddings with dimension dropout

### Infrastructure

- **PyTorch**: Deep learning with quantization support
- **MongoDB + Unified Cache**: Multi-level storage
- **OpenAI API**: Synthetic data generation
- **FAISS**: Accelerated similarity search with PQ/IVF

## Features

### Hierarchical Semantic Encoding

```python
from floridify.wotd.embeddings import get_hierarchy_encoder

encoder = get_hierarchy_encoder()
components = encoder.extract_semantic_components(embedding)
# Returns: {'style': tensor, 'complexity': tensor, 'era': tensor, 'variation': tensor}
```

### Multi-Resolution Embeddings

```python
from floridify.wotd.embeddings import get_embedder

embedder = get_embedder(model_name='Alibaba-NLP/gte-Qwen2-1.5B-instruct')

# Generate embeddings at multiple resolutions
hierarchy = await embedder.encode_hierarchical(
    texts=["example", "words"],
    hierarchy_dims=[256, 512, 1024, 2048, 4096]
)
```

### Binary Quantization for Production

```python
# Enable binary embeddings for 32x speedup
from floridify.wotd.constants import USE_BINARY_EMBEDDINGS
USE_BINARY_EMBEDDINGS = True

# Binary similarity is computed with XOR + popcount
# Retains ~90% accuracy with massive efficiency gains
```

## System Architecture Summary

The WOTD pipeline represents a novel approach to controlled text generation through semantic discretization. By combining:

1. **High-dimensional embeddings** from state-of-the-art models
2. **Matryoshka truncation** for computational efficiency
3. **Finite scalar quantization** for interpretable discrete codes
4. **Synthetic preference-based training** for self-supervision
5. **Conditional language modeling** for controlled generation

The system achieves a balance between representation fidelity, computational efficiency, and generation control, enabling fine-grained semantic manipulation of natural language.

## References

1. Kusupati et al. (2022). "Matryoshka Representation Learning"
2. van den Oord et al. (2017). "Neural Discrete Representation Learning" (VQ-VAE)
3. Mentzer et al. (2023). "Finite Scalar Quantization"
4. Lee et al. (2022). "Autoregressive Image Generation using Residual Quantization"
