"""Tests for different corpus types and sizes: bespoke, language-level, literature, and French."""

from __future__ import annotations

import pytest

from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


@pytest.mark.asyncio
async def test_small_bespoke_corpus(tree_manager: TreeCorpusManager, test_db):
    """Test with a small, hand-crafted corpus."""
    vocabulary = ["hello", "world", "test", "corpus", "small"]

    corpus = await tree_manager.save_corpus(
        Corpus(
            corpus_name="bespoke_small",
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
        )
    )

    assert len(corpus.vocabulary) == len(vocabulary)
    assert all(word in corpus.vocabulary for word in vocabulary)
    assert corpus.corpus_type == CorpusType.CUSTOM


@pytest.mark.asyncio
async def test_language_level_corpus(tree_manager: TreeCorpusManager, test_db):
    """Test language-level corpus with larger vocabulary."""
    # Simulate a language corpus
    base_words = ["the", "be", "to", "of", "and", "a", "in", "that", "have", "I"]
    # Generate variations
    vocabulary = []
    for word in base_words:
        vocabulary.append(word)
        vocabulary.append(word.upper())
        vocabulary.append(word.capitalize())

    corpus = await tree_manager.save_corpus(
        Corpus(
            corpus_name="language_english",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
            is_master=True,  # Mark as master language corpus
        )
    )

    assert corpus.is_master is True
    assert corpus.corpus_type == CorpusType.LANGUAGE
    # Deduplication should reduce size
    assert len(corpus.vocabulary) <= len(vocabulary)


@pytest.mark.asyncio
async def test_literature_level_corpus(tree_manager: TreeCorpusManager, test_db):
    """Test literature-level corpus with domain-specific vocabulary."""
    # Shakespeare-style vocabulary
    vocabulary = [
        "thou",
        "thee",
        "thy",
        "thine",
        "art",
        "hath",
        "doth",
        "wherefore",
        "whence",
        "hither",
        "thither",
        "'tis",
        "'twas",
        "verily",
        "forsooth",
        "prithee",
        "anon",
        "ere",
        "oft",
    ]

    parent = await tree_manager.save_corpus(
        Corpus(
            corpus_name="english_literature",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=["english"],
            original_vocabulary=["english"],
            is_master=True,
        )
    )

    corpus = await tree_manager.save_corpus(
        Corpus(
            corpus_name="shakespeare_works",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
            parent_uuid=parent.corpus_uuid,
        )
    )

    assert corpus.corpus_type == CorpusType.LITERATURE
    assert corpus.parent_uuid == parent.corpus_uuid
    assert all(word in corpus.vocabulary for word in vocabulary)


@pytest.mark.asyncio
async def test_corpus_french_vocabulary(tree_manager: TreeCorpusManager, test_db):
    """Test corpus with French vocabulary and special characters."""
    vocabulary = [
        "français",
        "élève",
        "château",
        "œuvre",
        "naïf",
        "être",
        "avoir",
        "aller",
        "faire",
        "dire",
        "bœuf",
        "cœur",
        "sœur",
        "œil",
        "hôtel",
    ]

    corpus = await tree_manager.save_corpus(
        Corpus(
            corpus_name="french_corpus",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.FRENCH,
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
        )
    )

    assert corpus.language == Language.FRENCH
    assert len(corpus.vocabulary) == len(set(vocabulary))
    # Original forms should be preserved
    assert all(word in corpus.original_vocabulary for word in vocabulary)
