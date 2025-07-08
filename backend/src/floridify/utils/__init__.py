"""Utility modules for Floridify."""

from .logging import get_logger, setup_logging
from .text_utils import (
    bold_word_in_text,
    clean_markdown,
    ensure_sentence_case,
    normalize_word,
)

__all__ = [
    # Logging
    "setup_logging",
    "get_logger",
    # Text utilities
    "normalize_word",
    "bold_word_in_text",
    "clean_markdown",
    "ensure_sentence_case",
]
