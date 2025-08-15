"""Unified base classes for dictionary and literature providers."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from ..core.state_tracker import StateTracker
from ..models import Word
from ..models.dictionary import DictionaryProvider, DictionaryProviderData
from ..models.versioned import DictionaryVersionedData, StorageType
from ..utils.logging import get_logger
from .batch import BatchOperation

logger = get_logger(__name__)


class VersionConfig(BaseModel):
    """Configuration for versioned fetching behavior."""
    
    force_api: bool = Field(default=False, description="Force API call even if versioned data exists")
    version: str | None = Field(default=None, description="Fetch specific version from storage")
    save_versioned: bool = Field(default=True, description="Save API results to versioned storage")
    increment_version: bool = Field(default=True, description="Auto-increment version when saving")
    
    class Config:
        """Pydantic configuration."""
        frozen = True  # Make immutable


class DictionaryConnector(ABC):
    """Abstract base class for dictionary API connectors."""

    def __init__(self, rate_limit: float = 1.0) -> None:
        """Initialize connector with rate limiting.

        Args:
            rate_limit: Maximum requests per second
        """
        self.rate_limit = rate_limit
        self._rate_limiter = asyncio.Semaphore(1)
        self._last_request_time = 0.0
        self.progress_callback: Callable[[str, float, dict[str, Any]], None] | None = None

    @property
    @abstractmethod
    def provider_name(self) -> DictionaryProvider:
        """Name of the dictionary provider."""
        pass

    @property
    def provider_version(self) -> str:
        """Version of the provider implementation."""
        return "1.0.0"

    @property
    def schema_version(self) -> str:
        """Version of the data schema."""
        return "1.0"

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        async with self._rate_limiter:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self._last_request_time
            min_interval = 1.0 / self.rate_limit

            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {self.provider_name}")
                await asyncio.sleep(wait_time)

            self._last_request_time = asyncio.get_event_loop().time()

    async def fetch_definition(
        self,
        word_obj: Word,
        state_tracker: StateTracker | None = None,
        version_config: VersionConfig | None = None,
    ) -> DictionaryProviderData | None:
        """Unified fetch with optional versioning support.
        
        Args:
            word_obj: The word to look up
            state_tracker: Optional state tracker for progress updates
            version_config: Configuration for versioning behavior
            
        Returns:
            DictionaryProviderData containing definitions, pronunciation, and etymology
        """
        # Use default config if none provided
        if version_config is None:
            version_config = VersionConfig()
            
        # Initialize versioning manager (import here to avoid circular import)
        from ..caching.versioned import VersionedDataManager
        manager = VersionedDataManager[DictionaryVersionedData]()
        resource_id = f"{self.provider_name}_{word_obj.text}_{word_obj.language}"
        
        # Check for existing versioned data unless forcing API call
        if not version_config.force_api:
            try:
                existing = await manager.get_latest(
                    resource_id=resource_id,
                    resource_type="dictionary"
                )
                if existing:
                    content = await manager.get_content(existing)
                    if content:
                        logger.debug(f"Using existing versioned data for {word_obj.text} from {self.provider_name}")
                        return DictionaryProviderData(**content)
            except Exception as e:
                logger.debug(f"Could not retrieve versioned data: {e}")
        
        # Fetch from provider API
        start_time = datetime.now(UTC)
        try:
            # Call the actual implementation in child class
            provider_data = await self._fetch_from_provider(word_obj, state_tracker)
            
            if not provider_data:
                return None
            
            # Save to versioned storage if enabled
            if version_config.save_versioned:
                try:
                    raw_data = provider_data.model_dump(mode="json")
                    await manager.save(
                        resource_id=resource_id,
                        content=raw_data,
                        storage_type=StorageType.DATABASE,
                        metadata={
                            "word_id": str(word_obj.id) if word_obj.id else None,
                            "word_text": word_obj.text,
                            "provider_name": str(self.provider_name),
                            "language": str(word_obj.language),
                            "fetch_time_ms": int((datetime.now(UTC) - start_time).total_seconds() * 1000),
                        }
                    )
                except Exception as e:
                    logger.debug(f"Could not save versioned data: {e}")
            
            return provider_data
            
        except Exception as e:
            logger.error(f"Error fetching from {self.provider_name}: {e}")
            return None
    
    @abstractmethod
    async def _fetch_from_provider(
        self,
        word_obj: Word,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryProviderData | None:
        """Actual implementation of provider fetch logic.
        
        This method should be implemented by each concrete connector.
        
        Args:
            word_obj: The word to look up
            state_tracker: Optional state tracker
            
        Returns:
            DictionaryProviderData or None
        """
        pass





class LiteratureProvider(ABC):
    """Abstract base class for literature providers."""

    def __init__(self, rate_limit: float = 1.0) -> None:
        """Initialize provider with rate limiting.

        Args:
            rate_limit: Maximum requests per second
        """
        self.rate_limit = rate_limit
        self._rate_limiter = asyncio.Semaphore(1)
        self._last_request_time = 0.0

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the literature provider."""
        pass

    @property
    def provider_version(self) -> str:
        """Version of the provider implementation."""
        return "1.0.0"

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        async with self._rate_limiter:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self._last_request_time
            min_interval = 1.0 / self.rate_limit

            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {self.provider_name}")
                await asyncio.sleep(wait_time)

            self._last_request_time = asyncio.get_event_loop().time()

    @abstractmethod
    async def download_work(
        self,
        source_id: str,
        title: str | None = None,
        author_name: str | None = None,
        state_tracker: StateTracker | None = None,
    ) -> Any:
        """Download a literary work."""
        pass

    @abstractmethod
    async def search_works(
        self,
        author_name: str | None = None,
        title: str | None = None,
        subject: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search for works by criteria."""
        pass


class BatchConnector(DictionaryConnector):
    """Base class for connectors that support batch operations."""
    
    @abstractmethod
    async def batch_fetch(
        self,
        words: list[Word],
        batch_operation: BatchOperation | None = None,
    ) -> list[DictionaryProviderData]:
        """Fetch definitions for multiple words in batch."""
        pass


class BulkDownloadConnector(DictionaryConnector):
    """Base class for connectors that support bulk data downloads."""
    
    @abstractmethod
    async def download_bulk_data(
        self,
        output_path: str,
        batch_operation: BatchOperation | None = None,
    ) -> bool:
        """Download bulk data from the provider."""
        pass
    
    @abstractmethod
    async def import_bulk_data(
        self,
        data_path: str,
        batch_operation: BatchOperation | None = None,
    ) -> int:
        """Import bulk data into versioned storage."""
        pass