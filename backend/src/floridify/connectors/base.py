"""Base connector interface for dictionary providers with versioning support."""

from __future__ import annotations

import asyncio
import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ..core.state_tracker import StateTracker
from ..models import ProviderData, Word
from ..models.definition import DictionaryProvider
from ..models.provider import (
    BatchOperation,
    ProviderVersion,
    VersionedProviderData,
)
from ..utils.logging import get_logger
from .config import VersionConfig

logger = get_logger(__name__)


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
        # Backward compatibility parameters
        force_api: bool | None = None,
        version: str | None = None,
        save_versioned: bool | None = None,
        increment_version: bool | None = None,
    ) -> ProviderData | None:
        """Unified fetch with optional versioning support.
        
        Args:
            word_obj: The word to look up
            state_tracker: Optional state tracker for progress updates
            version_config: Configuration for versioning behavior
            force_api: (Deprecated) Use version_config instead
            version: (Deprecated) Use version_config instead
            save_versioned: (Deprecated) Use version_config instead
            increment_version: (Deprecated) Use version_config instead
            
        Returns:
            ProviderData containing definitions, pronunciation, and etymology
        """
        # Handle backward compatibility - if old parameters are provided, create config from them
        if version_config is None:
            if any(param is not None for param in [force_api, version, save_versioned, increment_version]):
                # Old-style call with individual parameters
                version_config = VersionConfig(
                    force_api=force_api if force_api is not None else False,
                    version=version,
                    save_versioned=save_versioned if save_versioned is not None else True,
                    increment_version=increment_version if increment_version is not None else True,
                )
            else:
                # Use default config
                version_config = VersionConfig()
        # If specific version requested, fetch from versioned storage
        if version_config.version and not version_config.force_api:
            try:
                versioned = await VersionedProviderData.find_one(
                    {
                        "word_id": word_obj.id,
                        "provider": self.provider_name,
                        "version_info.provider_version": version_config.version,
                    }
                )
                if versioned:
                    # Convert versioned data back to ProviderData
                    return self._versioned_to_provider_data(versioned)
                logger.warning(f"Version {version_config.version} not found for {word_obj.text}")
                return None
            except Exception as e:
                logger.debug(f"Database not available for version lookup: {e}")
                # Continue to fresh API call
        
        # Check for existing versioned data unless forcing API call
        if not version_config.force_api and version_config.save_versioned:
            try:
                existing = await VersionedProviderData.find_one(
                    {
                        "word_id": word_obj.id,
                        "provider": self.provider_name,
                        "version_info.is_latest": True,
                    }
                )
                if existing:
                    logger.debug(f"Using existing versioned data for {word_obj.text} from {self.provider_name}")
                    return self._versioned_to_provider_data(existing)
            except Exception as e:
                logger.debug(f"Database not available for versioned data lookup: {e}")
                # Continue to fresh API call
        
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
                    await self._save_versioned(
                        word_obj,
                        provider_data,
                        version_config.increment_version,
                        start_time,
                    )
                except Exception as e:
                    logger.debug(f"Could not save versioned data (database unavailable): {e}")
                    # Continue without saving - data is still returned
            
            return provider_data
            
        except Exception as e:
            logger.error(f"Error fetching from {self.provider_name}: {e}")
            
            # Store error in versioned data if enabled
            if version_config.save_versioned:
                try:
                    await self._save_error_versioned(word_obj, e)
                except Exception as save_error:
                    logger.debug(f"Could not save error data (database unavailable): {save_error}")
            
            return None
    
    @abstractmethod
    async def _fetch_from_provider(
        self,
        word_obj: Word,
        state_tracker: StateTracker | None = None,
    ) -> ProviderData | None:
        """Actual implementation of provider fetch logic.
        
        This method should be implemented by each concrete connector.
        
        Args:
            word_obj: The word to look up
            state_tracker: Optional state tracker
            
        Returns:
            ProviderData or None
        """
        pass

    def _compute_data_hash(self, data: dict[str, Any]) -> str:
        """Compute a hash of the data for deduplication."""
        # Sort keys for consistent hashing
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode()).hexdigest()

    async def _save_versioned(
        self,
        word_obj: Word,
        provider_data: ProviderData,
        increment_version: bool,
        start_time: datetime,
    ) -> VersionedProviderData:
        """Save provider data to versioned storage.
        
        Args:
            word_obj: Word object
            provider_data: Provider data to save
            increment_version: Whether to increment version number
            start_time: When the fetch started (for timing)
            
        Returns:
            Saved VersionedProviderData
        """
        # Convert to dict for hashing and storage
        raw_data = provider_data.model_dump(mode="json")
        data_hash = self._compute_data_hash(raw_data)
        
        # Check if this exact data already exists
        duplicate = await VersionedProviderData.find_one(
            {"version_info.data_hash": data_hash}
        )
        if duplicate:
            logger.debug(f"Data already exists (hash match) for {word_obj.text}")
            return duplicate
        
        # Get current version if incrementing
        current_version = self.provider_version
        if increment_version:
            latest = await VersionedProviderData.find_one(
                {
                    "word_id": word_obj.id,
                    "provider": self.provider_name,
                    "version_info.is_latest": True,
                }
            )
            if latest:
                # Parse and increment version
                try:
                    parts = latest.version_info.provider_version.split(".")
                    if len(parts) == 3:  # Semantic versioning
                        parts[2] = str(int(parts[2]) + 1)
                        current_version = ".".join(parts)
                    else:
                        # Simple increment
                        current_version = str(float(latest.version_info.provider_version) + 0.1)
                except (ValueError, AttributeError):
                    current_version = self.provider_version
        
        # Create versioned data entry
        if not word_obj.id:
            raise ValueError(f"Word {word_obj.text} must be saved before versioning")
        
        versioned_data = VersionedProviderData(
            word_id=word_obj.id,
            word_text=word_obj.text,
            language=word_obj.language,
            provider=self.provider_name,
            version_info=ProviderVersion(
                provider_version=current_version,
                schema_version=self.schema_version,
                data_hash=data_hash,
                is_latest=True,
            ),
            raw_data=raw_data,
            provider_metadata={
                "fetch_time_ms": int((datetime.now(UTC) - start_time).total_seconds() * 1000),
                "rate_limit": self.rate_limit,
            },
        )
        
        await versioned_data.save()
        logger.info(f"Saved versioned data v{current_version} for {word_obj.text} from {self.provider_name}")
        return versioned_data
    
    async def _save_error_versioned(
        self,
        word_obj: Word,
        error: Exception,
    ) -> None:
        """Save error to versioned storage for tracking.
        
        Args:
            word_obj: Word that failed
            error: The exception that occurred
        """
        try:
            if not word_obj.id:
                logger.warning(f"Cannot save error for unsaved word {word_obj.text}")
                return
            
            error_data = VersionedProviderData(
                word_id=word_obj.id,
                word_text=word_obj.text,
                language=word_obj.language,
                provider=self.provider_name,
                version_info=ProviderVersion(
                    provider_version="error",
                    schema_version=self.schema_version,
                    data_hash=f"error_{datetime.now(UTC).isoformat()}",
                    is_latest=False,  # Don't mark errors as latest
                ),
                raw_data={},
                error=str(error),
                error_code=getattr(error, "code", None),
            )
            await error_data.save()
        except Exception as save_error:
            logger.error(f"Failed to save error data: {save_error}")
    
    def _versioned_to_provider_data(self, versioned: VersionedProviderData) -> ProviderData | None:
        """Convert VersionedProviderData back to ProviderData.
        
        Args:
            versioned: Versioned provider data
            
        Returns:
            ProviderData or None if conversion fails
        """
        try:
            if versioned.raw_data:
                # Reconstruct ProviderData from raw_data
                return ProviderData(**versioned.raw_data)
            return None
        except Exception as e:
            logger.error(f"Failed to convert versioned data: {e}")
            return None
    
    # Backward compatibility - keep fetch_with_versioning as alias
    async def fetch_with_versioning(
        self,
        word_obj: Word,
        state_tracker: StateTracker | None = None,
        force_fetch: bool = False,
    ) -> VersionedProviderData | None:
        """Backward compatible method that returns VersionedProviderData.
        
        This is maintained for backward compatibility.
        Use fetch_definition with VersionConfig instead.
        """
        config = VersionConfig(
            force_api=force_fetch,
            save_versioned=True,
        )
        result = await self.fetch_definition(
            word_obj,
            state_tracker,
            version_config=config,
        )
        
        if result:
            # Get the versioned data that was just saved
            return await VersionedProviderData.find_one(
                {
                    "word_id": word_obj.id,
                    "provider": self.provider_name,
                    "version_info.is_latest": True,
                }
            )
        return None


