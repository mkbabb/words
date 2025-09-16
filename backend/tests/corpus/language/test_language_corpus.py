"""Comprehensive tests for LanguageCorpus with real MongoDB integration."""

import asyncio

import pytest

from floridify.corpus.language.core import LanguageCorpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusSource, CorpusType
from floridify.models.base import Language
from floridify.providers.core import ConnectorConfig
from floridify.providers.language.core import LanguageConnector
from floridify.providers.language.sources import LANGUAGE_CORPUS_SOURCES


class TestLanguageCorpus:
    """Test LanguageCorpus functionality with real MongoDB."""

    @pytest.mark.asyncio
    async def test_language_corpus_creation(self, test_db):
        """Test creating a LanguageCorpus with MongoDB persistence."""
        corpus = LanguageCorpus(
            corpus_name="test_language_corpus",
            language=Language.ENGLISH,
            vocabulary=["apple", "banana", "cherry"],
            corpus_type=CorpusType.LANGUAGE,
        )

        # Save to MongoDB
        await corpus.save()

        assert corpus.id is not None
        assert corpus.corpus_name == "test_language_corpus"
        assert corpus.language == Language.ENGLISH
        assert len(corpus.vocabulary) == 3
        assert corpus.corpus_type == CorpusType.LANGUAGE

        # Retrieve from MongoDB
        retrieved = await LanguageCorpus.get(corpus.id)
        assert retrieved is not None
        assert retrieved.corpus_name == corpus.corpus_name
        assert retrieved.vocabulary == corpus.vocabulary

    @pytest.mark.asyncio
    async def test_language_corpus_from_sources(self, test_db):
        """Test creating LanguageCorpus from language sources."""
        sources = [
            CorpusSource(
                name="test_source_1",
                url="https://example.com/words1.txt",
                parser_type="text_lines",
            ),
            CorpusSource(
                name="test_source_2",
                url="https://example.com/words2.txt",
                parser_type="text_lines",
            ),
        ]

        corpus = await LanguageCorpus.from_sources(
            corpus_name="multi_source_corpus",
            sources=sources,
            language=Language.ENGLISH,
        )

        assert corpus.corpus_name == "multi_source_corpus"
        assert corpus.language == Language.ENGLISH
        # Should have created child corpora for each source
        assert len(corpus.child_corpus_ids) == len(sources)

    @pytest.mark.asyncio
    async def test_language_corpus_with_providers(self, test_db):
        """Test LanguageCorpus integration with language providers."""
        # Create a language provider
        config = ConnectorConfig()
        provider = LanguageConnector(config)

        # Create corpus
        corpus = LanguageCorpus(
            corpus_name="provider_corpus",
            language=Language.ENGLISH,
            vocabulary=[],
        )
        await corpus.save()

        # Add vocabulary from provider (simulated)
        test_vocabulary = ["test", "example", "sample", "demo"]
        corpus.vocabulary = test_vocabulary
        await corpus.save()

        # Verify MongoDB persistence
        retrieved = await LanguageCorpus.get(corpus.id)
        assert retrieved.vocabulary == test_vocabulary

    @pytest.mark.asyncio
    async def test_language_corpus_tree_structure(self, test_db):
        """Test LanguageCorpus as part of TreeCorpus hierarchy."""
        manager = TreeCorpusManager()

        # Create master language corpus
        master = LanguageCorpus(
            corpus_name="master_language",
            language=Language.ENGLISH,
            vocabulary=[],
            is_master=True,
        )
        await manager.save_corpus(master)

        # Create child corpora for different sources
        children = []
        for i in range(3):
            child = LanguageCorpus(
                corpus_name=f"source_{i}",
                language=Language.ENGLISH,
                vocabulary=[f"word{i}_1", f"word{i}_2", f"word{i}_3"],
                parent_corpus_id=master.id,
            )
            await manager.save_corpus(child)
            children.append(child)

        # Update master's children
        master.child_corpus_ids = [c.id for c in children]
        await manager.save_corpus(master)

        # Test vocabulary aggregation
        aggregated = await manager.aggregate_vocabularies(master)

        # Should contain all child vocabularies
        expected_words = []
        for i in range(3):
            expected_words.extend([f"word{i}_1", f"word{i}_2", f"word{i}_3"])

        assert len(aggregated) == len(set(expected_words))
        for word in expected_words:
            assert word in aggregated

    @pytest.mark.asyncio
    async def test_language_corpus_versioning(self, test_db):
        """Test versioning of LanguageCorpus with MongoDB."""
        corpus = LanguageCorpus(
            corpus_name="versioned_language",
            language=Language.ENGLISH,
            vocabulary=["initial", "words"],
        )
        await corpus.save()

        initial_version = corpus.version_info.version if corpus.version_info else 1

        # Update vocabulary
        corpus.vocabulary = ["initial", "words", "updated", "vocabulary"]
        await corpus.save()

        # Version should be incremented
        if corpus.version_info:
            assert corpus.version_info.version > initial_version

        # Retrieve and verify
        retrieved = await LanguageCorpus.get(corpus.id)
        assert "updated" in retrieved.vocabulary
        assert "vocabulary" in retrieved.vocabulary

    @pytest.mark.asyncio
    async def test_language_corpus_high_quality_sources(self, test_db):
        """Test using predefined high-quality language sources."""
        # Test with actual high-quality sources
        english_sources = [s for s in LANGUAGE_CORPUS_SOURCES if s.language == Language.ENGLISH]

        if english_sources:
            source = english_sources[0]

            corpus = LanguageCorpus(
                corpus_name=f"hq_{source.name}",
                language=source.language,
                vocabulary=[],
            )

            # Add as metadata
            corpus.metadata = {
                "source_name": source.name,
                "source_url": source.url,
                "parser_type": source.parser_type,
            }

            await corpus.save()

            assert corpus.id is not None
            assert corpus.metadata["source_name"] == source.name

    @pytest.mark.asyncio
    async def test_language_corpus_bulk_operations(self, test_db):
        """Test bulk operations on LanguageCorpus."""
        # Create multiple corpora
        corpora = []
        for i in range(5):
            corpus = LanguageCorpus(
                corpus_name=f"bulk_corpus_{i}",
                language=Language.ENGLISH,
                vocabulary=[f"bulk_word_{i}_{j}" for j in range(10)],
            )
            await corpus.save()
            corpora.append(corpus)

        # Bulk retrieve
        ids = [c.id for c in corpora]
        retrieved = await LanguageCorpus.find(LanguageCorpus.id.in_(ids)).to_list()

        assert len(retrieved) == 5
        for corpus in retrieved:
            assert corpus.corpus_name.startswith("bulk_corpus_")

    @pytest.mark.asyncio
    async def test_language_corpus_search_integration(self, test_db):
        """Test LanguageCorpus integration with search functionality."""
        from floridify.search.core import Search

        # Create corpus with searchable vocabulary
        corpus = LanguageCorpus(
            corpus_name="searchable_language",
            language=Language.ENGLISH,
            vocabulary=["apple", "application", "apply", "banana", "band"],
        )
        await corpus.save()

        # Create search engine from corpus
        search = await Search.from_corpus(corpus.resource_id)

        # Test exact search
        results = await search.search("apple")
        assert len(results) > 0
        assert results[0].word == "apple"

        # Test fuzzy search
        results = await search.search("aple")  # Misspelled
        assert len(results) > 0
        found_words = [r.word for r in results[:3]]
        assert "apple" in found_words or "apply" in found_words

    @pytest.mark.asyncio
    async def test_language_corpus_metadata_persistence(self, test_db):
        """Test metadata persistence in MongoDB."""
        corpus = LanguageCorpus(
            corpus_name="metadata_corpus",
            language=Language.FRENCH,
            vocabulary=["bonjour", "merci", "au revoir"],
            metadata={
                "description": "French greetings",
                "category": "common_phrases",
                "difficulty": "beginner",
                "tags": ["greetings", "basic", "essential"],
            },
        )
        await corpus.save()

        # Retrieve and verify metadata
        retrieved = await LanguageCorpus.get(corpus.id)
        assert retrieved.metadata["description"] == "French greetings"
        assert retrieved.metadata["category"] == "common_phrases"
        assert "greetings" in retrieved.metadata["tags"]

    @pytest.mark.asyncio
    async def test_language_corpus_concurrent_updates(self, test_db):
        """Test concurrent updates to LanguageCorpus."""
        corpus = LanguageCorpus(
            corpus_name="concurrent_corpus",
            language=Language.ENGLISH,
            vocabulary=["initial"],
        )
        await corpus.save()

        # Simulate concurrent updates
        async def update_vocabulary(word: str):
            retrieved = await LanguageCorpus.get(corpus.id)
            retrieved.vocabulary.append(word)
            await retrieved.save()
            return retrieved

        # Run concurrent updates
        tasks = [update_vocabulary(f"word_{i}") for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Final retrieval
        final = await LanguageCorpus.get(corpus.id)

        # Should have some words (exact count may vary due to race conditions)
        assert len(final.vocabulary) > 1
        assert "initial" in final.vocabulary

    @pytest.mark.asyncio
    async def test_language_corpus_deletion_cascade(self, test_db):
        """Test deletion cascade in LanguageCorpus tree."""
        manager = TreeCorpusManager()

        # Create parent-child structure
        parent = LanguageCorpus(
            corpus_name="parent_to_delete",
            language=Language.ENGLISH,
            vocabulary=["parent_word"],
        )
        await manager.save_corpus(parent)

        child = LanguageCorpus(
            corpus_name="child_to_delete",
            language=Language.ENGLISH,
            vocabulary=["child_word"],
            parent_corpus_id=parent.id,
        )
        await manager.save_corpus(child)

        # Update parent's children
        parent.child_corpus_ids = [child.id]
        await manager.save_corpus(parent)

        # Delete parent (should handle child relationship)
        await manager.delete_corpus(parent.id, cascade=True)

        # Verify deletion
        parent_check = await LanguageCorpus.get(parent.id)
        assert parent_check is None

        child_check = await LanguageCorpus.get(child.id)
        assert child_check is None

    @pytest.mark.asyncio
    async def test_language_corpus_cache_invalidation(self, test_db):
        """Test cache invalidation when LanguageCorpus is updated."""
        manager = TreeCorpusManager()

        corpus = LanguageCorpus(
            corpus_name="cache_test_corpus",
            language=Language.ENGLISH,
            vocabulary=["cache", "test"],
        )
        await manager.save_corpus(corpus)

        # Update vocabulary (should trigger cache invalidation)
        corpus.vocabulary = ["cache", "test", "updated"]
        await manager.save_corpus(corpus)

        # Invalidation should have been called
        # Verify by retrieving fresh data
        fresh = await manager.get_corpus(corpus.id)
        assert "updated" in fresh.vocabulary

    @pytest.mark.asyncio
    async def test_language_corpus_with_frequencies(self, test_db):
        """Test LanguageCorpus with word frequency data."""
        corpus = LanguageCorpus(
            corpus_name="frequency_corpus",
            language=Language.ENGLISH,
            vocabulary=["the", "a", "an", "and", "or"],
            metadata={
                "frequencies": {
                    "the": 1000000,
                    "a": 500000,
                    "an": 250000,
                    "and": 400000,
                    "or": 300000,
                }
            },
        )
        await corpus.save()

        # Retrieve and verify frequencies
        retrieved = await LanguageCorpus.get(corpus.id)
        frequencies = retrieved.metadata.get("frequencies", {})

        assert frequencies["the"] == 1000000
        assert frequencies["a"] == 500000

        # Test sorting by frequency
        sorted_words = sorted(corpus.vocabulary, key=lambda w: frequencies.get(w, 0), reverse=True)
        assert sorted_words[0] == "the"
        assert sorted_words[1] == "a"
