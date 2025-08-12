"""Unified provider system for dictionary and literature sources.

This module provides a unified architecture for all data providers,
with common versioning, caching, and storage capabilities.
"""

from .base import BatchConnector, BulkDownloadConnector, DictionaryConnector, LiteratureProvider

# Import literature providers
from .literature import *  # noqa: F403, F401
from .versioned import (
    ContentLocation,
    DictionaryVersionedData,
    LiteratureVersionedData,
    ProviderSource,
    VersionedData,
    VersionedDataManager,
    versioned_manager,
)

__all__ = [
    # Base classes
    "DictionaryConnector",
    "LiteratureProvider",
    "BatchConnector",
    "BulkDownloadConnector",
    # Versioning
    "VersionedData",
    "DictionaryVersionedData",
    "LiteratureVersionedData",
    "VersionedDataManager",
    "versioned_manager",
    "ProviderSource",
    "ContentLocation",
]
