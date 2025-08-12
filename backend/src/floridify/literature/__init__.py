"""Floridify Literature System - Unified literature corpus management.

This module provides comprehensive literature integration for the Floridify
ecosystem, including downloading, processing, and corpus generation from
classic literature sources.

Key Components:
    - Multi-source literature downloading (Gutenberg, Archive.org, Wikisource)
    - Integration with existing Corpus/CorpusMetadata models
    - Respectful scraping with rate limiting and caching
    - AI-powered literary analysis and semantic classification
    - Export to various formats (WOTD training, search corpus, etc.)
"""

from .connectors import (
    GutenbergConnector,
    InternetArchiveConnector,
    LiteratureSourceManager,
    WikisourceConnector,
)
from .corpus import LiteratureCorpusBuilder, LiteratureCorpus
from .models import (
    Author,
    AuthorMetadata, 
    Genre,
    LiteraryWork,
    LiteraryWord,
    Period,
)

__all__ = [
    # Connectors
    "GutenbergConnector",
    "InternetArchiveConnector", 
    "WikisourceConnector",
    "LiteratureSourceManager",
    
    # Corpus Building
    "LiteratureCorpusBuilder",
    "LiteratureCorpus",
    
    # Models
    "Author",
    "AuthorMetadata",
    "Genre", 
    "LiteraryWork",
    "LiteraryWord",
    "Period",
]

# Version info
__version__ = "1.0.0"