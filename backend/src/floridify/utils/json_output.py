"""JSON output utilities for CLI and API isomorphism.

This module provides utilities to serialize responses to JSON format,
ensuring that CLI --json output matches API responses exactly.

KISS: Keep serialization simple and predictable
DRY: Single source of truth for JSON formatting
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


def json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for types not handled by default json module.

    Handles:
    - datetime objects -> ISO format strings
    - Enums -> their values
    - Pydantic models -> dict representation
    - Sets -> lists
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, set):
        return list(obj)
    else:
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def to_json(data: Any, indent: int | None = 2, sort_keys: bool = False) -> str:
    """Convert data to JSON string with custom serialization.

    Args:
        data: Data to serialize (BaseModel, dict, list, etc.)
        indent: Indentation level (None for compact, 2 for pretty)
        sort_keys: Whether to sort dictionary keys

    Returns:
        JSON string representation

    Example:
        >>> from models.responses import LookupResponse
        >>> response = LookupResponse(word="test", ...)
        >>> json_str = to_json(response)
        >>> print(json_str)
        {
          "word": "test",
          ...
        }
    """
    # If it's a Pydantic model, use model_dump first
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")

    return json.dumps(
        data,
        default=json_serializer,
        indent=indent,
        sort_keys=sort_keys,
        ensure_ascii=False,  # Allow unicode characters
    )


def print_json(data: Any, indent: int | None = 2, sort_keys: bool = False) -> None:
    """Print data as JSON to stdout.

    Convenience function for CLI commands using --json flag.

    Args:
        data: Data to print
        indent: Indentation level
        sort_keys: Whether to sort keys
    """
    print(to_json(data, indent=indent, sort_keys=sort_keys))


def format_json_compact(data: Any) -> str:
    """Format as compact JSON (no indentation).

    Useful for logging or single-line output.
    """
    return to_json(data, indent=None, sort_keys=False)


def format_json_pretty(data: Any) -> str:
    """Format as pretty JSON with indentation and sorted keys.

    Useful for human-readable output.
    """
    return to_json(data, indent=2, sort_keys=True)
