"""Language precedence helpers for shared multi-language handling."""

from __future__ import annotations

from ..models.base import Language


def language_code(language: Language | str) -> str:
    """Normalize language input to ISO code."""
    return language.value if isinstance(language, Language) else language


def to_language_codes(languages: list[Language | str]) -> list[str]:
    """Normalize a language list to ISO codes."""
    return [language_code(language) for language in languages]


def merge_language_precedence(
    requested_languages: list[Language | str],
    existing_languages: list[Language | str],
) -> list[str]:
    """Merge requested and existing language lists with requested precedence."""
    merged: list[str] = []
    seen: set[str] = set()

    for language in [*requested_languages, *existing_languages]:
        code = language_code(language)
        if code in seen:
            continue
        seen.add(code)
        merged.append(code)

    return merged
