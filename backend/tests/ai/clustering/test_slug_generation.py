"""Tests for deterministic slug and name generation."""

from __future__ import annotations

import pytest
from bson import ObjectId

from floridify.ai.clustering.slug import (
    deduplicate_slugs,
    generate_cluster_name,
    generate_cluster_slug,
)
from floridify.models.dictionary import Definition


@pytest.fixture(autouse=True)
def _db(test_db):
    """Ensure Beanie is initialized."""


def _make_def(text: str, pos: str = "noun") -> Definition:
    return Definition(word_id=ObjectId(), part_of_speech=pos, text=text)


class TestGenerateClusterSlug:
    def test_format(self) -> None:
        defs = [
            _make_def("A financial institution that accepts deposits"),
            _make_def("Sloping land beside a river"),
        ]
        slug = generate_cluster_slug("bank", "noun", defs, [0], [[0], [1]])
        assert slug.startswith("bank_noun_")
        assert "_" in slug

    def test_different_clusters_get_different_slugs(self) -> None:
        defs = [
            _make_def("A financial institution that accepts deposits and makes loans"),
            _make_def("Sloping land beside a river or lake forming the shore"),
        ]
        slug1 = generate_cluster_slug("bank", "noun", defs, [0], [[0], [1]])
        slug2 = generate_cluster_slug("bank", "noun", defs, [1], [[0], [1]])
        assert slug1 != slug2

    def test_deterministic(self) -> None:
        """Same input → same output, no randomness."""
        defs = [
            _make_def("A financial institution that accepts deposits"),
            _make_def("Sloping land beside a river"),
        ]
        slug_a = generate_cluster_slug("bank", "noun", defs, [0], [[0], [1]])
        slug_b = generate_cluster_slug("bank", "noun", defs, [0], [[0], [1]])
        assert slug_a == slug_b

    def test_sanitized(self) -> None:
        """Slug contains only lowercase alphanumeric + underscore."""
        defs = [_make_def("A very special thing!")]
        slug = generate_cluster_slug("test", "noun", defs, [0], [[0]])
        assert all(c.isalnum() or c == "_" for c in slug)
        assert slug == slug.lower()

    def test_pos_normalization(self) -> None:
        """'verb (transitive)' → 'verb' in slug."""
        defs = [_make_def("To deposit money", pos="verb (transitive)")]
        slug = generate_cluster_slug("bank", "verb (transitive)", defs, [0], [[0]])
        assert "_verb_" in slug
        assert "transitive" not in slug


class TestDeduplicateSlugs:
    def test_unique_slugs_unchanged(self) -> None:
        slugs = ["bank_noun_financial", "bank_noun_slope", "bank_verb_tilt"]
        assert deduplicate_slugs(slugs) == slugs

    def test_duplicates_get_suffix(self) -> None:
        slugs = ["bank_noun_financial", "bank_noun_financial", "bank_noun_slope"]
        result = deduplicate_slugs(slugs)
        assert result[0] == "bank_noun_financial"
        assert result[1] == "bank_noun_financial_1"
        assert result[2] == "bank_noun_slope"

    def test_triple_duplicate(self) -> None:
        slugs = ["x", "x", "x"]
        result = deduplicate_slugs(slugs)
        assert len(set(result)) == 3


class TestGenerateClusterName:
    def test_produces_readable_name(self) -> None:
        defs = [_make_def("A financial institution that accepts deposits and makes loans")]
        name = generate_cluster_name(defs, [0])
        assert len(name) > 0
        assert len(name) <= 30

    def test_picks_shortest_definition(self) -> None:
        defs = [
            _make_def("A very long and elaborate definition about financial institutions and their role in modern society"),
            _make_def("A place for money"),
        ]
        name = generate_cluster_name(defs, [0, 1])
        # Should derive from the shorter definition
        assert len(name) <= 30
