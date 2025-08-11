"""Batch processing utilities for dictionary providers."""

from .bulk_downloader import BulkDownloader, WiktionaryBulkDownloader
from .corpus_walker import CorpusWalker, MultiProviderWalker

__all__ = [
    "BulkDownloader",
    "WiktionaryBulkDownloader",
    "CorpusWalker",
    "MultiProviderWalker",
]