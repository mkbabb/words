"""Dictionary API connectors."""

from .base import DictionaryConnector
from .dictionary_com import DictionaryComConnector
from .oxford import OxfordConnector
from .wiktionary import WiktionaryConnector

Connector = WiktionaryConnector | OxfordConnector | DictionaryComConnector

__all__ = [
    "DictionaryConnector",
    "WiktionaryConnector",
    "OxfordConnector",
    "DictionaryComConnector",
    "Connector",
]
