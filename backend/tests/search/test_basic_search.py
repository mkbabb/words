"""Simple test to verify basic search functionality."""

from floridify.corpus.core import Corpus
from floridify.search.fuzzy import FuzzySearch
from floridify.search.trie import TrieSearch


class TestSimpleSearch:
    """Test basic search without MongoDB."""

    def test_trie_search(self):
        """Test TrieSearch without persistence."""
        from beanie import PydanticObjectId

        # Create simple corpus
        corpus = Corpus(
            corpus_name="test",
            language="en",
            vocabulary=["apple", "application", "apply", "banana", "band"],
            original_vocabulary=["apple", "application", "apply", "banana", "band"],
            unique_word_count=5,
            total_word_count=5,
        )

        # Create trie index with correct fields from TrieIndex model
        from floridify.search.models import TrieIndex

        trie_index = TrieIndex(
            corpus_id=PydanticObjectId(),
            corpus_name=corpus.corpus_name,
            vocabulary_hash="test_hash",
            trie_data=sorted(corpus.vocabulary),  # Sorted for marisa-trie
            word_frequencies={"apple": 10, "application": 5, "apply": 8, "banana": 7, "band": 6},
            original_vocabulary=corpus.vocabulary,
            normalized_to_original={word: word for word in corpus.vocabulary},
            word_count=len(corpus.vocabulary),
            max_frequency=10,
        )

        # Create trie search
        trie = TrieSearch(index=trie_index)

        # Test exact search - returns str | None
        result = trie.search_exact("apple")
        assert result == "apple"

        # Test prefix search - returns list[str]
        results = trie.search_prefix("app")
        assert len(results) == 3
        assert "apple" in results
        assert "application" in results
        assert "apply" in results

        # Test non-existent
        result = trie.search_exact("xyz")
        assert result is None

    def test_fuzzy_search(self):
        """Test FuzzySearch without persistence."""
        # Create simple corpus with all required fields
        vocabulary = ["apple", "application", "apply", "banana", "band"]
        corpus = Corpus(
            corpus_name="test",
            language="en",
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
            vocabulary_to_index={word: i for i, word in enumerate(vocabulary)},
            # Add signature buckets for fuzzy matching
            signature_buckets={},
            length_buckets={
                4: [4],  # band
                5: [0, 2],  # apple, apply
                6: [3],  # banana
                11: [1],  # application
            },
            unique_word_count=5,
            total_word_count=5,
        )

        # Build signature index manually
        from floridify.text.normalize import get_word_signature

        for idx, word in enumerate(vocabulary):
            sig = get_word_signature(word)
            if sig not in corpus.signature_buckets:
                corpus.signature_buckets[sig] = []
            corpus.signature_buckets[sig].append(idx)

        # Create fuzzy search
        fuzzy = FuzzySearch(min_score=0.5)

        # Test exact match
        results = fuzzy.search("apple", corpus)
        assert len(results) > 0
        assert results[0].word == "apple"
        assert results[0].score >= 0.99

        # Test fuzzy match
        results = fuzzy.search("aple", corpus)
        assert len(results) > 0
        assert "apple" in [r.word for r in results[:3]]

        # Test with typo
        results = fuzzy.search("banan", corpus)
        assert len(results) > 0
        assert "banana" in [r.word for r in results[:3]]
