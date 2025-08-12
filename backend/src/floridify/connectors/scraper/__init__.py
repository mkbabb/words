"""Web scraper dictionary connectors."""

# Dictionary.com connector removed - JavaScript-heavy site
from .wiktionary import WiktionaryConnector

__all__ = [
    "WiktionaryConnector",
]