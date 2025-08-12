"""Abstract base class for literature providers.

This module provides the base class that all literature connectors inherit from,
with common functionality for downloading, versioning, and storage.
"""

from __future__ import annotations

import hashlib
from abc import abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from ...core.state_tracker import StateTracker
from ...utils.logging import get_logger
from ...utils.scraping import RateLimitConfig
from ...utils.scraping import RateLimitConfig
from .models import AuthorInfo, LiteratureMetadata, LiteratureSource

logger = get_logger(__name__)


class LiteratureConnector:
    """Abstract base class for literature download connectors."""

    def __init__(self, source: LiteratureSource):
        self.source = source

        # Rate limiting configuration with sensible defaults
        self.rate_config = RateLimitConfig(
            base_requests_per_second=1.0,
            min_delay=1.0,
            max_delay=30.0,
            backoff_multiplier=2.0,
            success_speedup=1.05,
            success_threshold=20,
            max_consecutive_errors=3,
        )

    @property
    def provider_name(self) -> str:
        """Provider name based on source."""
        return self.source.value

    @abstractmethod
    async def _fetch_work_metadata(
        self, source_id: str, title: str | None = None, author_name: str | None = None
    ) -> dict[str, Any]:
        """Fetch metadata for a work from the provider.

        Returns:
            Dictionary containing work metadata
        """
        pass

    @abstractmethod
    async def _fetch_work_content(self, source_id: str, metadata: dict[str, Any]) -> str | None:
        """Fetch text content for a work.

        Args:
            source_id: Provider-specific ID
            metadata: Metadata from _fetch_work_metadata

        Returns:
            Full text content or None if not available
        """
        pass

    async def download_work(
        self,
        source_id: str,
        title: str | None = None,
        author_name: str | None = None,
        state_tracker: StateTracker | None = None,
    ) -> LiteratureMetadata | None:
        """Download a literary work with versioning support."""

        logger.info(f"📚 Downloading {self.source.value} work {source_id}")

        # Check for existing data unless forcing refresh
        if not self.config.force_refresh:
            existing = await versioned_manager.get_latest_data(
                resource_id=source_id,
                provider_type="literature",
                provider_name=self.provider_name,
                include_content=False,
            )

            if existing:
                logger.debug(f"Using existing data for {source_id}")
                # Convert to LiteratureMetadata
                return await self._versioned_to_metadata(existing)

        try:
            # Fetch metadata
            work_metadata = await self._fetch_work_metadata(source_id, title, author_name)
            if not work_metadata:
                logger.warning(f"No metadata found for {source_id}")
                return None

            # Fetch content
            text_content = await self._fetch_work_content(source_id, work_metadata)
            if not text_content:
                logger.warning(f"No content found for {source_id}")
                return None

            # Validate content quality
            if not self._validate_content(text_content):
                logger.warning(f"Content quality validation failed for {source_id}")
                return None

            # Create LiteratureMetadata
            literature_metadata = await self._create_metadata(
                source_id=source_id,
                title=work_metadata.get("title", title or f"Work {source_id}"),
                author_name=work_metadata.get("author", author_name or "Unknown Author"),
                metadata_dict=work_metadata,
                text_content=text_content,
            )

            # Save versioned data
            if self.config.save_versioned:
                await self._save_versioned_data(
                    literature_metadata=literature_metadata,
                    text_content=text_content,
                    metadata_dict=work_metadata,
                )

            logger.info(
                f"✅ Downloaded '{literature_metadata.title}' "
                f"({literature_metadata.quality_metrics.word_count:,} words)"
            )

            return literature_metadata

        except Exception as e:
            logger.error(f"Error downloading {source_id}: {e}")
            return None

    async def bulk_download_author(
        self, author_name: str, max_works: int = 10, state_tracker: StateTracker | None = None
    ) -> AsyncGenerator[LiteratureMetadata, None]:
        """Download multiple works by an author."""

        # Search for works
        search_results = await self.search_works(author_name=author_name, limit=max_works)

        downloaded_count = 0
        for work_data in search_results:
            if downloaded_count >= max_works:
                break

            try:
                work = await self.download_work(
                    source_id=work_data["source_id"],
                    title=work_data.get("title"),
                    author_name=work_data.get("author", author_name),
                    state_tracker=state_tracker,
                )

                if work:
                    downloaded_count += 1
                    logger.info(f"📚 Downloaded {downloaded_count}/{max_works}: '{work.title}'")
                    yield work

            except Exception as e:
                logger.error(
                    f"Failed to download {work_data.get('title', work_data['source_id'])}: {e}"
                )
                continue

        logger.info(f"✅ Bulk download complete: {downloaded_count} works by {author_name}")

    def _validate_content(self, text: str, min_length: int = 500) -> bool:
        """Validate text content quality."""
        if not text or len(text.strip()) < min_length:
            return False

        # Check for reasonable character distribution
        printable_ratio = sum(1 for c in text if c.isprintable()) / len(text)
        if printable_ratio < 0.8:
            return False

        return True

    async def _create_metadata(
        self,
        source_id: str,
        title: str,
        author_name: str,
        metadata_dict: dict[str, Any],
        text_content: str,
    ) -> LiteratureMetadata:
        """Create LiteratureMetadata from fetched data."""

        # Create Author object
        author = Author(
            name=author_name,
            period=metadata_dict.get("period", "contemporary"),
            primary_genre=metadata_dict.get("genre", "novel"),
            birth_year=metadata_dict.get("author_birth_year"),
            death_year=metadata_dict.get("author_death_year"),
            nationality=metadata_dict.get("author_nationality"),
        )

        # Calculate content hash
        text_hash = hashlib.sha256(text_content.encode()).hexdigest()

        # Create content location (will be set when saving)
        from ..versioned import ContentLocation

        content_location = ContentLocation(storage_type="memory")

        # Create metadata
        metadata = LiteratureMetadata(
            source_id=source_id,
            title=title,
            author=author,
            source=self.source,
            source_url=metadata_dict.get("source_url"),
            text_hash=text_hash,
            content_location=content_location,
            publication_year=metadata_dict.get("year"),
            genre=metadata_dict.get("genre"),
            period=metadata_dict.get("period"),
            external_ids=metadata_dict.get("external_ids", {}),
        )

        # Calculate and set quality metrics
        metadata.quality_metrics = metadata._calculate_quality_metrics(text_content)
        metadata.estimated_reading_time_minutes = metadata.quality_metrics.word_count // 200

        return metadata

    async def _save_versioned_data(
        self,
        literature_metadata: LiteratureMetadata,
        text_content: str,
        metadata_dict: dict[str, Any],
    ) -> None:
        """Save work data to versioned storage."""

        # Create version info
        version_info = VersionInfo(
            provider_version=self.provider_version,
            schema_version="1.0",
            data_hash=literature_metadata.text_hash,
        )

        # Save to versioned storage
        versioned_data = await versioned_manager.save_literature_data(
            source_id=literature_metadata.source_id,
            title=literature_metadata.title,
            author_name=literature_metadata.author.name,
            provider_name=self.provider_name,
            content=text_content,
            version_info=version_info,
            work_id=literature_metadata.id,
            content_metadata={
                "source_url": literature_metadata.source_url,
                "genre": literature_metadata.genre.value if literature_metadata.genre else None,
                "period": literature_metadata.period.value if literature_metadata.period else None,
                "publication_year": literature_metadata.publication_year,
            },
            processing_metadata={
                "quality_metrics": literature_metadata.quality_metrics.model_dump(),
                "processing_version": literature_metadata.processing_version,
            },
            use_disk=True,
        )

        # Update content location in metadata
        literature_metadata.content_location = versioned_data.content_location
        await literature_metadata.save()

    async def _versioned_to_metadata(self, versioned_data) -> LiteratureMetadata | None:
        """Convert versioned data back to LiteratureMetadata."""
        try:
            # Check if metadata already exists
            existing_metadata = await LiteratureMetadata.find_one(
                {"source_id": versioned_data.source_id, "source": self.source}
            )

            if existing_metadata:
                return existing_metadata

            # Create new metadata from versioned data
            author = Author(
                name=versioned_data.author_name, period="contemporary", primary_genre="novel"
            )

            metadata = LiteratureMetadata(
                source_id=versioned_data.source_id,
                title=versioned_data.title,
                author=author,
                source=self.source,
                text_hash=versioned_data.version_info.data_hash,
                content_location=versioned_data.content_location,
            )

            await metadata.save()
            return metadata

        except Exception as e:
            logger.error(f"Failed to convert versioned data: {e}")
            return None
