"""Words router module."""

from .definitions import router as definitions_router
from .examples import router as examples_router
from .main import router as main_router
from .versions import router as versions_router

__all__ = [
    "definitions_router",
    "examples_router",
    "main_router",
    "versions_router",
]
