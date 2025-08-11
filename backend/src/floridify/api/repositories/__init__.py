"""Repository implementations for data models."""

from .audio_repository import AudioCreate, AudioFilter, AudioRepository, AudioUpdate

# corpus_repository removed - using corpus_manager directly
from .definition_repository import (
    DefinitionCreate,
    DefinitionFilter,
    DefinitionRepository,
    DefinitionUpdate,
)
from .example_repository import (
    ExampleCreate,
    ExampleFilter,
    ExampleRepository,
    ExampleUpdate,
)
from .fact_repository import FactCreate, FactFilter, FactRepository, FactUpdate
from .image_repository import ImageCreate, ImageFilter, ImageRepository, ImageUpdate
from .synthesis_repository import (
    SynthesisCreate,
    SynthesisFilter,
    SynthesisRepository,
    SynthesisUpdate,
)
from .word_repository import WordCreate, WordFilter, WordRepository, WordUpdate
from .wordlist_repository import (
    StudySessionRequest,
    WordAddRequest,
    WordListCreate,
    WordListFilter,
    WordListRepository,
    WordListUpdate,
    WordReviewRequest,
)

__all__ = [
    "WordRepository",
    "WordCreate",
    "WordUpdate",
    "WordFilter",
    "DefinitionRepository",
    "DefinitionCreate",
    "DefinitionUpdate",
    "DefinitionFilter",
    "ExampleRepository",
    "ExampleCreate",
    "ExampleUpdate",
    "ExampleFilter",
    "FactRepository",
    "FactCreate",
    "FactUpdate",
    "FactFilter",
    "SynthesisRepository",
    "SynthesisCreate",
    "SynthesisUpdate",
    "SynthesisFilter",
    "WordListRepository",
    "WordListCreate",
    "WordListUpdate",
    "WordListFilter",
    "WordAddRequest",
    "WordReviewRequest",
    "StudySessionRequest",
    # "CorpusRepository" removed
    "ImageRepository",
    "ImageCreate",
    "ImageUpdate",
    "ImageFilter",
    "AudioRepository",
    "AudioCreate",
    "AudioUpdate",
    "AudioFilter",
]
