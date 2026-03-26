"""Fixtures for phonetic search tests."""

from __future__ import annotations

import pytest

from floridify.search.phonetic.encoder import PhoneticEncoder, get_phonetic_encoder
from floridify.search.phonetic.index import PhoneticIndex


@pytest.fixture(scope="module")
def encoder() -> PhoneticEncoder:
    return get_phonetic_encoder()


@pytest.fixture(scope="module")
def multilingual_vocab() -> list[str]:
    return sorted([
        "en coulisses", "a fond", "joie de vivre", "raison d etre",
        "coup de grace", "creme de la creme", "faux pas", "carte blanche",
        "bon voyage", "rendez vous", "mise en scene", "haute couture",
        "c est la vie", "entrepreneur", "bourgeois", "restaurant",
        "accommodate", "necessary", "perspicacious", "coulisses",
        "apple", "application", "apply", "banana", "beautiful",
        "cat", "dog", "elephant", "philosophy", "government",
    ])


@pytest.fixture(scope="module")
def phonetic_index(multilingual_vocab: list[str], encoder: PhoneticEncoder) -> PhoneticIndex:
    return PhoneticIndex(multilingual_vocab, encoder=encoder)
