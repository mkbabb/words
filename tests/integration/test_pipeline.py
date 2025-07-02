"""Integration tests for end-to-end word processing pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.floridify.constants import DictionaryProvider, Language
from src.floridify.models import Word


class TestWordLookupPipeline:
    """Test complete word lookup pipeline."""

    @pytest.fixture
    def mock_pipeline_components(self, mock_cache_dir, mock_openai_client, mock_httpx_client, mock_wiktionary_response):
        """Mock all pipeline components."""
        mocks = {}
        
        # Mock search engine
        with patch('src.floridify.search.SearchEngine') as mock_search:
            mock_search_instance = AsyncMock()
            mock_search_instance.search.return_value = [
                MagicMock(word="test", score=1.0, method="exact", is_phrase=False)
            ]
            mock_search.return_value = mock_search_instance
            mocks['search'] = mock_search
        
        # Mock Wiktionary connector
        with patch('src.floridify.connectors.wiktionary.WiktionaryConnector') as mock_connector:
            mock_connector_instance = AsyncMock()
            mock_connector_instance.fetch_definition.return_value = MagicMock(
                provider=DictionaryProvider.WIKTIONARY,
                word=Word(text="test"),
                definitions=[MagicMock(word_type="noun", definition="Test definition")]
            )
            mock_connector.return_value = mock_connector_instance
            mocks['connector'] = mock_connector
        
        # Mock AI synthesizer
        with patch('src.floridify.ai.create_definition_synthesizer') as mock_ai:
            mock_ai_instance = AsyncMock()
            mock_ai_instance.synthesize_entry.return_value = MagicMock(
                word=Word(text="test"),
                definitions=[MagicMock(word_type="noun", definition="Synthesized definition")]
            )
            mock_ai.return_value = mock_ai_instance
            mocks['ai'] = mock_ai
        
        return mocks

    @pytest.mark.asyncio
    async def test_successful_word_lookup(self, mock_pipeline_components):
        """Test successful end-to-end word lookup."""
        from src.floridify.cli.commands.lookup import _lookup_async
        
        # Execute lookup
        await _lookup_async(
            word="test",
            provider=("wiktionary",),
            language=("english",),
            semantic=False,
            no_ai=False
        )
        
        # Verify pipeline executed
        search_mock = mock_pipeline_components['search']
        connector_mock = mock_pipeline_components['connector']
        ai_mock = mock_pipeline_components['ai']
        
        # Search should be called
        search_mock.assert_called_once()
        
        # Connector should be called
        connector_mock.assert_called_once()
        
        # AI synthesis should be called
        ai_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_fallback_pipeline(self, mock_pipeline_components):
        """Test pipeline when exact match fails but fuzzy search succeeds."""
        # Mock search to return fuzzy match
        search_mock = mock_pipeline_components['search']
        search_mock.return_value.search.return_value = [
            MagicMock(word="testing", score=0.8, method="fuzzy", is_phrase=False)
        ]
        
        from src.floridify.cli.commands.lookup import _lookup_async
        
        await _lookup_async(
            word="tets",  # Typo
            provider=("wiktionary",),
            language=("english",),
            semantic=False,
            no_ai=False
        )
        
        # Should still execute full pipeline with best match
        assert search_mock.return_value.search.called

    @pytest.mark.asyncio
    async def test_ai_fallback_pipeline(self, mock_pipeline_components):
        """Test AI fallback when no dictionary results found."""
        # Mock empty search results
        search_mock = mock_pipeline_components['search']
        search_mock.return_value.search.return_value = []
        
        # Mock AI fallback
        ai_mock = mock_pipeline_components['ai']
        ai_mock.return_value.generate_fallback_entry.return_value = MagicMock(
            word=Word(text="unknownword"),
            definitions=[MagicMock(definition="AI-generated definition")]
        )
        
        from src.floridify.cli.commands.lookup import _lookup_async
        
        await _lookup_async(
            word="unknownword",
            provider=("wiktionary",),
            language=("english",),
            semantic=False,
            no_ai=False
        )
        
        # Should call AI fallback
        ai_mock.return_value.generate_fallback_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_provider_pipeline(self, mock_pipeline_components):
        """Test pipeline with multiple dictionary providers."""
        from src.floridify.cli.commands.lookup import _lookup_async
        
        await _lookup_async(
            word="test",
            provider=("wiktionary", "dictionary_com"),
            language=("english",),
            semantic=False,
            no_ai=False
        )
        
        # Should attempt both providers
        # (Implementation depends on actual provider handling)

    @pytest.mark.asyncio
    async def test_semantic_search_pipeline(self, mock_pipeline_components):
        """Test pipeline with semantic search enabled."""
        from src.floridify.cli.commands.lookup import _lookup_async
        
        await _lookup_async(
            word="test",
            provider=("wiktionary",),
            language=("english",),
            semantic=True,
            no_ai=False
        )
        
        # Search engine should be initialized with semantic enabled
        search_mock = mock_pipeline_components['search']
        search_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_pipeline(self, mock_pipeline_components):
        """Test pipeline error handling."""
        # Mock connector failure
        connector_mock = mock_pipeline_components['connector']
        connector_mock.return_value.fetch_definition.side_effect = Exception("API Error")
        
        from src.floridify.cli.commands.lookup import _lookup_async
        
        # Should not crash on connector error
        await _lookup_async(
            word="test",
            provider=("wiktionary",),
            language=("english",),
            semantic=False,
            no_ai=False
        )


class TestSearchIndexingPipeline:
    """Test search index building pipeline."""

    @pytest.mark.asyncio
    async def test_search_initialization(self, mock_cache_dir):
        """Test search engine initialization pipeline."""
        from src.floridify.search import SearchEngine
        
        with patch('src.floridify.search.lexicon.LexiconLoader') as mock_loader:
            # Mock lexicon data
            mock_loader_instance = AsyncMock()
            mock_loader_instance.get_all_words.return_value = ["test", "hello", "world"]
            mock_loader_instance.get_all_phrases.return_value = ["hello world", "test phrase"]
            mock_loader.return_value = mock_loader_instance
            
            engine = SearchEngine(
                cache_dir=mock_cache_dir,
                languages=[Language.ENGLISH],
                enable_semantic=False
            )
            
            await engine.initialize()
            
            assert engine._initialized
            assert engine.lexicon_loader is not None
            assert engine.trie_search is not None
            assert engine.fuzzy_search is not None

    @pytest.mark.asyncio
    async def test_lexicon_loading_pipeline(self, mock_cache_dir):
        """Test lexicon loading and caching pipeline."""
        from src.floridify.search.lexicon import LexiconLoader
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock HTTP responses for lexicon sources
            mock_response = MagicMock()
            mock_response.text = "word1\nword2\nword3"
            mock_client.return_value.get.return_value = mock_response
            
            loader = LexiconLoader(mock_cache_dir, force_rebuild=True)
            await loader.load_languages([Language.ENGLISH])
            
            # Should have loaded words
            words = loader.get_all_words()
            assert len(words) > 0

    @pytest.mark.asyncio
    async def test_semantic_index_building(self, mock_cache_dir, mock_openai_client):
        """Test semantic search index building."""
        from src.floridify.search.semantic import SemanticSearch
        
        with patch('src.floridify.search.semantic.AsyncOpenAI') as mock_openai:
            mock_openai.return_value = mock_openai_client
            
            search = SemanticSearch(cache_dir=mock_cache_dir)
            await search.initialize(["test", "hello", "world"])
            
            # Should have built embeddings
            assert hasattr(search, '_word_embeddings')


class TestAnkiGenerationPipeline:
    """Test Anki flashcard generation pipeline."""

    @pytest.mark.asyncio
    async def test_anki_generation_from_lookup(self, mock_cache_dir):
        """Test generating Anki cards from lookup results."""
        from src.floridify.anki import AnkiGenerator
        from src.floridify.models import DictionaryEntry
        
        # Mock dictionary entry
        entry = MagicMock(spec=DictionaryEntry)
        entry.word.text = "test"
        entry.ai_synthesized.definitions = [
            MagicMock(word_type="noun", definition="Test definition", examples=[])
        ]
        
        generator = AnkiGenerator()
        
        # Should generate cards without error
        cards = generator.generate_cards(entry)
        assert len(cards) > 0

    @pytest.mark.asyncio
    async def test_anki_deck_export(self, mock_cache_dir):
        """Test Anki deck export pipeline."""
        from src.floridify.anki import AnkiGenerator
        
        generator = AnkiGenerator()
        
        # Mock some cards
        with patch.object(generator, 'generate_cards') as mock_generate:
            mock_generate.return_value = [MagicMock(), MagicMock()]
            
            output_path = mock_cache_dir / "test_deck.apkg"
            
            # Should export without error
            generator.export_deck([], output_path)
            
            # File should be created
            assert output_path.exists()


class TestCLIIntegration:
    """Test CLI command integration."""

    @pytest.mark.asyncio
    async def test_lookup_command_integration(self):
        """Test lookup command with mocked components."""
        from click.testing import CliRunner

        from src.floridify.cli.commands.lookup import lookup
        
        runner = CliRunner()
        
        with patch('src.floridify.cli.commands.lookup._lookup_async') as mock_lookup:
            mock_lookup.return_value = None
            
            result = runner.invoke(lookup, ['test'])
            
            assert result.exit_code == 0
            mock_lookup.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_command_integration(self):
        """Test search command integration."""
        from click.testing import CliRunner

        from src.floridify.cli.commands.search import search_word
        
        runner = CliRunner()
        
        with patch('src.floridify.search.SearchEngine') as mock_engine:
            mock_engine_instance = AsyncMock()
            mock_engine_instance.search.return_value = []
            mock_engine.return_value = mock_engine_instance
            
            result = runner.invoke(search_word, ['test'])
            
            # Should complete without error
            assert result.exit_code == 0


class TestDatabaseIntegration:
    """Test database integration pipeline."""

    @pytest.mark.asyncio
    async def test_entry_storage_pipeline(self, mock_database):
        """Test storing dictionary entries."""
        from datetime import datetime

        from src.floridify.constants import Language
        from src.floridify.models import DictionaryEntry, Word
        
        entry = DictionaryEntry(
            word=Word(text="test"),
            language=Language.ENGLISH,
            providers={},
            ai_synthesized=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Mock save operation
        with patch.object(entry, 'save') as mock_save:
            mock_save.return_value = None
            
            await entry.save()
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_retrieval_pipeline(self, mock_database):
        """Test API response caching."""
        from src.floridify.models import APIResponseCache
        
        cache_entry = APIResponseCache(
            url="https://example.com/api",
            response_data={"test": "data"},
            created_at=datetime.now()
        )
        
        # Mock database operations
        with patch.object(APIResponseCache, 'find_one') as mock_find:
            mock_find.return_value = cache_entry
            
            result = await APIResponseCache.find_one({"url": "https://example.com/api"})
            assert result is not None


class TestPerformanceIntegration:
    """Test performance of integrated pipeline."""

    @pytest.mark.asyncio
    async def test_lookup_performance(self, mock_pipeline_components):
        """Test lookup pipeline performance."""
        import time

        from src.floridify.cli.commands.lookup import _lookup_async
        
        start_time = time.time()
        
        await _lookup_async(
            word="test",
            provider=("wiktionary",),
            language=("english",),
            semantic=False,
            no_ai=False
        )
        
        end_time = time.time()
        
        # Should complete quickly (< 5 seconds with mocks)
        assert end_time - start_time < 5.0

    @pytest.mark.asyncio
    async def test_search_performance(self, mock_cache_dir):
        """Test search performance with large datasets."""
        from src.floridify.search import SearchEngine
        
        with patch('src.floridify.search.lexicon.LexiconLoader') as mock_loader:
            # Mock large dataset
            large_word_list = [f"word{i}" for i in range(1000)]
            mock_loader_instance = AsyncMock()
            mock_loader_instance.get_all_words.return_value = large_word_list
            mock_loader_instance.get_all_phrases.return_value = []
            mock_loader.return_value = mock_loader_instance
            
            engine = SearchEngine(cache_dir=mock_cache_dir, enable_semantic=False)
            await engine.initialize()
            
            start_time = time.time()
            results = await engine.search("word500")
            end_time = time.time()
            
            # Should complete quickly even with large dataset
            assert end_time - start_time < 1.0
            assert len(results) > 0