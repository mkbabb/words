"""Utility helpers for wordlist management."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime


def generate_wordlist_name(words: Iterable[str] | None = None) -> str:
    """Generate a human-friendly name for a wordlist.

    If a list of candidate words is provided, the name is derived from them;
    otherwise a timestamp-based name is produced.
    """
    if words:
        normalized = [word.strip().lower() for word in words if word.strip()]
        if normalized:
            unique = sorted(set(normalized))
            base = "-".join(unique[:2]) if len(unique) >= 2 else unique[0]
            return base[:40]

    now = datetime.now(UTC)
    return now.strftime("wordlist-%Y%m%d-%H%M%S")


def generate_wordlist_hash(words: Iterable[str]) -> str:
    """Return a stable hash for the supplied word collection."""
    normalized = sorted({word.strip().lower() for word in words if word.strip()})
    payload = "|".join(normalized)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
