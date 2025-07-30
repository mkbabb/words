"""Media router module."""

from .images import router as images_router
from .audio import router as audio_router

__all__ = ["images_router", "audio_router"]