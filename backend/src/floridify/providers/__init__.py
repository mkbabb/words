"""Unified provider system for dictionary and literature sources.

This module provides a unified architecture for all data providers,
with common versioning, caching, and storage capabilities.
"""

from .batch import BatchOperation, BatchStatus
from .config import ProviderConfiguration
from .dictionary.base import DictionaryConnector

# Import literature providers
from .literature import *  # noqa: F403
from .literature.base import LiteratureConnector

__all__ = [
    # Base classes
    "DictionaryConnector",
    "LiteratureConnector",
    # Batch operations
    "BatchOperation",
    "BatchStatus",
    # Configuration
    "ProviderConfiguration",
]
