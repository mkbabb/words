"""Pure functions for version chain management.

Zero dependencies on I/O, zero side effects, deterministic outputs.
Handles version incrementing, chain logic, and version ordering.
"""

from __future__ import annotations

import re
from typing import NamedTuple

__all__ = [
    "VersionParts",
    "compare_versions",
    "increment_version",
    "parse_version",
]


class VersionParts(NamedTuple):
    """Structured version components."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        """Convert back to version string."""
        return f"{self.major}.{self.minor}.{self.patch}"


def parse_version(version: str) -> VersionParts:
    """Parse semantic version string into components.

    Pure function - zero side effects, deterministic output.

    Args:
        version: Semantic version string (e.g., "1.2.3")

    Returns:
        VersionParts with major, minor, patch integers

    Raises:
        ValueError: If version string is invalid

    Examples:
        >>> parse_version("1.2.3")
        VersionParts(major=1, minor=2, patch=3)
        >>> parse_version("10.0.15")
        VersionParts(major=10, minor=0, patch=15)
    """
    # Match semantic version pattern: major.minor.patch
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)

    if not match:
        raise ValueError(
            f"Invalid version string: {version}. Expected format: 'major.minor.patch' (e.g., '1.2.3')"
        )

    major, minor, patch = match.groups()
    return VersionParts(int(major), int(minor), int(patch))


def increment_version(version: str, level: str = "patch") -> str:
    """Increment version at specified level.

    Pure function - zero side effects, deterministic output.

    Args:
        version: Current semantic version string
        level: Which component to increment ('major', 'minor', or 'patch')

    Returns:
        New version string with incremented component

    Raises:
        ValueError: If version string is invalid or level is unknown

    Examples:
        >>> increment_version("1.2.3", "patch")
        '1.2.4'
        >>> increment_version("1.2.3", "minor")
        '1.3.0'
        >>> increment_version("1.2.3", "major")
        '2.0.0'
    """
    parts = parse_version(version)

    if level == "patch":
        return str(VersionParts(parts.major, parts.minor, parts.patch + 1))
    elif level == "minor":
        return str(VersionParts(parts.major, parts.minor + 1, 0))
    elif level == "major":
        return str(VersionParts(parts.major + 1, 0, 0))
    else:
        raise ValueError(f"Invalid level: {level}. Must be 'major', 'minor', or 'patch'")


def compare_versions(v1: str, v2: str) -> int:
    """Compare two semantic versions.

    Pure function - zero side effects, deterministic output.

    Args:
        v1: First version string
        v2: Second version string

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2

    Raises:
        ValueError: If either version string is invalid

    Examples:
        >>> compare_versions("1.2.3", "1.2.4")
        -1
        >>> compare_versions("2.0.0", "1.9.9")
        1
        >>> compare_versions("1.0.0", "1.0.0")
        0
    """
    parts1 = parse_version(v1)
    parts2 = parse_version(v2)

    # Compare major
    if parts1.major < parts2.major:
        return -1
    if parts1.major > parts2.major:
        return 1

    # Compare minor
    if parts1.minor < parts2.minor:
        return -1
    if parts1.minor > parts2.minor:
        return 1

    # Compare patch
    if parts1.patch < parts2.patch:
        return -1
    if parts1.patch > parts2.patch:
        return 1

    return 0
