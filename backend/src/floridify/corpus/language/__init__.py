"""Language corpus module.

Provides language-specific corpus functionality including loading,
source management, and vocabulary processing.
"""

from .core import LanguageCorpus

__all__ = [
    "LanguageCorpus",
    "LanguageCorpusMetadata",
]
