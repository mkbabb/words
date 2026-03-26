"""Semantic quality tests for AI synthesis output.

These tests validate the semantic correctness and quality of golden fixture data
using heuristic checks (no AI calls needed).
"""

from __future__ import annotations

import pytest

from tests.quality.models import GoldenFixture
from tests.quality.validators import (
    validate_cluster_diversity,
    validate_examples_contain_word,
    validate_language_consistency,
    validate_no_duplicate_definitions,
    validate_pos_coverage,
    validate_synonyms_not_contain_word,
    validate_synonyms_not_duplicate_antonyms,
)


class TestBankSemantic:
    """Semantic tests for 'bank' — polysemous English word."""

    def test_synonyms_not_duplicate_antonyms(self, golden_bank: GoldenFixture) -> None:
        all_errors = []
        for i, d in enumerate(golden_bank.definitions):
            errors = validate_synonyms_not_duplicate_antonyms(d)
            if errors:
                all_errors.extend([f"Definition {i}: {e}" for e in errors])
        assert not all_errors, f"Synonym/antonym overlap: {all_errors}"

    def test_synonyms_not_self_referential(self, golden_bank: GoldenFixture) -> None:
        all_errors = []
        for i, d in enumerate(golden_bank.definitions):
            errors = validate_synonyms_not_contain_word(golden_bank.word, d.synonyms)
            if errors:
                all_errors.extend([f"Definition {i}: {e}" for e in errors])
        assert not all_errors, f"Self-referential synonyms: {all_errors}"

    def test_language_is_english(self, golden_bank: GoldenFixture) -> None:
        errors = validate_language_consistency(golden_bank, "en")
        assert not errors, f"Language mismatch: {errors}"

    def test_has_noun_and_verb(self, golden_bank: GoldenFixture) -> None:
        ok, msg = validate_pos_coverage(golden_bank.definitions, {"noun", "verb"})
        assert ok, f"'bank' should have noun and verb: {msg}"

    def test_no_duplicate_definitions(self, golden_bank: GoldenFixture) -> None:
        errors = validate_no_duplicate_definitions(golden_bank.definitions)
        assert not errors, f"Duplicate definitions: {errors}"

    def test_etymology_mentions_origin(self, golden_bank: GoldenFixture) -> None:
        if golden_bank.etymology is None:
            pytest.skip("No etymology in fixture")
        ety_text = golden_bank.etymology.text.lower()
        has_origin = any(
            origin in ety_text
            for origin in ["italian", "germanic", "german", "old french", "norse", "proto", "banca"]
        )
        assert has_origin, (
            f"Etymology doesn't mention expected origin languages: '{ety_text[:200]}'"
        )


class TestForkSemantic:
    """Semantic tests for 'fork' — polysemous English word with enrichment."""

    def test_language_is_english(self, golden_fork: GoldenFixture) -> None:
        errors = validate_language_consistency(golden_fork, "en")
        assert not errors, f"Language mismatch: {errors}"

    def test_synonyms_not_self_referential(self, golden_fork: GoldenFixture) -> None:
        all_errors = []
        for i, d in enumerate(golden_fork.definitions):
            errors = validate_synonyms_not_contain_word(golden_fork.word, d.synonyms)
            if errors:
                all_errors.extend([f"Definition {i}: {e}" for e in errors])
        assert not all_errors, f"Self-referential synonyms: {all_errors}"

    def test_synonyms_not_duplicate_antonyms(self, golden_fork: GoldenFixture) -> None:
        all_errors = []
        for i, d in enumerate(golden_fork.definitions):
            errors = validate_synonyms_not_duplicate_antonyms(d)
            if errors:
                all_errors.extend([f"Definition {i}: {e}" for e in errors])
        assert not all_errors, f"Synonym/antonym overlap: {all_errors}"

    def test_has_noun_and_verb(self, golden_fork: GoldenFixture) -> None:
        ok, msg = validate_pos_coverage(golden_fork.definitions, {"noun", "verb"})
        assert ok, f"'fork' should have noun and verb: {msg}"

    def test_no_duplicate_definitions(self, golden_fork: GoldenFixture) -> None:
        errors = validate_no_duplicate_definitions(golden_fork.definitions)
        assert not errors, f"Duplicate definitions: {errors}"


class TestFrenchSemantic:
    """Semantic tests for 'en coulisses' — enriched French phrase."""

    def test_language_is_french(self, golden_fr: GoldenFixture) -> None:
        errors = validate_language_consistency(golden_fr, "fr")
        assert not errors, f"Language mismatch: {errors}"

    @pytest.mark.xfail(reason="Known bug: synthesis includes word in its own synonym list")
    def test_synonyms_not_self_referential(self, golden_fr: GoldenFixture) -> None:
        all_errors = []
        for i, d in enumerate(golden_fr.definitions):
            errors = validate_synonyms_not_contain_word(golden_fr.word, d.synonyms)
            if errors:
                all_errors.extend([f"Definition {i}: {e}" for e in errors])
        assert not all_errors, f"Self-referential synonyms: {all_errors}"

    def test_no_duplicate_definitions(self, golden_fr: GoldenFixture) -> None:
        errors = validate_no_duplicate_definitions(golden_fr.definitions)
        assert not errors, f"Duplicate definitions: {errors}"

    def test_has_multiple_clusters(self, golden_fr: GoldenFixture) -> None:
        has_diversity, msg = validate_cluster_diversity(golden_fr.definitions)
        assert has_diversity, f"Expected multiple meaning clusters for 'en coulisses': {msg}"

    def test_examples_contain_word(self, golden_fr: GoldenFixture) -> None:
        all_errors = []
        for i, d in enumerate(golden_fr.definitions):
            if d.examples:
                example_texts = [ex.text for ex in d.examples]
                errors = validate_examples_contain_word(golden_fr.word, example_texts)
                if errors:
                    all_errors.extend([f"Definition {i}: {e}" for e in errors])
        assert len(all_errors) <= len(golden_fr.definitions), (
            f"Too many examples missing the word: {all_errors}"
        )
