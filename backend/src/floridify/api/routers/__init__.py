"""API routers."""

from .batch import router as batch
from .corpus import router as corpus
from .health import router as health
from .lookup import router as lookup
from .search import router as search

# Import sub-modules
from .ai import main_router as ai, suggestions_router as suggestions
from .media import images_router as images, audio_router as audio
from .words import (
    main_router as words,
    definitions_router as definitions,
    examples_router as examples,
    facts_router as facts,
    word_of_the_day_router as word_of_the_day,
)
from .wordlists import (
    main_router as wordlists,
    words_router as wordlist_words,
    reviews_router as wordlist_reviews,
)

__all__ = [
    "ai",
    "audio",
    "batch",
    "corpus",
    "definitions",
    "examples",
    "facts",
    "health",
    "images",
    "lookup",
    "search",
    "suggestions",
    "word_of_the_day",
    "wordlist_reviews",
    "wordlist_words",
    "wordlists",
    "words",
]