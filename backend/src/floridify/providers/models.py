"""Base models for provider system.

Provides the VersionedData hierarchy and common models.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from beanie import Document
from pydantic import Field

from ..models.base import BaseMetadata
from ..models.definition import Language


class StorageType(str, Enum):
    """Storage types for content."""
    
    CACHE = "cache"
    DISK = "disk"
    MEMORY = "memory"


class ContentLocation(BaseMetadata):
    """Location of content storage."""
    
    storage_type: StorageType = StorageType.CACHE
    cache_namespace: str | None = None
    cache_key: str | None = None
    file_path: str | None = None
    content_type: str = "json"  # json, text, binary
    compression_type: str | None = None
    size_bytes: int | None = None


class VersionedData(Document, BaseMetadata):
    """Base class for versioned data storage."""
    
    # Core identification
    resource_id: str = Field(description="Unique identifier for the resource")
    resource_type: str = Field(description="Type: word, literary_work, etc.")
    language: Language = Field(default=Language.ENGLISH)
    
    # Provider information
    provider_type: str  # 'dictionary' or 'literature'
    provider_name: str
    provider_version: str = "1.0.0"
    
    # Versioning (simplified)
    data_hash: str = Field(description="Content hash for deduplication")
    is_latest: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Content storage
    content_location: ContentLocation
    
    # Unified metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    # Status
    error: str | None = None
    
    class Settings:
        name = "versioned_data"
        indexes = [
            "resource_id",
            "resource_type",
            "provider_type",
            "provider_name",
            "data_hash",
            "is_latest",
            [("resource_id", 1), ("provider_name", 1), ("is_latest", -1)],
        ]
        
    async def mark_as_old(self) -> None:
        """Mark this version as not latest."""
        self.is_latest = False
        await self.save()