"""Unified versioned data storage for all providers.

This module provides versioning capabilities for both dictionary and literature
providers, managing metadata in MongoDB while storing large content on disk.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Any

from beanie import Document, SortDirection
from pydantic import BaseModel, Field

from ..caching.unified import get_unified
from ..models.base import BaseMetadata, PydanticObjectId
from ..models.definition import Language
from ..models.provider import ProviderVersion
from ..utils.logging import get_logger
from ..utils.paths import get_cache_directory

logger = get_logger(__name__)


class ProviderSource(BaseModel):
    """Source information for versioned data."""

    provider_type: str  # 'dictionary' or 'literature'
    provider_name: str  # 'oxford', 'gutenberg', etc.
    source_version: str = "1.0.0"


class ContentLocation(BaseModel):
    """Location information for stored content."""

    storage_type: str  # 'cache', 'disk', 'memory'
    cache_namespace: str | None = None
    cache_key: str | None = None
    file_path: str | None = None
    content_type: str = "json"  # 'json', 'text', 'binary'
    compressed: bool = False


class VersionedData(Document, BaseMetadata):
    """Base class for versioned provider data with flexible storage."""

    # Core identification
    resource_id: str = Field(description="Unique identifier for the resource")
    resource_type: str = Field(description="Type of resource (word, work, etc.)")
    language: Language = Field(default=Language.ENGLISH)

    # Provider information
    source: ProviderSource

    # Versioning
    version_info: ProviderVersion

    # Content location
    content_location: ContentLocation

    # Metadata
    content_metadata: dict[str, Any] = Field(default_factory=dict)
    processing_metadata: dict[str, Any] = Field(default_factory=dict)

    # Status
    error: str | None = None
    error_code: str | None = None

    class Settings:
        name = "versioned_data"
        indexes = [
            [("resource_id", 1)],
            [("source.provider_type", 1), ("source.provider_name", 1)],
            [("version_info.data_hash", 1)],
            [("version_info.is_latest", 1)],
            [("resource_type", 1)],
        ]


class DictionaryVersionedData(VersionedData):
    """Versioned data for dictionary providers."""

    word_id: PydanticObjectId = Field(description="Reference to Word document")
    word_text: str = Field(description="Original word text")

    def __init__(self, **data: Any) -> None:
        data["resource_type"] = "word"
        data["source"] = data.get(
            "source",
            ProviderSource(
                provider_type="dictionary", provider_name=data.get("provider_name", "unknown")
            ),
        )
        super().__init__(**data)


class LiteratureVersionedData(VersionedData):
    """Versioned data for literature providers."""

    work_id: PydanticObjectId | None = Field(None, description="Reference to LiteraryWork document")
    source_id: str = Field(description="Provider-specific source ID")
    title: str = Field(description="Work title")
    author_name: str = Field(description="Author name")

    def __init__(self, **data: Any) -> None:
        data["resource_type"] = "literary_work"
        data["source"] = data.get(
            "source",
            ProviderSource(
                provider_type="literature", provider_name=data.get("provider_name", "unknown")
            ),
        )
        super().__init__(**data)


class VersionedDataManager:
    """Manager for versioned data storage and retrieval."""

    def __init__(self) -> None:
        self.cache_dir = get_cache_directory("versioned_data")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def save_content(
        self,
        content: Any,
        content_type: str = "json",
        use_cache: bool = True,
        use_disk: bool = False,
        namespace: str | None = None,
    ) -> ContentLocation:
        """Save content and return location information."""

        if use_cache:
            # Store in unified cache
            cache_key = f"content_{asyncio.get_event_loop().time()}"
            if namespace:
                cache_key = f"{namespace}_{cache_key}"

            cache = await get_unified()
            async with cache:
                await cache.set(
                    namespace=namespace or "versioned_content",
                    key=cache_key,
                    value=content,
                    ttl=timedelta(hours=168),  # 7 days
                )

            return ContentLocation(
                storage_type="cache",
                cache_namespace=namespace or "versioned_content",
                cache_key=cache_key,
                content_type=content_type,
            )

        elif use_disk:
            # Store on disk
            file_path = self.cache_dir / f"content_{asyncio.get_event_loop().time()}.{content_type}"

            if content_type == "json":
                import json

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
            elif content_type == "text":
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(content))
            else:
                with open(file_path, "wb") as f:
                    f.write(content if isinstance(content, bytes) else str(content).encode())

            return ContentLocation(
                storage_type="disk", file_path=str(file_path), content_type=content_type
            )

        else:
            # Memory storage (temporary)
            return ContentLocation(storage_type="memory", content_type=content_type)

    async def load_content(self, location: ContentLocation) -> Any:
        """Load content from storage location."""

        if location.storage_type == "cache":
            cache = await get_unified()
            async with cache:
                return await cache.get(location.cache_namespace or "versioned_content", location.cache_key or "")

        elif location.storage_type == "disk":
            if not location.file_path:
                logger.warning("No file path provided for disk storage")
                return None
            file_path = Path(location.file_path)
            if not file_path.exists():
                logger.warning(f"Content file not found: {file_path}")
                return None

            if location.content_type == "json":
                import json

                with open(file_path, encoding="utf-8") as f:
                    return json.load(f)
            elif location.content_type == "text":
                with open(file_path, encoding="utf-8") as f:
                    return f.read()
            else:
                with open(file_path, "rb") as f:
                    return f.read()

        else:
            logger.warning("Cannot load content from memory storage")
            return None

    async def save_dictionary_data(
        self,
        word_id: PydanticObjectId,
        word_text: str,
        provider_name: str,
        content: Any,
        version_info: ProviderVersion,
        content_metadata: dict[str, Any] | None = None,
        processing_metadata: dict[str, Any] | None = None,
    ) -> DictionaryVersionedData:
        """Save dictionary provider data."""

        # Save content
        content_location = await self.save_content(
            content=content,
            content_type="json",
            use_cache=True,
            namespace=f"dictionary_{provider_name}",
        )

        # Create versioned data entry
        versioned_data = DictionaryVersionedData(
            resource_id=str(word_id),
            word_id=word_id,
            word_text=word_text,
            source=ProviderSource(provider_type="dictionary", provider_name=provider_name),
            version_info=version_info,
            content_location=content_location,
            content_metadata=content_metadata or {},
            processing_metadata=processing_metadata or {},
        )

        await versioned_data.save()
        logger.info(f"Saved dictionary data for {word_text} from {provider_name}")
        return versioned_data

    async def save_literature_data(
        self,
        source_id: str,
        title: str,
        author_name: str,
        provider_name: str,
        content: Any,
        version_info: ProviderVersion,
        work_id: PydanticObjectId | None = None,
        content_metadata: dict[str, Any] | None = None,
        processing_metadata: dict[str, Any] | None = None,
        use_disk: bool = True,  # Literature content is usually large
    ) -> LiteratureVersionedData:
        """Save literature provider data."""

        # Save content (prefer disk storage for large literature texts)
        content_location = await self.save_content(
            content=content,
            content_type="text",
            use_cache=not use_disk,
            use_disk=use_disk,
            namespace=f"literature_{provider_name}",
        )

        # Create versioned data entry
        versioned_data = LiteratureVersionedData(
            resource_id=source_id,
            source_id=source_id,
            title=title,
            author_name=author_name,
            work_id=work_id,
            source=ProviderSource(provider_type="literature", provider_name=provider_name),
            version_info=version_info,
            content_location=content_location,
            content_metadata=content_metadata or {},
            processing_metadata=processing_metadata or {},
        )

        await versioned_data.save()
        logger.info(f"Saved literature data for '{title}' by {author_name} from {provider_name}")
        return versioned_data

    async def get_latest_data(
        self, resource_id: str, provider_type: str, provider_name: str, include_content: bool = True
    ) -> DictionaryVersionedData | LiteratureVersionedData | None:
        """Get latest versioned data for a resource."""

        versioned_data = await VersionedData.find_one(
            {
                "resource_id": resource_id,
                "source.provider_type": provider_type,
                "source.provider_name": provider_name,
                "version_info.is_latest": True,
            }
        )

        if not versioned_data:
            return None

        # Load content if requested
        if include_content:
            content = await self.load_content(versioned_data.content_location)
            versioned_data.content_metadata["loaded_content"] = content

        return versioned_data

    async def cleanup_old_versions(
        self, resource_id: str, provider_type: str, provider_name: str, keep_versions: int = 5
    ) -> int:
        """Clean up old versions, keeping only the most recent."""

        # Get all versions for this resource
        all_versions = (
            await VersionedData.find(
                {
                    "resource_id": resource_id,
                    "source.provider_type": provider_type,
                    "source.provider_name": provider_name,
                }
            )
            .sort([("version_info.created_at", SortDirection.DESCENDING)])
            .to_list()
        )

        if len(all_versions) <= keep_versions:
            return 0

        # Mark old versions for deletion
        old_versions = all_versions[keep_versions:]
        deleted_count = 0

        for version in old_versions:
            try:
                # Clean up content if stored on disk
                if (
                    version.content_location.storage_type == "disk"
                    and version.content_location.file_path
                ):
                    file_path = Path(version.content_location.file_path)
                    if file_path.exists():
                        file_path.unlink()

                # Delete metadata
                await version.delete()
                deleted_count += 1

            except Exception as e:
                logger.warning(f"Failed to delete old version {version.id}: {e}")

        logger.info(f"Cleaned up {deleted_count} old versions for {resource_id}")
        return deleted_count


# Global manager instance
versioned_manager = VersionedDataManager()
