"""Logging utilities for verbose output control."""

from __future__ import annotations

from typing import Any

_verbose_enabled = False


def set_verbose(enabled: bool) -> None:
    """Set global verbose logging state.

    Args:
        enabled: Whether to enable verbose logging
    """
    global _verbose_enabled
    _verbose_enabled = enabled


def is_verbose() -> bool:
    """Check if verbose logging is enabled.

    Returns:
        True if verbose logging is enabled
    """
    return _verbose_enabled


def vprint(*args: Any, **kwargs: Any) -> None:
    """Print only if verbose mode is enabled.

    Args:
        *args: Arguments to print
        **kwargs: Keyword arguments to pass to print
    """
    if _verbose_enabled:
        print(*args, **kwargs)
