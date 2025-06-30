"""Utility modules for Floridify."""

from .logging import is_verbose, set_verbose, vprint
from .normalization import clean_phrase, generate_word_variants, is_phrase, normalize_word

__all__ = [
    "set_verbose",
    "is_verbose",
    "vprint",
    "normalize_word",
    "generate_word_variants",
    "is_phrase",
    "clean_phrase",
]
