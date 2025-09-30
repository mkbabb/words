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


def parse_epub(content: bytes | str | dict[str, Any]) -> str:
    """Parse EPUB content to plain text.

    Extracts text from all chapters in the EPUB document.

    Args:
        content: EPUB content as bytes, or text/dict for fallback

    Returns:
        Clean text extracted from EPUB chapters

    """
    # Handle dict/string input - fallback to text parser
    if isinstance(content, dict):
        if "content" in content:
            content = content["content"]
        else:
            return parse_text(content)

    if isinstance(content, str):
        return parse_text(content)

    # Parse EPUB from bytes
    try:
        import io

        import ebooklib
        from bs4 import BeautifulSoup
        from ebooklib import epub

        book = epub.read_epub(io.BytesIO(content))
        text_parts = []

        # Extract text from all document items (chapters)
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text()
            if text.strip():
                text_parts.append(text)

        full_text = "\n\n".join(text_parts)
        return parse_text(full_text)  # Clean using existing logic

    except Exception:
        # Fall back to text parser on any error
        return parse_text(str(content))


def parse_pdf(content: bytes | str | dict[str, Any]) -> str:
    """Parse PDF content to plain text.

    Extracts text from all pages in the PDF document.

    Args:
        content: PDF content as bytes, or text/dict for fallback

    Returns:
        Clean text extracted from PDF pages

    """
    # Handle dict/string input - fallback to text parser
    if isinstance(content, dict):
        if "content" in content:
            content = content["content"]
        else:
            return parse_text(content)

    if isinstance(content, str):
        return parse_text(content)

    # Parse PDF from bytes
    try:
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        text_parts = []

        # Extract text from all pages
        for page in reader.pages:
            text = page.extract_text()
            if text.strip():
                text_parts.append(text)

        full_text = "\n\n".join(text_parts)
        return parse_text(full_text)  # Clean using existing logic

    except Exception:
        # Fall back to text parser on any error
        return parse_text(str(content))


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
