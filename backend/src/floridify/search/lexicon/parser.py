"""Functional parsers for lexicon data formats.

Simple, focused functions for parsing different lexicon formats.
Each function takes content and returns (words, phrases) tuple.
"""

from __future__ import annotations

import base64
import csv
import json
from io import StringIO
from typing import Any

from ...constants import Language
from ...utils.logging import get_logger
from ..constants import LexiconFormat
from ..phrase import MultiWordExpression, PhraseNormalizer

logger = get_logger(__name__)

ParseResult = tuple[list[str], list[MultiWordExpression]]


def _create_phrase(
    text: str, normalized: str, language: Language, *, is_idiom: bool = False
) -> MultiWordExpression:
    """Create a MultiWordExpression with standard parameters."""
    return MultiWordExpression(
        text=text,
        normalized=normalized,
        word_count=len(normalized.split()),
        is_idiom=is_idiom,
        language=language,
    )


def parse_text_lines(
    content: str, language: Language, phrase_normalizer: PhraseNormalizer
) -> ParseResult:
    """Parse simple text file with one word per line."""
    words = []
    phrases = []

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        normalized = phrase_normalizer.normalize(line)
        if not normalized:
            continue

        if phrase_normalizer.is_phrase(normalized):
            phrase = _create_phrase(line, normalized, language)
            phrases.append(phrase)
        else:
            words.append(normalized)

    return words, phrases


def parse_frequency_list(
    content: str, language: Language, phrase_normalizer: PhraseNormalizer
) -> ParseResult:
    """Parse frequency list format (word frequency pairs)."""
    words = []
    phrases = []

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Split on whitespace and take the first part (word)
        parts = line.split()
        if not parts:
            continue

        word = parts[0]
        normalized = phrase_normalizer.normalize(word)
        if not normalized:
            continue

        if phrase_normalizer.is_phrase(normalized):
            phrase = _create_phrase(word, normalized, language)
            phrases.append(phrase)
        else:
            words.append(normalized)

    return words, phrases


def parse_json_idioms(
    content: str, language: Language, phrase_normalizer: PhraseNormalizer
) -> ParseResult:
    """Parse JSON file containing idioms and phrases."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return [], []

    phrases = []

    # Extract items from various JSON structures
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "idioms" in data:
        idioms = data["idioms"]
        items = idioms if isinstance(idioms, list) else []
    elif isinstance(data, dict):
        items = list(data.values())
    else:
        return [], []

    for item in items:
        # Extract phrase text from item
        if isinstance(item, str):
            phrase_text = item
        elif isinstance(item, dict):
            phrase_text = item.get("idiom") or item.get("phrase") or item.get("text") or ""
        else:
            continue

        if not phrase_text:
            continue

        normalized = phrase_normalizer.normalize(phrase_text)
        if normalized and phrase_normalizer.is_phrase(normalized):
            phrase = _create_phrase(phrase_text, normalized, language, is_idiom=True)
            phrases.append(phrase)

    return [], phrases


def parse_json_dict(
    content: str, language: Language, phrase_normalizer: PhraseNormalizer
) -> ParseResult:
    """Parse JSON dictionary format."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return [], []

    words = []
    phrases = []

    if isinstance(data, dict):
        for key in data.keys():
            normalized = phrase_normalizer.normalize(key)
            if not normalized:
                continue

            if phrase_normalizer.is_phrase(normalized):
                phrase = _create_phrase(key, normalized, language)
                phrases.append(phrase)
            else:
                words.append(normalized)

    return words, phrases


