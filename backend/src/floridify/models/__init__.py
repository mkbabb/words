"""Data models for Floridify dictionary entries."""

# Base models and metadata
from .base import AudioMedia, BaseMetadata, Etymology, ImageMedia, ModelInfo

# Constants
from .constants import LiteratureSourceType
from .models import (
    Definition as LegacyDefinition,
)

# Legacy models (kept temporarily for migration)
from .models import (
    DictionaryEntry as LegacyDictionaryEntry,
)
from .models import (
    Examples as LegacyExamples,
)
from .models import (
    GeneratedExample as LegacyGeneratedExample,
)
from .models import (
    LiteratureExample as LegacyLiteratureExample,
)
from .models import (
    LiteratureSource as LegacyLiteratureSource,
)
from .models import (
    Pronunciation as LegacyPronunciation,
)
from .models import (
    ProviderData as LegacyProviderData,
)
from .models import (
    SynthesizedDictionaryEntry as LegacySynthesizedDictionaryEntry,
)

# Core document models
from .models_v2 import (
    Definition,
    Example,
    Fact,
    LiteratureSource,
    Pronunciation,
    ProviderData,
    SynthesizedDictionaryEntry,
    Word,
)

# Phrasal expressions
from .phrasal import PhrasalExpression

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
    "PhrasalExpression",
    # Constants
    "LiteratureSourceType",
    # Legacy (for migration)
    "LegacyDictionaryEntry",
    "LegacyDefinition",
    "LegacyExamples",
    "LegacyGeneratedExample",
    "LegacyLiteratureExample",
    "LegacyLiteratureSource",
    "LegacyPronunciation",
    "LegacyProviderData",
    "LegacySynthesizedDictionaryEntry",
]
