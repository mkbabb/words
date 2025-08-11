"""Web scraper dictionary connectors."""

from .dictionary_com import DictionaryComConnector
from .wiktionary import WiktionaryConnector

__all__ = [
    "DictionaryComConnector",
    "WiktionaryConnector",
]