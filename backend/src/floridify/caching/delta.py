"""Pure functions for delta-based version storage.

Zero I/O, deterministic, testable in isolation.
Uses DeepDiff for efficient change detection and bidirectional delta computation.
"""

from __future__ import annotations

from typing import Any

from deepdiff import DeepDiff, Delta


def compute_delta(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Compute a serializable delta from old to new content.

    The delta can reconstruct `old` from `new` via `apply_delta(new, delta)`.

    Args:
        old: Previous version content dict
        new: Current version content dict

    Returns:
        Serializable delta dict (DeepDiff flat representation)

    Examples:
        >>> old = {"a": 1, "b": 2}
        >>> new = {"a": 1, "b": 3, "c": 4}
        >>> delta = compute_delta(old, new)
        >>> apply_delta(new, delta) == old
        True
    """
    diff = DeepDiff(new, old, verbose_level=2)
    if not diff:
        return {}
    # Serialize to a portable dict format
    return diff.to_dict()


def apply_delta(snapshot: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct a previous version by applying a delta to a snapshot.

    Args:
        snapshot: The base snapshot content (newer version)
        delta: Delta dict produced by compute_delta()

    Returns:
        Reconstructed content of the older version

    Examples:
        >>> snapshot = {"a": 1, "b": 3, "c": 4}
        >>> delta = compute_delta({"a": 1, "b": 2}, snapshot)
        >>> apply_delta(snapshot, delta)
        {'a': 1, 'b': 2}
    """
    if not delta:
        return dict(snapshot)
    try:
        d = Delta(delta)
        return d + snapshot  # type: ignore[return-value]
    except Exception as e:
        raise ValueError(f"Failed to apply delta (keys: {list(delta.keys())[:5]}): {e}") from e


def reconstruct_version(
    snapshot: dict[str, Any],
    delta_chain: list[dict[str, Any]],
) -> dict[str, Any]:
    """Reconstruct a version by applying a chain of deltas to a base snapshot.

    Deltas are applied in order: each delta transforms the result toward the
    target version (further back in history).

    Args:
        snapshot: Base snapshot content (the most recent full snapshot)
        delta_chain: Ordered list of deltas, from newest to oldest

    Returns:
        Reconstructed content at the target version
    """
    result = dict(snapshot)
    for delta in delta_chain:
        result = apply_delta(result, delta)
    return result


def compute_diff_between(
    a: dict[str, Any],
    b: dict[str, Any],
) -> dict[str, Any]:
    """Compute a human-readable diff between two content dicts.

    Unlike compute_delta, this is meant for display/API responses rather than
    reconstruction. Returns a rich diff with type information.

    Args:
        a: First content dict (typically older)
        b: Second content dict (typically newer)

    Returns:
        Dict with categorized changes (values_changed, items_added, items_removed, etc.)
    """
    import json

    diff = DeepDiff(a, b, verbose_level=2)
    if not diff:
        return {}
    # Round-trip through JSON to ensure all values are JSON-serializable
    # (DeepDiff's type_changes includes Python type objects like <class 'str'>)
    return json.loads(json.dumps(diff.to_dict(), default=str))


def compute_field_level_changes(
    old: dict[str, Any],
    new: dict[str, Any],
    max_value_length: int = 200,
) -> list[dict[str, str | None]]:
    """Extract structured field-level changes from two content dicts.

    Returns a list of FieldChange-shaped dicts with field_path, change_type,
    and truncated old/new values suitable for UI display.

    Args:
        old: Previous version content
        new: Current version content
        max_value_length: Truncate values longer than this

    Returns:
        List of {field_path, change_type, old_value, new_value} dicts
    """
    import json as _json

    diff = DeepDiff(old, new, verbose_level=2)
    if not diff:
        return []

    def _truncate(val: Any) -> str | None:
        if val is None:
            return None
        s = str(val) if not isinstance(val, str) else val
        return s[:max_value_length] + "..." if len(s) > max_value_length else s

    def _parse_path(path: str) -> str:
        """Convert DeepDiff path like "root['etymology']['text']" to "etymology.text"."""
        import re

        parts = re.findall(r"\['([^']+)'\]|\[(\d+)\]", path)
        segments = []
        for key, idx in parts:
            if key:
                segments.append(key)
            elif idx:
                segments.append(f"[{idx}]")
        return ".".join(segments) if segments else path

    changes: list[dict[str, str | None]] = []
    diff_dict = _json.loads(_json.dumps(diff.to_dict(), default=str))

    for path, change in (diff_dict.get("values_changed") or {}).items():
        changes.append(
            {
                "field_path": _parse_path(path),
                "change_type": "modified",
                "old_value": _truncate(change.get("old_value")),
                "new_value": _truncate(change.get("new_value")),
            }
        )

    for path, value in (diff_dict.get("dictionary_item_added") or {}).items():
        changes.append(
            {
                "field_path": _parse_path(path),
                "change_type": "added",
                "old_value": None,
                "new_value": _truncate(value),
            }
        )

    for path, value in (diff_dict.get("dictionary_item_removed") or {}).items():
        changes.append(
            {
                "field_path": _parse_path(path),
                "change_type": "removed",
                "old_value": _truncate(value),
                "new_value": None,
            }
        )

    for path, change in (diff_dict.get("type_changes") or {}).items():
        changes.append(
            {
                "field_path": _parse_path(path),
                "change_type": "modified",
                "old_value": _truncate(change.get("old_value")),
                "new_value": _truncate(change.get("new_value")),
            }
        )

    return changes


def should_keep_as_snapshot(version_num: int, interval: int = 10) -> bool:
    """Determine if a version should be stored as a full snapshot.

    Version 0 (first) and every Nth version are kept as full snapshots
    to bound the maximum delta chain length.

    Args:
        version_num: Zero-based version number (derived from version string patch)
        interval: Keep a snapshot every N versions

    Returns:
        True if this version should be a full snapshot

    Examples:
        >>> should_keep_as_snapshot(0, 10)
        True
        >>> should_keep_as_snapshot(5, 10)
        False
        >>> should_keep_as_snapshot(10, 10)
        True
        >>> should_keep_as_snapshot(20, 10)
        True
    """
    return version_num == 0 or version_num % interval == 0
