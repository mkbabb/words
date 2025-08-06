"""Dictionary API connectors."""

from .base import DictionaryConnector
from .oxford import OxfordConnector
from .wiktionary import WiktionaryConnector

Connector = WiktionaryConnector | OxfordConnector

__all__ = [
    "DictionaryConnector",
    "WiktionaryConnector",
    "OxfordConnector",
    "Connector",
]