class BatchConnector(DictionaryConnector):
    """Base class for connectors that support batch operations."""
    
    @abstractmethod
    async def batch_fetch(
        self,
        words: list[Word],
        batch_operation: BatchOperation | None = None,
    ) -> list[VersionedProviderData]:
        """Fetch definitions for multiple words in batch.
        
        Args:
            words: List of words to fetch
            batch_operation: Optional batch operation for tracking
            
        Returns:
            List of versioned provider data
        """
        pass


class BulkDownloadConnector(DictionaryConnector):
    """Base class for connectors that support bulk data downloads."""
    
    @abstractmethod
    async def download_bulk_data(
        self,
        output_path: str,
        batch_operation: BatchOperation | None = None,
    ) -> bool:
        """Download bulk data from the provider.
        
        Args:
            output_path: Path to save the downloaded data
            batch_operation: Optional batch operation for tracking
            
        Returns:
            True if download was successful
        """
        pass
    
    @abstractmethod
    async def import_bulk_data(
        self,
        data_path: str,
        batch_operation: BatchOperation | None = None,
    ) -> int:
        """Import bulk data into versioned storage.
        
        Args:
            data_path: Path to the bulk data file
            batch_operation: Optional batch operation for tracking
            
        Returns:
            Number of items imported
        """
        pass
