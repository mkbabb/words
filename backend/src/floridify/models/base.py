"""Base models and utilities for dictionary data."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


def objectid_json_serializer(obj: ObjectId | PydanticObjectId) -> str:
    """High-performance ObjectId serializer for Pydantic v2."""
    return str(obj)


class BaseMetadata(BaseModel):
    """Standard metadata for entities requiring CRUD tracking."""
    
    model_config = ConfigDict(
        # Configure custom JSON serializers for ObjectIds
        json_serializers={
            ObjectId: objectid_json_serializer,
            PydanticObjectId: objectid_json_serializer,
        },
        # Performance optimizations
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        use_enum_values=True
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1, ge=1)


class DocumentWithObjectIdSupport(Document, BaseMetadata):
    """Base class for all Beanie Document models with proper ObjectId serialization."""
    
    model_config = ConfigDict(
        # Ensure ObjectId serializers are properly inherited for Beanie Documents
        json_serializers={
            ObjectId: objectid_json_serializer,
            PydanticObjectId: objectid_json_serializer,
        },
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        use_enum_values=True
    )


class ModelInfo(BaseModel):
    """AI model metadata for synthesized content."""

    name: str  # e.g., "gpt-4o", "gpt-3.5-turbo"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    temperature: float = Field(ge=0.0, le=2.0, default=0.7)
    generation_count: int = Field(default=1, ge=1)  # Times regenerated
    last_generated: datetime = Field(default_factory=datetime.utcnow)


class ImageMedia(DocumentWithObjectIdSupport):
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


class AudioMedia(DocumentWithObjectIdSupport):
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
