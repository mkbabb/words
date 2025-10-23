"""WOTD core types - semantic preference learning data models.

Key Concepts:
    - Semantic ID: 4-tuple representing [style, complexity, era, variation]
    - Preference Vector: 1024D BGE embedding of user word preferences
    - Corpus: Collection of words with consistent semantic characteristics
    - Training Pipeline: Corpus → Embeddings → RVQ → DSL fine-tuning
    - Authorship: Influences training data generation, not semantic ID dimensions
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from .constants import (
    DEFAULT_EMBEDDING_DIM,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LANGUAGE_MODEL,
    DEFAULT_NUM_CORPORA,
    DEFAULT_WORDS_PER_CORPUS,
    LM_EPOCHS,
    LM_LEARNING_RATE,
    LM_MAX_LENGTH,
    LORA_ALPHA,
    LORA_DROPOUT,
    LORA_RANK,
    NORMALIZE_EMBEDDINGS,
    RVQ_CODEBOOK_SIZE,
    RVQ_ENCODER_EPOCHS,
    RVQ_ENCODER_LR,
    RVQ_NUM_LEVELS,
)


# Core Semantic Categories
class Style(str, Enum):
    CLASSICAL = "classical"
    MODERN = "modern"
    ROMANTIC = "romantic"
    NEUTRAL = "neutral"


class Complexity(str, Enum):
    SIMPLE = "simple"
    BEAUTIFUL = "beautiful"
    COMPLEX = "complex"
    PLAIN = "plain"


class Era(str, Enum):
    SHAKESPEAREAN = "shakespearean"
    VICTORIAN = "victorian"
    MODERNIST = "modernist"
    CONTEMPORARY = "contemporary"


class Author(str, Enum):
    """Classical literature authors organized by period."""

    # Ancient (Homer, Greek tragedians, Roman poets)
    HOMER = "homer"
    SOPHOCLES = "sophocles"
    EURIPIDES = "euripides"
    AESCHYLUS = "aeschylus"
    VIRGIL = "virgil"
    OVID = "ovid"

    # Medieval (Dante, Chaucer, etc.)
    DANTE = "dante"
    CHAUCER = "chaucer"
    BOCCACCIO = "boccaccio"
    PETRARCH = "petrarch"

    # Renaissance (Shakespeare, Cervantes, Montaigne, etc.)
    SHAKESPEARE = "shakespeare"
    CERVANTES = "cervantes"
    MONTAIGNE = "montaigne"
    RABELAIS = "rabelais"
    SPENSER = "spenser"
    MILTON = "milton"

    # Classical to Romantic (Goethe, etc.)
    GOETHE = "goethe"

    # 19th Century (Dickens, Tolstoy, Dumas, etc.)
    DICKENS = "dickens"
    TOLSTOY = "tolstoy"
    DUMAS = "dumas"

    # Modernist (Joyce, Woolf, Proust, etc.)
    JOYCE = "joyce"
    WOOLF = "woolf"
    PROUST = "proust"


# Core Data Types - Semantic Preference System
SemanticID = tuple[
    int,
    int,
    int,
    int,
]  # [style, complexity, era, variation] - 4D discrete preference space


class WOTDWord(BaseModel):
    """Individual word with semantic labels for corpus construction.

    Core unit of semantic preference learning - each word carries
    style/complexity/era labels that define its position in preference space.
    """

    word: str  # Target vocabulary word
    definition: str  # Semantic definition for context
    pos: str  # Part of speech (noun, verb, adj, etc.)
    style: Style  # Aesthetic style classification
    complexity: Complexity  # Linguistic sophistication level
    era: Era  # Historical/literary period
    author: Author | None = None  # Optional literary influence


class WOTDCorpus(BaseModel):
    """Semantically coherent word collection for preference vector extraction.

    Contains ~100 words with consistent semantic characteristics that
    represent a single point in preference space. BGE embeddings of the
    word collection create the preference vector for RVQ compression.
    """

    id: str  # Human-readable identifier
    style: Style  # Dominant aesthetic style
    complexity: Complexity  # Linguistic sophistication
    era: Era  # Historical/literary period
    author: Author | None = None  # Optional literary influence
    words: list[WOTDWord]  # Word collection (~100 words)
    semantic_id: SemanticID | None = None  # Assigned after RVQ compression
    created_at: datetime = Field(default_factory=datetime.now)


class TrainingConfig(BaseModel):
    """WOTD training configuration using constants for reproducibility."""

    # Corpus Generation (Stage 1)
    words_per_corpus: int = DEFAULT_WORDS_PER_CORPUS  # Words per semantic corpus
    num_corpora: int = DEFAULT_NUM_CORPORA  # Total semantic coverage

    # GTE-Qwen2 Embeddings (Stage 2) - SOTA multilingual embeddings
    embedding_model: str = DEFAULT_EMBEDDING_MODEL  # GTE-Qwen2-1.5B for quality
    embedding_dim: int = DEFAULT_EMBEDDING_DIM  # 4096D vectors with Matryoshka
    normalize_embeddings: bool = NORMALIZE_EMBEDDINGS  # L2 normalization

    # Semantic Encoder (Stage 3) - RVQ for preference compression
    num_levels: int = RVQ_NUM_LEVELS  # Residual quantization levels
    codebook_size: int = RVQ_CODEBOOK_SIZE  # Codebook size per level
    encoder_epochs: int = RVQ_ENCODER_EPOCHS  # RVQ training epochs
    encoder_lr: float = RVQ_ENCODER_LR  # RVQ learning rate

    # Language Model (Stage 4) - Phi-3.5 + LoRA fine-tuning
    base_model: str = DEFAULT_LANGUAGE_MODEL  # Microsoft Phi-3.5 mini
    max_length: int = LM_MAX_LENGTH  # Token sequence limit
    lm_epochs: int = LM_EPOCHS  # Fine-tuning epochs
    lm_lr: float = LM_LEARNING_RATE  # LoRA learning rate
    lora_rank: int = LORA_RANK  # Adaptation dimension
    lora_alpha: int = LORA_ALPHA  # LoRA scaling factor
    lora_dropout: float = LORA_DROPOUT  # Regularization


class TrainingResults(BaseModel):
    """Results from training run."""

    config: TrainingConfig
    duration_seconds: float
    num_corpora: int
    total_words: int
    semantic_ids: dict[str, SemanticID]
    model_paths: dict[str, str]
    created_at: datetime = Field(default_factory=datetime.now)


# Cache Keys
class CacheKeys:
    """Unified cache namespace keys."""

    NAMESPACE = "wotd"
    SYNTHETIC_CORPUS = "synthetic_corpus"
    EMBEDDINGS = "embeddings"
    SEMANTIC_IDS = "semantic_ids"
    MODELS = "models"


# MongoDB Collections
class Collections:
    """MongoDB collection names."""

    CORPORA = "wotd_corpora"
    TRAINING_RUNS = "wotd_training_runs"
    SYNTHETIC_DATA = "wotd_synthetic_data"


# Path Constants
class Paths:
    """Common path constants."""

    DEFAULT_MODELS_DIR = "./models/wotd"
    CACHE_DIR = "./cache/wotd"
    OUTPUT_DIR = "./output/wotd"

    # File extensions
    MODEL_EXT = ".pt"
    JSON_EXT = ".json"
    CONFIG_EXT = ".toml"


# Type Aliases - Performance-optimized collections
CorpusDict = dict[str, WOTDCorpus]  # Corpus lookup by ID
EmbeddingDict = dict[str, list[float]]  # 1024D preference vectors by corpus
SemanticIDDict = dict[str, SemanticID]  # 4D compressed IDs by corpus


# DSL Syntax
class DSLPattern(BaseModel):
    """DSL pattern parser for generation."""

    levels: tuple[int | Literal["*"], ...]

    @classmethod
    def parse(cls, pattern: str) -> DSLPattern | None:
        """Parse [0,1,*,2] format."""
        import re

        match = re.match(r"\[([0-9*]),([0-9*]),([0-9*]),([0-9*])\]", pattern)
        if not match:
            return None

        levels: list[int | Literal["*"]] = []
        for group in match.groups():
            levels.append(int(group) if group != "*" else "*")

        return cls(levels=tuple(levels))


# Request/Response for API
class GenerateRequest(BaseModel):
    """Word generation request."""

    prompt: str
    num_words: int = Field(default=10, ge=1, le=50)
    temperature: float = Field(default=0.8, ge=0.1, le=2.0)


class GenerateResponse(BaseModel):
    """Word generation response."""

    words: list[str]
    semantic_id: SemanticID | None
    processing_ms: int
    confidence: float = Field(ge=0.0, le=1.0)
