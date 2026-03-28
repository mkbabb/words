"""Language filtering for AI-generated synonyms and antonyms.

Separates primary-language items from cross-language cognates based on
the candidate.language field in AI responses. Uses ISO 639-1 code ↔
language name mapping for normalization.
"""

from __future__ import annotations

# ISO 639-1 code → set of recognized language name variants (lowercase)
_LANGUAGE_NAMES: dict[str, set[str]] = {
    "en": {"english", "en", "eng"},
    "fr": {"french", "fr", "fra", "français"},
    "es": {"spanish", "es", "spa", "español"},
    "de": {"german", "de", "deu", "deutsch"},
    "it": {"italian", "it", "ita", "italiano"},
    "pt": {"portuguese", "pt", "por", "português"},
    "la": {"latin", "la", "lat"},
    "grc": {"ancient greek", "grc", "greek"},
    "ja": {"japanese", "ja", "jpn"},
    "zh": {"chinese", "zh", "zho", "mandarin"},
    "ar": {"arabic", "ar", "ara"},
    "nl": {"dutch", "nl", "nld"},
    "ru": {"russian", "ru", "rus"},
    "hi": {"hindi", "hi", "hin"},
}


def _build_reverse_map() -> dict[str, str]:
    """Build {language_name_variant -> iso_code} reverse lookup."""
    reverse: dict[str, str] = {}
    for code, names in _LANGUAGE_NAMES.items():
        for name in names:
            reverse[name] = code
    return reverse


_NAME_TO_CODE = _build_reverse_map()


def normalize_language_code(language: str) -> str:
    """Normalize a free-text language name to ISO 639-1 code.

    Examples:
        "English" → "en"
        "French" → "fr"
        "Latin" → "la"
        "en" → "en"
    """
    return _NAME_TO_CODE.get(language.lower().strip(), language.lower().strip())


def is_primary_language(candidate_language: str, primary_code: str) -> bool:
    """Check if a candidate's language matches the primary language.

    Args:
        candidate_language: The language field from AI response (e.g., "English", "French")
        primary_code: The ISO 639-1 code of the word's language (e.g., "en", "fr")
    """
    candidate_code = normalize_language_code(candidate_language)
    return candidate_code == primary_code
