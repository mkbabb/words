"""Dictionary provider models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ...caching.models import (
    BaseVersionedData,
    CacheNamespace,
    ResourceType,
)
from ...models.base import Language
from ...models.versioned import register_model


class DictionaryProviderEntry(BaseModel):
    """In-memory representation of a dictionary entry from a provider."""

    # Core identification
    word: str
    provider: str
    language: Language = Language.ENGLISH

    # Content
    definitions: list[dict[str, Any]] = Field(default_factory=list)
    pronunciation: str | None = None
    etymology: str | None = None
    examples: list[str] = Field(default_factory=list)

    # Provider-specific data
    raw_data: dict[str, Any] = Field(default_factory=dict)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)

    @register_model(ResourceType.DICTIONARY)
    class Metadata(BaseVersionedData):
        """Minimal dictionary metadata for versioning."""

        def __init__(self, **data: Any) -> None:
            data.setdefault("resource_type", ResourceType.DICTIONARY)
            data.setdefault("namespace", CacheNamespace.DICTIONARY)
            super().__init__(**data)
