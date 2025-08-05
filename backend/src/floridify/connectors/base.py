"""Base connector interface for dictionary providers."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from ..core.state_tracker import StateTracker
from ..models import ProviderData, Word
from ..models.definition import DictionaryProvider
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
    def provider_name(self) -> DictionaryProvider:
        """Name of the dictionary provider."""
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

    @abstractmethod
    async def fetch_definition(
        self,
        word_obj: Word,
        state_tracker: StateTracker | None = None,
    ) -> ProviderData | None:
        """Fetch definitions for a word from the provider.

        Args:
            word: The word to look up
            state_tracker: Optional state tracker for progress updates

        Returns:
            ProviderData containing definitions, pronunciation, and etymology
        """
        pass
