"""Language corpus module.

Provides language-specific corpus functionality including loading,
source management, and vocabulary processing.
"""

# TODO: LanguageCorpus needs to be implemented in core.py
# from .core import LanguageCorpus
# TODO: LanguageCorpusLoader needs to be implemented
# from .loader import LanguageCorpusLoader
from .sources import LANGUAGE_CORPUS_SOURCES

__all__ = [
    # "LanguageCorpus",  # TODO: Implement in core.py
    # "LanguageCorpusLoader",  # TODO: Implement loader
    "LANGUAGE_CORPUS_SOURCES",
]
