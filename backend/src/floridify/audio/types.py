"""Shared audio synthesis types."""

from __future__ import annotations

from pydantic import BaseModel


class TTSResult(BaseModel):
    """Lightweight result from TTS synthesis (no MongoDB dependency)."""

    url: str
    format: str
    size_bytes: int
    duration_ms: int
    accent: str | None = None
    quality: str = "standard"
