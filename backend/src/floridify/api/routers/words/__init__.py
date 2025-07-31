"""Words router module."""

from .definitions import router as definitions_router
from .entries import router as entries_router
from .examples import router as examples_router
from .facts import router as facts_router
from .main import router as main_router
from .word_of_the_day import router as word_of_the_day_router

__all__ = [
    "main_router",
    "definitions_router",
    "entries_router",
    "examples_router",
    "facts_router",
    "word_of_the_day_router",
]
