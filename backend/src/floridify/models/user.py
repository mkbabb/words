"""User model for authentication."""

from __future__ import annotations

from datetime import UTC, datetime

from beanie import Document
from pydantic import Field


class User(Document):
    """User document backed by Clerk authentication.

    The clerk_id is the primary identifier from Clerk's JWT.
    """

    clerk_id: str = Field(..., description="Clerk user ID (sub claim)")
    email: str | None = Field(default=None, description="Primary email address")
    username: str | None = Field(default=None, description="Display name")
    role: str = Field(default="user", description="User role: user | admin")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_login: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "users"
        indexes = [
            "clerk_id",
            "email",
        ]

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
