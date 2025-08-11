"""Dictionary API connectors with versioned provider data support."""

# Import from new locations for extended functionality
from .api.free_dictionary import FreeDictionaryConnector
from .api.merriam_webster import MerriamWebsterConnector
from .api.oxford import OxfordConnector
from .base import BatchConnector, BulkDownloadConnector, DictionaryConnector
from .batch.bulk_downloader import BulkDownloader, WiktionaryBulkDownloader
from .batch.corpus_walker import CorpusWalker, MultiProviderWalker
from .local.apple_dictionary import AppleDictionaryConnector
from .scraper.dictionary_com import DictionaryComConnector
from .scraper.wiktionary import WiktionaryConnector
from .scraper.wordhippo import WordHippoConnector

# Union type for all connectors
Connector = (
    WiktionaryConnector
    | OxfordConnector
    | AppleDictionaryConnector
    | MerriamWebsterConnector
    | FreeDictionaryConnector
    | DictionaryComConnector
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
    "DictionaryComConnector",
    "WordHippoConnector",
    # Local connectors
    "AppleDictionaryConnector",
    # Batch processing
    "CorpusWalker",
    "MultiProviderWalker",
    "BulkDownloader",
    "WiktionaryBulkDownloader",
    # Union type
    "Connector",
]
