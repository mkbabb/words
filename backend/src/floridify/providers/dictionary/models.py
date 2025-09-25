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

    class Metadata(BaseVersionedData):
        """Minimal dictionary metadata for versioning."""

        resource_type: ResourceType = ResourceType.DICTIONARY
        namespace: CacheNamespace = CacheNamespace.DICTIONARY
