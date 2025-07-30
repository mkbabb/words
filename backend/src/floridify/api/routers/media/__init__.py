"""Media router module."""

from .audio import router as audio_router
from .images import router as images_router

__all__ = ["images_router", "audio_router"]
