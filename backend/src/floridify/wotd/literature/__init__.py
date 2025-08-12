"""Literature corpus extraction system for WOTD training.

Provides unified interface for downloading, processing, and analyzing
literary texts from Project Gutenberg and other sources.
"""

from .connector import GutenbergConnector
from .corpus_builder import LiteratureCorpusBuilder  
from .mappings import AUTHOR_WORKS_MAPPING, get_author_works
from .models import LiteraryWork, LiteraryWord

__all__ = [
    "GutenbergConnector",
    "LiteratureCorpusBuilder", 
    "AUTHOR_WORKS_MAPPING",
    "get_author_works",
    "LiteraryWork",
    "LiteraryWord",
]