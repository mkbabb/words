"""Fixtures for fuzzy search tests."""

from __future__ import annotations

import asyncio

import pytest

from floridify.corpus.core import Corpus
from floridify.search.fuzzy.bk_tree import BKTree
from floridify.search.fuzzy.suffix_array import SuffixArray


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
def bk_tree(multilingual_vocab: list[str]) -> BKTree:
    return BKTree.build(multilingual_vocab)


@pytest.fixture(scope="module")
def suffix_array(multilingual_vocab: list[str]) -> SuffixArray:
    return SuffixArray(multilingual_vocab)


@pytest.fixture(scope="module")
def small_corpus():
    """In-memory corpus for integration tests."""
    vocab = sorted([
        "cafe", "café", "naive", "naïve", "resume", "résumé",
        "apple", "application", "apply", "banana", "beautiful",
        "accommodate", "necessary", "perspicacious", "philosophy",
        "en coulisses", "joie de vivre", "mise en scene", "faux pas",
        "coulisses", "entrepreneur", "bourgeois", "restaurant",
    ])
    return asyncio.get_event_loop().run_until_complete(Corpus.create("test_components", vocab))
