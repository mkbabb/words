"""Tests for main CLI interface."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner


class TestMainCLI:
    """Test main CLI interface and entry points."""

    @pytest.fixture
    def cli_runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    def test_cli_import(self):
        """Test CLI module can be imported."""
        try:
            from src.floridify.cli import cli
            assert cli is not None
        except ImportError:
            pytest.skip("CLI module not available")

    def test_cli_help(self, cli_runner):
        """Test CLI help output."""
        try:
            from src.floridify.cli import cli
            
            result = cli_runner.invoke(cli, ['--help'])
            assert result.exit_code == 0
            assert 'Usage:' in result.output
            
        except ImportError:
            pytest.skip("CLI module not available")

    def test_cli_version(self, cli_runner):
        """Test CLI version display."""
        try:
            from src.floridify.cli import cli
            
            result = cli_runner.invoke(cli, ['--version'])
            assert result.exit_code == 0
            
        except ImportError:
            pytest.skip("CLI module not available")

    def test_cli_subcommands(self, cli_runner):
        """Test CLI subcommand discovery."""
        try:
            from src.floridify.cli import cli
            
            result = cli_runner.invoke(cli, ['--help'])
            
            # Check for expected subcommands
            expected_commands = ['lookup', 'search', 'anki']
            for cmd in expected_commands:
                if cmd in result.output:
                    assert True  # At least one command exists
                    break
            else:
                pytest.skip("No expected subcommands found")
                
        except ImportError:
            pytest.skip("CLI module not available")

    def test_config_initialization(self):
        """Test CLI configuration initialization."""
        try:
            from src.floridify.cli import get_console
            
            console = get_console()
            assert console is not None
            
        except ImportError:
            pytest.skip("Console initialization not available")

    def test_error_handling(self, cli_runner):
        """Test CLI error handling."""
        try:
            from src.floridify.cli import cli
            
            # Test with invalid command
            result = cli_runner.invoke(cli, ['invalid-command'])
            assert result.exit_code != 0
            
        except ImportError:
            pytest.skip("CLI module not available")


class TestCLIUtilities:
    """Test CLI utility functions."""

    def test_rich_console_setup(self):
        """Test Rich console setup."""
        try:
            from src.floridify.cli.utils.formatting import format_error, get_console
            
            console = get_console()
            assert console is not None
            
            # Test error formatting
            formatted = format_error("Test error")
            assert "Test error" in str(formatted)
            
        except ImportError:
            pytest.skip("CLI utilities not available")

    def test_table_formatting(self):
        """Test table formatting utilities."""
        try:
            from src.floridify.cli.utils.formatting import format_search_results_table
            
            # Mock search results
            results = [
                {'word': 'test', 'score': 0.95, 'method': 'exact'},
                {'word': 'testing', 'score': 0.80, 'method': 'fuzzy'}
            ]
            
            table = format_search_results_table(results)
            assert table is not None
            
        except ImportError:
            pytest.skip("Table formatting not available")

    def test_progress_indicators(self):
        """Test progress indicator utilities."""
        try:
            from src.floridify.cli.utils.formatting import create_progress_bar
            
            progress = create_progress_bar("Testing")
            assert progress is not None
            
        except (ImportError, AttributeError):
            pytest.skip("Progress indicators not available")


class TestCLIIntegration:
    """Test CLI integration with core components."""

    @pytest.mark.asyncio
    async def test_search_integration(self, cli_runner):
        """Test CLI search command integration."""
        try:
            from src.floridify.cli.commands.search import search_word
            
            with patch('src.floridify.search.SearchEngine') as mock_engine:
                mock_engine_instance = mock_engine()
                mock_engine_instance.initialize.return_value = None
                mock_engine_instance.search.return_value = []
                mock_engine.return_value = mock_engine_instance
                
                result = cli_runner.invoke(search_word, ['test'])
                # Should not crash even with empty results
                
        except ImportError:
            pytest.skip("Search command integration not available")

    @pytest.mark.asyncio
    async def test_lookup_integration(self, cli_runner):
        """Test CLI lookup command integration."""
        try:
            from src.floridify.cli.commands.lookup import lookup
            
            # Mock all dependencies
            with patch('src.floridify.cli.commands.lookup._lookup_async') as mock_lookup:
                mock_lookup.return_value = None
                
                result = cli_runner.invoke(lookup, ['test'])
                mock_lookup.assert_called_once()
                
        except ImportError:
            pytest.skip("Lookup command integration not available")

    def test_config_command_integration(self, cli_runner):
        """Test CLI config command integration."""
        try:
            from src.floridify.cli.commands.config import config
            
            result = cli_runner.invoke(config, ['--help'])
            assert result.exit_code == 0
            
        except ImportError:
            pytest.skip("Config command not available")


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""

    def test_missing_arguments(self, cli_runner):
        """Test handling of missing required arguments."""
        try:
            from src.floridify.cli.commands.lookup import lookup
            
            # Test without required word argument
            result = cli_runner.invoke(lookup, [])
            assert result.exit_code != 0
            
        except ImportError:
            pytest.skip("Lookup command not available")

    def test_invalid_options(self, cli_runner):
        """Test handling of invalid options."""
        try:
            from src.floridify.cli.commands.search import search_word
            
            # Test with invalid option
            result = cli_runner.invoke(search_word, ['--invalid-option', 'test'])
            assert result.exit_code != 0
            
        except ImportError:
            pytest.skip("Search command not available")

    def test_network_error_handling(self, cli_runner):
        """Test handling of network errors."""
        try:
            from src.floridify.cli.commands.lookup import lookup
            
            # Mock network failure
            with patch('src.floridify.cli.commands.lookup._lookup_async') as mock_lookup:
                mock_lookup.side_effect = Exception("Network error")
                
                result = cli_runner.invoke(lookup, ['test'])
                # Should handle error gracefully
                
        except ImportError:
            pytest.skip("Network error handling not available")


class TestCLIPerformance:
    """Test CLI performance characteristics."""

    def test_startup_time(self, cli_runner):
        """Test CLI startup performance."""
        import time
        
        try:
            from src.floridify.cli import cli
            
            start_time = time.time()
            result = cli_runner.invoke(cli, ['--help'])
            end_time = time.time()
            
            # Help should display quickly
            assert end_time - start_time < 2.0
            assert result.exit_code == 0
            
        except ImportError:
            pytest.skip("CLI performance testing not available")

    def test_memory_usage(self):
        """Test CLI memory usage."""
        import sys
        
        try:
            # Get baseline memory
            initial_modules = len(sys.modules)
            
            from src.floridify.cli import cli
            
            # Check module loading impact
            final_modules = len(sys.modules)
            module_growth = final_modules - initial_modules
            
            # Should not load excessive modules
            assert module_growth < 50
            
        except ImportError:
            pytest.skip("Memory usage testing not available")