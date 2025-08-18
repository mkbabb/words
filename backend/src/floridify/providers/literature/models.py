"""Literature metadata models for versioned storage.

This module contains metadata models for literature that integrate with the
versioned data system for proper storage and retrieval.
"""

from __future__ import annotations

from typing import Any

from ...caching.models import (
    BaseVersionedData,
    CacheNamespace,
    ResourceType,
)
from ...models.versioned import register_model


@register_model(ResourceType.LITERATURE)
class LiteratureEntryMetadata(BaseVersionedData):
    """Literature work metadata with external content storage."""

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.LITERATURE)
        data.setdefault("namespace", CacheNamespace.LITERATURE)
        super().__init__(**data)
