"""Data models for Floridify dictionary entries."""

# Base models and metadata

# Word of the Day models
from ..wordlist.word_of_the_day import (
    NotificationFrequency,
    WordOfTheDayBatch,
    WordOfTheDayConfig,
    WordOfTheDayEntry,
)
from .base import AudioMedia, BaseMetadata, Etymology, ImageMedia, ModelInfo

# Core models from definition.py (includes constants)
from .dictionary import (
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

# Versioned models
from .versioned import DictionaryEntryMetadata

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
    "DictionaryEntry",
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
    # Constants
    "Language",
    "DictionaryProvider",
    "OutputFormat",
    "CorpusType",
    "LiteratureSourceType",
    # Versioned models
    "DictionaryEntryMetadata",
]
