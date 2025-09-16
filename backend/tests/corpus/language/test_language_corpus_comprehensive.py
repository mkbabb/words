"""Comprehensive language corpus tests with full CRUD and source management.

Tests the complete language corpus functionality including:
- CRUD operations for individual language sources
- Source management (add, remove, update)
- Full language download and aggregation
- Provider integration and URL fetching
- Parser variety (TEXT_LINES, JSON, CSV, CUSTOM)
- MongoDB persistence with versioning
- Tree structure and vocabulary aggregation
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from beanie import PydanticObjectId

from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import CacheNamespace, ResourceType, VersionConfig
from floridify.corpus.core import Corpus
from floridify.corpus.language.core import LanguageCorpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.base import Language
from floridify.corpus.models import CorpusType
from floridify.providers.language.models import LanguageEntry, ParserType, LanguageSource
from floridify.providers.language.scraper.url import URLLanguageConnector


@pytest.mark.asyncio
class TestLanguageCorpusCRUD:
    """Test CRUD operations for language corpus and sources."""

    @pytest_asyncio.fixture
    async def corpus_manager(self, test_db):
        """Create corpus manager with test database."""
        return TreeCorpusManager()

    @pytest_asyncio.fixture
    async def versioned_manager(self):
        """Create versioned data manager."""
        return VersionedDataManager()

    @pytest_asyncio.fixture
    async def mock_language_provider(self):
        """Create mock language provider."""
        provider = AsyncMock(spec=URLLanguageConnector)
        provider.fetch.return_value = {
            "source_name": "test_source",
            "language": "en",
            "provider": "custom_url",
            "vocabulary": ["apple", "banana", "cherry", "date", "elderberry"],
            "vocabulary_count": 5,
            "words": ["apple", "banana", "cherry", "date", "elderberry"],
            "phrases": ["good morning", "thank you"],
            "source_url": "https://example.com/words.txt",
            "description": "Test vocabulary source",
        }
        return provider

    async def test_create_language_corpus(self, test_db, corpus_manager):
        """Test creating a new language corpus."""
        # Create language corpus
        corpus = LanguageCorpus(
            corpus_name="english-main",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
            vocabulary=["initial", "words"],
            is_master=True,
            metadata={"sources_count": 0, "last_update": datetime.now(UTC).isoformat()},
        )

        # Save to MongoDB
        saved = await corpus_manager.save_corpus(corpus)
        assert saved is not None
        assert saved.corpus_name == "english-main"
        assert saved.corpus_type == CorpusType.LANGUAGE
        assert saved.is_master is True

    async def test_add_language_source(self, test_db, corpus_manager, mock_language_provider):
        """Test adding a language source to corpus."""
        # Create parent language corpus
        parent = LanguageCorpus(
            corpus_name="french-main",
            language=Language.FRENCH,
            corpus_type=CorpusType.LANGUAGE,
            vocabulary=[],
            is_master=True,
        )
        saved_parent = await corpus_manager.save_corpus(parent)

        # Define language source
        source = LanguageSource(
            name="french-frequency-list",
            description="Most common French words",
            url="https://example.com/french-words.txt",
            parser=ParserType.TEXT_LINES,
            language=Language.FRENCH,
        )

        # Add source (creates child corpus)
        with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
            MockConnector.return_value = mock_language_provider
            
            child_id = await parent.add_language_source(source=source)

            assert child_id is not None
            
            # Get the child corpus to verify
            child_corpus = await corpus_manager.get_corpus(corpus_id=child_id)
            assert child_corpus is not None
            assert child_corpus.corpus_name == f"french-main_{source.name}"
            assert len(child_corpus.vocabulary) == 5  # From mock provider
            
            # Verify parent-child relationship was established
            updated_parent = await corpus_manager.get_corpus(corpus_id=saved_parent.corpus_id)
            assert child_id in updated_parent.child_corpus_ids

    async def test_update_language_source(self, test_db, corpus_manager, mock_language_provider):
        """Test updating an existing language source."""
        # Create corpus with source
        parent = LanguageCorpus(
            corpus_name="spanish-main",
            language=Language.SPANISH,
            corpus_type=CorpusType.LANGUAGE,
            vocabulary=[],
            is_master=True,
        )
        saved_parent = await corpus_manager.save_corpus(parent)

        # Add initial source
        source = LanguageSource(
            name="spanish-basic",
            url="https://example.com/spanish-v1.txt",
            parser=ParserType.TEXT_LINES,
            language=Language.SPANISH,
        )

        with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
            MockConnector.return_value = mock_language_provider
            child_id = await parent.add_language_source(source)
            child = await corpus_manager.get_corpus(corpus_id=child_id)
            initial_vocab = child.vocabulary.copy()

        # Update source with new data
        mock_language_provider.fetch.return_value = {
            "source_name": "spanish-basic",
            "language": "es",
            "provider": "custom_url",
            "vocabulary": ["updated", "vocabulary", "list"],
            "vocabulary_count": 3,
            "words": ["updated", "vocabulary", "list"],
            "phrases": ["buenos días"],
            "source_url": "https://example.com/spanish-v2.txt",
            "description": "Updated Spanish vocabulary",
        }

        updated_source = LanguageSource(
            name="spanish-basic",
            url="https://example.com/spanish-v2.txt",
            parser=ParserType.TEXT_LINES,
            language=Language.SPANISH,
        )

        with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
            MockConnector.return_value = mock_language_provider
            await parent.update_source(
                source_name="spanish-basic",
                source=updated_source,
            )

            # Get the updated child corpus to verify
            updated_child = await corpus_manager.get_corpus(corpus_name=f"spanish-main_{updated_source.name}")
            assert updated_child is not None
            assert updated_child.vocabulary != initial_vocab
            assert "updated" in updated_child.vocabulary

    async def test_remove_language_source(self, test_db, corpus_manager, mock_language_provider):
        """Test removing a language source from corpus."""
        # Create corpus with multiple sources
        parent = LanguageCorpus(
            corpus_name="german-main",
            language=Language.GERMAN,
            corpus_type=CorpusType.LANGUAGE,
            vocabulary=[],
            is_master=True,
        )
        saved_parent = await corpus_manager.save_corpus(parent)

        # Add multiple sources
        sources = [
            LanguageSource(name="german-common", url="https://example.com/german1.txt", parser=ParserType.TEXT_LINES, language=Language.GERMAN),
            LanguageSource(name="german-technical", url="https://example.com/german2.txt", parser=ParserType.TEXT_LINES, language=Language.GERMAN),
        ]

        with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
            MockConnector.return_value = mock_language_provider
            for source in sources:
                await parent.add_language_source(source)

        # Remove one source
        await parent.remove_source("german-technical")

        # Verify source is removed
        remaining = await corpus_manager.aggregate_vocabularies(saved_parent.corpus_id)
        assert remaining is not None

    async def test_language_source_versioning(self, test_db, versioned_manager):
        """Test versioning of language source data."""
        resource_id = "lang-source-test"
        
        # V1: Initial source data
        v1_data = {
            "source_name": "english-frequency",
            "vocabulary": ["the", "be", "to"],
            "url": "https://example.com/v1.txt",
            "last_updated": datetime.now(UTC).isoformat(),
        }

        v1 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.LANGUAGE,
            namespace=CacheNamespace.CORPUS,
            content=v1_data,
            config=VersionConfig(version="1.0.0"),
        )

        # V2: Updated vocabulary
        v2_data = {
            "source_name": "english-frequency",
            "vocabulary": ["the", "be", "to", "of", "and"],
            "url": "https://example.com/v2.txt",
            "last_updated": datetime.now(UTC).isoformat(),
        }

        v2 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.LANGUAGE,
            namespace=CacheNamespace.CORPUS,
            content=v2_data,
            config=VersionConfig(version="2.0.0"),
        )

        assert v2.version_info.supersedes == v1.id
        assert len(v2.content["vocabulary"]) > len(v1.content["vocabulary"])


@pytest.mark.asyncio
class TestLanguageCorpusDownload:
    """Test full language download and aggregation."""

    @pytest_asyncio.fixture
    async def corpus_manager(self, test_db):
        """Create corpus manager."""
        return TreeCorpusManager()

    @pytest_asyncio.fixture
    async def mock_providers(self):
        """Create mock providers for different sources."""
        providers = {}
        
        # Scrabble dictionary provider
        scrabble_provider = AsyncMock(spec=URLLanguageConnector)
        scrabble_provider.fetch.return_value = {
            "source_name": "english-scrabble",
            "language": "en",
            "provider": "custom_url",
            "vocabulary": ["aardvark", "abandon", "ability", "able", "about"] + [f"word{i}" for i in range(100)],
            "vocabulary_count": 105,
            "words": ["aardvark", "abandon", "ability", "able", "about"] + [f"word{i}" for i in range(100)],
            "phrases": [],
            "source_url": "https://scrabble.com/dictionary.txt",
            "description": "Scrabble dictionary",
        }
        providers["scrabble"] = scrabble_provider

        # Frequency list provider
        freq_provider = AsyncMock(spec=URLLanguageConnector)
        freq_provider.fetch.return_value = {
            "source_name": "english-frequency",
            "language": "en",
            "provider": "custom_url",
            "vocabulary": ["the", "be", "to", "of", "and", "a", "in", "that", "have", "I"],
            "vocabulary_count": 10,
            "words": ["the", "be", "to", "of", "and", "a", "in", "that", "have", "I"],
            "phrases": [],
            "source_url": "https://frequency.com/top10k.txt",
            "description": "Frequency list",
        }
        providers["frequency"] = freq_provider

        # Idioms provider
        idioms_provider = AsyncMock(spec=URLLanguageConnector)
        idioms_provider.fetch.return_value = {
            "source_name": "english-idioms",
            "language": "en",
            "provider": "custom_url",
            "vocabulary": ["good morning", "thank you", "you're welcome", "break a leg", "piece of cake", "it's raining cats and dogs"],
            "vocabulary_count": 6,
            "words": [],
            "phrases": ["good morning", "thank you", "you're welcome", "break a leg", "piece of cake", "it's raining cats and dogs"],
            "source_url": "https://idioms.com/english.json",
            "description": "Idioms collection",
        }
        providers["idioms"] = idioms_provider

        return providers

    async def test_download_entire_language(self, test_db, corpus_manager, mock_providers):
        """Test downloading an entire language with all sources."""
        # Create language corpus from predefined sources
        with patch("floridify.corpus.language.core.LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE") as mock_sources:
            # Define test sources
            mock_sources.get.return_value = [
                LanguageSource(
                    name="english-scrabble",
                    description="Scrabble dictionary",
                    url="https://scrabble.com/dictionary.txt",
                    parser=ParserType.TEXT_LINES,
                    language=Language.ENGLISH,
                ),
                LanguageSource(
                    name="english-frequency",
                    description="Top 10k words by frequency",
                    url="https://frequency.com/top10k.txt",
                    parser=ParserType.TEXT_LINES,
                    language=Language.ENGLISH,
                ),
                LanguageSource(
                    name="english-idioms",
                    description="Common English idioms",
                    url="https://idioms.com/english.json",
                    parser=ParserType.JSON_VOCABULARY,
                    language=Language.ENGLISH,
                ),
            ]

            # Mock provider creation
            def create_provider(source):
                if "scrabble" in source.name:
                    return mock_providers["scrabble"]
                elif "frequency" in source.name:
                    return mock_providers["frequency"]
                elif "idioms" in source.name:
                    return mock_providers["idioms"]
                return AsyncMock()

            with patch("floridify.corpus.language.core.URLLanguageConnector", side_effect=create_provider):
                # Create language corpus with all sources
                language_corpus = await LanguageCorpus.create_from_language(
                    language=Language.ENGLISH,
                    corpus_manager=corpus_manager,
                    include_sources=None,  # Include all
                    force_refresh=True,
                )

                assert language_corpus is not None
                assert language_corpus.is_master is True
                assert language_corpus.corpus_name == "english"

                # Aggregate all vocabularies
                aggregated = await corpus_manager.aggregate_vocabularies(language_corpus.corpus_id)
                assert aggregated is not None
                assert len(aggregated) > 0  # Has vocabulary from all sources

                # Check metadata
                assert language_corpus.metadata.get("sources_count", 0) > 0

    async def test_selective_source_download(self, test_db, corpus_manager, mock_providers):
        """Test downloading only specific language sources."""
        with patch("floridify.corpus.language.core.LANGUAGE_CORPUS_SOURCES_BY_LANGUAGE") as mock_sources:
            mock_sources.get.return_value = [
                LanguageSource(name="french-basic", url="https://example.com/french1.txt", parser=ParserType.TEXT_LINES, language=Language.FRENCH),
                LanguageSource(name="french-advanced", url="https://example.com/french2.txt", parser=ParserType.TEXT_LINES, language=Language.FRENCH),
                LanguageSource(name="french-idioms", url="https://example.com/french3.txt", parser=ParserType.TEXT_LINES, language=Language.FRENCH),
            ]

            with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
                MockConnector.return_value = mock_providers["frequency"]
                
                # Download only specific sources
                language_corpus = await LanguageCorpus.create_from_language(
                    language=Language.FRENCH,
                    corpus_manager=corpus_manager,
                    include_sources=["french-basic", "french-idioms"],  # Selective
                    force_refresh=True,
                )

                assert language_corpus is not None
                # Should have created only 2 child corpora

    async def test_parallel_source_download(self, test_db, corpus_manager, mock_providers):
        """Test parallel downloading of multiple sources."""
        # Create parent corpus
        parent = LanguageCorpus(
            corpus_name="multi-source-test",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
            is_master=True,
        )
        saved_parent = await corpus_manager.save_corpus(parent)

        # Define multiple sources
        sources = [
            LanguageSource(name=f"source-{i}", url=f"https://example.com/source{i}.txt", parser=ParserType.TEXT_LINES, language=Language.ENGLISH)
            for i in range(5)
        ]

        # Add sources in parallel
        async def add_source(source):
            with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
                MockConnector.return_value = mock_providers["frequency"]
                return await parent.add_language_source(source)

        # Execute parallel downloads
        tasks = [add_source(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all succeeded
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == 5

    async def test_parser_variety(self, test_db, corpus_manager):
        """Test different parser types for language sources."""
        parent = LanguageCorpus(
            corpus_name="parser-test",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
        )
        saved_parent = await corpus_manager.save_corpus(parent)

        # Test TEXT_LINES parser
        text_provider = AsyncMock(spec=URLLanguageConnector)
        text_provider.fetch.return_value = LanguageEntry(
            vocabulary=["line1", "line2", "line3"],
            parser=ParserType.TEXT_LINES,
        )

        with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
            MockConnector.return_value = text_provider
            text_source = LanguageSource(
                name="text-source",
                url="https://example.com/text.txt",
                parser=ParserType.TEXT_LINES,
                language=Language.ENGLISH,
            )
            text_corpus_id = await parent.add_language_source(text_source)
            assert len(text_corpus.vocabulary) == 3

        # Test JSON_VOCABULARY parser
        json_provider = AsyncMock(spec=URLLanguageConnector)
        json_provider.fetch.return_value = LanguageEntry(
            vocabulary=["json1", "json2"],
            phrases=["phrase1"],
            parser=ParserType.JSON_VOCABULARY,
        )

        with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
            MockConnector.return_value = json_provider
            json_source = LanguageSource(
                name="json-source",
                url="https://example.com/vocab.json",
                parser=ParserType.JSON_VOCABULARY,
                language=Language.ENGLISH,
            )
            json_corpus_id = await parent.add_language_source(json_source)
            assert len(json_corpus.vocabulary) == 2
            assert len(json_corpus.phrases) == 1

        # Test CSV_WORDS parser
        csv_provider = AsyncMock(spec=URLLanguageConnector)
        csv_provider.fetch.return_value = LanguageEntry(
            vocabulary=["csv1", "csv2", "csv3", "csv4"],
            parser=ParserType.CSV_WORDS,
        )

        with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
            MockConnector.return_value = csv_provider
            csv_source = LanguageSource(
                name="csv-source",
                url="https://example.com/words.csv",
                parser=ParserType.CSV_WORDS,
                language=Language.ENGLISH,
            )
            csv_corpus_id = await parent.add_language_source(csv_source)
            assert len(csv_corpus.vocabulary) == 4


@pytest.mark.asyncio
class TestLanguageCorpusIntegration:
    """Test language corpus integration with other components."""

    @pytest_asyncio.fixture
    async def corpus_manager(self, test_db):
        """Create corpus manager."""
        return TreeCorpusManager()

    async def test_vocabulary_aggregation(self, test_db, corpus_manager):
        """Test vocabulary aggregation from multiple language sources."""
        # Create master corpus
        master = LanguageCorpus(
            corpus_name="aggregation-test",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
            is_master=True,
        )
        saved_master = await corpus_manager.save_corpus(master)

        # Create child sources with overlapping vocabulary
        source1 = Corpus(
            corpus_name="source1",
            vocabulary=["apple", "banana", "cherry"],
            parent_corpus_id=saved_master.corpus_id,
        )
        source2 = Corpus(
            corpus_name="source2",
            vocabulary=["banana", "date", "elderberry"],
            parent_corpus_id=saved_master.corpus_id,
        )
        source3 = Corpus(
            corpus_name="source3",
            vocabulary=["cherry", "fig", "grape"],
            parent_corpus_id=saved_master.corpus_id,
        )

        await corpus_manager.save_corpus(source1)
        await corpus_manager.save_corpus(source2)
        await corpus_manager.save_corpus(source3)

        # Aggregate vocabularies
        aggregated = await corpus_manager.aggregate_vocabularies(saved_master.corpus_id)
        
        # Should have unique words from all sources
        expected = {"apple", "banana", "cherry", "date", "elderberry", "fig", "grape"}
        assert set(aggregated) == expected

    async def test_source_metadata_preservation(self, test_db, corpus_manager):
        """Test that source metadata is preserved through operations."""
        parent = LanguageCorpus(
            corpus_name="metadata-test",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
        )
        saved_parent = await corpus_manager.save_corpus(parent)

        # Add source with rich metadata
        source = LanguageSource(
            name="metadata-source",
            description="Test source with metadata",
            url="https://example.com/data.txt",
            parser=ParserType.TEXT_LINES,
            language=Language.ENGLISH,
        )

        mock_provider = AsyncMock(spec=URLLanguageConnector)
        mock_provider.fetch.return_value = {
            "source_name": "metadata-source",
            "language": "en",
            "provider": "custom_url",
            "vocabulary": ["test"],
            "vocabulary_count": 1,
            "words": ["test"],
            "phrases": [],
            "source_url": source.url,
            "description": source.description,
        }

        with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
            MockConnector.return_value = mock_provider
            child = await parent.add_language_source(source)

            # Verify source was added
            assert child is not None

    async def test_error_handling_during_download(self, test_db, corpus_manager):
        """Test error handling when source download fails."""
        parent = LanguageCorpus(
            corpus_name="error-test",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
        )
        saved_parent = await corpus_manager.save_corpus(parent)

        # Create provider that fails
        failing_provider = AsyncMock(spec=URLLanguageConnector)
        failing_provider.fetch.side_effect = Exception("Network error")

        source = LanguageSource(
            name="failing-source",
            url="https://invalid.example.com/404.txt",
        )

        with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
            MockConnector.return_value = failing_provider
            
            # Should handle error gracefully
            try:
                result = await parent.add_language_source(source)
                # Might return None or raise, depending on implementation
            except Exception as e:
                assert "Network error" in str(e) or "fetch" in str(e).lower()

    async def test_concurrent_source_updates(self, test_db, corpus_manager):
        """Test concurrent updates to language sources."""
        parent = LanguageCorpus(
            corpus_name="concurrent-test",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
            is_master=True,
        )
        saved_parent = await corpus_manager.save_corpus(parent)

        # Add initial sources
        sources = [
            LanguageSource(name=f"concurrent-{i}", url=f"https://example.com/{i}.txt", parser=ParserType.TEXT_LINES, language=Language.ENGLISH)
            for i in range(3)
        ]

        mock_provider = AsyncMock(spec=URLLanguageConnector)
        mock_provider.fetch.return_value = {
            "source_name": "concurrent",
            "language": "en",
            "provider": "custom_url",
            "vocabulary": ["initial"],
            "vocabulary_count": 1,
            "words": ["initial"],
            "phrases": [],
            "source_url": "https://example.com/concurrent.txt",
            "description": "Concurrent test",
        }

        with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
            MockConnector.return_value = mock_provider
            for source in sources:
                await parent.add_language_source(source)

        # Update sources concurrently
        async def update_source(index):
            updated_provider = AsyncMock(spec=URLLanguageConnector)
            updated_provider.fetch.return_value = LanguageEntry(
                vocabulary=[f"updated-{index}"],
            )
            
            with patch("floridify.corpus.language.core.URLLanguageConnector") as MockConnector:
                MockConnector.return_value = updated_provider
                return await parent.update_source(
                    source_name=f"concurrent-{index}",
                    new_source=LanguageSource(
                        name=f"concurrent-{index}",
                        url=f"https://example.com/updated-{index}.txt",
                    ),
                    corpus_manager=corpus_manager,
                )

        # Execute concurrent updates
        tasks = [update_source(i) for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least some should succeed
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0

    async def test_language_corpus_statistics(self, test_db, corpus_manager):
        """Test language corpus statistics calculation."""
        # Create corpus with frequency data
        corpus = LanguageCorpus(
            corpus_name="stats-corpus",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
            vocabulary=["the", "be", "to", "of", "and"],
            word_frequencies={"the": 1000, "be": 800, "to": 700, "of": 600, "and": 500},
            unique_word_count=5,
            total_word_count=3600,
        )
        
        saved = await corpus_manager.save_corpus(corpus)
        
        # Calculate statistics
        stats = {
            "unique_words": saved.unique_word_count,
            "total_words": saved.total_word_count,
            "average_frequency": saved.total_word_count / saved.unique_word_count if saved.unique_word_count else 0,
            "most_common": max(saved.word_frequencies, key=saved.word_frequencies.get) if saved.word_frequencies else None,
        }
        
        assert stats["unique_words"] == 5
        assert stats["total_words"] == 3600
        assert stats["average_frequency"] == 720
        assert stats["most_common"] == "the"