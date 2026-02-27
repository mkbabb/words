"""Functional parsers for lexicon data formats.

Simple, focused functions for parsing different lexicon formats.
Each function takes content and returns (words, phrases) tuple.
"""

from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any

from ...models.base import Language
from ...text import is_phrase, normalize
from ...utils.logging import get_logger

logger = get_logger(__name__)

ParseResult = tuple[list[str], list[str]]


def parse_text_lines(content: str, language: Language) -> ParseResult:
    """Parse text content with one word/phrase per line or frequency lists.

    Handles:
    - Simple word lists (one per line)
    - Frequency lists (word frequency pairs)
    - Comments starting with #
    """
    words = []
    phrases = []

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Check if line contains a phrase (multiple words)
        # or if it's a frequency list (word followed by number)
        parts = line.split()
        if not parts:
            continue

        # If there's only one part or the second part is a number (frequency),
        # treat the first part as the word/phrase
        if len(parts) == 1 or (len(parts) >= 2 and parts[1].isdigit()):
            word = parts[0]
        else:
            # Otherwise, treat the whole line as a potential phrase
            word = line

        normalized = normalize(word)
        if not normalized:
            continue

        if is_phrase(normalized):
            phrases.append(normalized)
        else:
            words.append(normalized)

    return list(set(words)), list(set(phrases))


def parse_json_vocabulary(content: str | dict[str, Any], language: Language) -> ParseResult:
    """Parse JSON vocabulary data from string or dict.

    Handles various JSON structures:
    - {"words": [...], "phrases": [...]}
    - {"vocabulary": [...]}
    - {"idioms": [...]}
    - Simple arrays [...]
    - Dictionary keys as vocabulary
    - GitHub API responses
    """
    # Handle both string and dict inputs
    if isinstance(content, str):
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON content")
            return [], []
    elif isinstance(content, dict):
        data = content
    else:
        return [], []

    words = []
    phrases = []

    # Handle simple array
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                normalized = normalize(item)
                if not normalized:
                    continue
                if is_phrase(normalized):
                    phrases.append(normalized)
                else:
                    words.append(normalized)
            elif isinstance(item, dict):
                # Handle objects with text fields
                text = (
                    item.get("word")
                    or item.get("text")
                    or item.get("idiom")
                    or item.get("phrase")
                    or item.get("verb")  # Phrasal verbs
                    or item.get("term")
                    or item.get("name")  # GitHub files
                    or ""
                )
                if text:
                    normalized = normalize(text)
                    if normalized:
                        if is_phrase(normalized):
                            phrases.append(normalized)
                        else:
                            words.append(normalized)

    # Handle dictionary
    elif isinstance(data, dict):
        # Handle scraped data with "data" key (e.g., French expressions)
        if "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                if isinstance(item, dict):
                    # Extract expression or other text fields
                    text = (
                        item.get("expression")
                        or item.get("word")
                        or item.get("text")
                        or item.get("phrase")
                        or ""
                    )
                    if text:
                        normalized = normalize(text)
                        if normalized:
                            if is_phrase(normalized):
                                phrases.append(normalized)
                            else:
                                words.append(normalized)
                elif isinstance(item, str):
                    normalized = normalize(item)
                    if normalized:
                        if is_phrase(normalized):
                            phrases.append(normalized)
                        else:
                            words.append(normalized)

        # Extract from specific keys
        for key in ["words", "vocabulary", "vocab", "terms"]:
            if key in data and isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, str):
                        normalized = normalize(item)
                        if normalized:
                            if is_phrase(normalized):
                                phrases.append(normalized)
                            else:
                                words.append(normalized)

        # Extract phrases from phrase-specific keys
        for key in ["phrases", "expressions", "phrasal_verbs"]:
            if key in data and isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, str):
                        normalized = normalize(item)
                        if normalized:
                            phrases.append(normalized)
                    elif isinstance(item, dict):
                        # Extract from nested structure
                        text = (
                            item.get("idiom")
                            or item.get("phrase")
                            or item.get("verb")  # Phrasal verbs
                            or item.get("text")
                            or item.get("expression")
                            or ""
                        )
                        if text:
                            normalized = normalize(text)
                            if normalized:
                                phrases.append(normalized)

        # Extract proverbs from nested category structure
        # Format: {"proverbs": [{"Category": ["proverb1", "proverb2"]}, ...]}
        if "proverbs" in data and isinstance(data["proverbs"], list):
            for category_dict in data["proverbs"]:
                if isinstance(category_dict, dict):
                    for category_name, proverb_list in category_dict.items():
                        if isinstance(proverb_list, list):
                            for proverb in proverb_list:
                                if isinstance(proverb, str):
                                    normalized = normalize(proverb)
                                    if normalized:
                                        phrases.append(normalized)

        # Extract idioms as vocabulary items (they're multi-word expressions)
        if "idioms" in data and isinstance(data["idioms"], list):
            for item in data["idioms"]:
                if isinstance(item, str):
                    normalized = normalize(item)
                    if normalized:
                        words.append(normalized)  # Add idioms to vocabulary

        # Use dictionary keys as vocabulary if no explicit vocabulary keys found
        if not words and not phrases and len(data) > 0:
            # Check if this looks like a word dictionary (not a structured data object)
            sample_keys = list(data.keys())[:5]
            if all(key and not key.startswith("_") and len(key) < 50 for key in sample_keys):
                for key in data.keys():
                    normalized = normalize(key)
                    if normalized:
                        if is_phrase(normalized):
                            phrases.append(normalized)
                        else:
                            words.append(normalized)

    return list(set(words)), list(set(phrases))


