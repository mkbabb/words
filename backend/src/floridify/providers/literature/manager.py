"""Literature provider manager with unified versioning."""

from __future__ import annotations

from datetime import timedelta

from ...caching.models import CacheTTL
from ...caching.manager import BaseManager
from ...core.constants import ResourceType
from ...caching.versioned import VersionConfig, VersionedDataManager, get_literature_version_manager
from ...models.versioned import LiteratureVersionedData
from ...utils.logging import get_logger
from .api.gutenberg import GutenbergConnector
from .api.internet_archive import InternetArchiveConnector
from .base import LiteratureConnector
from .models import LiteratureMetadata, LiteratureSource

logger = get_logger(__name__)


class LiteratureProviderManager(BaseManager[LiteratureMetadata, LiteratureMetadata]):
    """Unified manager for literature providers with versioning support."""

    def __init__(self) -> None:
        """Initialize the literature provider manager."""
        super().__init__()

    @property
    def resource_type(self) -> ResourceType:
        """Get the resource type this manager handles."""
        return ResourceType.LITERATURE

    @property
    def default_cache_ttl(self) -> timedelta | None:
        """Get default cache TTL for literature operations."""
        return CacheTTL.CORPUS

    def _get_version_manager(self) -> VersionedDataManager[LiteratureVersionedData]:
        """Get the version manager for literature data."""
        return get_literature_version_manager()

    async def _reconstruct_resource(
        self, versioned_data: LiteratureVersionedData
    ) -> LiteratureMetadata | None:
        """Reconstruct literature metadata from versioned data."""
        try:
            if versioned_data.content_inline:
                content = versioned_data.content_inline
            elif versioned_data.content_location:
                # Load content from storage
                version_manager = self._get_version_manager()
                content = await version_manager.load_content(versioned_data.content_location)
            else:
                return None

            if content:
                metadata_dict = content.get("metadata", {})
                if metadata_dict:
                    return LiteratureMetadata(**metadata_dict)
            return None
        except Exception:
            return None

    def _get_provider_connector(self, provider: LiteratureSource) -> LiteratureConnector | None:
        """Get a connector instance for the given literature provider."""
        provider_classes = {
            LiteratureSource.GUTENBERG: GutenbergConnector,
            LiteratureSource.INTERNET_ARCHIVE: InternetArchiveConnector,
        }

        connector_class = provider_classes.get(provider)
        if not connector_class:
            logger.warning(f"No connector class found for literature provider: {provider.value}")
            return None

        try:
            return connector_class()
        except Exception as e:
            logger.warning(f"Failed to initialize {provider.value}: {e}")
            return None

    async def get_or_create_work(
        self,
        source_id: str,
        provider: LiteratureSource,
        use_ttl: bool = True,
    ) -> LiteratureMetadata | None:
        """Get existing work or download new one.

        Args:
            source_id: Provider-specific work ID
            provider: The provider to use
            use_ttl: Whether to use TTL for caching

        Returns:
            Literature metadata or None

        """
        connector = self._get_provider_connector(provider)
        if not connector:
            logger.error(f"Provider {provider.value} not available")
            return None

        resource_id = f"{provider.value}:{source_id}"

        # Try to get from base manager first
        cached_metadata = await self.get(resource_id, use_ttl)
        if cached_metadata:
            logger.debug(f"Using cached version for {resource_id}")
            return cached_metadata

        # Download from provider
        try:
            metadata = await connector.download_work(source_id)

            if metadata:
                # Configure versioning with TTL
                config = VersionConfig(
                    save_versions=True,
                    ttl=CacheTTL.CORPUS if use_ttl else None,
                )

                # Save to versioned storage
                content = {
                    "metadata": metadata.model_dump(),
                    "text": metadata.text if metadata.text else None,
                }

                version_manager = self._get_version_manager()
                await version_manager.save(
                    resource_id=resource_id,
                    content=content,
                    resource_type=self.resource_type.value,
                    metadata={
                        "source": provider.value,
                        "source_id": source_id,
                        "title": metadata.title,
                        "author": metadata.author.name if metadata.author else None,
                    },
                    tags=[provider.value, "literature"],
                    config=config,
                    source_id=source_id,
                    title=metadata.title,
                    author_name=metadata.author.name if metadata.author else "Unknown",
                    source=provider.value,
                )

                # Cache the metadata
                self._cache[resource_id] = metadata

            return metadata

        except Exception as e:
            logger.error(f"Failed to download {source_id} from {provider.value}: {e}")
            return None

    async def get_or_create(
        self,
        resource_id: str,
        use_ttl: bool = True,
    ) -> LiteratureMetadata | None:
        """Simplified get or create method.

        Args:
            resource_id: The resource identifier (format: provider:source_id)
            use_ttl: Whether to use TTL for caching

        Returns:
            Literature metadata or None

        """
        return await self.get(resource_id, use_ttl)

    async def cleanup_versions(
        self,
        source_id: str | None = None,
        provider: LiteratureSource | None = None,
        keep_count: int = 3,
    ) -> int:
        """Clean up old versions of literature works.

        Args:
            source_id: Optional work ID to clean up
            provider: Optional provider to clean up
            keep_count: Number of versions to keep

        Returns:
            Total number of versions deleted

        """
        if source_id and provider:
            resource_id = f"{provider.value}:{source_id}"
            return await super().cleanup_versions(resource_id, keep_count)
        logger.info("Full cleanup not yet implemented")
        return 0


# Global manager instance
_literature_manager: LiteratureProviderManager | None = None


def get_literature_manager() -> LiteratureProviderManager:
    """Get the global literature provider manager instance."""
    global _literature_manager
    if _literature_manager is None:
        _literature_manager = LiteratureProviderManager()
    return _literature_manager
