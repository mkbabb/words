"""Word of the Day models for daily vocabulary learning."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field

from .base import BaseMetadata


class NotificationFrequency(str, Enum):
    """Notification frequency options."""

    EVERY_15_MINUTES = "15min"
    EVERY_30_MINUTES = "30min"
    EVERY_HOUR = "1hour"
    EVERY_2_HOURS = "2hours"
    EVERY_4_HOURS = "4hours"
    TWICE_DAILY = "twice_daily"
    DAILY = "daily"
    EVERY_2_DAYS = "2days"
    WEEKLY = "weekly"

    @property
    def minutes(self) -> int:
        """Get the frequency in minutes."""
        mapping = {
            self.EVERY_15_MINUTES: 15,
            self.EVERY_30_MINUTES: 30,
            self.EVERY_HOUR: 60,
            self.EVERY_2_HOURS: 120,
            self.EVERY_4_HOURS: 240,
            self.TWICE_DAILY: 720,  # 12 hours
            self.DAILY: 1440,  # 24 hours
            self.EVERY_2_DAYS: 2880,  # 48 hours
            self.WEEKLY: 10080,  # 7 days
        }
        return mapping[self]


class WordOfTheDayEntry(BaseModel):
    """A single Word of the Day entry."""

    word: str = Field(..., description="The word")
    definition: str = Field(..., description="Clear, concise definition")
    etymology: str = Field(..., description="Brief origin and historical development")
    example_usage: str = Field(..., description="Natural sentence demonstrating proper usage")
    fascinating_fact: str = Field(
        ..., description="Interesting linguistic, cultural, or historical insight"
    )
    difficulty_level: str = Field(..., description="Difficulty level: intermediate or advanced")
    memorable_aspect: str = Field(
        ..., description="What makes this word particularly worth learning"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence in word selection")
    generated_at: datetime = Field(
        default_factory=datetime.now, description="When this entry was generated"
    )
    sent_at: datetime | None = Field(default=None, description="When this entry was sent to users")


class WordOfTheDayBatch(Document, BaseMetadata):
    """A batch of Word of the Day entries with configuration."""

    context: str = Field(default="", description="Context steering for word generation")
    frequency: NotificationFrequency = Field(
        default=NotificationFrequency.DAILY, description="Notification frequency"
    )
    max_seen_words: int = Field(default=500, description="Maximum number of seen words to track")
    active: bool = Field(default=True, description="Whether this batch is active")

    # Word pools
    current_batch: list[WordOfTheDayEntry] = Field(
        default_factory=list, description="Current batch of unsent words"
    )
    sent_words: list[str] = Field(default_factory=list, description="Words that have been sent")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    last_generation: datetime | None = Field(default=None, description="Last batch generation time")
    last_sent: datetime | None = Field(default=None, description="Last word sent time")
    next_send_time: datetime | None = Field(default=None, description="Next scheduled send time")

    # Statistics
    total_words_sent: int = Field(default=0, ge=0, description="Total words sent to users")
    batch_count: int = Field(default=0, ge=0, description="Number of batches generated")

    class Settings:
        name = "word_of_the_day_batches"
        indexes = [
            "active",
            "next_send_time",
            "created_at",
            "updated_at",
        ]

    def get_next_word(self) -> WordOfTheDayEntry | None:
        """Get the next word to send."""
        if not self.current_batch:
            return None
        return self.current_batch[0]

    def mark_word_sent(self, word: str) -> None:
        """Mark a word as sent and remove from current batch."""
        if self.current_batch and self.current_batch[0].word == word:
            sent_entry = self.current_batch.pop(0)
            sent_entry.sent_at = datetime.now()

            # Add to sent words list, maintaining max size
            self.sent_words.append(word)
            if len(self.sent_words) > self.max_seen_words:
                self.sent_words = self.sent_words[-self.max_seen_words :]

            # Update statistics
            self.total_words_sent += 1
            self.last_sent = datetime.now()
            self.updated_at = datetime.now()

            # Calculate next send time
            self.next_send_time = datetime.now() + timedelta(minutes=self.frequency.minutes)

    def needs_new_batch(self) -> bool:
        """Check if a new batch of words is needed."""
        return len(self.current_batch) < 10  # Generate new batch when under 10 words

    def add_words_to_batch(self, words: list[WordOfTheDayEntry]) -> None:
        """Add new words to the current batch."""
        self.current_batch.extend(words)
        self.last_generation = datetime.now()
        self.batch_count += 1
        self.updated_at = datetime.now()

    def is_due_for_sending(self) -> bool:
        """Check if it's time to send the next word."""
        if not self.next_send_time:
            return True  # First word
        return datetime.now() >= self.next_send_time

    def get_context_for_generation(self) -> dict[str, Any]:
        """Get context parameters for AI word generation."""
        return {
            "context": self.context if self.context else None,
            "previous_words": self.sent_words[-50:] if self.sent_words else None,  # Last 50 words
        }

    async def initialize_first_batch(self) -> None:
        """Initialize the first batch if needed."""
        if not self.current_batch and not self.next_send_time:
            self.next_send_time = datetime.now()
            await self.save()


class WordOfTheDayConfig(Document, BaseMetadata):
    """Global configuration for Word of the Day system."""

    default_batch_size: int = Field(
        default=20, ge=5, le=100, description="Default batch size for generation"
    )
    min_batch_threshold: int = Field(
        default=5, ge=1, le=20, description="Generate new batch when below this threshold"
    )
    max_previous_words: int = Field(
        default=100, ge=10, le=1000, description="Max previous words to send to AI"
    )
    generation_enabled: bool = Field(
        default=True, description="Whether to generate new batches automatically"
    )

    # Singleton pattern - there should only be one config
    config_id: str = Field(default="default", description="Config identifier")

    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    class Settings:
        name = "word_of_the_day_config"
        indexes = ["config_id"]

    @classmethod
    async def get_default(cls) -> WordOfTheDayConfig:
        """Get or create the default configuration."""
        config = await cls.find_one({"config_id": "default"})
        if not config:
            config = cls(config_id="default")
            await config.create()
        return config
