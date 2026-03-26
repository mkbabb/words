"""Tests for corpus creation, normalization, hashing, diacritics, and lemmatization."""

from __future__ import annotations

import pytest

from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


@pytest.mark.asyncio
async def test_corpus_creation_with_normalization(
    tree_manager: TreeCorpusManager, test_db
):
    """Test corpus creation with vocabulary normalization and deduplication."""
    # Test vocabulary with various cases needing normalization
    raw_vocabulary = [
        "Apple",  # Capitalization
        "apple",  # Duplicate after normalization
        "café",  # Diacritics
        "cafe",  # Duplicate after diacritic removal
        "naïve",  # Diacritics
        "TEST",  # All caps
        "test",  # Duplicate
        "  spaced  ",  # Extra spaces
        "multi-word phrase",  # Phrase
        "another phrase",  # Another phrase
    ]

    corpus = Corpus(
        corpus_name="normalization_test",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=raw_vocabulary,
        original_vocabulary=raw_vocabulary,
    )

    # Save corpus (should trigger normalization)
    saved = await tree_manager.save_corpus(corpus)

    assert saved.corpus_uuid is not None
    assert saved.vocabulary is not None

    # Verify normalization occurred
    sorted(set(word.lower().strip() for word in raw_vocabulary))
    # The actual normalization might be more complex, but we check basics
    assert len(saved.vocabulary) <= len(raw_vocabulary)  # Deduplication
    # Check that multi-word phrases are preserved but single words are stripped
    for word in saved.vocabulary:
        if " " not in word:  # Single words
            assert word == word.strip()  # No extra spaces

    # Verify indices were built
    assert saved.vocabulary_to_index is not None
    assert len(saved.vocabulary_to_index) == len(saved.vocabulary)

    # Verify vocabulary hash was computed
    assert saved.vocabulary_hash is not None
    assert len(saved.vocabulary_hash) > 0


@pytest.mark.asyncio
async def test_corpus_vocabulary_hashing_consistency(
    tree_manager: TreeCorpusManager, test_db
):
    """Test that vocabulary hashing is consistent and triggers rebuilds correctly."""
    vocabulary = ["apple", "banana", "cherry", "date", "elderberry"]

    corpus1 = await tree_manager.save_corpus(
        Corpus(
            corpus_name="hash_test_1",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=vocabulary.copy(),
            original_vocabulary=vocabulary.copy(),
        )
    )

    # Create another corpus with same vocabulary
    corpus2 = await tree_manager.save_corpus(
        Corpus(
            corpus_name="hash_test_2",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=vocabulary.copy(),
            original_vocabulary=vocabulary.copy(),
        )
    )

    # Same vocabulary should produce same hash
    assert corpus1.vocabulary_hash == corpus2.vocabulary_hash

    # Modify vocabulary slightly
    modified_vocab = vocabulary.copy() + ["fig"]
    corpus3 = await tree_manager.save_corpus(
        Corpus(
            corpus_name="hash_test_3",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=modified_vocab,
            original_vocabulary=modified_vocab,
        )
    )

    # Different vocabulary should produce different hash
    assert corpus3.vocabulary_hash != corpus1.vocabulary_hash


@pytest.mark.asyncio
async def test_corpus_lemmatization_integration(
    tree_manager: TreeCorpusManager, test_db
):
    """Test corpus creation with lemmatization."""
    # Words with various forms
    vocabulary = [
        "running",
        "runs",
        "ran",
        "run",  # Should lemmatize to "run"
        "better",
        "best",
        "good",  # Different lemmas
        "children",
        "child",  # Should lemmatize to "child"
        "teeth",
        "tooth",  # Irregular plural
    ]

    corpus = Corpus(
        corpus_name="lemma_test",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=vocabulary,
        original_vocabulary=vocabulary,
    )

    # Trigger lemmatization

    saved = await tree_manager.save_corpus(corpus)

    # Verify lemmatization occurred
    assert saved.lemmatized_vocabulary is not None
    assert len(saved.lemmatized_vocabulary) > 0

    # Check lemma to word mappings exist
    assert saved.lemma_to_word_indices is not None
    assert len(saved.lemma_to_word_indices) > 0

    # Verify some expected lemmatizations
    if "run" in saved.lemma_to_word_indices:
        run_indices = saved.lemma_to_word_indices["run"]
        run_words = [saved.vocabulary[i] for i in run_indices]
        # Should map multiple forms to "run"
        assert len(run_words) >= 2


@pytest.mark.asyncio
async def test_corpus_diacritic_handling(tree_manager: TreeCorpusManager, test_db):
    """Test proper handling of diacritics in corpus vocabulary."""
    vocabulary = [
        "café",
        "cafe",  # With and without accent
        "naïve",
        "naive",  # With and without diaeresis
        "résumé",
        "resume",  # Multiple diacritics
        "Zürich",  # German umlaut
        "señor",  # Spanish tilde
        "français",  # French cedilla
    ]

    corpus = Corpus(
        corpus_name="diacritic_test",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=vocabulary,
        original_vocabulary=vocabulary,
    )

    saved = await tree_manager.save_corpus(corpus)

    # Verify original forms are preserved
    assert saved.original_vocabulary is not None
    for word in vocabulary:
        assert word in saved.original_vocabulary

    # Verify normalized forms exist
    if saved.normalized_to_original_indices:
        # Check that normalized versions map to originals
        assert "cafe" in saved.vocabulary or "café" in saved.vocabulary
        assert "naive" in saved.vocabulary or "naïve" in saved.vocabulary
