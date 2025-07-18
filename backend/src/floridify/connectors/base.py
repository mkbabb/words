"""Base connector interface for dictionary providers."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from ..models import ProviderData
from ..utils.logging import get_logger
from ..utils.state_tracker import PipelineStage, StateTracker

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
        self.state_tracker: Optional[StateTracker] = None
        self.progress_callback: Optional[Callable[[str, float, dict[str, Any]], None]] = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the dictionary provider."""
        pass

    @abstractmethod
    async def fetch_definition(
        self, 
        word: str,
        state_tracker: Optional[StateTracker] = None,
        progress_callback: Optional[Callable[[str, float, dict[str, Any]], None]] = None,
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

    async def _report_progress(
        self, 
        stage: str, 
        progress: float, 
        metadata: dict[str, Any],
        state_tracker: Optional[StateTracker] = None,
    ) -> None:
        """Report progress through callback or state tracker.
        
        Args:
            stage: Current stage (e.g., 'connecting', 'downloading', 'parsing')
            progress: Progress percentage (0-100)
            metadata: Additional metadata about the progress
            state_tracker: Optional state tracker to update
        """
        # Use provided state tracker or instance one
        tracker = state_tracker or self.state_tracker
        
        if tracker:
            # Map stage names to PipelineStage enum
            stage_map = {
                'start': PipelineStage.PROVIDER_START,
                'connecting': PipelineStage.PROVIDER_CONNECTED,
                'downloading': PipelineStage.PROVIDER_DOWNLOADING,
                'parsing': PipelineStage.PROVIDER_PARSING,
                'complete': PipelineStage.PROVIDER_COMPLETE,
            }
            
            if stage in stage_map:
                await tracker.update(
                    stage_map[stage],
                    progress,
                    f"{self.provider_name}: {stage}",
                    metadata
                )
        
        # Also call progress callback if available
        if self.progress_callback:
            try:
                self.progress_callback(stage, progress, metadata)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def _normalize_response(self, response_data: dict[str, Any]) -> ProviderData:
        """Normalize provider response to internal format.

        Args:
            response_data: Raw response from provider API

        Returns:
            Normalized ProviderData
        """
        # Default implementation - override in subclasses
        return ProviderData(
            provider_name=self.provider_name, definitions=[], raw_metadata=response_data
        )
