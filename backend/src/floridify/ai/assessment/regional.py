"""Local regional variant detection from definition text and Wiktionary labels.

Detects British, American, Australian, etc. usage from indicator keywords.
"""

from __future__ import annotations

import re

# Regional variant patterns — (region_code, keywords)
_REGIONAL_PATTERNS: list[tuple[str, list[str]]] = [
    ("US", [
        "american", "us english", "north american",
        "united states", "chiefly us", "chiefly american",
    ]),
    ("UK", [
        "british", "uk english", "chiefly british",
        "chiefly uk", "england", "commonwealth",
    ]),
    ("AU", [
        "australian", "chiefly australian", "australia",
    ]),
    ("CA", [
        "canadian", "chiefly canadian", "canada",
    ]),
    ("IE", [
        "irish", "ireland", "hiberno-english",
    ]),
    ("SC", [
        "scottish", "scots", "scotland",
    ]),
    ("NZ", [
        "new zealand", "kiwi",
    ]),
    ("SA", [
        "south african", "south africa",
    ]),
    ("IN", [
        "indian english", "india",
    ]),
]

_COMPILED_REGIONS: list[tuple[str, re.Pattern[str]]] = [
    (
        region,
        re.compile(r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b", re.IGNORECASE),
    )
    for region, keywords in _REGIONAL_PATTERNS
]


def detect_regional_local(definition_text: str) -> str | None:
    """Detect regional variant from definition text.

    Returns:
        Region code (US, UK, AU, etc.), or None if no regional indicator found.
    """
    for region, pattern in _COMPILED_REGIONS:
        if pattern.search(definition_text):
            return region

    return None
