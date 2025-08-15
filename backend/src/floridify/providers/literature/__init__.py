"""Literature providers with unified architecture.

Provides unified interface for downloading, processing, and analyzing
literary texts from various sources.
"""

from .api.gutenberg import GutenbergConnector
from .api.internet_archive import InternetArchiveConnector
from .core import LiteratureConnector
from .models import LiteratureEntry

__all__ = [
    # Base
    "LiteratureConnector",
    # Connectors
    "GutenbergConnector",
    "InternetArchiveConnector",
    # Models
    "LiteratureEntry",
]
