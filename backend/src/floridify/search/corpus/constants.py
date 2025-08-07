"""Corpus-specific constants."""

from __future__ import annotations

from enum import Enum


class LexiconFormat(Enum):
    """
    Data formats supported for lexicon sources.

    These formats define how lexicon data is structured and should be parsed.
    """

    TEXT_LINES = "text_lines"  # Simple text file with one word/phrase per line
    JSON_IDIOMS = "json_idioms"  # JSON file containing idioms and phrases
    FREQUENCY_LIST = "frequency_list"  # Word frequency list with scores
    JSON_DICT = "json_dict"  # JSON dictionary format (key-value pairs)
    JSON_ARRAY = "json_array"  # JSON array of words/phrases
    JSON_GITHUB_API = "json_github_api"  # GitHub API response format
    CSV_IDIOMS = "csv_idioms"  # CSV format with idiom,definition columns
    DICEWARE = "diceware"  # Diceware format (number:word pairs)
    JSON_PHRASAL_VERBS = "json_phrasal_verbs"  # JSON format with phrasal verbs, definitions
    CUSTOM_SCRAPER = "custom_scraper"  # Custom scraper function for dynamic data extraction
