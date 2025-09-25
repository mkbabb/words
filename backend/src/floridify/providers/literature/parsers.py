"""Literature text parsing utilities."""

from __future__ import annotations

import re
from typing import Any


def parse_text(content: str | dict[str, Any]) -> str:
    """Parse raw content into clean text.

    Args:
        content: Raw content from scraper (text or structured data)

    Returns:
        Clean text content

    """
    if isinstance(content, dict):
        # Extract text from structured data
        if "text" in content:
            return str(content["text"])
        if "content" in content:
            return str(content["content"])
        if "body" in content:
            return str(content["body"])
        # Try to extract from nested structure
        for key in ["data", "result", "response"]:
            if key in content and isinstance(content[key], str):
                return str(content[key])
        return str(content)

    # Clean text content
    text = str(content)

    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # Remove common artifacts
    text = re.sub(r"^\s*Page \d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

    return text.strip()


def parse_markdown(content: str | dict[str, Any]) -> str:
    """Parse Markdown content to plain text.

    For now, just strips basic markdown formatting.
    """
    text = parse_text(content)

    # Remove markdown headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Remove bold/italic markers
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)

    # Remove links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    return text


def parse_html(content: str | dict[str, Any]) -> str:
    """Parse HTML content to plain text.

    Simple HTML stripping - proper implementation would use BeautifulSoup.
    """
    text = parse_text(content)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode common HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")

    return text


def parse_epub(content: str | dict[str, Any]) -> str:
    """Parse EPUB content to plain text.

    Stub implementation - full version would extract from EPUB structure.
    """
    # For now, just use plain text parser
    # Full implementation would unzip EPUB and extract chapters
    return parse_text(content)


def parse_pdf(content: str | dict[str, Any]) -> str:
    """Parse PDF content to plain text.

    Stub implementation - full version would use PyPDF2 or similar.
    """
    # For now, just use plain text parser
    # Full implementation would extract text from PDF
    return parse_text(content)


def extract_metadata(content: str | dict[str, Any]) -> dict[str, Any]:
    """Extract metadata from content.

    Args:
        content: Raw content from scraper

    Returns:
        Extracted metadata dictionary

    """
    metadata = {}

    if isinstance(content, dict):
        # Extract known metadata fields
        for field in ["title", "author", "year", "genre", "language", "source"]:
            if field in content:
                metadata[field] = content[field]

    return metadata
