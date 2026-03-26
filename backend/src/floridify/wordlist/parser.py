"""Word list parsing functionality - multi-format support."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ParsedWordEntry(BaseModel):
    """Structured parsed entry with preserved frequency and notes."""

    source_text: str = Field(..., description="Original parsed text")
    frequency: int = Field(default=1, ge=1, description="Occurrence count")
    notes: str | None = Field(default=None, description="Optional notes")


class ParsedWordList(BaseModel):
    """Result of parsing a word list file."""

    entries: list[ParsedWordEntry] = Field(..., description="Extracted structured entries")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Parsing metadata")
    source_file: str | None = Field(default=None, description="Source file path")

    @property
    def words(self) -> list[str]:
        """Compatibility helper for legacy callers that only need text."""
        return [entry.source_text for entry in self.entries]


def collapse_entries(entries: list[ParsedWordEntry]) -> list[ParsedWordEntry]:
    """Merge duplicate entries while summing frequency and preserving first notes."""
    collapsed: dict[str, ParsedWordEntry] = {}
    for entry in entries:
        key = preserve_text_format(entry.source_text).lower()
        existing = collapsed.get(key)
        if existing:
            existing.frequency += entry.frequency
            if entry.notes and not existing.notes:
                existing.notes = entry.notes
        else:
            collapsed[key] = ParsedWordEntry(
                source_text=preserve_text_format(entry.source_text),
                frequency=entry.frequency,
                notes=entry.notes,
            )
    return list(collapsed.values())


def _coerce_frequency(value: Any) -> int:
    """Coerce a possibly malformed frequency value to a safe positive integer."""
    try:
        return max(1, int(str(value).strip() or "1"))
    except (TypeError, ValueError, AttributeError):
        return 1


def preserve_text_format(text: str) -> str:
    """Normalize text aggressively while preserving word integrity.

    - Preserves Unicode characters and diacritics
    - Strips excessive whitespace
    - Removes zero-width characters
    - Normalizes quotes and dashes
    """
    # Normalize Unicode (NFC = canonical composition)
    text = unicodedata.normalize("NFC", text)

    # Remove zero-width characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    # Normalize curly quotes/apostrophes to their ASCII equivalents.
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("„", '"')
        .replace("‟", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("‛", "'")
    )

    # Normalize dashes (keep hyphens for compound words)
    text = text.replace("—", "-").replace("–", "-")

    # Strip and collapse whitespace
    text = " ".join(text.split())

    return text


def extract_word_from_line(line: str) -> str | list[str] | None:
    """Extract a word or phrase from a line with various formats.

    Handles:
    - Numbered lists: "1. word" or "1) word"
    - Bulleted lists: "- word", "* word", "• word"
    - Tab-separated: "1\tword"
    - Plain text: "word"

    Returns a single word, list of words, or None.
    """
    line = line.strip()
    if not line:
        return None

    # Skip comments
    if line.startswith("#"):
        return None

    # Numbered list patterns
    patterns = [
        r"^\d+[.)]\s*(.+)$",  # 1. word or 1) word
        r"^\d+\.\s+(.+)$",  # 1. word (with extra space)
        r"^\d+\t(.+)$",  # 1<tab>word
        r"^[a-zA-Z][.)]\s*(.+)$",  # a. word or a) word
    ]

    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            return preserve_text_format(match.group(1))

    # Bullet patterns
    bullet_chars = ["-", "*", "•", "·", "○", "□", "▪", "▫", "►", "▸"]
    for bullet in bullet_chars:
        if line.startswith(bullet):
            # Handle bullet with or without space
            text = line[len(bullet) :].lstrip()
            if text:
                return preserve_text_format(text)

    # Plain text - check if it's a phrase or multiple words
    normalized = preserve_text_format(line)

    # Check if it looks like a phrase
    if _looks_like_phrase(normalized):
        return normalized

    # Check for comma or semicolon separated words
    if "," in normalized or ";" in normalized:
        words = re.split(r"[,;]\s*", normalized)
        return [w.strip() for w in words if w.strip()]

    # If multiple words and not a phrase, split them
    words = normalized.split()
    if len(words) > 1:
        return words

    return normalized


def _looks_like_phrase(text: str) -> bool:
    """Determine if text is likely a single phrase vs multiple words."""
    # If it has articles, prepositions, or conjunctions, likely a phrase
    phrase_indicators = {
        "a",
        "an",
        "the",
        "of",
        "in",
        "on",
        "at",
        "by",
        "for",
        "with",
        "to",
        "and",
        "or",
        "but",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "la",
        "le",
        "de",
        "du",
        "des",
        "il",
        "et",
        "en",  # Common French
        "el",
        "los",
        "las",
        "y",
        "o",
        "del",  # Common Spanish
    }
    words = text.lower().split()

    # Single word is not a phrase
    if len(words) <= 1:
        return False

    # If it has phrase indicators, it's likely a phrase
    if any(word in phrase_indicators for word in words):
        return True

    # Common Latin/foreign phrases (exact matches)
    common_phrases = {
        "quid pro quo",
        "carpe diem",
        "et cetera",
        "ad hoc",
        "per se",
        "vice versa",
        "status quo",
        "modus operandi",
        "alma mater",
        "bona fide",
        "de facto",
        "prima facie",
        "pro bono",
        "sine qua non",
        "coup de grace",
        "deja vu",
        "faux pas",
        "raison d'etre",
        "au revoir",
        "bon appetit",
        "c'est la vie",
        "joie de vivre",
    }
    if text.lower() in common_phrases:
        return True

    # If all words are capitalized (proper noun phrase), keep together
    if all(word[0].isupper() for word in words if word):
        return True

    return False


def is_valid_word(word: str) -> bool:
    """Check if a word is valid for inclusion."""
    if not word:
        return False

    # Length constraints
    if len(word) < 1 or len(word) > 100:
        return False

    # Must contain at least one letter
    if not re.search(r"[a-zA-Z\u00C0-\u017F\u0400-\u04FF]", word):
        return False

    # Skip pure numbers or punctuation
    if re.match(r"^[\d\W\s]+$", word):
        return False

    # Skip if it contains parentheses with "should be skipped" etc
    if "should be skipped" in word.lower():
        return False

    return True


def parse_text_file(path: Path) -> ParsedWordList:
    """Parse a plain text file with various list formats."""
    logger.info(f"📄 Parsing text file: {path}")

    entries: list[ParsedWordEntry] = []
    skipped = 0

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("UTF-8 decode failed, trying latin-1")
        content = path.read_text(encoding="latin-1")

    lines = content.splitlines()

    for line in lines:
        result = extract_word_from_line(line)
        if result:
            if isinstance(result, list):
                # Multiple words from one line
                for word in result:
                    if is_valid_word(word):
                        entries.append(ParsedWordEntry(source_text=word))
                    else:
                        skipped += 1
            # Single word
            elif is_valid_word(result):
                entries.append(ParsedWordEntry(source_text=result))
            else:
                skipped += 1
        elif line.strip():  # Non-empty line was skipped
            skipped += 1

    metadata = {
        "format": "text",
        "total_lines": len(lines),
        "parsed_words": len(entries),
        "skipped_lines": skipped,
    }

    collapsed = collapse_entries(entries)
    metadata["unique_words"] = len(collapsed)
    metadata["total_words"] = sum(entry.frequency for entry in collapsed)
    return ParsedWordList(entries=collapsed, metadata=metadata, source_file=str(path))


def parse_csv_file(path: Path) -> ParsedWordList:
    """Parse a CSV file (first column contains words)."""
    logger.info(f"📊 Parsing CSV file: {path}")

    entries: list[ParsedWordEntry] = []
    skipped = 0
    has_header = False

    with open(path, newline="", encoding="utf-8") as f:
        # Detect delimiter
        sample = f.read(1024)
        f.seek(0)
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter

        reader = csv.reader(f, delimiter=delimiter)

        for i, row in enumerate(reader):
            if not row:
                continue

            # Skip header if detected
            if i == 0 and row[0]:
                # Common header words
                header_words = {
                    "word",
                    "words",
                    "term",
                    "terms",
                    "vocabulary",
                    "name",
                    "text",
                    "entry",
                }
                if row[0].lower() in header_words:
                    has_header = True
                    continue

            word = preserve_text_format(row[0])
            frequency = 1
            notes: str | None = None
            if len(row) > 1:
                frequency = _coerce_frequency(row[1])
            if len(row) > 2:
                notes = str(row[2]).strip() or None

            if is_valid_word(word):
                entries.append(
                    ParsedWordEntry(
                        source_text=word,
                        frequency=frequency,
                        notes=notes,
                    )
                )
            else:
                skipped += 1

    metadata = {
        "format": "csv",
        "delimiter": delimiter,
        "has_header": has_header,
        "parsed_words": len(entries),
        "skipped_rows": skipped,
    }

    collapsed = collapse_entries(entries)
    metadata["unique_words"] = len(collapsed)
    metadata["total_words"] = sum(entry.frequency for entry in collapsed)
    return ParsedWordList(entries=collapsed, metadata=metadata, source_file=str(path))


def parse_markdown_file(path: Path) -> ParsedWordList:
    """Parse a Markdown file extracting words from lists and tables."""
    logger.info(f"📝 Parsing Markdown file: {path}")

    entries: list[ParsedWordEntry] = []
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    in_code_block = False
    in_table = False

    for line in lines:
        # Handle code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Handle tables
        if "|" in line and not in_table:
            # Check if this is a table separator
            if re.match(r"^\s*\|[\s\-:|]+\|\s*$", line):
                in_table = True
                continue

        if in_table and "|" in line:
            # Extract first column from table
            parts = line.split("|")
            if len(parts) >= 2:
                word = preserve_text_format(parts[1])
                if is_valid_word(word):
                    entries.append(ParsedWordEntry(source_text=word))
            continue
        if in_table:
            in_table = False

        # Handle lists
        result = extract_word_from_line(line)
        if result:
            if isinstance(result, list):
                for word in result:
                    if is_valid_word(word):
                        entries.append(ParsedWordEntry(source_text=word))
            elif is_valid_word(result):
                entries.append(ParsedWordEntry(source_text=result))

    metadata = {
        "format": "markdown",
        "total_lines": len(lines),
        "parsed_words": len(entries),
    }

    collapsed = collapse_entries(entries)
    metadata["unique_words"] = len(collapsed)
    metadata["total_words"] = sum(entry.frequency for entry in collapsed)
    return ParsedWordList(entries=collapsed, metadata=metadata, source_file=str(path))


def parse_json_file(path: Path) -> ParsedWordList:
    """Parse a JSON file containing word lists."""
    logger.info(f"🗂️ Parsing JSON file: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    entries: list[ParsedWordEntry] = []

    # Handle different JSON structures
    if isinstance(data, list):
        # Direct list of words
        for item in data:
            if isinstance(item, str):
                word = preserve_text_format(item)
                if is_valid_word(word):
                    entries.append(ParsedWordEntry(source_text=word))
            elif isinstance(item, dict) and "word" in item:
                word = preserve_text_format(str(item["word"]))
                if is_valid_word(word):
                    notes_value = item.get("notes")
                    entries.append(
                        ParsedWordEntry(
                            source_text=word,
                            frequency=_coerce_frequency(item.get("frequency", 1)),
                            notes=str(notes_value).strip() or None if notes_value is not None else None,
                        )
                    )
    elif isinstance(data, dict):
        # Look for common keys
        for key in ["words", "wordlist", "vocabulary", "terms"]:
            if key in data and isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, str):
                        word = preserve_text_format(item)
                        if is_valid_word(word):
                            entries.append(ParsedWordEntry(source_text=word))
                    elif isinstance(item, dict) and "word" in item:
                        word = preserve_text_format(str(item["word"]))
                        if is_valid_word(word):
                            notes_value = item.get("notes")
                            entries.append(
                                ParsedWordEntry(
                                    source_text=word,
                                    frequency=_coerce_frequency(item.get("frequency", 1)),
                                    notes=str(notes_value).strip() or None
                                    if notes_value is not None
                                    else None,
                                )
                            )
                break

    metadata = {
        "format": "json",
        "structure": type(data).__name__,
        "parsed_words": len(entries),
    }

    collapsed = collapse_entries(entries)
    metadata["unique_words"] = len(collapsed)
    metadata["total_words"] = sum(entry.frequency for entry in collapsed)
    return ParsedWordList(entries=collapsed, metadata=metadata, source_file=str(path))


# Excel and Word parsers require additional dependencies


def parse_excel_file(path: Path) -> ParsedWordList:
    """Parse an Excel file (requires openpyxl).

    Raises:
        NotImplementedError: Excel parsing not yet implemented
    """
    raise NotImplementedError(
        "Excel file parsing not implemented. Install openpyxl to add support: pip install openpyxl"
    )


def parse_word_file(path: Path) -> ParsedWordList:
    """Parse a Word document (requires python-docx).

    Raises:
        NotImplementedError: Word document parsing not yet implemented
    """
    raise NotImplementedError(
        "Word document parsing not implemented. "
        "Install python-docx to add support: pip install python-docx"
    )


# Parser registry
PARSERS: dict[str, Callable[[Path], ParsedWordList]] = {
    ".txt": parse_text_file,
    ".csv": parse_csv_file,
    ".tsv": parse_csv_file,
    ".md": parse_markdown_file,
    ".markdown": parse_markdown_file,
    ".json": parse_json_file,
    ".jsonl": parse_json_file,
    ".xlsx": parse_excel_file,
    ".xls": parse_excel_file,
    ".docx": parse_word_file,
    ".doc": parse_word_file,
}


def parse_file(file_path: Path) -> ParsedWordList:
    """Parse word list from file with automatic format detection."""
    if not file_path.exists():
        raise FileNotFoundError(f"Word list file not found: {file_path}")

    # Get parser based on file extension
    suffix = file_path.suffix.lower()
    parser = PARSERS.get(suffix, parse_text_file)

    logger.info(f"📋 Parsing word list from: {file_path} (format: {suffix or 'text'})")

    try:
        result = parser(file_path)
        logger.info(f"✅ Successfully parsed {len(result.words)} words")

        # Add parse timestamp
        result.metadata["parse_date"] = datetime.now(UTC).isoformat() + "Z"

        return result
    except Exception as e:
        logger.error(f"❌ Failed to parse {file_path}: {e}")
        raise
