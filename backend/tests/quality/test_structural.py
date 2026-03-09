"""Structural quality tests for AI synthesis output.

These tests validate the structure and completeness of golden fixture data.
They run without API calls using pre-recorded fixtures.
"""

from __future__ import annotations

from tests.quality.models import GoldenFixture
from tests.quality.validators import (
    validate_definition_count_range,
    validate_definition_fields,
    validate_definition_text_length,
    validate_entry_completeness,
)


class TestBankStructural:
    """Structural tests for 'bank' — polysemous English word."""

    def test_entry_completeness(self, golden_bank: GoldenFixture) -> None:
        errors = validate_entry_completeness(golden_bank)
        assert not errors, f"Entry incomplete: {errors}"

    def test_definition_count(self, golden_bank: GoldenFixture) -> None:
        ok, msg = validate_definition_count_range(
            golden_bank.definitions, min_count=3, max_count=15
        )
        assert ok, msg

    def test_definitions_have_required_fields(self, golden_bank: GoldenFixture) -> None:
        all_errors = []
        for i, d in enumerate(golden_bank.definitions):
            errors = validate_definition_fields(d)
            if errors:
                all_errors.extend([f"Definition {i}: {e}" for e in errors])
        assert not all_errors, f"Field errors: {all_errors}"

    def test_valid_cefr_levels(self, golden_bank: GoldenFixture) -> None:
        """Any CEFR levels present are validated by the model itself (Literal type)."""
        for i, d in enumerate(golden_bank.definitions):
            if d.cefr_level is not None:
                assert d.cefr_level in {"A1", "A2", "B1", "B2", "C1", "C2"}, (
                    f"Definition {i}: invalid CEFR level '{d.cefr_level}'"
                )

    def test_valid_frequency_bands(self, golden_bank: GoldenFixture) -> None:
        """Any frequency bands present are validated by the model itself (ge=1, le=5)."""
        for i, d in enumerate(golden_bank.definitions):
            if d.frequency_band is not None:
                assert 1 <= d.frequency_band <= 5, (
                    f"Definition {i}: invalid frequency band {d.frequency_band}"
                )

    def test_pronunciation_present(self, golden_bank: GoldenFixture) -> None:
        assert golden_bank.pronunciation, "Pronunciation missing from fixture"

    def test_etymology_present(self, golden_bank: GoldenFixture) -> None:
        assert golden_bank.etymology, "Etymology missing from fixture"

    def test_definition_text_reasonable_length(self, golden_bank: GoldenFixture) -> None:
        errors = validate_definition_text_length(golden_bank.definitions)
        assert not errors, f"Length errors: {errors}"


class TestForkStructural:
    """Structural tests for 'fork' — polysemous English word with synonyms."""

    def test_entry_completeness(self, golden_fork: GoldenFixture) -> None:
        errors = validate_entry_completeness(golden_fork)
        assert not errors, f"Entry incomplete: {errors}"

    def test_definition_count(self, golden_fork: GoldenFixture) -> None:
        ok, msg = validate_definition_count_range(
            golden_fork.definitions, min_count=5, max_count=30
        )
        assert ok, msg

    def test_definitions_have_required_fields(self, golden_fork: GoldenFixture) -> None:
        all_errors = []
        for i, d in enumerate(golden_fork.definitions):
            errors = validate_definition_fields(d)
            if errors:
                all_errors.extend([f"Definition {i}: {e}" for e in errors])
        assert not all_errors, f"Field errors: {all_errors}"

    def test_definitions_have_synonyms(self, golden_fork: GoldenFixture) -> None:
        defs_with_synonyms = sum(1 for d in golden_fork.definitions if d.synonyms)
        assert defs_with_synonyms > 0, "No definitions have synonyms"

    def test_definition_text_reasonable_length(self, golden_fork: GoldenFixture) -> None:
        errors = validate_definition_text_length(golden_fork.definitions)
        assert not errors, f"Length errors: {errors}"


class TestFrenchStructural:
    """Structural tests for 'en coulisses' — enriched French phrase."""

    def test_entry_completeness(self, golden_fr: GoldenFixture) -> None:
        errors = validate_entry_completeness(golden_fr)
        assert not errors, f"Entry incomplete: {errors}"

    def test_definition_count(self, golden_fr: GoldenFixture) -> None:
        ok, msg = validate_definition_count_range(golden_fr.definitions, min_count=1, max_count=5)
        assert ok, msg

    def test_definitions_have_required_fields(self, golden_fr: GoldenFixture) -> None:
        all_errors = []
        for i, d in enumerate(golden_fr.definitions):
            errors = validate_definition_fields(d)
            if errors:
                all_errors.extend([f"Definition {i}: {e}" for e in errors])
        assert not all_errors, f"Field errors: {all_errors}"

    def test_definitions_have_synonyms(self, golden_fr: GoldenFixture) -> None:
        defs_with_synonyms = sum(1 for d in golden_fr.definitions if d.synonyms)
        assert defs_with_synonyms > 0, "No definitions have synonyms"

    def test_definitions_have_examples(self, golden_fr: GoldenFixture) -> None:
        defs_with_examples = sum(1 for d in golden_fr.definitions if d.examples)
        assert defs_with_examples > 0, "No definitions have examples"

    def test_pronunciation_present(self, golden_fr: GoldenFixture) -> None:
        assert golden_fr.pronunciation, "Pronunciation missing from fixture"

    def test_facts_present(self, golden_fr: GoldenFixture) -> None:
        assert golden_fr.facts and len(golden_fr.facts) > 0, "No facts in fixture"

    def test_definition_text_reasonable_length(self, golden_fr: GoldenFixture) -> None:
        errors = validate_definition_text_length(golden_fr.definitions)
        assert not errors, f"Length errors: {errors}"
