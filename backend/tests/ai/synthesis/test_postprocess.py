"""Tests for definition text post-processing."""

from __future__ import annotations

from floridify.ai.synthesis.postprocess import (
    clean_definition_text,
    strip_trailing_domain_label,
)


class TestStripTrailingDomainLabel:
    def test_strips_trailing_aviation(self) -> None:
        text = "The tilting of an aircraft around its longitudinal axis. Aviation."
        cleaned, domain = strip_trailing_domain_label(text)
        assert domain == "aviation"
        assert "Aviation" not in cleaned
        assert cleaned.endswith(".")

    def test_strips_trailing_finance(self) -> None:
        text = "An institution that accepts deposits; finance"
        cleaned, domain = strip_trailing_domain_label(text)
        assert domain == "finance"

    def test_does_not_strip_mid_sentence(self) -> None:
        """'Aviation is a field of engineering' — 'Aviation' is part of the sentence."""
        text = "Aviation is a field of engineering."
        cleaned, domain = strip_trailing_domain_label(text)
        # Should NOT strip "aviation" from mid-sentence
        assert "aviation" in cleaned.lower() or "Aviation" in cleaned

    def test_no_op_on_clean_text(self) -> None:
        text = "A financial institution that accepts deposits."
        cleaned, domain = strip_trailing_domain_label(text)
        assert domain is None
        assert cleaned == text

    def test_extracts_domain_lowercase(self) -> None:
        _, domain = strip_trailing_domain_label("Something. Geography.")
        assert domain == "geography"

    def test_handles_no_period_after_domain(self) -> None:
        text = "Some definition text. Medicine"
        cleaned, domain = strip_trailing_domain_label(text)
        assert domain == "medicine"
        assert cleaned.endswith(".")


class TestCleanDefinitionText:
    def test_normalizes_whitespace(self) -> None:
        assert clean_definition_text("a   financial   institution") == "a financial institution."

    def test_fixes_double_periods(self) -> None:
        assert "..." not in clean_definition_text("End of sentence..")
        assert clean_definition_text("End..").endswith(".")

    def test_strips_domain_and_cleans(self) -> None:
        result = clean_definition_text("The tilting of an aircraft. Aviation.")
        assert "Aviation" not in result
        assert result.endswith(".")

    def test_ensures_final_period(self) -> None:
        assert clean_definition_text("No period").endswith(".")
