"""Input sanitization utilities for security."""

from __future__ import annotations

import re
from typing import Any


def sanitize_mongodb_input(value: str) -> str:
    """Sanitize user input to prevent MongoDB injection attacks.

    Removes MongoDB operators and special characters that could be used
    for injection attacks.

    Args:
        value: Raw user input string

    Returns:
        Sanitized string safe for MongoDB queries

    """
    if not isinstance(value, str):
        return str(value)

    # Remove MongoDB operators ($, {, })
    sanitized = re.sub(r"[${}]", "", value)

    # Remove null bytes
    sanitized = sanitized.replace("\x00", "")

    # Trim whitespace
    sanitized = sanitized.strip()

    # Limit length to prevent DoS
    max_length = 1000
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def validate_word_input(word: str) -> str:
    """Validate and sanitize word input for dictionary lookups.

    Args:
        word: Raw word input

    Returns:
        Validated and sanitized word

    Raises:
        ValueError: If word is invalid

    """
    # Basic sanitization
    word = sanitize_mongodb_input(word)

    # Check minimum length
    if not word or len(word) < 1:
        raise ValueError("Word cannot be empty")

    # Check maximum length
    if len(word) > 100:
        raise ValueError("Word too long (max 100 characters)")

    # Allow letters, spaces, hyphens, apostrophes, and common diacritics
    if not re.match(r"^[\w\s\-\'àâäçèéêëîïôùûüÿæœÀÂÄÇÈÉÊËÎÏÔÙÛÜŸÆŒ]+$", word):
        raise ValueError("Word contains invalid characters")

    return word


def sanitize_field_name(field: str) -> str:
    """Sanitize field names to prevent injection attacks.

    Args:
        field: Raw field name

    Returns:
        Sanitized field name

    Raises:
        ValueError: If field name is invalid

    """
    # Only allow alphanumeric and underscore
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", field):
        raise ValueError(f"Invalid field name: {field}")

    # Prevent access to private/magic attributes
    if field.startswith("_"):
        raise ValueError(f"Cannot access private field: {field}")

    return field


def sanitize_query_params(params: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a dictionary of query parameters.

    Args:
        params: Raw query parameters

    Returns:
        Sanitized parameters

    """
    sanitized: dict[str, Any] = {}

    for key, value in params.items():
        # Sanitize key
        clean_key = sanitize_field_name(key)

        # Sanitize value based on type
        if isinstance(value, str):
            sanitized[clean_key] = sanitize_mongodb_input(value)
        elif isinstance(value, list | tuple):
            sanitized[clean_key] = [
                sanitize_mongodb_input(v) if isinstance(v, str) else v for v in value
            ]
        else:
            sanitized[clean_key] = value

    return sanitized
