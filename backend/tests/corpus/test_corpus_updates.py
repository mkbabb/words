"""Tests for incremental corpus update operations (add_words, remove_words).

Phase 2 Critical - These methods were previously missing (CRITICAL GAP).
Tests cover:
- Adding words incrementally
- Removing words incrementally
- Index consistency after updates
- Hash recalculation
- Vocabulary statistics updates
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus
from floridify.models.base import Language


@pytest_asyncio.fixture
async def base_corpus() -> Corpus:
    """Create a base corpus for testing updates."""
    words = ["apple", "banana", "cherry", "date", "elderberry"]
    corpus = await Corpus.create(
        corpus_name="test-corpus",
        vocabulary=words,
        language=Language.ENGLISH,
    )
    return corpus


class TestCorpusAddWords:
    """Test incremental word addition to corpus."""

    @pytest.mark.asyncio
    async def test_add_words_basic(self, base_corpus: Corpus) -> None:
        """Test adding new words to corpus."""
        original_count = len(base_corpus.vocabulary)
        original_hash = base_corpus.vocabulary_hash

        # Add new words
        new_words = ["fig", "grape", "honeydew"]
        added = await base_corpus.add_words(new_words)

        # Verify counts
        assert added == 3
        assert len(base_corpus.vocabulary) == original_count + 3
        assert base_corpus.unique_word_count == original_count + 3

        # Verify words were added
        assert "fig" in base_corpus.vocabulary
        assert "grape" in base_corpus.vocabulary
        assert "honeydew" in base_corpus.vocabulary

        # Verify hash changed
        assert base_corpus.vocabulary_hash != original_hash

        # Verify vocabulary is still sorted
        assert base_corpus.vocabulary == sorted(base_corpus.vocabulary)

    @pytest.mark.asyncio
    async def test_add_words_with_duplicates(self, base_corpus: Corpus) -> None:
        """Test adding words that already exist (should deduplicate)."""
        original_count = len(base_corpus.vocabulary)

        # Add words, some duplicates
        new_words = ["apple", "fig", "banana", "grape"]  # apple and banana already exist
        added = await base_corpus.add_words(new_words)

        # Should only add 2 new unique words
        assert added == 2
        assert len(base_corpus.vocabulary) == original_count + 2
        assert "fig" in base_corpus.vocabulary
        assert "grape" in base_corpus.vocabulary

    @pytest.mark.asyncio
    async def test_add_words_empty_list(self, base_corpus: Corpus) -> None:
        """Test adding empty list does nothing."""
        original_count = len(base_corpus.vocabulary)
        original_hash = base_corpus.vocabulary_hash

        added = await base_corpus.add_words([])

        assert added == 0
        assert len(base_corpus.vocabulary) == original_count
        assert base_corpus.vocabulary_hash == original_hash

    @pytest.mark.asyncio
    async def test_add_words_updates_indices(self, base_corpus: Corpus) -> None:
        """Test that adding words rebuilds all indices correctly."""
        # Add new words
        new_words = ["kiwi", "lemon", "mango"]
        await base_corpus.add_words(new_words)

        # Verify vocabulary_to_index is consistent
        for idx, word in enumerate(base_corpus.vocabulary):
            assert base_corpus.vocabulary_to_index[word] == idx

        # Verify all added words are in the index
        assert "kiwi" in base_corpus.vocabulary_to_index
        assert "lemon" in base_corpus.vocabulary_to_index
        assert "mango" in base_corpus.vocabulary_to_index

    @pytest.mark.asyncio
    async def test_add_words_updates_original_vocabulary(self, base_corpus: Corpus) -> None:
        """Test that original vocabulary is preserved."""
        original_count = len(base_corpus.original_vocabulary)

        # Add words with different cases (original forms preserved)
        new_words = ["Kiwi", "LEMON", "mango"]
        await base_corpus.add_words(new_words)

        # Verify original forms are preserved
        assert len(base_corpus.original_vocabulary) == original_count + 3
        assert "Kiwi" in base_corpus.original_vocabulary
        assert "LEMON" in base_corpus.original_vocabulary
        assert "mango" in base_corpus.original_vocabulary

        # Verify normalized forms are in vocabulary
        assert "kiwi" in base_corpus.vocabulary
        assert "lemon" in base_corpus.vocabulary
        assert "mango" in base_corpus.vocabulary

    @pytest.mark.asyncio
    async def test_add_words_updates_lemmatization(self, base_corpus: Corpus) -> None:
        """Test that lemmatization maps are rebuilt."""
        # Add words
        new_words = ["running", "runner", "runs"]
        await base_corpus.add_words(new_words)

        # Verify lemmatized vocabulary exists
        assert base_corpus.lemmatized_vocabulary is not None
        assert len(base_corpus.lemmatized_vocabulary) > 0

        # Verify mappings exist
        assert len(base_corpus.word_to_lemma_indices) > 0
        assert len(base_corpus.lemma_to_word_indices) > 0

    @pytest.mark.asyncio
    async def test_add_words_updates_signature_index(self, base_corpus: Corpus) -> None:
        """Test that signature buckets are rebuilt."""
        # Add words
        new_words = ["xyz", "abc", "def"]
        await base_corpus.add_words(new_words)

        # Verify signature buckets contain new words
        assert len(base_corpus.signature_buckets) > 0
        assert len(base_corpus.length_buckets) > 0

        # Verify new words are indexed
        for word in new_words:
            word_idx = base_corpus.vocabulary_to_index.get(word)
            assert word_idx is not None

    @pytest.mark.asyncio
    async def test_add_words_updates_frequencies(self, base_corpus: Corpus) -> None:
        """Test that word frequencies are tracked."""
        # Add words
        new_words = ["fig", "grape", "fig"]  # fig appears twice
        await base_corpus.add_words(new_words)

        # Verify frequencies
        assert "fig" in base_corpus.word_frequencies
        assert "grape" in base_corpus.word_frequencies
        # fig appears twice in new_words
        assert base_corpus.word_frequencies["fig"] >= 2

    @pytest.mark.asyncio
    async def test_add_words_updates_timestamp(self, base_corpus: Corpus) -> None:
        """Test that last_updated timestamp is updated."""
        import time

        original_timestamp = base_corpus.last_updated
        time.sleep(0.01)  # Small delay

        await base_corpus.add_words(["newword"])

        assert base_corpus.last_updated > original_timestamp


class TestCorpusRemoveWords:
    """Test incremental word removal from corpus."""

    @pytest.mark.asyncio
    async def test_remove_words_basic(self, base_corpus: Corpus) -> None:
        """Test removing words from corpus."""
        original_count = len(base_corpus.vocabulary)
        original_hash = base_corpus.vocabulary_hash

        # Remove words
        words_to_remove = ["apple", "cherry"]
        removed = await base_corpus.remove_words(words_to_remove)

        # Verify counts
        assert removed == 2
        assert len(base_corpus.vocabulary) == original_count - 2
        assert base_corpus.unique_word_count == original_count - 2

        # Verify words were removed
        assert "apple" not in base_corpus.vocabulary
        assert "cherry" not in base_corpus.vocabulary

        # Verify remaining words still present
        assert "banana" in base_corpus.vocabulary
        assert "date" in base_corpus.vocabulary
        assert "elderberry" in base_corpus.vocabulary

        # Verify hash changed
        assert base_corpus.vocabulary_hash != original_hash

        # Verify vocabulary is still sorted
        assert base_corpus.vocabulary == sorted(base_corpus.vocabulary)

    @pytest.mark.asyncio
    async def test_remove_words_nonexistent(self, base_corpus: Corpus) -> None:
        """Test removing words that don't exist."""
        original_count = len(base_corpus.vocabulary)

        # Try to remove words that don't exist
        words_to_remove = ["xyz", "abc", "def"]
        removed = await base_corpus.remove_words(words_to_remove)

        # Nothing should be removed
        assert removed == 0
        assert len(base_corpus.vocabulary) == original_count

    @pytest.mark.asyncio
    async def test_remove_words_empty_list(self, base_corpus: Corpus) -> None:
        """Test removing empty list does nothing."""
        original_count = len(base_corpus.vocabulary)
        original_hash = base_corpus.vocabulary_hash

        removed = await base_corpus.remove_words([])

        assert removed == 0
        assert len(base_corpus.vocabulary) == original_count
        assert base_corpus.vocabulary_hash == original_hash

    @pytest.mark.asyncio
    async def test_remove_words_updates_indices(self, base_corpus: Corpus) -> None:
        """Test that removing words rebuilds all indices correctly."""
        # Remove words
        await base_corpus.remove_words(["apple", "banana"])

        # Verify vocabulary_to_index is consistent
        for idx, word in enumerate(base_corpus.vocabulary):
            assert base_corpus.vocabulary_to_index[word] == idx

        # Verify removed words are not in index
        assert "apple" not in base_corpus.vocabulary_to_index
        assert "banana" not in base_corpus.vocabulary_to_index

    @pytest.mark.asyncio
    async def test_remove_words_updates_original_vocabulary(self, base_corpus: Corpus) -> None:
        """Test that original vocabulary is updated."""
        original_count = len(base_corpus.original_vocabulary)

        # Remove words
        await base_corpus.remove_words(["apple", "cherry"])

        # Verify original vocabulary is updated
        assert len(base_corpus.original_vocabulary) < original_count
        assert "apple" not in base_corpus.original_vocabulary
        assert "cherry" not in base_corpus.original_vocabulary

    @pytest.mark.asyncio
    async def test_remove_words_updates_lemmatization(self, base_corpus: Corpus) -> None:
        """Test that lemmatization maps are rebuilt."""
        # Remove words
        await base_corpus.remove_words(["apple", "banana"])

        # Verify lemmatization still valid
        assert base_corpus.lemmatized_vocabulary is not None
        assert len(base_corpus.word_to_lemma_indices) == len(base_corpus.vocabulary)

    @pytest.mark.asyncio
    async def test_remove_words_updates_frequencies(self, base_corpus: Corpus) -> None:
        """Test that word frequencies are removed."""
        # Ensure frequencies exist
        base_corpus.word_frequencies["apple"] = 5
        base_corpus.word_frequencies["banana"] = 3

        # Remove words
        await base_corpus.remove_words(["apple"])

        # Verify frequency removed
        assert "apple" not in base_corpus.word_frequencies
        assert "banana" in base_corpus.word_frequencies

    @pytest.mark.asyncio
    async def test_remove_words_updates_timestamp(self, base_corpus: Corpus) -> None:
        """Test that last_updated timestamp is updated."""
        import time

        original_timestamp = base_corpus.last_updated
        time.sleep(0.01)  # Small delay

        await base_corpus.remove_words(["apple"])

        assert base_corpus.last_updated > original_timestamp


