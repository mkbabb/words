"""Tests for multilingual synonym/antonym language filtering."""

from __future__ import annotations

from floridify.ai.synthesis.language_filter import (
    is_primary_language,
    normalize_language_code,
)


class TestNormalizeLanguageCode:
    def test_english_name(self) -> None:
        assert normalize_language_code("English") == "en"

    def test_iso_code_passthrough(self) -> None:
        assert normalize_language_code("en") == "en"

    def test_french(self) -> None:
        assert normalize_language_code("French") == "fr"

    def test_latin(self) -> None:
        assert normalize_language_code("Latin") == "la"

    def test_case_insensitive(self) -> None:
        assert normalize_language_code("ENGLISH") == "en"
        assert normalize_language_code("french") == "fr"

    def test_unknown_returns_lowered(self) -> None:
        assert normalize_language_code("Klingon") == "klingon"


class TestIsPrimaryLanguage:
    def test_english_matches_en(self) -> None:
        assert is_primary_language("English", "en")

    def test_french_matches_fr(self) -> None:
        assert is_primary_language("French", "fr")

    def test_french_does_not_match_en(self) -> None:
        assert not is_primary_language("French", "en")

    def test_latin_does_not_match_en(self) -> None:
        assert not is_primary_language("Latin", "en")

    def test_iso_code_matches(self) -> None:
        assert is_primary_language("en", "en")

    def test_spanish_matches_es(self) -> None:
        assert is_primary_language("Spanish", "es")
        assert is_primary_language("español", "es")
