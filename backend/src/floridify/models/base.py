"""Base models and utilities for dictionary data."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field


class BaseMetadata(BaseModel):
    """Standard metadata for entities requiring CRUD tracking."""

    model_config = ConfigDict(
        # Performance optimizations
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        use_enum_values=True,
        # JSON serialization configuration
        json_encoders={
            datetime: lambda v: v.isoformat(),
            PydanticObjectId: str,
            UUID: str,
            Path: str,
            bytes: lambda v: base64.b64encode(v).decode("utf-8"),
        },
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = Field(default=1, ge=1)

    def mark_updated(self) -> None:
        """Update the timestamp and increment version."""
        self.updated_at = datetime.now(UTC)
        self.version += 1


class AccessTrackingMixin(BaseModel):
    """Mixin for entities that need access tracking functionality."""

    # Access tracking
    last_accessed: datetime | None = Field(default=None, description="Last time accessed")
    access_count: int = Field(default=0, ge=0, description="Number of times accessed")

    def mark_accessed(self) -> None:
        """Mark entity as accessed."""
        self.last_accessed = datetime.now(UTC)
        self.access_count += 1
        # Also mark as updated if this entity has that capability
        if hasattr(self, "mark_updated"):
            self.mark_updated()


class BaseMetadataWithAccess(BaseMetadata, AccessTrackingMixin):
    """Base metadata with access tracking for entities that need both."""

    pass


class ModelInfo(BaseModel):
    """AI model metadata for synthesized content."""

    name: str  # e.g., "gpt-4o", "gpt-3.5-turbo"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    temperature: float = Field(ge=0.0, le=2.0, default=0.7)
    generation_count: int = Field(default=1, ge=1)  # Times regenerated
    last_generated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ImageMedia(Document, BaseMetadata):
    """Image media storage."""

    url: str | None = None  # Optional URL for external images
    data: bytes | None = None  # Binary image data stored in MongoDB
    format: str  # png, jpg, webp
    size_bytes: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    alt_text: str | None = None
    description: str | None = None  # Additional description for hover/tooltip

    class Settings:
        name = "image_media"


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
