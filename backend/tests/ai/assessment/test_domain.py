"""Tests for local domain classification via embedding-based WordNet taxonomy."""

from __future__ import annotations

import pytest

from floridify.ai.assessment.domain import (
    _synset_domain,
    classify_domain_local,
)


class TestSynsetDomain:
    """Domain inference from individual synsets via lexname + hypernym chain."""

    def test_financial_institution_synset(self) -> None:
        domain = _synset_domain("depository_financial_institution.n.01")
        assert domain == "finance"

    def test_slope_synset(self) -> None:
        domain = _synset_domain("bank.n.01")
        assert domain == "geography"

    def test_animal_synset(self) -> None:
        domain = _synset_domain("dog.n.01")
        assert domain == "biology"


class TestClassifyDomainLocal:
    """End-to-end domain classification using embedding-based synset matching."""

    @pytest.mark.asyncio
    async def test_bank_financial_sense(self) -> None:
        result = await classify_domain_local(
            "a financial institution that accepts deposits and channels money into lending",
            word="bank", part_of_speech="noun",
        )
        assert result == "finance"

    @pytest.mark.asyncio
    async def test_bank_geography_sense(self) -> None:
        result = await classify_domain_local(
            "sloping land especially the slope beside a body of water",
            word="bank", part_of_speech="noun",
        )
        assert result == "geography"

    @pytest.mark.asyncio
    async def test_bank_different_senses_different_domains(self) -> None:
        domain_finance = await classify_domain_local(
            "A financial institution that manages deposits and provides loans",
            word="bank", part_of_speech="noun",
        )
        domain_geo = await classify_domain_local(
            "A raised strip of ground along a river forming the water's edge",
            word="bank", part_of_speech="noun",
        )
        assert domain_finance != domain_geo

    @pytest.mark.asyncio
    async def test_bank_aviation_tilt(self) -> None:
        """Key regression test — previously returned 'geography'."""
        result = await classify_domain_local(
            "The lateral tilt of an aircraft during a turn, measured by wing angle",
            word="bank", part_of_speech="noun",
        )
        assert result == "aviation"

    @pytest.mark.asyncio
    async def test_dog_biology(self) -> None:
        result = await classify_domain_local(
            "a domesticated carnivorous mammal",
            word="dog", part_of_speech="noun",
        )
        assert result == "biology"

    @pytest.mark.asyncio
    async def test_returns_none_without_word(self) -> None:
        assert await classify_domain_local("some definition text") is None
