"""API routers."""

# Import sub-modules
from .ai import main_router as ai, suggestions_router as suggestions
from .cache import router as cache
from .config import router as config
from .corpus import router as corpus
from .database import router as database
from .health import router as health
from .lookup import router as lookup
from .media import audio_router as audio, images_router as images
from .providers import router as providers
from .search import router as search
from .wordlist import (
    main_router as wordlists,
    reviews_router as wordlist_reviews,
    search_router as wordlist_search,
    words_router as wordlist_words,
)
from .words import (
    definitions_router as definitions,
    examples_router as examples,
    main_router as words,
)

# from .wotd import (
#     main_router as wotd_main,
#     ml_router as wotd_ml,
# )

__all__ = [
    "ai",
    "audio",
    "cache",
    "config",
    "corpus",
    "database",
    "definitions",
    "examples",
    "health",
    "images",
    "lookup",
    "providers",
    "search",
    "suggestions",
    "wordlist_reviews",
    "wordlist_search",
    "wordlist_words",
    "wordlists",
    "words",
    # "wotd_main",
    # "wotd_ml",
]
