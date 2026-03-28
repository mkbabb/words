"""Wholesale download connectors for bulk data."""

from .batch import ImportMode
from .connector import WiktionaryWholesaleConnector

__all__ = [
    "ImportMode",
    "WiktionaryWholesaleConnector",
]
