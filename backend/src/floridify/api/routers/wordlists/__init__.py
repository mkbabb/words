"""WordLists router module."""

from .main import router as main_router
from .reviews import router as reviews_router
from .words import router as words_router

__all__ = ["main_router", "words_router", "reviews_router"]
