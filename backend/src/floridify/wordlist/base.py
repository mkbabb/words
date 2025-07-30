"""Base models for wordlist entities."""

from datetime import datetime

from pydantic import BaseModel, Field


class BaseMetadata(BaseModel):
    """Base metadata for wordlist-related entities with usage tracking."""

    # Core timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    # Access tracking
    last_accessed: datetime | None = Field(default=None, description="Last time accessed")
    access_count: int = Field(default=0, ge=0, description="Number of times accessed")

    # Version tracking
    version: int = Field(default=1, ge=1, description="Version number for optimistic locking")

    def mark_accessed(self) -> None:
        """Mark entity as accessed."""
        self.last_accessed = datetime.now()
        self.access_count += 1
        self.updated_at = datetime.now()

    def mark_updated(self) -> None:
        """Mark entity as updated."""
        self.updated_at = datetime.now()
        self.version += 1
