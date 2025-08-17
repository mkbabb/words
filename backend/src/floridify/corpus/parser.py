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

from ..models.dictionary import Language
from ..text import is_phrase, normalize
from ..utils.logging import get_logger

logger = get_logger(__name__)

ParseResult = tuple[list[str], list[str]]


def parse_text_lines(content: str, language: Language) -> ParseResult:
    """Parse simple text file with one word per line."""
    words = []
    phrases = []

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        normalized = normalize(line)
        if not normalized:
            continue

        if is_phrase(normalized):
            phrases.append(normalized)
        else:
            words.append(normalized)

    return words, phrases


def parse_frequency_list(content: str, language: Language) -> ParseResult:
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
        normalized = normalize(word)
        if not normalized:
            continue

        if is_phrase(normalized):
            phrases.append(normalized)
        else:
            words.append(normalized)

    return words, phrases


def parse_json_idioms(content: str, language: Language) -> ParseResult:
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

        normalized = normalize(phrase_text)
        if normalized and is_phrase(normalized):
            phrases.append(normalized)

    return [], phrases


def parse_json_dict(content: str, language: Language) -> ParseResult:
    """Parse JSON dictionary format."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return [], []

    words = []
    phrases = []

    if isinstance(data, dict):
        for key in data.keys():
            normalized = normalize(key)
            if not normalized:
                continue

            if is_phrase(normalized):
                phrases.append(normalized)
            else:
                words.append(normalized)

    return words, phrases


def parse_json_array(content: str, language: Language) -> ParseResult:
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
                normalized = normalize(item)
                if not normalized:
                    continue

                if is_phrase(normalized):
                    phrases.append(normalized)
                else:
                    words.append(normalized)

    return words, phrases


def parse_github_api(content: str, language: Language) -> ParseResult:
    """Parse GitHub API response format."""
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "content" in data:
            # Decode base64 content
            decoded_content = base64.b64decode(data["content"]).decode("utf-8")
            # Delegate to JSON array parser
            return parse_json_array(decoded_content, language)
    except Exception:
        pass
    return [], []


def parse_csv_idioms(content: str, language: Language) -> ParseResult:
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

            normalized = normalize(idiom_text)
            if normalized and is_phrase(normalized):
                phrases.append(normalized)

    except Exception as e:
        logger.warning(f"Failed to parse CSV idioms: {e}")
        return [], []

    return [], phrases


def parse_json_phrasal_verbs(content: str, language: Language) -> ParseResult:
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

                    normalized = normalize(verb_text)
                    if normalized and is_phrase(normalized):
                        phrases.append(normalized)

    except Exception as e:
        logger.warning(f"Failed to parse JSON phrasal verbs: {e}")
        return [], []

    return [], phrases


def parse_scraped_data(
    content: dict[str, Any],
    language: Language,
) -> ParseResult:
    """Parse data returned by custom scrapers."""
    words = []
    phrases = []

    # Extract words if present
    if "words" in content and isinstance(content["words"], list):
        for word in content["words"]:
            if isinstance(word, str):
                normalized = normalize(word)
                if normalized:
                    words.append(normalized)

    # Extract phrases if present
    if "phrases" in content and isinstance(content["phrases"], list):
        for phrase_data in content["phrases"]:
            phrase_text = (
                phrase_data if isinstance(phrase_data, str) else phrase_data.get("text", "")
            )
            if phrase_text:
                normalized = normalize(phrase_text)
                if normalized and is_phrase(normalized):
                    phrases.append(normalized)

    return words, phrases
