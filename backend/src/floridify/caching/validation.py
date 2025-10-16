"""Pure validation functions for caching module.

Zero dependencies on I/O, zero side effects, deterministic outputs.
All functions are stateless and testable in isolation.
"""

from __future__ import annotations

from typing import Any

from .models import BaseVersionedData

__all__ = [
    "validate_metadata_changed",
    "validate_content_match",
    "should_create_new_version",
]


def validate_metadata_changed(
    existing_metadata: dict[str, Any],
    new_metadata: dict[str, Any],
    comparison_fields: list[str],
) -> tuple[bool, list[str]]:
    """Check if specified metadata fields have changed.

    Pure function - zero side effects, deterministic output.

    Args:
        existing_metadata: Current metadata dictionary
        new_metadata: New metadata dictionary
        comparison_fields: List of field names to compare

    Returns:
        Tuple of (changed, list_of_changed_fields)

    Examples:
        >>> existing = {"author": "Alice", "version": "1.0"}
        >>> new = {"author": "Bob", "version": "1.0"}
        >>> changed, fields = validate_metadata_changed(existing, new, ["author"])
        >>> changed
        True
        >>> fields
        ['author']
    """
    changed_fields: list[str] = []

    for field in comparison_fields:
        if field not in new_metadata:
            continue

        existing_value = existing_metadata.get(field)
        new_value = new_metadata.get(field)

        if existing_value != new_value:
            changed_fields.append(field)

    return len(changed_fields) > 0, changed_fields


def validate_content_match(
    existing: BaseVersionedData,
    content_hash: str,
    new_metadata: dict[str, Any] | None,
    comparison_fields: list[str] | None,
) -> tuple[bool, str]:
    """Validate if content and metadata match existing version.

    Pure function - determines if new version should be created.

    Args:
        existing: Existing versioned data object
        content_hash: Hash of new content
        new_metadata: New metadata dictionary (optional)
        comparison_fields: Fields to compare for metadata changes (optional)

    Returns:
        Tuple of (should_reuse_existing, reason_string)

    Examples:
        >>> # Content matches, no metadata comparison
        >>> match, reason = validate_content_match(existing, "abc123", None, None)
        >>> match
        True
        >>> reason
        'content_match'

        >>> # Content matches, metadata unchanged
        >>> match, reason = validate_content_match(
        ...     existing, "abc123", {"author": "Alice"}, ["author"]
        ... )
        >>> match
        True
        >>> reason
        'content_and_metadata_match'
    """
    # Check content hash match
    if existing.version_info.data_hash != content_hash:
        return False, "content_different"

    # No metadata comparison requested - content match is sufficient
    if not comparison_fields or not new_metadata:
        return True, "content_match"

    # Check metadata changes
    existing_data = existing.model_dump()
    existing_metadata = existing_data.get("metadata", {})

    changed, changed_fields = validate_metadata_changed(
        existing_metadata,
        new_metadata,
        comparison_fields,
    )

    if changed:
        return False, f"metadata_changed:{','.join(changed_fields)}"

    return True, "content_and_metadata_match"


def should_create_new_version(
    existing: BaseVersionedData | None,
    content_hash: str,
    new_metadata: dict[str, Any] | None,
    comparison_fields: list[str] | None,
    force_rebuild: bool,
) -> tuple[bool, str]:
    """Determine if a new version should be created.

    Pure function - consolidates version creation logic.

    Args:
        existing: Existing version with same content hash (if any)
        content_hash: Hash of new content
        new_metadata: New metadata dictionary (optional)
        comparison_fields: Fields to compare for metadata changes (optional)
        force_rebuild: Force creation even if content matches

    Returns:
        Tuple of (should_create, reason_string)

    Examples:
        >>> # Force rebuild
        >>> create, reason = should_create_new_version(existing, "abc", None, None, True)
        >>> create
        True
        >>> reason
        'force_rebuild'

        >>> # No existing version
        >>> create, reason = should_create_new_version(None, "abc", None, None, False)
        >>> create
        True
        >>> reason
        'no_existing'

        >>> # Content matches
        >>> create, reason = should_create_new_version(existing, "abc", None, None, False)
        >>> create
        False
        >>> reason
        'content_match'
    """
    # Force rebuild overrides everything
    if force_rebuild:
        return True, "force_rebuild"

    # No existing version - must create
    if existing is None:
        return True, "no_existing"

    # Check content and metadata match
    should_reuse, reason = validate_content_match(
        existing,
        content_hash,
        new_metadata,
        comparison_fields,
    )

    if should_reuse:
        return False, reason

    return True, reason
