"""User model for authentication."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from beanie import Document
from pydantic import Field
from pymongo import IndexModel


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