class TestCorpusUpdateCombinations:
    """Test combinations of add and remove operations."""

    @pytest.mark.asyncio
    async def test_add_then_remove(self, base_corpus: Corpus) -> None:
        """Test adding words then removing them."""
        original_count = len(base_corpus.vocabulary)

        # Add words
        await base_corpus.add_words(["kiwi", "lemon"])
        assert len(base_corpus.vocabulary) == original_count + 2

        # Remove words
        await base_corpus.remove_words(["kiwi"])
        assert len(base_corpus.vocabulary) == original_count + 1
        assert "kiwi" not in base_corpus.vocabulary
        assert "lemon" in base_corpus.vocabulary

    @pytest.mark.asyncio
    async def test_remove_then_add_back(self, base_corpus: Corpus) -> None:
        """Test removing words then adding them back."""
        original_count = len(base_corpus.vocabulary)
        original_hash = base_corpus.vocabulary_hash

        # Remove word
        await base_corpus.remove_words(["apple"])
        assert "apple" not in base_corpus.vocabulary

        # Add it back
        await base_corpus.add_words(["apple"])
        assert "apple" in base_corpus.vocabulary
        assert len(base_corpus.vocabulary) == original_count

        # Hash might be same or different depending on implementation
        # but corpus should be valid

    @pytest.mark.asyncio
    async def test_multiple_sequential_updates(self, base_corpus: Corpus) -> None:
        """Test multiple sequential add/remove operations."""
        # Track consistency through multiple operations
        for _ in range(3):
            await base_corpus.add_words(["test1", "test2"])
            await base_corpus.remove_words(["test1"])

        # Verify corpus is still consistent
        assert base_corpus.vocabulary == sorted(base_corpus.vocabulary)
        for idx, word in enumerate(base_corpus.vocabulary):
            assert base_corpus.vocabulary_to_index[word] == idx

    @pytest.mark.asyncio
    async def test_vocabulary_consistency_after_updates(self, base_corpus: Corpus) -> None:
        """Test that vocabulary remains consistent after complex updates."""
        # Complex sequence of operations
        await base_corpus.add_words(["x", "y", "z"])
        await base_corpus.remove_words(["apple", "banana"])
        await base_corpus.add_words(["a", "b", "c"])
        await base_corpus.remove_words(["x", "y"])

        # Verify consistency
        assert base_corpus.vocabulary == sorted(base_corpus.vocabulary)
        assert len(base_corpus.vocabulary) == base_corpus.unique_word_count
        assert len(base_corpus.original_vocabulary) == base_corpus.total_word_count
        assert len(base_corpus.vocabulary_to_index) == len(base_corpus.vocabulary)

        # Verify no duplicates
        assert len(set(base_corpus.vocabulary)) == len(base_corpus.vocabulary)