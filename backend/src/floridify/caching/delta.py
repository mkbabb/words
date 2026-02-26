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
    diff = DeepDiff(a, b, verbose_level=2)
    if not diff:
        return {}
    return diff.to_dict()


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
