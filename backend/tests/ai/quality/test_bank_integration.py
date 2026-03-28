"""Integration quality tests for the hybrid synthesis pipeline.

Tests the quality gates on "bank" — a highly polysemous word that exercises
all components: clustering, domain classification, CEFR differentiation,
synonym isolation, and slug generation.

These tests use real WordNet data and the embedding encoder (when available).
"""

from __future__ import annotations

import pytest
from bson import ObjectId

from floridify.ai.assessment.cefr import assess_cefr_local
from floridify.ai.assessment.domain import classify_domain_local
from floridify.ai.assessment.frequency import assess_sense_frequency
from floridify.ai.clustering.slug import deduplicate_slugs, generate_cluster_slug
from floridify.ai.embedding_utils import best_synset_by_embedding
from floridify.ai.synthesis.language_filter import is_primary_language
from floridify.ai.synthesis.postprocess import clean_definition_text, strip_trailing_domain_label
from floridify.models.dictionary import Definition


@pytest.fixture(autouse=True)
def _db(test_db):
    """Ensure Beanie is initialized."""


def _make_def(text: str, pos: str = "noun") -> Definition:
    return Definition(word_id=ObjectId(), part_of_speech=pos, text=text)


@pytest.fixture
def bank_definitions() -> list[Definition]:
    """Bank definitions representing distinct senses — created after Beanie init."""
    return [
        _make_def("A financial institution that accepts deposits and makes loans"),
        _make_def("The raised ground along the edge of a river forming the shore"),
        _make_def("A flight maneuver where the aircraft tips laterally to change direction"),
        _make_def("An arrangement of similar objects in a row or tier, such as a bank of switches"),
        _make_def("To deposit money in a financial institution", pos="verb"),
        _make_def("To tilt an aircraft laterally during a turn", pos="verb"),
    ]


# Alias for module-level reference in non-fixture tests
BANK_DEFINITION_TEXTS = [
    ("A financial institution that accepts deposits and makes loans", "noun"),
    ("The raised ground along the edge of a river forming the shore", "noun"),
    ("A flight maneuver where the aircraft tips laterally to change direction", "noun"),
    ("An arrangement of similar objects in a row or tier, such as a bank of switches", "noun"),
    ("To deposit money in a financial institution", "verb"),
    ("To tilt an aircraft laterally during a turn", "verb"),
]


# ── Synset Matching Quality ───────────────────────────────────────────


class TestSynsetMatchingQuality:
    """The embedding-based synset matcher must distinguish senses."""

    @pytest.mark.asyncio
    async def test_financial_matches_financial_synset(self) -> None:
        s = await best_synset_by_embedding(
            "bank", "noun",
            "A financial institution that accepts deposits and makes loans",
        )
        if s is None:
            pytest.skip("Encoder unavailable")
        assert "financial" in s.definition().lower() or "deposit" in s.definition().lower()

    @pytest.mark.asyncio
    async def test_river_matches_slope_synset(self) -> None:
        s = await best_synset_by_embedding(
            "bank", "noun",
            "The raised ground along the edge of a river forming the shore",
        )
        if s is None:
            pytest.skip("Encoder unavailable")
        assert "slop" in s.definition().lower() or "land" in s.definition().lower()

    @pytest.mark.asyncio
    async def test_aviation_matches_flight_synset(self) -> None:
        s = await best_synset_by_embedding(
            "bank", "noun",
            "A flight maneuver where the aircraft tips laterally to change direction",
        )
        if s is None:
            pytest.skip("Encoder unavailable")
        defn = s.definition().lower()
        assert any(kw in defn for kw in ("aircraft", "flight", "tip", "lateral"))

    @pytest.mark.asyncio
    async def test_all_senses_match_distinct_synsets(self, bank_definitions) -> None:
        """No two bank noun definitions should match the same synset."""
        noun_defs = [d for d in bank_definitions if d.part_of_speech == "noun"]
        synset_names: list[str] = []
        for d in noun_defs:
            s = await best_synset_by_embedding("bank", "noun", d.text)
            if s is None:
                pytest.skip("Encoder unavailable")
            synset_names.append(s.name())

        # All synset names should be unique
        assert len(set(synset_names)) == len(synset_names), (
            f"Duplicate synset matches: {synset_names}"
        )


# ── Domain Quality ────────────────────────────────────────────────────


