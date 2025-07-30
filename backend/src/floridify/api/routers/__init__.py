"""API routers."""

# Import sub-modules
from .ai import main_router as ai
from .ai import suggestions_router as suggestions
from .batch import router as batch
from .corpus import router as corpus
from .health import router as health
from .lookup import router as lookup
from .media import audio_router as audio
from .media import images_router as images
from .search import router as search
from .wordlists import (
    main_router as wordlists,
)
from .wordlists import (
    reviews_router as wordlist_reviews,
)
from .wordlists import (
    words_router as wordlist_words,
)
from .words import (
    definitions_router as definitions,
)
from .words import (
    examples_router as examples,
)
from .words import (
    facts_router as facts,
)
from .words import (
    main_router as words,
)
from .words import (
    word_of_the_day_router as word_of_the_day,
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
