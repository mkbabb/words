"""Wholesale download connectors for bulk data."""

from .wiktionary_wholesale import (
    WiktionaryTitleListDownloader,
    WiktionaryWholesaleConnector,
)

__all__ = [
    "WiktionaryTitleListDownloader",
    "WiktionaryWholesaleConnector",
]