def parse_csv_words(content: str, language: Language) -> ParseResult:
    """Parse CSV with word/phrase data.

    Handles:
    - CSV with headers (word, text, vocabulary, term, idiom, phrase columns)
    - Simple CSV without headers
    - Falls back to text parsing if not valid CSV
    """
    words = []
    phrases = []

    try:
        lines = content.strip().split("\n")
        if not lines:
            return [], []

        first_line = lines[0]

        # Check if content looks like CSV with headers
        if "," in first_line and any(
            col in first_line.lower()
            for col in [
                "word",
                "text",
                "vocabulary",
                "term",
                "frequency",
                "type",
                "idiom",
                "phrase",
            ]
        ):
            csv_reader = csv.DictReader(StringIO(content))

            for row in csv_reader:
                # Extract text from common column names
                text = (
                    row.get("word")
                    or row.get("text")
                    or row.get("vocabulary")
                    or row.get("term")
                    or row.get("idiom")
                    or row.get("phrase")
                    or row.get("expression")
                    or ""
                ).strip()

                if not text:
                    # Try first column if no named columns match
                    first_col = list(row.values())[0] if row else ""
                    text = first_col.strip() if first_col else ""

                if text:
                    normalized = normalize(text)
                    if normalized:
                        # Check type column if it exists
                        item_type = row.get("type", "").lower()
                        if item_type in ["phrase", "idiom", "expression"] or is_phrase(normalized):
                            phrases.append(normalized)
                        else:
                            words.append(normalized)
        else:
            # Fall back to simple CSV parsing without headers
            simple_csv_reader = csv.reader(StringIO(content))
            for csv_row in simple_csv_reader:
                if csv_row:
                    # Take first column
                    text = csv_row[0].strip()
                    if text:
                        normalized = normalize(text)
                        if normalized:
                            if is_phrase(normalized):
                                phrases.append(normalized)
                            else:
                                words.append(normalized)

    except Exception as e:
        logger.debug(f"CSV parsing failed, falling back to text parsing: {e}")
        # Fall back to text parsing
        return parse_text_lines(content, language)

    return list(set(words)), list(set(phrases))


def parse_scraped_data(
    content: dict[str, Any],
    language: Language,
) -> ParseResult:
    """Parse scraped data from custom scrapers.

    This handles the output from specialized scrapers that return
    structured data instead of raw text.
    """
    words = []
    phrases = []

    # Direct vocabulary extraction
    if "vocabulary" in content and isinstance(content["vocabulary"], list):
        for item in content["vocabulary"]:
            if isinstance(item, str):
                normalized = normalize(item)
                if normalized:
                    if is_phrase(normalized):
                        phrases.append(normalized)
                    else:
                        words.append(normalized)

    # Separate words and phrases
    if "words" in content and isinstance(content["words"], list):
        for word in content["words"]:
            if isinstance(word, str):
                normalized = normalize(word)
                if normalized:
                    words.append(normalized)

    if "phrases" in content and isinstance(content["phrases"], list):
        for phrase in content["phrases"]:
            if isinstance(phrase, str):
                normalized = normalize(phrase)
                if normalized:
                    phrases.append(normalized)

    # Handle expressions/idioms
    for key in ["expressions", "idioms"]:
        if key in content and isinstance(content[key], list):
            for item in content[key]:
                if isinstance(item, str):
                    normalized = normalize(item)
                    if normalized:
                        phrases.append(normalized)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("expression") or ""
                    if text:
                        normalized = normalize(text)
                        if normalized:
                            phrases.append(normalized)

    return list(set(words)), list(set(phrases))
