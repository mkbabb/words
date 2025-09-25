"""Batch operation tracking for providers."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from beanie import Document
from pydantic import Field

from ..models.base import BaseMetadata, Language
from ..models.dictionary import DictionaryProvider


class BatchStatus(str, Enum):
    """Status of a batch download operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class BatchOperation(Document, BaseMetadata):
    """Track batch download/processing operations for resume capability."""

    # Operation identification
    operation_id: str = Field(description="Unique operation identifier")
    operation_type: str = Field(description="Type of operation")
    provider: DictionaryProvider

    # Progress tracking
    status: BatchStatus = Field(default=BatchStatus.PENDING)
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0

    # Checkpoint data for resume
    checkpoint: dict[str, Any] = Field(default_factory=dict)

    # Corpus information
    corpus_name: str | None = None
    corpus_language: Language = Field(default=Language.ENGLISH)

    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_checkpoint_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Error tracking
    errors: list[dict[str, Any]] = Field(default_factory=list)

    # Statistics
    statistics: dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "batch_operations"
        indexes = [
            "operation_id",
            [("provider", 1), ("status", 1)],
            [("operation_type", 1), ("status", 1)],
            "started_at",
        ]

    def update_checkpoint(self, data: dict[str, Any]) -> None:
        """Update checkpoint data for resume capability."""
        self.checkpoint.update(data)
        self.last_checkpoint_at = datetime.now(UTC)

    def add_error(self, word: str, error: str, error_code: str | None = None) -> None:
        """Add an error to the error log."""
        self.errors.append(
            {
                "word": word,
                "error": error,
                "error_code": error_code,
                "timestamp": datetime.now(UTC),
            },
        )
        self.failed_items += 1
