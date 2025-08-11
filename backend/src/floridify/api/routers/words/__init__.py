"""Words router module."""

from .definitions import router as definitions_router
from .examples import router as examples_router
from .main import router as main_router
from .ml_word_of_the_day import router as ml_word_of_the_day_router
from .word_of_the_day import router as word_of_the_day_router

__all__ = [
    "main_router",
    "definitions_router",
    "examples_router",
    "word_of_the_day_router",
    "ml_word_of_the_day_router",
]
