"""Literature-specific connector base class."""

from __future__ import annotations

import hashlib
from abc import abstractmethod
from typing import Any

from ...caching.unified import get_unified
from ...caching.core import CacheNamespace
from ...core.state_tracker import StateTracker
from ...models.definition import Language
from ...utils.logging import get_logger
from ..connector import BaseConnector, ConnectorConfig, ProviderType
from ..models import ContentLocation, StorageType
from .models import AuthorInfo, LiteratureMetadata, LiteratureSource
from .versioned import VersionedLiteratureData

logger = get_logger(__name__)


class LiteratureConnector(BaseConnector):
    """Base class for literature providers."""
    
    def __init__(
        self,
        source: LiteratureSource,
        config: ConnectorConfig | None = None,
    ):
        super().__init__(
            provider_type=ProviderType.LITERATURE,
            provider_name=source.value,
            config=config,
        )
        self.source = source
        
    async def download_work(
        self,
        source_id: str,
        title: str | None = None,
        author_name: str | None = None,
        state_tracker: StateTracker | None = None,
    ) -> LiteratureMetadata | None:
        """Download a literary work with versioning support."""
        
        logger.info(f"📚 Downloading {self.source.value} work {source_id}")
        
        # Check for existing data
        if not self.config.force_refresh:
            existing = await self._get_existing_work(source_id)
            if existing:
                logger.debug(f"Using existing data for {source_id}")
                return existing
                
        # Enforce rate limiting
        await self._enforce_rate_limit()
        
        try:
            # Fetch metadata and content
            metadata = await self._fetch_work_metadata(source_id, title, author_name)
            if not metadata:
                logger.warning(f"No metadata found for {source_id}")
                return None
                
            content = await self._fetch_work_content(source_id, metadata)
            if not content:
                logger.warning(f"No content found for {source_id}")
                return None
                
            # Validate content
            if not self._validate_content(content):
                logger.warning(f"Content validation failed for {source_id}")
                return None
                
            # Create and save metadata
            literature_metadata = await self._create_and_save_metadata(
                source_id=source_id,
                metadata=metadata,
                content=content,
            )
            
            logger.info(
                f"✅ Downloaded '{literature_metadata.title}' "
                f"({literature_metadata.quality_metrics.word_count:,} words)"
            )
            
            return literature_metadata
            
        except Exception as e:
            logger.error(f"Error downloading {source_id}: {e}")
            if state_tracker:
                await state_tracker.update_error(
                    error=f"Error from {self.provider_name}: {e}",
                    stage=f"DOWNLOAD_{self.provider_name.upper()}",
                )
            return None
            
    @abstractmethod
    async def _fetch_work_metadata(
        self,
        source_id: str,
        title: str | None = None,
        author_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Fetch metadata for a work from the provider.
        
        Must be implemented by subclasses.
        """
        pass
        
    @abstractmethod
    async def _fetch_work_content(
        self,
        source_id: str,
        metadata: dict[str, Any],
    ) -> str | None:
        """Fetch text content for a work.
        
        Must be implemented by subclasses.
        """
        pass
        
    async def _get_existing_work(self, source_id: str) -> LiteratureMetadata | None:
        """Get existing work from storage."""
        
        # Check MongoDB first
        existing = await LiteratureMetadata.find_one({
            "source_id": source_id,
            "source": self.source,
        })
        
        if existing:
            return existing
            
        # Check versioned storage
        versioned = await VersionedLiteratureData.find_one({
            "source_id": source_id,
            "provider_name": self.provider_name,
            "is_latest": True,
        })
        
        if versioned:
            # Reconstruct metadata from versioned data
            return await self._reconstruct_metadata(versioned)
            
        return None
        
    def _validate_content(self, text: str, min_length: int = 500) -> bool:
        """Validate text content quality."""
        if not text or len(text.strip()) < min_length:
            return False
            
        # Check printable ratio
        printable_ratio = sum(1 for c in text if c.isprintable()) / len(text)
        return printable_ratio >= 0.8
        
    async def _create_and_save_metadata(
        self,
        source_id: str,
        metadata: dict[str, Any],
        content: str,
    ) -> LiteratureMetadata:
        """Create metadata and save content."""
        
        # Calculate hash
        text_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Save content to permanent storage
        cache = await get_unified()
        cache_key = f"work_{source_id}_{text_hash[:8]}"
        
        # Use compressed storage for large texts
        await cache.set_compressed(
            namespace=CacheNamespace.CORPUS,
            key=cache_key,
            value={"text": content, "metadata": metadata},
            ttl=None,  # Permanent storage
            tags=[
                f"author:{metadata.get('author', 'unknown')}",
                f"source:{self.source.value}",
            ],
        )
        
        # Create content location
        content_location = ContentLocation(
            storage_type=StorageType.CACHE,
            cache_namespace=CacheNamespace.CORPUS,
            cache_key=cache_key,
            content_type="text",
            compression_type="zlib",
            size_bytes=len(content),
        )
        
        # Create AuthorInfo
        from .models import Genre, Period
        
        author_info = AuthorInfo(
            name=metadata.get("author", "Unknown Author"),
            period=Period(metadata.get("period", "contemporary")),
            primary_genre=Genre(metadata.get("genre", "novel")),
            language=Language(metadata.get("language", "en")),
            birth_year=metadata.get("birth_year"),
            death_year=metadata.get("death_year"),
            nationality=metadata.get("nationality"),
        )
        
        # Create LiteratureMetadata
        literature_metadata = LiteratureMetadata(
            source_id=source_id,
            title=metadata.get("title", f"Work {source_id}"),
            author=author_info,
            source=self.source,
            source_url=metadata.get("source_url"),
            text_hash=text_hash,
            content_location=content_location,
            language=Language(metadata.get("language", "en")),
            publication_year=metadata.get("year"),
            genre=Genre(metadata.get("genre")) if metadata.get("genre") else None,
            period=Period(metadata.get("period")) if metadata.get("period") else None,
        )
        
        # Calculate quality metrics
        literature_metadata.quality_metrics = literature_metadata._calculate_quality_metrics(content)
        literature_metadata.estimated_reading_time_minutes = (
            literature_metadata.quality_metrics.word_count // 200
        )
        
        # Save to MongoDB
        await literature_metadata.save()
        
        # Save versioned data
        if self.config.save_versioned:
            await self._save_versioned_data(literature_metadata, metadata)
            
        return literature_metadata
        
    async def _save_versioned_data(
        self,
        literature_metadata: LiteratureMetadata,
        metadata: dict[str, Any],
    ) -> None:
        """Save versioned data record."""
        
        # Mark old versions as not latest
        await VersionedLiteratureData.find({
            "source_id": literature_metadata.source_id,
            "provider_name": self.provider_name,
            "is_latest": True,
        }).update({"$set": {"is_latest": False}})
        
        # Create versioned record
        versioned = VersionedLiteratureData(
            resource_id=literature_metadata.source_id,
            source_id=literature_metadata.source_id,
            title=literature_metadata.title,
            author_name=literature_metadata.author.name,
            work_id=literature_metadata.id,
            language=literature_metadata.language,
            provider_name=self.provider_name,
            data_hash=literature_metadata.text_hash,
            content_location=literature_metadata.content_location,
            metadata=metadata,
        )
        
        await versioned.save()
        
    async def _reconstruct_metadata(
        self,
        versioned: VersionedLiteratureData,
    ) -> LiteratureMetadata | None:
        """Reconstruct metadata from versioned data."""
        
        # Check if metadata already exists
        existing = await LiteratureMetadata.find_one({"_id": versioned.work_id})
        if existing:
            return existing
            
        # Create new metadata from versioned data
        from .models import Genre, Period
        
        metadata_dict = versioned.metadata or {}
        
        author_info = AuthorInfo(
            name=versioned.author_name,
            period=Period(metadata_dict.get("period", "contemporary")),
            primary_genre=Genre(metadata_dict.get("genre", "novel")),
            language=versioned.language,
        )
        
        literature_metadata = LiteratureMetadata(
            source_id=versioned.source_id,
            title=versioned.title,
            author=author_info,
            source=self.source,
            text_hash=versioned.data_hash,
            content_location=versioned.content_location,
            language=versioned.language,
        )
        
        await literature_metadata.save()
        return literature_metadata
        
    async def fetch(
        self,
        resource_id: str,
        state_tracker: StateTracker | None = None,
        **kwargs: Any,
    ) -> LiteratureMetadata | None:
        """Implementation of abstract fetch method."""
        title = kwargs.get("title")
        author_name = kwargs.get("author_name")
        return await self.download_work(
            source_id=resource_id,
            title=title,
            author_name=author_name,
            state_tracker=state_tracker,
        )