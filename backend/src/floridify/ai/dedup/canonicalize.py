"""Text canonicalization for definition deduplication.

Ported from gaggle's ngram_dedup._canonicalize() and adapted for
dictionary definition texts.
"""

from __future__ import annotations

import re


def canonicalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace.

    Ported from gaggle/content/generate/pipeline/ngram_dedup.py:30-34.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_content_words(text: str) -> set[str]:
    """Extract significant content words from text, filtering stopwords.

    Used as a pre-filter for fuzzy matching — only compare definitions
    that share at least one meaningful word.
    """
    from ...text.constants import ENGLISH_STOPWORDS

    canonical = canonicalize(text)
    words = set(canonical.split())
    return words - ENGLISH_STOPWORDS
