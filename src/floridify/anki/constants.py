"""
Anki-related constants and enums.

Contains enums for flashcard types and Anki-specific configurations.
"""

from __future__ import annotations

from enum import Enum


class CardType(Enum):
    """Types of flashcards that can be generated for Anki."""

    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"
    DEFINITION_TO_WORD = "definition_to_word"
    WORD_TO_DEFINITION = "word_to_definition"