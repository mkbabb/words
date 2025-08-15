"""Free Dictionary API connector.

Free, open API with no authentication required.
API documentation: https://dictionaryapi.dev/
"""

from __future__ import annotations

from typing import Any

import httpx

from ....caching.decorators import cached_api_call
from ....core.state_tracker import Stages, StateTracker
from ....models import Word
from ....models.dictionary import DictionaryProvider, DictionaryProviderData
from ....utils.logging import get_logger
from ..base import DictionaryConnector

logger = get_logger(__name__)


class FreeDictionaryConnector(DictionaryConnector):
    """Connector for Free Dictionary API.

    The Free Dictionary API provides:
    - Multiple definitions with meanings
    - Phonetic pronunciations with audio
    - Parts of speech
    - Examples
    - Synonyms and antonyms
    - Source attributions
    """

    def __init__(self, rate_limit: float = 60.0) -> None:
        """Initialize Free Dictionary connector.

        Args:
            rate_limit: Maximum requests per second (default: 60, very generous)

        """
        super().__init__()
        self.base_url = "https://api.dictionaryapi.dev/api/v2/entries/en"
        self.session = httpx.AsyncClient(timeout=30.0)

    @property
    def provider_name(self) -> DictionaryProvider:
        """Return the provider name."""
        return DictionaryProvider.FREE_DICTIONARY

    @property
    def provider_version(self) -> str:
        """Version of the Free Dictionary API implementation."""
        return "1.0.0"

    async def __aenter__(self) -> FreeDictionaryConnector:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        await self.session.aclose()

    @cached_api_call(ttl_hours=24.0, key_prefix="free_dictionary")
    async def _fetch_from_api(self, word: str) -> list[dict[str, Any]] | None:
        """Fetch word data from Free Dictionary API.

        Args:
            word: The word to look up

        Returns:
            API response data or None if not found

        """
        await self._enforce_rate_limit()

        url = f"{self.base_url}/{word}"

        try:
            response = await self.session.get(url)

            if response.status_code == 404:
                logger.debug(f"Word '{word}' not found in Free Dictionary")
                return None

            response.raise_for_status()
            data = response.json()

            # API returns a list of entries
            if isinstance(data, list) and data:
                return data

            return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Free Dictionary API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from Free Dictionary: {e}")
            return None

    async def _fetch_from_provider(
        self,
        word_obj: Word,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryProviderData | None:
        """Fetch definition from Free Dictionary.

        Args:
            word_obj: The word to look up
            state_tracker: Optional state tracker for progress

        Returns:
            ProviderData with definitions, pronunciation, and etymology

        """
        try:
            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)

            # Fetch from API
            entries = await self._fetch_from_api(word_obj.text)
            if not entries:
                return None

            # Check that word_obj has been saved and has an ID
            if not word_obj.id:
                raise ValueError(f"Word {word_obj.text} must be saved before processing")

            # Parse and create provider data
            provider_data = DictionaryProviderData(
                word_id=word_obj.id,
                provider=self.provider_name,
                definition_ids=[],
                raw_data={"entries": entries},
            )

            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)

            return provider_data

        except Exception as e:
            logger.error(f"Error fetching from Free Dictionary: {e}")
            if state_tracker:
                await state_tracker.update_error(str(e), Stages.PROVIDER_FETCH_ERROR)
            return None