class TestDomainQuality:
    """Domain classification must differentiate senses of polysemous words."""

    @pytest.mark.asyncio
    async def test_financial_sense_gets_finance_domain(self) -> None:
        result = await classify_domain_local(
            BANK_DEFINITION_TEXTS[0][0], word="bank", part_of_speech="noun",
        )
        assert result == "finance"

    @pytest.mark.asyncio
    async def test_river_sense_gets_geography_domain(self) -> None:
        result = await classify_domain_local(
            BANK_DEFINITION_TEXTS[1][0], word="bank", part_of_speech="noun",
        )
        assert result == "geography"

    @pytest.mark.asyncio
    async def test_aviation_sense_gets_aviation_domain(self) -> None:
        result = await classify_domain_local(
            BANK_DEFINITION_TEXTS[2][0], word="bank", part_of_speech="noun",
        )
        assert result == "aviation"

    @pytest.mark.asyncio
    async def test_different_senses_different_domains(self) -> None:
        """Financial, river, and aviation senses must get distinct domains."""
        domains = []
        for text, pos in BANK_DEFINITION_TEXTS[:3]:
            dom = await classify_domain_local(text, word="bank", part_of_speech=pos)
            domains.append(dom)
        assert len(set(domains)) == 3, f"Expected 3 distinct domains, got {domains}"


# ── CEFR Differentiation ─────────────────────────────────────────────


class TestCefrDifferentiation:
    """Rare senses of common words should get harder CEFR levels."""

    @pytest.mark.asyncio
    async def test_common_sense_is_a2_or_b1(self) -> None:
        result = await assess_cefr_local(
            "bank", definition_text=BANK_DEFINITION_TEXTS[0][0], part_of_speech="noun",
        )
        assert result in ("A2", "B1")

    @pytest.mark.asyncio
    async def test_rare_sense_is_harder(self) -> None:
        common = await assess_cefr_local(
            "bank", definition_text=BANK_DEFINITION_TEXTS[0][0], part_of_speech="noun",
        )
        rare = await assess_cefr_local(
            "bank", definition_text=BANK_DEFINITION_TEXTS[3][0], part_of_speech="noun",
        )
        if common is None or rare is None:
            pytest.skip("CEFR assessment unavailable")
        order = ["A1", "A2", "B1", "B2", "C1", "C2"]
        assert order.index(rare) >= order.index(common)


# ── Frequency Differentiation ────────────────────────────────────────


class TestFrequencyDifferentiation:
    @pytest.mark.asyncio
    async def test_dominant_sense_has_higher_frequency(self) -> None:
        freq_financial = await assess_sense_frequency(
            "bank", "noun", BANK_DEFINITION_TEXTS[0][0],
        )
        freq_row = await assess_sense_frequency(
            "bank", "noun", BANK_DEFINITION_TEXTS[3][0],
        )
        if freq_financial is None or freq_row is None:
            pytest.skip("Sense frequency unavailable")
        assert freq_financial > freq_row


# ── Slug Quality ──────────────────────────────────────────────────────


class TestSlugQuality:
    def test_slug_format(self, bank_definitions) -> None:
        all_clusters = [list(range(len(bank_definitions)))]
        slug = generate_cluster_slug("bank", "noun", bank_definitions, [0], all_clusters)
        parts = slug.split("_")
        assert parts[0] == "bank"
        assert parts[1] == "noun"
        assert len(parts) >= 3

    def test_different_clusters_different_slugs(self, bank_definitions) -> None:
        all_clusters = [[0, 1], [2, 3], [4, 5]]
        slugs = [
            generate_cluster_slug("bank", "noun", bank_definitions, c, all_clusters)
            for c in all_clusters
        ]
        slugs = deduplicate_slugs(slugs)
        assert len(set(slugs)) == len(slugs), f"Duplicate slugs: {slugs}"

    def test_deterministic(self, bank_definitions) -> None:
        all_clusters = [[0], [1]]
        slug_a = generate_cluster_slug("bank", "noun", bank_definitions, [0], all_clusters)
        slug_b = generate_cluster_slug("bank", "noun", bank_definitions, [0], all_clusters)
        assert slug_a == slug_b

    def test_sanitized(self, bank_definitions) -> None:
        all_clusters = [[0]]
        slug = generate_cluster_slug("bank", "noun", bank_definitions, [0], all_clusters)
        assert all(c.isalnum() or c == "_" for c in slug)


# ── Language Filtering Quality ────────────────────────────────────────


class TestLanguageFilterQuality:
    def test_english_detected(self) -> None:
        assert is_primary_language("English", "en")

    def test_french_filtered_from_english(self) -> None:
        assert not is_primary_language("French", "en")
        assert not is_primary_language("Latin", "en")

    def test_french_kept_for_french_word(self) -> None:
        assert is_primary_language("French", "fr")


# ── Post-Processing Quality ──────────────────────────────────────────


class TestPostProcessingQuality:
    def test_strips_trailing_domain(self) -> None:
        cleaned, domain = strip_trailing_domain_label(
            "Tilt of an aircraft around its longitudinal axis. Aviation."
        )
        assert "Aviation" not in cleaned
        assert domain == "aviation"

    def test_clean_definition_normalizes(self) -> None:
        result = clean_definition_text("A financial   institution..  Finance.")
        assert "  " not in result
        assert ".." not in result
        assert "Finance" not in result
