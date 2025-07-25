"""Base connector interface for dictionary providers."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from ..constants import DictionaryProvider
from ..core.state_tracker import StateTracker
from ..models import Definition, Etymology, Pronunciation, ProviderData, Word
from ..utils.logging import get_logger

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
        self.progress_callback: Callable[[str, float, dict[str, Any]], None] | None = (
            None
        )

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the dictionary provider."""
        pass

    @abstractmethod
    async def fetch_definition(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
    ) -> ProviderData | None:
        """Fetch definition data for a word.

        Args:
            word: The word to look up
            state_tracker: Optional state tracker for progress updates
            progress_callback: Optional callback for provider-specific progress

        Returns:
            ProviderData if successful, None if not found or error
        """
        pass

    @abstractmethod
    async def extract_pronunciation(self, raw_data: dict[str, Any]) -> Pronunciation | None:
        """Extract pronunciation from raw provider data.

        Args:
            raw_data: Raw response from provider API

        Returns:
            Pronunciation if found, None otherwise
        """
        pass

    @abstractmethod
    async def extract_definitions(self, raw_data: dict[str, Any], word_id: str) -> list[Definition]:
        """Extract definitions from raw provider data.

        Args:
            raw_data: Raw response from provider API
            word_id: ID of the word these definitions belong to

        Returns:
            List of Definition objects
        """
        pass

    @abstractmethod
    async def extract_etymology(self, raw_data: dict[str, Any]) -> Etymology | None:
        """Extract etymology from raw provider data.

        Args:
            raw_data: Raw response from provider API

        Returns:
            Etymology if found, None otherwise
        """
        pass

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        async with self._rate_limiter:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self._last_request_time
            min_interval = 1.0 / self.rate_limit

            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                logger.debug(
                    f"Rate limiting: waiting {wait_time:.2f}s for {self.provider_name}"
                )
                await asyncio.sleep(wait_time)

            self._last_request_time = asyncio.get_event_loop().time()

    async def _normalize_response(self, response_data: dict[str, Any], word: Word) -> ProviderData:
        """Normalize provider response to internal format.

        Args:
            response_data: Raw response from provider API
            word: The Word object this data belongs to

        Returns:
            Normalized ProviderData
        """
        # Extract components using abstract methods
        pronunciation = await self.extract_pronunciation(response_data)
        definitions = await self.extract_definitions(response_data, str(word.id))
        etymology = await self.extract_etymology(response_data)
        
        # Save pronunciation if found
        pronunciation_id = None
        if pronunciation:
            pronunciation.word_id = str(word.id)
            await pronunciation.save()
            pronunciation_id = str(pronunciation.id)
        
        # Save definitions and collect IDs
        definition_ids = []
        for definition in definitions:
            await definition.save()
            definition_ids.append(str(definition.id))
        
        # Create and save provider data
        # Filter out any non-serializable data from raw_data
        safe_raw_data = {
            k: v for k, v in response_data.items() 
            if k != "definitions"  # Exclude definitions which may contain ObjectIds
        }
        
        provider_data = ProviderData(
            word_id=str(word.id),
            provider=DictionaryProvider(self.provider_name),
            definition_ids=definition_ids,
            pronunciation_id=pronunciation_id,
            etymology=etymology,
            raw_data=safe_raw_data,
        )
        await provider_data.save()
        
        return provider_data
