"""Local system dictionary connectors."""

from .apple_dictionary import AppleDictionaryConnector
from .wordnet_provider import WordNetConnector

__all__ = [
    "AppleDictionaryConnector",
    "WordNetConnector",
]
