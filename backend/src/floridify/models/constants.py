"""
Model-related constants and enums.

Contains enums for data models, dictionary structures, and literature sources.
"""

from __future__ import annotations

from enum import Enum


class LiteratureSourceType(Enum):
    """Enumeration for different types of literature sources."""

    BOOK = "book"
    ARTICLE = "article"
    DOCUMENT = "document"
