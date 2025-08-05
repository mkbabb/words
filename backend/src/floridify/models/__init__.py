"""Data models for Floridify dictionary entries."""

# Base models and metadata
from ..search.corpus.semantic_cache import (
    IndexType,
    QuantizationType,
    SemanticIndexCache,
)

# Cache models
from ..search.models import (
    CompressionType,
    CorpusCacheEntry,
    CorpusCompressionUtils,
    CorpusData,
)

# Word of the Day models
from ..wordlist.word_of_the_day import (
    NotificationFrequency,
    WordOfTheDayBatch,
    WordOfTheDayConfig,
    WordOfTheDayEntry,
)
from .base import AudioMedia, BaseMetadata, Etymology, ImageMedia, ModelInfo

# Core models from definition.py (includes constants)
from .definition import (
    CorpusType,
    Definition,
    DictionaryProvider,
    Example,
    Fact,
    Language,
    LiteratureSource,
    LiteratureSourceType,
    OutputFormat,
    Pronunciation,
    ProviderData,
    SynthesizedDictionaryEntry,
    Word,
)

# Relationship and supplementary models
from .relationships import (
    Collocation,
    GrammarPattern,
    MeaningCluster,
    UsageNote,
    WordForm,
    WordRelationship,
)

__all__ = [
    # Base models
    "BaseMetadata",
    "Etymology",
    "ImageMedia",
    "AudioMedia",
    "ModelInfo",
    # Core documents
    "Word",
    "Definition",
    "Example",
    "Fact",
    "Pronunciation",
    "ProviderData",
    "SynthesizedDictionaryEntry",
    "LiteratureSource",
    # Relationships
    "WordForm",
    "GrammarPattern",
    "Collocation",
    "UsageNote",
    "MeaningCluster",
    "WordRelationship",
    # Word of the Day
    "NotificationFrequency",
    "WordOfTheDayBatch",
    "WordOfTheDayConfig",
    "WordOfTheDayEntry",
    # Cache models
    "CompressionType",
    "CorpusData",
    "CorpusCacheEntry",
    "CorpusCompressionUtils",
    "IndexType",
    "QuantizationType",
    "SemanticIndexCache",
    # Constants
    "Language",
    "DictionaryProvider",
    "OutputFormat",
    "CorpusType",
    "LiteratureSourceType",
]
