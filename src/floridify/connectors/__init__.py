"""Dictionary API connectors."""

from .base import DictionaryConnector
from .cached_connector import CachedDictionaryConnector
from .dictionary_com import DictionaryComConnector
from .oxford import OxfordConnector
from .wiktionary import WiktionaryConnector

__all__ = [
    "DictionaryConnector",
    "CachedDictionaryConnector",
    "WiktionaryConnector",
    "OxfordConnector",
    "DictionaryComConnector",
]
