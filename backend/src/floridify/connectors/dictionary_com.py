"""Dictionary.com connector stub."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ..core.state_tracker import PipelineState, StateTracker
from ..models import ProviderData
from ..utils.logging import get_logger
from .base import DictionaryConnector

logger = get_logger(__name__)


class DictionaryComConnector(DictionaryConnector):
    """Stub connector for Dictionary.com API."""

    def __init__(
        self, api_key: str = "", rate_limit: float = 5.0, force_refresh: bool = False
    ) -> None:
        """Initialize Dictionary.com connector stub.

        Args:
            api_key: Dictionary.com API key (if available)
            rate_limit: Requests per second
            force_refresh: Force fresh HTTP requests (bypass cache)
        """
        super().__init__(rate_limit=rate_limit)
        self.api_key = api_key
        self.force_refresh = force_refresh

    @property
    def provider_name(self) -> str:
        """Name of the dictionary provider."""
        return "dictionary_com"

    async def fetch_definition(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
    ) -> ProviderData | None:
        """Fetch definition data for a word from Dictionary.com.

        This is a stub implementation that returns None.

        Args:
            word: The word to look up
            state_tracker: Optional state tracker for progress updates
            progress_callback: Optional callback for provider-specific progress

        Returns:
            None (stub implementation)
        """
        try:
            # Report start
            if state_tracker:
                await state_tracker.update(
                    stage="PROVIDER_FETCH_START",
                    message=f"Fetching from {self.provider_name}",
                    details={"word": word},
                )

            # TODO: Implement Dictionary.com API integration
            logger.info(f"Dictionary.com connector stub called for word: {word}")

            # Simulate some work for the stub
            await asyncio.sleep(0.1)  # Simulate network delay

            if state_tracker:
                await state_tracker.update(
                    stage="PROVIDER_FETCH_COMPLETE",
                    message=f"Fetch complete for {self.provider_name}",
                    details={
                        "word": word,
                        "success": False,
                        "error": "Dictionary.com connector not implemented",
                    },
                )

            return None

        except Exception as e:
            if state_tracker:
                await state_tracker.update(
                    stage="PROVIDER_FETCH_ERROR",
                    message=f"Error fetching from {self.provider_name}",
                    details={"word": word, "error": str(e)},
                )

            logger.error(f"Error in Dictionary.com stub for {word}: {e}")

            return None
