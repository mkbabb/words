"""Dictionary providers with unified architecture."""

from .api.free_dictionary import FreeDictionaryConnector
from .api.merriam_webster import MerriamWebsterConnector
from .api.oxford import OxfordConnector
from .local.apple_dictionary import AppleDictionaryConnector
from .scraper.wiktionary import WiktionaryConnector
from .scraper.wordhippo import WordHippoConnector

__all__ = [
    # API providers
    "FreeDictionaryConnector",
    "MerriamWebsterConnector",
    "OxfordConnector",
    # Scraper providers
    "WiktionaryConnector",
    "WordHippoConnector",
    # Local providers
    "AppleDictionaryConnector",
]
