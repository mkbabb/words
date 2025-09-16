"""Free Dictionary API connector.

Free, open API with no authentication required.
API documentation: https://dictionaryapi.dev/
"""

from __future__ import annotations

from typing import Any

import httpx

from ....caching.decorators import cached_api_call
from ....core.state_tracker import StateTracker
from ....models.dictionary import DictionaryProvider
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ..core import DictionaryConnector

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

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        """Initialize Free Dictionary connector.

        Args:
            config: Connector configuration (default: 60 RPS)

        """
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.API_FAST.value)
        super().__init__(provider=DictionaryProvider.FREE_DICTIONARY, config=config)
        self.base_url = "https://api.dictionaryapi.dev/api/v2/entries/en"

    @cached_api_call(ttl_hours=24.0, key_prefix="free_dictionary")
    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
    ) -> dict[str, Any] | None:
        """Fetch definition from Free Dictionary.

        Args:
            word: The word to look up
            state_tracker: Optional state tracker for monitoring

        Returns:
            Dictionary data with definitions, pronunciation, and etymology

        """
        url = f"{self.base_url}/{word}"

        try:
            response = await self.api_client.get(url)

            if response.status_code == httpx.codes.NOT_FOUND:
                logger.debug(f"Word '{word}' not found in Free Dictionary")
                return None

            response.raise_for_status()
            data = response.json()

            # API returns a list of entries
            if isinstance(data, list) and data:
                # Return raw dictionary data
                return {
                    "word": word,
                    "provider": self.provider.value,
                    "entries": data,
                    "raw_data": {"entries": data},
                }

            return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Free Dictionary API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from Free Dictionary: {e}")
            return None