def parse_json_array(
    content: str, language: Language, phrase_normalizer: PhraseNormalizer
) -> ParseResult:
    """Parse JSON array format."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return [], []

    words = []
    phrases = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                normalized = phrase_normalizer.normalize(item)
                if not normalized:
                    continue

                if phrase_normalizer.is_phrase(normalized):
                    phrase = _create_phrase(item, normalized, language)
                    phrases.append(phrase)
                else:
                    words.append(normalized)

    return words, phrases


def parse_github_api(
    content: str, language: Language, phrase_normalizer: PhraseNormalizer
) -> ParseResult:
    """Parse GitHub API response format."""
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "content" in data:
            # Decode base64 content
            decoded_content = base64.b64decode(data["content"]).decode("utf-8")
            # Delegate to JSON array parser
            return parse_json_array(decoded_content, language, phrase_normalizer)
    except Exception:
        pass
    return [], []


def parse_csv_idioms(
    content: str, language: Language, phrase_normalizer: PhraseNormalizer
) -> ParseResult:
    """Parse CSV format with idiom/definition columns."""
    phrases = []

    try:
        csv_reader = csv.DictReader(StringIO(content))

        for row in csv_reader:
            # Extract idiom text from common column names
            idiom_text = (
                row.get("idiom")
                or row.get("phrase")
                or row.get("expression")
                or row.get("text")
                or ""
            ).strip()

            if not idiom_text:
                continue

            normalized = phrase_normalizer.normalize(idiom_text)
            if normalized and phrase_normalizer.is_phrase(normalized):
                phrase = _create_phrase(idiom_text, normalized, language, is_idiom=True)
                phrases.append(phrase)

    except Exception as e:
        logger.warning(f"Failed to parse CSV idioms: {e}")
        return [], []

    return [], phrases


def parse_json_phrasal_verbs(
    content: str, language: Language, phrase_normalizer: PhraseNormalizer
) -> ParseResult:
    """Parse JSON format with phrasal verbs."""
    phrases = []

    try:
        data = json.loads(content)

        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    # Extract verb text
                    verb_text = (
                        entry.get("verb") or entry.get("phrasal_verb") or entry.get("phrase") or ""
                    ).strip()

                    if not verb_text:
                        continue

                    # Clean up verb text
                    verb_text = verb_text.replace("*", "").replace("+", "").strip()

                    normalized = phrase_normalizer.normalize(verb_text)
                    if normalized and phrase_normalizer.is_phrase(normalized):
                        phrase = _create_phrase(verb_text, normalized, language, is_idiom=False)
                        phrases.append(phrase)

    except Exception as e:
        logger.warning(f"Failed to parse JSON phrasal verbs: {e}")
        return [], []

    return [], phrases


def parse_scraped_data(
    content: dict[str, Any], language: Language, phrase_normalizer: PhraseNormalizer
) -> ParseResult:
    """Parse data returned by custom scrapers."""
    words = []
    phrases = []

    # Extract words if present
    if "words" in content and isinstance(content["words"], list):
        for word in content["words"]:
            if isinstance(word, str):
                normalized = phrase_normalizer.normalize(word)
                if normalized:
                    words.append(normalized)

    # Extract phrases if present
    if "phrases" in content and isinstance(content["phrases"], list):
        for phrase_data in content["phrases"]:
            phrase_text = (
                phrase_data if isinstance(phrase_data, str) else phrase_data.get("text", "")
            )
            if phrase_text:
                normalized = phrase_normalizer.normalize(phrase_text)
                if normalized and phrase_normalizer.is_phrase(normalized):
                    is_idiom = (
                        phrase_data.get("is_idiom", False)
                        if isinstance(phrase_data, dict)
                        else False
                    )
                    phrase = _create_phrase(phrase_text, normalized, language, is_idiom=is_idiom)
                    phrases.append(phrase)

    return words, phrases


# Parser registry - maps LexiconFormat enum to parser functions
PARSERS = {
    LexiconFormat.TEXT_LINES: parse_text_lines,
    LexiconFormat.JSON_IDIOMS: parse_json_idioms,
    LexiconFormat.FREQUENCY_LIST: parse_frequency_list,
    LexiconFormat.JSON_DICT: parse_json_dict,
    LexiconFormat.JSON_ARRAY: parse_json_array,
    LexiconFormat.JSON_GITHUB_API: parse_github_api,
    LexiconFormat.CSV_IDIOMS: parse_csv_idioms,
    LexiconFormat.JSON_PHRASAL_VERBS: parse_json_phrasal_verbs,
}


def parse_content(
    lexicon_format: LexiconFormat | str,
    content: Any,
    language: Language,
    phrase_normalizer: PhraseNormalizer,
) -> ParseResult:
    """Parse content using the appropriate parser function."""
    # Convert string to enum if needed for backward compatibility
    if isinstance(lexicon_format, str):
        try:
            lexicon_format = LexiconFormat(lexicon_format)
        except ValueError:
            raise ValueError(f"Unknown format: {lexicon_format}")

    # Handle scraped data specially since it takes a dict
    if lexicon_format == LexiconFormat.CUSTOM_SCRAPER:
        return parse_scraped_data(content, language, phrase_normalizer)

    parser_func = PARSERS.get(lexicon_format)
    if not parser_func:
        raise ValueError(f"Unknown format: {lexicon_format}")

    # Convert content to string for text-based parsers
    text_content = str(content) if not isinstance(content, str) else content
    return parser_func(text_content, language, phrase_normalizer)
