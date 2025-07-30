"""AI router module."""

from .main import router as main_router
from .suggestions import router as suggestions_router

__all__ = ["main_router", "suggestions_router"]