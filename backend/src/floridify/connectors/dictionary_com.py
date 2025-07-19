"""Dictionary.com connector stub."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ..models import ProviderData
from ..utils.logging import get_logger
from ..utils.state_tracker import ProviderMetrics, StateTracker
from .base import DictionaryConnector

logger = get_logger(__name__)


class DictionaryComConnector(DictionaryConnector):
    """Stub connector for Dictionary.com API."""

    def __init__(self, api_key: str = "", rate_limit: float = 5.0, force_refresh: bool = False) -> None:
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
        progress_callback: Any | None = None,
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
        # Initialize timing and metrics
        start_time = time.time()
        metrics = ProviderMetrics(
            provider_name=self.provider_name,
            response_time_ms=0,
            response_size_bytes=0,
        )
        
        try:
            # Report start
            if state_tracker:
                await self._report_progress(
                    'start', 0, 
                    {'provider': self.provider_name, 'word': word},
                    state_tracker
                )
            
            # TODO: Implement Dictionary.com API integration
            logger.info(f"Dictionary.com connector stub called for word: {word}")
            
            # Simulate some work for the stub
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Report completion (stub always fails)
            metrics.success = False
            metrics.error_message = "Dictionary.com connector not implemented"
            metrics.response_time_ms = (time.time() - start_time) * 1000
            
            if state_tracker:
                await self._report_progress(
                    'complete', 100,
                    {
                        'provider': self.provider_name,
                        'word': word,
                        'success': False,
                        'error': metrics.error_message,
                        'metrics': metrics.__dict__
                    },
                    state_tracker
                )
            
            return None
            
        except Exception as e:
            metrics.success = False
            metrics.error_message = str(e)
            metrics.response_time_ms = (time.time() - start_time) * 1000
            
            if state_tracker:
                await self._report_progress(
                    'complete', 100,
                    {
                        'provider': self.provider_name,
                        'word': word,
                        'success': False,
                        'error': str(e),
                        'metrics': metrics.__dict__
                    },
                    state_tracker
                )
            
            logger.error(f"Error in Dictionary.com stub for {word}: {e}")
            return None
