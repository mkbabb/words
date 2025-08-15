"""Data models for corpus management.

Provides data structures for storing and managing corpus data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..models.dictionary import Language
from ..models.versioned import VersionInfo


@dataclass
class LexiconData:
    """Base class for lexicon data storage.

    Stores vocabulary, frequencies, and metadata for a corpus.
    """

    # Core vocabulary data
    vocabulary: list[str] = field(default_factory=list)
    frequencies: list[int] = field(default_factory=list)

    # Metadata
    corpus_name: str = ""
    language: Language = Language.ENGLISH
    source_id: str = ""
    sources: list[str] = field(default_factory=list)

    # Statistics
    total_words: int = 0
    unique_words: int = 0
    unique_word_count: int = 0  # Alias for unique_words
    total_entries: int = 0  # Total number of entries
    vocabulary_hash: str | None = None

    # Version information
    version_info: VersionInfo | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Calculate statistics after initialization."""
        if self.vocabulary:
            self.unique_words = len(set(self.vocabulary))
            self.unique_word_count = self.unique_words
            self.total_words = sum(self.frequencies) if self.frequencies else len(self.vocabulary)
            self.total_entries = len(self.vocabulary)

    def model_dump(self) -> dict[str, Any]:
        """Export data as dictionary for serialization."""
        return {
            "vocabulary": self.vocabulary,
            "frequencies": self.frequencies,
            "corpus_name": self.corpus_name,
            "language": self.language.value
            if isinstance(self.language, Language)
            else self.language,
            "source_id": self.source_id,
            "sources": self.sources,
            "total_words": self.total_words,
            "unique_words": self.unique_words,
            "unique_word_count": self.unique_word_count,
            "total_entries": self.total_entries,
            "vocabulary_hash": self.vocabulary_hash,
            "version_info": self.version_info,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "metadata": self.metadata,
        }

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> LexiconData:
        """Create instance from dictionary."""
        # Convert ISO datetime strings back to datetime objects
        for date_field in ["created_at", "updated_at", "last_updated"]:
            if date_field in data and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])

        # Convert language string to enum if needed
        if "language" in data and isinstance(data["language"], str):
            data["language"] = Language(data["language"])

        return cls(**data)


@dataclass
class LiteratureLexiconData(LexiconData):
    """Extended lexicon data for literature corpora.

    Includes author and work information.
    """

    # Literature-specific fields
    authors: list[str] = field(default_factory=list)
    works: list[str] = field(default_factory=list)
    total_works: int = 0

    def __post_init__(self) -> None:
        """Calculate statistics after initialization."""
        super().__post_init__()
        if self.works:
            self.total_works = len(self.works)


@dataclass
class CorpusMetadata:
    """Metadata for corpus tracking and versioning."""

    corpus_type: str  # "language", "literature", "custom"
    corpus_name: str
    corpus_hash: str

    # Source information
    source_id: str
    source_url: str | None = None

    # Statistics
    word_count: int = 0
    unique_words: int = 0

    # Version tracking
    version_info: VersionInfo | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime | None = None
    access_count: int = 0


__all__ = [
    "LexiconData",
    "LiteratureLexiconData",
    "CorpusMetadata",
]
