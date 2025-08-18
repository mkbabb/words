"""Data models for Floridify dictionary entries."""

# Base models and metadata

# Word of the Day models
# Corpus models
from ..corpus.models import CorpusType
from ..wordlist.word_of_the_day import (
    NotificationFrequency,
    WordOfTheDayBatch,
    WordOfTheDayConfig,
    WordOfTheDayEntry,
)

# Base models for language and other constants
from .base import AIResponseBase, AudioMedia, BaseMetadata, ImageMedia, Language, ModelInfo

# Core models from definition.py (includes constants)
from .dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Etymology,
    Example,
    Fact,
    LiteratureSourceExample,
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

# Versioned models - removed to avoid circular import
# DictionaryEntryMetadata is in providers.dictionary.models

__all__ = [
    # Base models
    "BaseMetadata",
    "Etymology",
    "ImageMedia",
    "AudioMedia",
    "ModelInfo",
    "AIResponseBase",
    # Core documents
    "Word",
    "Definition",
    "Example",
    "Fact",
    "Pronunciation",
    "DictionaryEntry",
    "LiteratureSourceExample",
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
    "CorpusType",
    # Versioned models - removed to avoid circular import
    # "DictionaryEntryMetadata",  # Available in providers.dictionary.models
]
