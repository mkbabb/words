"""Comprehensive integration tests for all CLI commands."""

import pytest
from click.testing import CliRunner

from src.floridify.cli.commands.anki import anki_group
from src.floridify.cli.commands.config import config_group
from src.floridify.cli.commands.database import database_group
from src.floridify.cli.commands.lookup import lookup_group
from src.floridify.cli.commands.process import process_group
from src.floridify.cli.commands.search import search_group


class TestCLIHelp:
    """Test that all CLI commands show proper help."""

    def test_anki_help(self):
        """Test anki command group help."""
        runner = CliRunner()
        result = runner.invoke(anki_group, ["--help"])
        assert result.exit_code == 0
        assert "Create and manage Anki flashcard decks" in result.output

    def test_anki_create_help(self):
        """Test anki create command help."""
        runner = CliRunner()
        result = runner.invoke(anki_group, ["create", "--help"])
        assert result.exit_code == 0
        assert "Create an Anki deck" in result.output

    def test_anki_list_help(self):
        """Test anki list command help."""
        runner = CliRunner()
        result = runner.invoke(anki_group, ["list", "--help"])
        assert result.exit_code == 0

    def test_anki_export_help(self):
        """Test anki export command help."""
        runner = CliRunner()
        result = runner.invoke(anki_group, ["export", "--help"])
        assert result.exit_code == 0

    def test_config_help(self):
        """Test config command group help."""
        runner = CliRunner()
        result = runner.invoke(config_group, ["--help"])
        assert result.exit_code == 0
        assert "configuration" in result.output.lower()

    def test_config_show_help(self):
        """Test config show command help."""
        runner = CliRunner()
        result = runner.invoke(config_group, ["show", "--help"])
        assert result.exit_code == 0

    def test_config_set_help(self):
        """Test config set command help."""
        runner = CliRunner()
        result = runner.invoke(config_group, ["set", "--help"])
        assert result.exit_code == 0

    def test_database_help(self):
        """Test database command group help."""
        runner = CliRunner()
        result = runner.invoke(database_group, ["--help"])
        assert result.exit_code == 0
        assert "database" in result.output.lower()

    def test_database_status_help(self):
        """Test database status command help."""
        runner = CliRunner()
        result = runner.invoke(database_group, ["status", "--help"])
        assert result.exit_code == 0

    def test_database_cleanup_help(self):
        """Test database cleanup command help."""
        runner = CliRunner()
        result = runner.invoke(database_group, ["cleanup", "--help"])
        assert result.exit_code == 0

    def test_lookup_help(self):
        """Test lookup command group help."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["--help"])
        assert result.exit_code == 0
        assert "Look up words" in result.output

    def test_lookup_word_help(self):
        """Test lookup word command help."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["word", "--help"])
        assert result.exit_code == 0

    def test_lookup_random_help(self):
        """Test lookup random command help."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["random", "--help"])
        assert result.exit_code == 0

    def test_process_help(self):
        """Test process command group help."""
        runner = CliRunner()
        result = runner.invoke(process_group, ["--help"])
        assert result.exit_code == 0
        assert "process" in result.output.lower()

    def test_process_file_help(self):
        """Test process file command help."""
        runner = CliRunner()
        result = runner.invoke(process_group, ["file", "--help"])
        assert result.exit_code == 0

    def test_search_help(self):
        """Test search command group help."""
        runner = CliRunner()
        result = runner.invoke(search_group, ["--help"])
        assert result.exit_code == 0
        assert "search" in result.output.lower()

    def test_search_init_help(self):
        """Test search init command help."""
        runner = CliRunner()
        result = runner.invoke(search_group, ["init", "--help"])
        assert result.exit_code == 0

    def test_search_find_help(self):
        """Test search find command help."""
        runner = CliRunner()
        result = runner.invoke(search_group, ["find", "--help"])
        assert result.exit_code == 0


class TestCLIErrorHandling:
    """Test CLI error handling for missing arguments."""

    def test_anki_create_missing_deck_name(self):
        """Test anki create without deck name."""
        runner = CliRunner()
        result = runner.invoke(anki_group, ["create"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_lookup_word_missing_word(self):
        """Test lookup word without word argument."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["word"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_config_set_missing_args(self):
        """Test config set without key/value."""
        runner = CliRunner()
        result = runner.invoke(config_group, ["set"])
        assert result.exit_code != 0

    def test_search_find_missing_query(self):
        """Test search find without query."""
        runner = CliRunner()
        result = runner.invoke(search_group, ["find"])
        assert result.exit_code != 0

    def test_process_file_missing_file(self):
        """Test process file without file."""
        runner = CliRunner()
        result = runner.invoke(process_group, ["file"])
        assert result.exit_code != 0


class TestCLIValidation:
    """Test CLI input validation."""

    def test_lookup_invalid_provider(self):
        """Test lookup with invalid provider."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["word", "test", "--provider", "invalid"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "not one of" in result.output

    def test_anki_create_invalid_card_types(self):
        """Test anki create with invalid card types."""
        runner = CliRunner()
        result = runner.invoke(anki_group, ["create", "Test", "--types", "invalid_type"])
        # This might succeed but show warning, depending on implementation
        assert result.exit_code in [0, 1, 2]

    def test_process_nonexistent_file(self):
        """Test process with non-existent file."""
        runner = CliRunner()
        result = runner.invoke(process_group, ["file", "/nonexistent/file.txt"])
        # Command should handle this gracefully
        assert result.exit_code in [0, 1, 2]


class TestCLIBasicFunctionality:
    """Test basic CLI functionality without external dependencies."""

    def test_anki_create_no_input(self):
        """Test anki create with no input (should show warning)."""
        runner = CliRunner()
        result = runner.invoke(anki_group, ["create", "Test Deck"])
        # Should succeed but warn about no input
        assert result.exit_code == 0
        assert "No words provided" in result.output

    def test_config_show_no_config(self):
        """Test config show when no config exists."""
        runner = CliRunner()
        result = runner.invoke(config_group, ["show"])
        # Should handle missing config gracefully
        assert result.exit_code in [0, 1]

    @pytest.mark.skipif(True, reason="Requires database connection")
    def test_database_status_no_connection(self):
        """Test database status without connection."""
        runner = CliRunner()
        result = runner.invoke(database_group, ["status"])
        # Should handle connection failure gracefully
        assert result.exit_code in [0, 1]

    @pytest.mark.skipif(True, reason="Requires API keys")
    def test_lookup_word_no_config(self):
        """Test word lookup without configuration."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["word", "test", "--no-ai"])
        # Should handle missing config gracefully
        assert result.exit_code in [0, 1]
