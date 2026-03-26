"""User model for authentication."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from beanie import Document
from pydantic import Field
from pymongo import IndexModel

from ..wordlist.stats import LearningStats


class UserRole(StrEnum):
    """User role tiers."""

    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"


class User(Document):
    """User document backed by Clerk authentication.

    The clerk_id is the primary identifier from Clerk's JWT.
    """

    clerk_id: str = Field(..., description="Clerk user ID (sub claim)")
    email: str | None = Field(default=None, description="Primary email address")
    username: str | None = Field(default=None, description="Display name")
    avatar_url: str | None = Field(default=None, description="Profile avatar URL")
    role: UserRole = Field(default=UserRole.USER, description="User role tier")
    preferences: dict[str, Any] = Field(
        default_factory=dict, description="Synced frontend preferences"
    )
    global_learning_stats: LearningStats = Field(
        default_factory=LearningStats,
        description="Aggregated learning stats across all wordlists",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_login: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("clerk_id", 1)], unique=True),
            "email",
        ]

    @property
    def is_premium(self) -> bool:
        return self.role in (UserRole.PREMIUM, UserRole.ADMIN)

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN


class UserHistory(Document):
    """User search and lookup history for cross-device sync."""

    clerk_id: str = Field(..., description="Clerk user ID")
    search_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Recent search queries with timestamps"
    )
    lookup_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Recent word lookups with timestamps"
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "user_history"
        indexes = [
            IndexModel([("clerk_id", 1)], unique=True),
        ]

    def add_lookup(self, word: str) -> None:
        """Add a lookup entry, deduplicating by word and capping at 100."""
        now = datetime.now(UTC).isoformat()
        # Remove existing entry for same word (keep most recent)
        self.lookup_history = [
            entry for entry in self.lookup_history if entry.get("word", "").lower() != word.lower()
        ]
        self.lookup_history.insert(0, {"word": word, "timestamp": now})
        # Cap at 100
        self.lookup_history = self.lookup_history[:100]
        self.updated_at = datetime.now(UTC)

    def add_search(self, query: str, mode: str = "dictionary") -> None:
        """Add a search entry, deduplicating by query and capping at 100."""
        now = datetime.now(UTC).isoformat()
        self.search_history = [
            entry
            for entry in self.search_history
            if entry.get("query", "").lower() != query.lower()
        ]
        self.search_history.insert(0, {"query": query, "mode": mode, "timestamp": now})
        self.search_history = self.search_history[:100]
        self.updated_at = datetime.now(UTC)
