"""Dictionary.com connector stub."""

from __future__ import annotations

from ..models import ProviderData
from .base import DictionaryConnector


class DictionaryComConnector(DictionaryConnector):
    """Stub connector for Dictionary.com API."""

    def __init__(self, api_key: str = "", rate_limit: float = 5.0) -> None:
        """Initialize Dictionary.com connector stub.

        Args:
            api_key: Dictionary.com API key (if available)
            rate_limit: Requests per second
        """
        super().__init__(rate_limit=rate_limit)
        self.api_key = api_key

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
        print(f"Dictionary.com connector stub called for word: {word}")
        return None
