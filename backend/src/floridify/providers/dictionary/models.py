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

        def __init__(self, **data: Any) -> None:
            import hashlib
            import json
            from datetime import datetime

            from ...caching.models import VersionInfo
            
            data.setdefault("resource_type", ResourceType.DICTIONARY)
            data.setdefault("namespace", CacheNamespace.DICTIONARY)
            
            # Create default version_info if not provided
            if "version_info" not in data:
                # Generate data hash from content
                content_str = json.dumps(data.get("content_inline", {}), sort_keys=True, default=str)
                data_hash = hashlib.sha256(content_str.encode()).hexdigest()
                
                data["version_info"] = VersionInfo(
                    version="1",
                    created_at=datetime.utcnow(),
                    data_hash=data_hash,
                    is_latest=True
                )
            
            super().__init__(**data)
