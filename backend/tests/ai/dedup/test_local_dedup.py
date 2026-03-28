"""Tests for the 3-tier local definition dedup pipeline.

Requires test_db fixture because Definition is a Beanie Document.
"""

from __future__ import annotations

import pytest
from bson import ObjectId

from floridify.ai.dedup.local_dedup import (
    _select_best_definition,
    _tier1_exact,
    _tier2_fuzzy,
    local_deduplicate_definitions,
)
from floridify.models.dictionary import Definition


@pytest.fixture(autouse=True)
def _db(test_db):
    """Ensure Beanie is initialized so Definition() can be constructed."""


def _make_def(text: str, pos: str = "noun", **kwargs) -> Definition:
    """Create a minimal Definition for testing (no DB save needed)."""
    return Definition(
        word_id=ObjectId(),
        part_of_speech=pos,
        text=text,
        **kwargs,
    )


# ── Tier 1: Exact ────────────────────────────────────────────────────


class TestTier1Exact:
    def test_groups_identical_canonical_text(self) -> None:
        defs = [
            _make_def("A large body of water."),
            _make_def("a large body of water"),
            _make_def("A financial institution."),
        ]
        groups, records = _tier1_exact(defs)
        assert len(groups) == 2  # Two unique canonical texts
        assert len(records) == 1  # One merge occurred

    def test_respects_pos_boundary(self) -> None:
        """Same text but different POS should NOT merge."""
        defs = [
            _make_def("to run quickly", pos="verb"),
            _make_def("to run quickly", pos="noun"),
        ]
        groups, records = _tier1_exact(defs)
        assert len(groups) == 2
        assert len(records) == 0

    def test_no_duplicates_returns_singletons(self) -> None:
        defs = [
            _make_def("A financial institution."),
            _make_def("Sloping land beside a river."),
        ]
        groups, records = _tier1_exact(defs)
        assert len(groups) == 2
        assert len(records) == 0

    def test_records_contain_tier_info(self) -> None:
        defs = [
            _make_def("A large body of water."),
            _make_def("a large body of water"),
        ]
        _, records = _tier1_exact(defs)
        assert len(records) == 1
        assert records[0].tier == "exact"
        assert records[0].similarity_score == 1.0


# ── Tier 2: Fuzzy ────────────────────────────────────────────────────


class TestTier2Fuzzy:
    def test_merges_similar_definitions(self) -> None:
        defs = [
            _make_def("A financial institution that accepts deposits."),
            _make_def("A financial institution which accepts deposits."),
        ]
        groups = [[0], [1]]
        merged_groups, records = _tier2_fuzzy(defs, groups, threshold=80.0)
        assert len(merged_groups) == 1  # Should merge
        assert len(records) == 1
        assert records[0].tier == "fuzzy"

    def test_does_not_merge_different_definitions(self) -> None:
        defs = [
            _make_def("A financial institution that accepts deposits."),
            _make_def("Sloping land beside a body of water."),
        ]
        groups = [[0], [1]]
        merged_groups, records = _tier2_fuzzy(defs, groups, threshold=80.0)
        assert len(merged_groups) == 2

    def test_respects_pos_boundary(self) -> None:
        defs = [
            _make_def("To run quickly across the field.", pos="verb"),
            _make_def("To run swiftly across the field.", pos="noun"),
        ]
        groups = [[0], [1]]
        merged_groups, _ = _tier2_fuzzy(defs, groups, threshold=80.0)
        assert len(merged_groups) == 2  # Different POS, no merge


# ── Best Selection ────────────────────────────────────────────────────


class TestSelectBest:
    def test_prefers_definition_with_more_synonyms(self) -> None:
        defs = [
            _make_def("Short def.", synonyms=["a"]),
            _make_def("Short def with more synonyms.", synonyms=["a", "b", "c"]),
        ]
        best = _select_best_definition(defs, [0, 1])
        assert best == 1

    def test_single_item_returns_itself(self) -> None:
        defs = [_make_def("Only one.")]
        assert _select_best_definition(defs, [0]) == 0


# ── Full Pipeline ─────────────────────────────────────────────────────


class TestLocalDeduplicateFull:
    @pytest.mark.asyncio
    async def test_single_definition_passes_through(self) -> None:
        defs = [_make_def("A single definition.")]
        response = await local_deduplicate_definitions("test", defs)
        assert len(response.deduplicated_definitions) == 1
        assert response.removed_count == 0

    @pytest.mark.asyncio
    async def test_empty_returns_empty(self) -> None:
        response = await local_deduplicate_definitions("test", [])
        assert len(response.deduplicated_definitions) == 0
        assert response.removed_count == 0

    @pytest.mark.asyncio
    async def test_exact_duplicates_merged(self) -> None:
        defs = [
            _make_def("A financial institution."),
            _make_def("a financial institution"),
            _make_def("Sloping land beside a river."),
        ]
        response = await local_deduplicate_definitions(
            "bank", defs, enable_semantic=False,
        )
        assert len(response.deduplicated_definitions) == 2
        assert response.removed_count == 1

    @pytest.mark.asyncio
    async def test_fuzzy_duplicates_merged(self) -> None:
        defs = [
            _make_def("A financial institution that accepts deposits and makes loans."),
            _make_def("A financial institution which accepts deposits and provides loans."),
            _make_def("Sloping land beside a body of water."),
        ]
        response = await local_deduplicate_definitions(
            "bank", defs, enable_semantic=False,
        )
        # The first two should merge (high fuzzy similarity)
        assert len(response.deduplicated_definitions) == 2
        assert response.removed_count == 1

    @pytest.mark.asyncio
    async def test_response_has_correct_structure(self) -> None:
        defs = [
            _make_def("First definition."),
            _make_def("Second definition."),
        ]
        response = await local_deduplicate_definitions("test", defs, enable_semantic=False)
        assert hasattr(response, "deduplicated_definitions")
        assert hasattr(response, "removed_count")
        assert hasattr(response, "confidence")
        for d in response.deduplicated_definitions:
            assert hasattr(d, "source_indices")
            assert hasattr(d, "part_of_speech")
            assert hasattr(d, "definition")
            assert hasattr(d, "quality_score")
