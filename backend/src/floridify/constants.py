"""
Core constants and enums used across multiple modules in Floridify.

This module contains the most general enums that are referenced throughout
the entire codebase and need consistent definitions.
"""

from __future__ import annotations

from enum import Enum


class Language(Enum):
    """Supported languages with ISO codes."""

    ENGLISH = "en"
    FRENCH = "fr"
    SPANISH = "es"
    GERMAN = "de"
    ITALIAN = "it"


class DictionaryProvider(Enum):
    """Dictionary and data providers supported by the system."""

    WIKTIONARY = "wiktionary"

    OXFORD = "oxford"

    DICTIONARY_COM = "dictionary_com"

    APPLE_DICTIONARY = "apple_dictionary"

    AI_FALLBACK = "ai_fallback"

    SYNTHESIS = "synthesis"

    @property
    def display_name(self) -> str:
        """Get human-readable display name for the provider."""
        display_names: dict[DictionaryProvider, str] = {
            DictionaryProvider.WIKTIONARY: "Wiktionary",
            DictionaryProvider.OXFORD: "Oxford Dictionary",
            DictionaryProvider.DICTIONARY_COM: "Dictionary.com",
            DictionaryProvider.APPLE_DICTIONARY: "Apple Dictionary",
            DictionaryProvider.AI_FALLBACK: "AI Fallback",
            DictionaryProvider.SYNTHESIS: "Synthesis",
        }
        return display_names.get(self, self.value.title())


class OutputFormat(Enum):
    """Output formats for CLI commands and data export."""

    JSON = "json"
    CSV = "csv"
    TXT = "txt"
    MD = "md"
