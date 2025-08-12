"""Dictionary-specific connector base class."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from beanie import PydanticObjectId

from ...core.state_tracker import StateTracker
from ...models.definition import DictionaryProvider, Language
from ...utils.logging import get_logger
from ..connector import BaseConnector, ConnectorConfig, ProviderType
from ..models import ContentLocation, StorageType
from .models import DictionaryProviderData, VersionedDictionaryData

logger = get_logger(__name__)


class DictionaryConnector(BaseConnector):
    """Base class for dictionary providers."""
    
    def __init__(
        self,
        provider: DictionaryProvider,
        config: ConnectorConfig | None = None,
    ):
        super().__init__(
            provider_type=ProviderType.DICTIONARY,
            provider_name=provider.value,
            config=config,
        )
        self.provider = provider
        
    async def fetch_definition(
        self,
        word: str,
        language: Language = Language.ENGLISH,
        word_id: PydanticObjectId | None = None,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryProviderData | None:
        """Fetch definition with versioning support."""
        
        # Check cache first
        if not self.config.force_refresh:
            cached = await self._get_cached_definition(word, language)
            if cached:
                logger.debug(f"Using cached definition for '{word}'")
                return cached
                
        # Enforce rate limiting
        await self._enforce_rate_limit()
        
        # Fetch from provider
        try:
            provider_data = await self._fetch_from_provider(word, language)
            
            if provider_data and self.config.save_versioned:
                await self._save_versioned_definition(
                    word=word,
                    word_id=word_id,
                    language=language,
                    provider_data=provider_data,
                )
                
            return provider_data
            
        except Exception as e:
            logger.error(f"Error fetching '{word}' from {self.provider_name}: {e}")
            if state_tracker:
                await state_tracker.update_error(
                    error=f"Error from {self.provider_name}: {e}",
                    stage=f"FETCH_{self.provider_name.upper()}",
                )
            return None
            
    @abstractmethod
    async def _fetch_from_provider(
        self,
        word: str,
        language: Language,
    ) -> DictionaryProviderData | None:
        """Fetch definition from the specific provider.
        
        Must be implemented by subclasses.
        """
        pass
        
    async def _get_cached_definition(
        self,
        word: str,
        language: Language,
    ) -> DictionaryProviderData | None:
        """Get definition from cache/versioned storage."""
        
        # Check versioned storage
        versioned = await VersionedDictionaryData.find_one({
            "word_text": word,
            "provider_name": self.provider_name,
            "language": language,
            "is_latest": True,
        })
        
        if versioned and versioned.content_location:
            # Load content from storage
            content = await self._load_versioned_content(versioned.content_location)
            if content:
                return DictionaryProviderData(**content)
                
        return None
        
    async def _save_versioned_definition(
        self,
        word: str,
        word_id: PydanticObjectId | None,
        language: Language,
        provider_data: DictionaryProviderData,
    ) -> None:
        """Save definition to versioned storage."""
        
        # Compute hash
        data_dict = provider_data.model_dump()
        data_hash = self.compute_hash(data_dict)
        
        # Check for existing version with same hash
        existing = await VersionedDictionaryData.find_one({
            "word_text": word,
            "provider_name": self.provider_name,
            "data_hash": data_hash,
        })
        
        if existing:
            logger.debug(f"Definition already exists for '{word}' with same content")
            return
            
        # Mark old versions as not latest
        await VersionedDictionaryData.find({
            "word_text": word,
            "provider_name": self.provider_name,
            "is_latest": True,
        }).update({"$set": {"is_latest": False}})
        
        # Save content to cache
        cache_key = f"{word}_{self.provider_name}_{data_hash[:8]}"
        await self.set_in_cache(cache_key, data_dict, ttl=86400 * 7)  # 7 days
        
        # Create versioned record
        versioned = VersionedDictionaryData(
            resource_id=word,
            word_text=word,
            word_id=word_id,
            language=language,
            provider_name=self.provider_name,
            data_hash=data_hash,
            content_location=ContentLocation(
                storage_type=StorageType.CACHE,
                cache_namespace=f"{self.provider_type}_{self.provider_name}",
                cache_key=cache_key,
                content_type="json",
            ),
            metadata={
                "definitions_count": len(provider_data.definitions),
                "has_pronunciation": provider_data.pronunciation is not None,
                "has_etymology": provider_data.etymology is not None,
            },
        )
        
        await versioned.save()
        logger.info(f"Saved versioned definition for '{word}' from {self.provider_name}")
        
    async def _load_versioned_content(
        self,
        location: ContentLocation,
    ) -> dict[str, Any] | None:
        """Load content from storage location."""
        
        if location.storage_type == StorageType.CACHE and location.cache_key:
            return await self.get_from_cache(
                location.cache_key,
                namespace=location.cache_namespace,
            )
        elif location.storage_type == StorageType.DISK:
            # TODO: Implement disk loading
            logger.warning("Disk storage not yet implemented for dictionary data")
            return None
        else:
            return None
            
    async def fetch(
        self,
        resource_id: str,
        state_tracker: StateTracker | None = None,
        **kwargs: Any,
    ) -> DictionaryProviderData | None:
        """Implementation of abstract fetch method."""
        language = kwargs.get("language", Language.ENGLISH)
        word_id = kwargs.get("word_id")
        return await self.fetch_definition(
            word=resource_id,
            language=language,
            word_id=word_id,
            state_tracker=state_tracker,
        )