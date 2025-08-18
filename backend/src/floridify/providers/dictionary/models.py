"""Dictionary provider models."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from pydantic import Field

from ...caching.models import (
    BaseVersionedData,
    CacheNamespace,
    ContentLocation,
    ResourceType,
)
from ...models.base import Language
from ...models.versioned import register_model


@register_model(ResourceType.DICTIONARY)
class DictionaryEntryMetadata(BaseVersionedData):
    """Dictionary entry with versioning support.

    Can represent either raw provider data or AI-synthesized entries.
    Synthesized entries have model_info and source_provider_data_ids populated.
    """

    # Core identification
    word: str
    provider: str
    language: Language = Language.ENGLISH

    # For synthesized entries
    source_provider_data_ids: list[PydanticObjectId] = Field(default_factory=list)
    model_info: dict[str, Any] | None = None  # AI model info for synthesized entries

    # Provider-specific metadata
    provider_metadata: dict[str, Any] = Field(default_factory=dict)

    # Etymology and raw data location (external storage for large content)
    raw_data_location: ContentLocation | None = None

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.DICTIONARY)
        data.setdefault("namespace", CacheNamespace.DICTIONARY)
        super().__init__(**data)

    class Settings:
        pass