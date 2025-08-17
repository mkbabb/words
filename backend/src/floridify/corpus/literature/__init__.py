"""Literature corpus module.

Provides literature-specific corpus functionality including loading,
work management, and vocabulary extraction from literary texts.
"""

from .core import LiteratureCorpus
from .loader import LiteratureCorpusLoader

__all__ = [
    "LiteratureCorpus",
    "LiteratureCorpusLoader",
]
