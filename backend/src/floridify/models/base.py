"""Base models and utilities for dictionary data."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field, field_serializer

# Explicitly export PydanticObjectId for use in other modules
__all__ = ["AIResponseBase", "BaseMetadata", "ModelInfo", "PydanticObjectId"]


class Language(Enum):
    """Supported languages with ISO codes."""

    ENGLISH = "en"
    FRENCH = "fr"
    SPANISH = "es"
    GERMAN = "de"
    ITALIAN = "it"


class BaseMetadata(BaseModel):
    """Standard metadata for entities requiring CRUD tracking."""

    model_config = ConfigDict(
        # Performance optimizations
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = Field(default=1, ge=1)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat()

    def mark_updated(self) -> None:
        """Update the timestamp and increment version."""
        self.updated_at = datetime.now(UTC)
        self.version += 1


class AccessTrackingMixin(BaseModel):
    """Mixin for entities that need access tracking functionality."""

    # Access tracking
    last_accessed: datetime | None = Field(
        default=None,
        description="Last time accessed",
    )
    access_count: int = Field(default=0, ge=0, description="Number of times accessed")

    def mark_accessed(self) -> None:
        """Mark entity as accessed."""
        self.last_accessed = datetime.now(UTC)
        self.access_count += 1
        # Also mark as updated if this entity has that method (mixin may be used standalone)
        if hasattr(self, "mark_updated"):
            self.mark_updated()


class BaseMetadataWithAccess(BaseMetadata, AccessTrackingMixin):
    """Base metadata with access tracking for entities that need both."""


class AIResponseBase(BaseModel):
    """Base class for AI response models with confidence tracking."""

    confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Model confidence in this response (0.0-1.0)",
    )


class ModelInfo(BaseModel):
    """AI model metadata for synthesized content."""

    name: str  # e.g., "gpt-4o", "gpt-3.5-turbo"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    temperature: float = Field(ge=0.0, le=2.0, default=0.7)
    max_tokens: int | None = None  # Max tokens for generation
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)  # Nucleus sampling
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    generation_count: int = Field(default=1, ge=1)  # Times regenerated
    prompt_tokens: int | None = None  # Tokens in prompt
    completion_tokens: int | None = None  # Tokens in completion
    total_tokens: int | None = None  # Total tokens used
    response_time_ms: int | None = None  # Response time in milliseconds
    last_generated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OperationType(str, Enum):
    """Classification of edit operations for audit trail."""

    AI_SYNTHESIS = "ai_synthesis"
    MANUAL_EDIT = "manual_edit"
    PROVIDER_REFRESH = "provider_refresh"
    ROLLBACK = "rollback"
    COMPONENT_REGENERATION = "component_regeneration"
    AUTO_CORRECT = "auto_correct"
    IMPORT = "import"


class FieldChange(BaseModel):
    """A single field-level change within a version."""

    field_path: str  # e.g., "etymology.text", "definitions[0].text"
    change_type: Literal["added", "removed", "modified"] = "modified"
    old_value: str | None = None  # String summary of old value (truncated for large values)
    new_value: str | None = None  # String summary of new value (truncated for large values)


class SynthesisAuditEntry(BaseModel):
    """Audit trail for AI synthesis operations."""

    model_name: str  # e.g., "gpt-5-mini"
    model_tier: str | None = None  # "high", "medium", "low"
    components_enhanced: list[str] = Field(default_factory=list)  # SynthesisComponent values
    total_tokens: int | None = None
    response_time_ms: int | None = None
    source_providers: list[str] = Field(default_factory=list)  # Provider names used
    definitions_input: int = 0  # Definitions from providers
    definitions_output: int = 0  # Definitions after synthesis
    dedup_removed: int = 0  # Duplicates removed
    clusters_created: int = 0


class EditMetadata(BaseModel):
    """Who/when/why metadata for a version change."""

    user_id: str | None = None  # Clerk user_id from JWT
    username: str | None = None  # Display name for UI
    operation_type: OperationType = OperationType.MANUAL_EDIT
    change_reason: str | None = None  # Free-text commit message
    field_changes: list[FieldChange] = Field(default_factory=list)
    synthesis_audit: SynthesisAuditEntry | None = None  # Present for AI operations


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
    word: str | None = None  # The word this audio is for
    language: str | None = None  # ISO language code (en, fr, es, etc.)

    class Settings:
        name = "audio_media"
        indexes = [
            [("word", 1), ("language", 1)],
        ]


# Explicit exports
__all__ = [
    "AIResponseBase",
    "AudioMedia",
    "BaseMetadata",
    "EditMetadata",
    "FieldChange",
    "ImageMedia",
    "Language",
    "ModelInfo",
    "OperationType",
    "SynthesisAuditEntry",
]
