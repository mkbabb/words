"""Integration tests for CLI lookup functionality."""

import pytest
from click.testing import CliRunner

from src.floridify.cli.commands.lookup import lookup_group


class TestLookupIntegration:
    """Integration tests that verify end-to-end functionality."""

    def test_lookup_word_help(self):
        """Test that lookup word command shows help."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["word", "--help"])

        assert result.exit_code == 0
        assert "Look up a word" in result.output
        assert "--provider" in result.output
        assert "--ai-comprehension" in result.output

    def test_lookup_random_help(self):
        """Test that lookup random command shows help."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["random", "--help"])

        assert result.exit_code == 0
        assert "random words" in result.output

    def test_lookup_history_help(self):
        """Test that lookup history command shows help."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["history", "--help"])

        assert result.exit_code == 0
        assert "lookup history" in result.output

    def test_lookup_group_help(self):
        """Test that lookup group shows help."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["--help"])

        assert result.exit_code == 0
        assert "Look up words" in result.output
        assert "word" in result.output
        assert "random" in result.output
        assert "history" in result.output

    @pytest.mark.skipif(True, reason="Requires MongoDB and API keys")
    def test_lookup_word_integration_wiktionary_only(self):
        """Integration test with real Wiktionary API (skipped by default)."""
        runner = CliRunner()
        result = runner.invoke(
            lookup_group, ["word", "test", "--provider", "wiktionary", "--no-ai-comprehension"]
        )

        # Should succeed or fail gracefully
        assert result.exit_code in [0, 1]  # Success or handled failure

    def test_lookup_missing_word_argument(self):
        """Test lookup with missing word argument."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["word"])

        # Should show error about missing argument
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_lookup_invalid_provider(self):
        """Test lookup with invalid provider."""
        runner = CliRunner()
        result = runner.invoke(lookup_group, ["word", "test", "--provider", "invalid_provider"])

        # Should show error about invalid choice
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "not one of" in result.output
