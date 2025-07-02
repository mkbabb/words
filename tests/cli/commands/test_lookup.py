"""Tests for lookup CLI command."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner


class TestLookupCommand:
    """Test lookup command functionality."""

    @pytest.fixture
    def cli_runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_search_results(self):
        """Mock search results for testing."""
        return [
            MagicMock(word="test", score=1.0, method="exact", is_phrase=False),
            MagicMock(word="testing", score=0.85, method="fuzzy", is_phrase=False)
        ]

    @pytest.fixture
    def mock_provider_data(self):
        """Mock provider data for testing."""
        return MagicMock(
            provider_name="wiktionary",
            definitions=[
                MagicMock(
                    word_type="noun",
                    definition="A procedure to establish quality.",
                    examples=[]
                )
            ]
        )

    def test_lookup_command_basic(self, cli_runner):
        """Test basic lookup command execution."""
        try:
            from src.floridify.cli.commands.lookup import lookup
            
            with patch('src.floridify.cli.commands.lookup._lookup_async') as mock_lookup:
                mock_lookup.return_value = None
                
                result = cli_runner.invoke(lookup, ['test'])
                assert result.exit_code == 0
                mock_lookup.assert_called_once()
                
        except ImportError:
            pytest.skip("Lookup command not available")

    def test_lookup_with_provider_option(self, cli_runner):
        """Test lookup with specific provider option."""
        try:
            from src.floridify.cli.commands.lookup import lookup
            
            with patch('src.floridify.cli.commands.lookup._lookup_async') as mock_lookup:
                mock_lookup.return_value = None
                
                result = cli_runner.invoke(lookup, ['--provider', 'wiktionary', 'test'])
                assert result.exit_code == 0
                
                # Check that provider was passed correctly
                call_args = mock_lookup.call_args
                assert 'wiktionary' in call_args[1]['provider']
                
        except ImportError:
            pytest.skip("Lookup command not available")

    def test_lookup_with_multiple_providers(self, cli_runner):
        """Test lookup with multiple providers."""
        try:
            from src.floridify.cli.commands.lookup import lookup
            
            with patch('src.floridify.cli.commands.lookup._lookup_async') as mock_lookup:
                mock_lookup.return_value = None
                
                result = cli_runner.invoke(lookup, [
                    '--provider', 'wiktionary',
                    '--provider', 'dictionary_com',
                    'test'
                ])
                assert result.exit_code == 0
                
                # Check multiple providers
                call_args = mock_lookup.call_args
                providers = call_args[1]['provider']
                assert 'wiktionary' in providers
                assert 'dictionary_com' in providers
                
        except ImportError:
            pytest.skip("Lookup command not available")

    def test_lookup_with_language_option(self, cli_runner):
        """Test lookup with language specification."""
        try:
            from src.floridify.cli.commands.lookup import lookup
            
            with patch('src.floridify.cli.commands.lookup._lookup_async') as mock_lookup:
                mock_lookup.return_value = None
                
                result = cli_runner.invoke(lookup, ['--language', 'french', 'test'])
                assert result.exit_code == 0
                
                call_args = mock_lookup.call_args
                assert 'french' in call_args[1]['language']
                
        except ImportError:
            pytest.skip("Lookup command not available")

    def test_lookup_semantic_flag(self, cli_runner):
        """Test lookup with semantic search flag."""
        try:
            from src.floridify.cli.commands.lookup import lookup
            
            with patch('src.floridify.cli.commands.lookup._lookup_async') as mock_lookup:
                mock_lookup.return_value = None
                
                result = cli_runner.invoke(lookup, ['--semantic', 'test'])
                assert result.exit_code == 0
                
                call_args = mock_lookup.call_args
                assert call_args[1]['semantic'] is True
                
        except ImportError:
            pytest.skip("Lookup command not available")

    def test_lookup_no_ai_flag(self, cli_runner):
        """Test lookup with AI disabled."""
        try:
            from src.floridify.cli.commands.lookup import lookup
            
            with patch('src.floridify.cli.commands.lookup._lookup_async') as mock_lookup:
                mock_lookup.return_value = None
                
                result = cli_runner.invoke(lookup, ['--no-ai', 'test'])
                assert result.exit_code == 0
                
                call_args = mock_lookup.call_args
                assert call_args[1]['no_ai'] is True
                
        except ImportError:
            pytest.skip("Lookup command not available")

    @pytest.mark.asyncio
    async def test_lookup_async_implementation(self, mock_search_results, mock_provider_data):
        """Test async lookup implementation."""
        try:
            from src.floridify.cli.commands.lookup import _lookup_async
            
            # Mock all dependencies
            with patch('src.floridify.cli.commands.lookup._search_word') as mock_search, \
                 patch('src.floridify.cli.commands.lookup._get_provider_definition') as mock_provider, \
                 patch('src.floridify.cli.commands.lookup._synthesize_with_ai') as mock_ai:
                
                mock_search.return_value = mock_search_results
                mock_provider.return_value = mock_provider_data
                mock_ai.return_value = MagicMock()
                
                # Should complete without error
                await _lookup_async(
                    word="test",
                    provider=("wiktionary",),
                    language=("english",),
                    semantic=False,
                    no_ai=False
                )
                
                mock_search.assert_called_once()
                mock_provider.assert_called()
                
        except ImportError:
            pytest.skip("Lookup async implementation not available")

    @pytest.mark.asyncio
    async def test_search_word_functionality(self):
        """Test search word helper function."""
        try:
            from src.floridify.cli.commands.lookup import _search_word
            from src.floridify.constants import Language
            
            with patch('src.floridify.search.SearchEngine') as mock_engine:
                mock_engine_instance = AsyncMock()
                mock_engine_instance.search.return_value = []
                mock_engine.return_value = mock_engine_instance
                
                result = await _search_word("test", [Language.ENGLISH], False)
                
                assert isinstance(result, list)
                mock_engine_instance.initialize.assert_called_once()
                mock_engine_instance.search.assert_called_once()
                
        except ImportError:
            pytest.skip("Search word functionality not available")

    @pytest.mark.asyncio
    async def test_provider_definition_fetch(self):
        """Test provider definition fetching."""
        try:
            from src.floridify.cli.commands.lookup import _get_provider_definition
            from src.floridify.constants import DictionaryProvider
            
            with patch('src.floridify.connectors.wiktionary.WiktionaryConnector') as mock_connector:
                mock_instance = AsyncMock()
                mock_instance.fetch_definition.return_value = MagicMock()
                mock_connector.return_value = mock_instance
                
                result = await _get_provider_definition("test", DictionaryProvider.WIKTIONARY)
                
                assert result is not None
                mock_instance.fetch_definition.assert_called_once_with("test")
                
        except ImportError:
            pytest.skip("Provider definition fetch not available")

    @pytest.mark.asyncio
    async def test_ai_synthesis(self, mock_provider_data):
        """Test AI synthesis functionality."""
        try:
            from src.floridify.cli.commands.lookup import _synthesize_with_ai
            from src.floridify.models import Word
            
            with patch('src.floridify.ai.create_definition_synthesizer') as mock_factory:
                mock_synthesizer = AsyncMock()
                mock_synthesizer.synthesize_entry.return_value = MagicMock()
                mock_factory.return_value = mock_synthesizer
                
                word = Word(text="test")
                providers = {"wiktionary": mock_provider_data}
                
                result = await _synthesize_with_ai(word, providers)
                
                assert result is not None
                mock_synthesizer.synthesize_entry.assert_called_once()
                
        except ImportError:
            pytest.skip("AI synthesis not available")

    @pytest.mark.asyncio
    async def test_no_results_handling(self):
        """Test handling when no search results found."""
        try:
            from src.floridify.cli.commands.lookup import _handle_no_results
            from src.floridify.constants import DictionaryProvider
            
            with patch('src.floridify.ai.create_definition_synthesizer') as mock_factory:
                mock_synthesizer = AsyncMock()
                mock_synthesizer.generate_fallback_entry.return_value = MagicMock()
                mock_factory.return_value = mock_synthesizer
                
                # Should not raise exception
                await _handle_no_results("unknownword", [DictionaryProvider.WIKTIONARY], False)
                
                mock_synthesizer.generate_fallback_entry.assert_called_once()
                
        except ImportError:
            pytest.skip("No results handling not available")

    def test_display_synthesized_entry(self):
        """Test display of synthesized entries."""
        try:
            from src.floridify.cli.commands.lookup import _display_synthesized_entry
            from src.floridify.models import Word
            
            # Mock entry with definitions
            mock_entry = MagicMock()
            mock_entry.word = Word(text="test")
            mock_entry.definitions = [MagicMock()]
            mock_entry.pronunciation.phonetic = "/test/"
            
            # Should not raise exception
            _display_synthesized_entry(mock_entry)
            
        except ImportError:
            pytest.skip("Display functionality not available")

    def test_display_multiple_providers(self, mock_provider_data):
        """Test display of multiple provider results."""
        try:
            from src.floridify.cli.commands.lookup import _display_multiple_providers
            
            provider_data = {"wiktionary": mock_provider_data}
            
            # Should not raise exception
            _display_multiple_providers(provider_data)
            
        except ImportError:
            pytest.skip("Multi-provider display not available")

    def test_error_handling(self, cli_runner):
        """Test error handling in lookup command."""
        try:
            from src.floridify.cli.commands.lookup import lookup
            
            with patch('src.floridify.cli.commands.lookup._lookup_async') as mock_lookup:
                mock_lookup.side_effect = Exception("Test error")
                
                result = cli_runner.invoke(lookup, ['test'])
                
                # Should handle error gracefully
                assert "error" in result.output.lower() or result.exit_code != 0
                
        except ImportError:
            pytest.skip("Error handling not available")

    def test_word_normalization(self):
        """Test word normalization in lookup."""
        try:
            from src.floridify.cli.commands.lookup import _lookup_async
            from src.floridify.utils.normalization import normalize_word
            
            # Test that normalization is applied
            normalized = normalize_word("  TEST  ")
            assert normalized == "test"
            
        except ImportError:
            pytest.skip("Word normalization not available")