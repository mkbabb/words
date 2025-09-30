"""Simple provider factory for creating dictionary connectors."""

from __future__ import annotations

from ..models.dictionary import DictionaryProvider
from ..utils.config import Config
from .dictionary.api.free_dictionary import FreeDictionaryConnector
from .dictionary.api.merriam_webster import MerriamWebsterConnector
from .dictionary.api.oxford import OxfordConnector
from .dictionary.core import DictionaryConnector
from .dictionary.local.apple_dictionary import AppleDictionaryConnector
from .dictionary.scraper.wiktionary import WiktionaryConnector
from .dictionary.scraper.wordhippo import WordHippoConnector


def create_connector(
    provider: DictionaryProvider,
    config: Config | None = None,
) -> DictionaryConnector:
    """Create a dictionary connector for the given provider.

    Args:
        provider: Provider type to create
        config: Optional configuration object

    Returns:
        Configured connector instance

    Raises:
        ValueError: If provider requires auth but credentials not configured
    """
    if config is None:
        config = Config.from_file()

    # Simple mapping of providers to connectors
    if provider == DictionaryProvider.WIKTIONARY:
        return WiktionaryConnector()

    elif provider == DictionaryProvider.OXFORD:
        if not config.oxford.app_id or not config.oxford.api_key:
            raise ValueError(
                "Oxford Dictionary API credentials not configured. "
                "Please update auth/config.toml with your Oxford app_id and api_key."
            )
        return OxfordConnector(app_id=config.oxford.app_id, api_key=config.oxford.api_key)

    elif provider == DictionaryProvider.APPLE_DICTIONARY:
        return AppleDictionaryConnector()

    elif provider == DictionaryProvider.MERRIAM_WEBSTER:
        if not config.merriam_webster or not config.merriam_webster.api_key:
            raise ValueError(
                "Merriam-Webster API key not configured. "
                "Please update auth/config.toml with your Merriam-Webster api_key."
            )
        return MerriamWebsterConnector(api_key=config.merriam_webster.api_key)

    elif provider == DictionaryProvider.WORDHIPPO:
        return WordHippoConnector()

    elif provider == DictionaryProvider.FREE_DICTIONARY:
        return FreeDictionaryConnector()

    else:
        raise ValueError(f"Unsupported provider: {provider.value}")
