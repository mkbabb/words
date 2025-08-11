"""Word of the Day (WOTD) router module."""

from .main import router as main_router
from .ml import router as ml_router

__all__ = [
    "main_router",
    "ml_router",
]
