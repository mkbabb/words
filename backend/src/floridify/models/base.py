"""Base models and utilities for dictionary data."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from beanie import Document
from pydantic import BaseModel, Field


class BaseMetadata(BaseModel):
    """Standard metadata for entities requiring CRUD tracking."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1, ge=1)


class ModelInfo(BaseModel):
    """AI model metadata for synthesized content."""

    name: str  # e.g., "gpt-4o", "gpt-3.5-turbo"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    temperature: float = Field(ge=0.0, le=2.0, default=0.7)
    generation_count: int = Field(default=1, ge=1)  # Times regenerated
    last_generated: datetime = Field(default_factory=datetime.utcnow)


class ImageMedia(BaseMetadata):
    """Image media storage."""

    url: str
    format: str  # png, jpg, webp
    size_bytes: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    alt_text: str | None = None


class AudioMedia(Document, BaseMetadata):
    """Audio media storage."""

    url: str
    format: str  # mp3, wav, ogg
    size_bytes: int = Field(gt=0)
    duration_ms: int = Field(gt=0)
    accent: str | None = None  # us, uk, au
    quality: Literal["low", "standard", "high"] = "standard"

    class Settings:
        name = "audio_media"


class Etymology(BaseModel):
    """Word origin information."""

    text: str  # e.g., "Latin 'florere' meaning 'to flower'"
    origin_language: str | None = None  # e.g., "Latin", "Greek"
    root_words: list[str] = Field(default_factory=list)
    first_known_use: str | None = None  # e.g., "14th century"
