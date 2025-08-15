"""Literature providers with unified architecture.

Provides unified interface for downloading, processing, and analyzing
literary texts from various sources.
"""

from .api.gutenberg import GutenbergConnector
from .api.internet_archive import InternetArchiveConnector
from .base import LiteratureConnector
from .models import (
    AuthorInfo,
    Genre,
    LiteraryWord,
    LiteraryWork,
    LiteratureMetadata,
    LiteratureSource,
    Period,
    TextQualityMetrics,
)

__all__ = [
    # Base
    "LiteratureConnector",
    # Connectors
    "GutenbergConnector",
    "InternetArchiveConnector",
    # Models
    "AuthorInfo",
    "Genre",
    "LiteraryWord",
    "LiteraryWork",
    "LiteratureMetadata",
    "LiteratureSource",
    "Period",
    "TextQualityMetrics",
]
