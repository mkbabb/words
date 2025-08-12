"""Literature providers with unified architecture.

Provides unified interface for downloading, processing, and analyzing
literary texts from various sources.
"""

from .api.gutenberg import GutenbergConnector
from .api.internet_archive import InternetArchiveConnector
from .base import LiteratureConnector
from .corpus_builder import LiteratureCorpusBuilder
from .mappings import get_author_metadata, get_author_works
from .models import (
    Author,
    AuthorMetadata,
    Genre,
    LiteraryWord,
    LiteraryWork,
    LiteratureCorpusMetadata,
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
    # Corpus building
    "LiteratureCorpusBuilder",
    # Mappings
    "get_author_works",
    "get_author_metadata",
    # Models
    "Author",
    "AuthorMetadata",
    "Genre",
    "LiteraryWord",
    "LiteraryWork",
    "LiteratureCorpusMetadata",
    "LiteratureMetadata",
    "LiteratureSource",
    "Period",
    "TextQualityMetrics",
]
