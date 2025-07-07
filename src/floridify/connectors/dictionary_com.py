"""Dictionary.com connector stub."""

from __future__ import annotations

from ..models import ProviderData
from ..utils.logging import get_logger
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

    async def fetch_definition(self, word: str) -> ProviderData | None:
        """Fetch definition data for a word from Dictionary.com.

        This is a stub implementation that returns None.

        Args:
            word: The word to look up

        Returns:
            None (stub implementation)
        """
        # TODO: Implement Dictionary.com API integration
        logger.info(f"Dictionary.com connector stub called for word: {word}")
        return None
