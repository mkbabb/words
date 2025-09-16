"""Utility functions for wordlist management."""

from datetime import UTC, datetime


def generate_wordlist_name() -> str:
    """Generate a default name for a new wordlist based on current timestamp."""
    now = datetime.now(UTC)
    return now.strftime("WordList_%Y%m%d_%H%M%S")
