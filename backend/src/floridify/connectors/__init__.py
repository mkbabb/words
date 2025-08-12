"""Dictionary API connectors with versioned provider data support."""

# Import from new locations for extended functionality
from .api.free_dictionary import FreeDictionaryConnector
from .api.merriam_webster import MerriamWebsterConnector
from .api.oxford import OxfordConnector
from .base import BatchConnector, BulkDownloadConnector, DictionaryConnector
# Batch processing moved to scrape.py
from .scrape import BulkScraper, BulkScrapingConfig
from .local.apple_dictionary import AppleDictionaryConnector
# Dictionary.com connector removed - JavaScript-heavy site
from .scraper.wiktionary import WiktionaryConnector
from .scraper.wordhippo import WordHippoConnector

# Union type for all connectors
Connector = (
    WiktionaryConnector
    | OxfordConnector
    | AppleDictionaryConnector
    | MerriamWebsterConnector
    | FreeDictionaryConnector
    | WordHippoConnector
)

__all__ = [
    # Base classes
    "DictionaryConnector",
    "BatchConnector",
    "BulkDownloadConnector",
    # API connectors
    "OxfordConnector",
    "MerriamWebsterConnector",
    "FreeDictionaryConnector",
    # Scraper connectors
    "WiktionaryConnector",
    "WordHippoConnector",
    # Local connectors
    "AppleDictionaryConnector",
    # Bulk scraping
    "BulkScraper",
    "BulkScrapingConfig",
    # Union type
    "Connector",
]
