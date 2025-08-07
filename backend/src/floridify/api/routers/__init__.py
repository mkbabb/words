"""API routers."""

# Import sub-modules
from .ai import main_router as ai, suggestions_router as suggestions
from .batch import router as batch

# corpus router disabled - using corpus_manager directly
from .health import router as health
from .lookup import router as lookup
from .media import audio_router as audio, images_router as images
from .search import router as search
from .wordlists import (
    main_router as wordlists,
    reviews_router as wordlist_reviews,
    search_router as wordlist_search,
    words_router as wordlist_words,
)
from .words import (
    definitions_router as definitions,
    examples_router as examples,
    facts_router as facts,
    main_router as words,
    word_of_the_day_router as word_of_the_day,
)

__all__ = [
    "ai",
    "audio",
    "batch",
    # "corpus" disabled
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
    "wordlist_search",
    "wordlist_words",
    "wordlists",
    "words",
]
