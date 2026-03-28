"""Tests for local register classification."""

from __future__ import annotations

from floridify.ai.assessment.register import classify_register_local


class TestClassifyRegister:
    def test_detects_informal(self) -> None:
        assert classify_register_local("(informal) to mess things up") == "informal"

    def test_detects_formal(self) -> None:
        assert classify_register_local("(formal) to commence proceedings") == "formal"

    def test_detects_slang(self) -> None:
        assert classify_register_local("(slang) money or cash") == "slang"

    def test_detects_technical(self) -> None:
        assert classify_register_local("a medical procedure for the removal of tissue") == "technical"

    def test_returns_none_for_neutral(self) -> None:
        assert classify_register_local("a large body of water") is None

    def test_slang_takes_precedence_over_informal(self) -> None:
        # Slang is more specific than informal
        result = classify_register_local("(vulgar slang) an offensive term")
        assert result == "slang"

    def test_case_insensitive(self) -> None:
        assert classify_register_local("(INFORMAL) a casual greeting") == "informal"
