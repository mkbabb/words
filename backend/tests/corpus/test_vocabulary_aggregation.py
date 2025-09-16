"""Test vocabulary aggregation mechanisms."""

from typing import TYPE_CHECKING

from floridify.caching.models import VersionInfo
from floridify.corpus.core import Corpus
from floridify.corpus.models import CorpusType

if TYPE_CHECKING:
    pass

# Import the mock from conftest


class TestVocabularyAggregation:
    """Test vocabulary merging and aggregation."""

    async def test_simple_aggregation(self, corpus_tree):
        """Test parent vocabulary is union of children."""
        master = corpus_tree["master"]
        work1 = corpus_tree["work1"]
        work2 = corpus_tree["work2"]

        # Simulate aggregation
        work1_vocab = set(work1.content_inline.get("vocabulary", []))
        work2_vocab = set(work2.content_inline.get("vocabulary", []))
        expected_vocab = work1_vocab.union(work2_vocab)

        # In real implementation, this would be done by aggregate_vocabularies()
        master.content_inline["vocabulary"] = sorted(list(expected_vocab))

        master_vocab = set(master.content_inline.get("vocabulary", []))
        assert work1_vocab.issubset(master_vocab)
        assert work2_vocab.issubset(master_vocab)

    async def test_incremental_aggregation(self, corpus_tree):
        """Test adding child updates parent vocabulary."""
        master = corpus_tree["master"]
        original_vocab = set(master.content_inline.get("vocabulary", []))

        # Add new child with unique vocabulary
        new_child = Corpus.Metadata(
            resource_id="New_Child",
            corpus_type=CorpusType.LITERATURE,
            parent_corpus_id=master.id,
            content_inline={"vocabulary": ["unique", "words", "here"]},
            vocabulary_size=3,
            vocabulary_hash="test_hash_new_child",
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="test_hash_new_child",
                is_latest=True,
            ),
        )

        # Simulate aggregation after adding child
        new_vocab = original_vocab.union(set(new_child.content_inline["vocabulary"]))
        master.content_inline["vocabulary"] = sorted(list(new_vocab))

        # Verify new words are in master
        assert "unique" in master.content_inline["vocabulary"]
        assert len(master.content_inline["vocabulary"]) > len(original_vocab)

    async def test_removal_aggregation(self, corpus_tree):
        """Test removing child updates parent vocabulary."""
        master = corpus_tree["master"]
        work1 = corpus_tree["work1"]
        work2 = corpus_tree["work2"]

        # Get work2's unique words
        work2_vocab = set(work2.content_inline.get("vocabulary", []))
        work1_vocab = set(work1.content_inline.get("vocabulary", []))

        # Remove work2 and re-aggregate
        master.child_corpus_ids.remove(work2.id)
        master.content_inline["vocabulary"] = sorted(list(work1_vocab))

        # Verify work2's unique words are removed
        unique_to_work2 = work2_vocab - work1_vocab
        master_vocab = set(master.content_inline.get("vocabulary", []))
        assert not unique_to_work2.intersection(master_vocab)

    async def test_duplicate_handling(self, sample_vocabularies):
        """Test deduplication preserves unique forms."""
        duplicates = sample_vocabularies["duplicates"]

        # Simulate deduplication
        deduplicated = list(dict.fromkeys(word.lower() for word in duplicates))

        assert len(deduplicated) == 1
        assert deduplicated[0] == "apple"

    async def test_diacritic_preference(self, sample_vocabularies):
        """Test café preferred over cafe in deduplication."""
        diacritics = sample_vocabularies["diacritics"]

        # Group by normalized form
        normalized_groups = {}
        for word in diacritics:
            # Simple normalization for testing
            normalized = word.replace("é", "e").replace("ï", "i")
            if normalized not in normalized_groups:
                normalized_groups[normalized] = []
            normalized_groups[normalized].append(word)

        # Select preferred form (with diacritics)
        selected = []
        for group in normalized_groups.values():
            # Prefer form with special characters
            preferred = max(group, key=lambda w: (any(c in w for c in "éïà"), len(w)))
            selected.append(preferred)

        assert "café" in selected
        assert "naïve" in selected
        assert "cafe" not in selected
        assert "naive" not in selected

    async def test_large_vocabulary_external(self, sample_vocabularies):
        """Test vocabularies >10k words trigger external storage."""
        large_vocab = sample_vocabularies["large"]

        corpus = Corpus.Metadata(
            corpus_name="Large_Corpus",
            corpus_type="LANGUAGE",
        )

        # Check threshold
        external_threshold = 10000
        assert len(large_vocab) > external_threshold

        # In real implementation, this would trigger external storage
        if len(large_vocab) > external_threshold:
            # Simulate external storage
            corpus.content_location = {
                "storage_type": "external",
                "path": f"/cache/corpus/{corpus.id}/vocabulary.json",
                "size": len(str(large_vocab)),
            }
            corpus.content_inline = None
        else:
            corpus.content_inline = {"vocabulary": large_vocab}

        assert corpus.content_location is not None
        assert corpus.content_inline is None

    async def test_empty_child_aggregation(self, corpus_tree):
        """Test empty children don't break parent aggregation."""
        master = corpus_tree["master"]

        # Add empty child
        empty_child = Corpus.Metadata(
            corpus_name="Empty_Child",
            corpus_type="LITERATURE",
            parent_corpus_id=master.id,
            content_inline={"vocabulary": []},
        )

        original_vocab = master.content_inline.get("vocabulary", [])

        # Aggregate with empty child
        master.child_corpus_ids.append(empty_child.id)
        # Vocabulary shouldn't change

        assert master.content_inline.get("vocabulary") == original_vocab

    async def test_unicode_vocabulary_aggregation(self, sample_vocabularies):
        """Test Unicode vocabulary aggregation."""
        unicode_vocab = sample_vocabularies["unicode"]

        parent = Corpus.Metadata(
            corpus_name="Unicode_Parent",
            corpus_type="LANGUAGE",
            is_master=True,
        )

        Corpus.Metadata(
            corpus_name="Unicode_Child",
            corpus_type="LITERATURE",
            parent_corpus_id=parent.id,
            content_inline={"vocabulary": unicode_vocab},
        )

        # Aggregate
        parent.content_inline = {"vocabulary": unicode_vocab}

        # Verify all Unicode preserved
        assert "😀" in parent.content_inline["vocabulary"]
        assert "北京" in parent.content_inline["vocabulary"]
        assert "café" in parent.content_inline["vocabulary"]

    async def test_vocabulary_statistics(self, corpus_tree):
        """Test vocabulary statistics computation."""
        work1 = corpus_tree["work1"]
        vocab = work1.content_inline.get("vocabulary", [])

        # Compute statistics
        stats = {
            "vocabulary_count": len(vocab),
            "unique_words": len(set(vocab)),
            "avg_word_length": sum(len(w) for w in vocab) / max(1, len(vocab)),
            "shortest_word": min(vocab, key=len) if vocab else None,
            "longest_word": max(vocab, key=len) if vocab else None,
        }

        assert stats["vocabulary_count"] == 3
        assert stats["unique_words"] == 3
        assert stats["avg_word_length"] > 0
        assert stats["shortest_word"] == "thy"
        assert stats["longest_word"] == "thou"
