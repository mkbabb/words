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
        self.progress_callback: Callable[[str, float, dict[str, Any]], None] | None = None

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
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {self.provider_name}")
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
        if not response_data:
            logger.warning(f"Empty response data for word '{word.text}' from {self.provider_name}")
            response_data = {}

        if not word or not word.id:
            raise ValueError(f"Invalid word object provided to {self.provider_name}")

        try:
            # Extract components using abstract methods with error handling
            pronunciation = None
            try:
                pronunciation = await self.extract_pronunciation(response_data)
            except Exception as e:
                logger.warning(f"Failed to extract pronunciation from {self.provider_name} for '{word.text}': {e}")

            definitions = []
            try:
                definitions = await self.extract_definitions(response_data, str(word.id))
            except Exception as e:
                logger.warning(f"Failed to extract definitions from {self.provider_name} for '{word.text}': {e}")

            etymology = None
            try:
                etymology = await self.extract_etymology(response_data)
            except Exception as e:
                logger.warning(f"Failed to extract etymology from {self.provider_name} for '{word.text}': {e}")

            # Save pronunciation if found
            pronunciation_id = None
            if pronunciation:
                try:
                    pronunciation.word_id = str(word.id)
                    await pronunciation.save()
                    pronunciation_id = str(pronunciation.id)
                except Exception as e:
                    logger.error(f"Failed to save pronunciation from {self.provider_name} for '{word.text}': {e}")

            # Save definitions and collect IDs
            definition_ids = []
            for definition in definitions or []:
                try:
                    await definition.save()
                    definition_ids.append(str(definition.id))
                except Exception as e:
                    logger.error(f"Failed to save definition from {self.provider_name} for '{word.text}': {e}")

            # Create and save provider data
            # Filter out any non-serializable data from raw_data
            safe_raw_data = {
                k: v
                for k, v in response_data.items()
                if k != "definitions" and v is not None  # Exclude definitions and None values
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

            logger.debug(f"Successfully normalized response from {self.provider_name} for '{word.text}': "
                        f"{len(definition_ids)} definitions, pronunciation: {pronunciation_id is not None}")

            return provider_data

        except Exception as e:
            logger.error(f"Failed to normalize response from {self.provider_name} for '{word.text}': {e}")
            raise
