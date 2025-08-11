"""API-based dictionary connectors."""

from .free_dictionary import FreeDictionaryConnector
from .merriam_webster import MerriamWebsterConnector
from .oxford import OxfordConnector

__all__ = [
    "FreeDictionaryConnector",
    "MerriamWebsterConnector",
    "OxfordConnector",
]