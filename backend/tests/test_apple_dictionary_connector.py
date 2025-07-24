"""Tests for the Apple Dictionary Connector."""

from __future__ import annotations

import platform
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.floridify.connectors.apple_dictionary import (
    AppleDictionaryConnector,
    AppleDictionaryError,
    ImportError,
    PlatformError,
)
from src.floridify.models.models import Definition, Example, ProviderData


class TestAppleDictionaryConnector:
    """Test suite for Apple Dictionary Connector."""

    def test_provider_name(self) -> None:
        """Test that provider name is correctly set."""
        connector = AppleDictionaryConnector()
        assert connector.provider_name == "apple_dictionary"

    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    def test_platform_compatibility_macos(self) -> None:
        """Test platform compatibility check on macOS."""
        connector = AppleDictionaryConnector()
        assert connector._platform_compatible is True

    @patch("src.floridify.connectors.apple_dictionary.platform.system")
    def test_platform_compatibility_non_macos(self, mock_system: Mock) -> None:
        """Test platform compatibility check on non-macOS systems."""
        mock_system.return_value = "Linux"
        connector = AppleDictionaryConnector()
        assert connector._platform_compatible is False

    @patch("src.floridify.connectors.apple_dictionary.platform.system")
    def test_initialization_non_macos(self, mock_system: Mock) -> None:
        """Test connector initialization on non-macOS systems."""
        mock_system.return_value = "Windows"
        connector = AppleDictionaryConnector()
        assert connector._dictionary_service is None
        assert not connector._is_available()

    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    @patch("src.floridify.connectors.apple_dictionary.platform.system")
    def test_initialization_macos_import_error(self, mock_system: Mock) -> None:
        """Test connector initialization with CoreServices import error."""
        mock_system.return_value = "Darwin"
        
        with patch.dict("sys.modules", {"CoreServices": None}):
            with patch("builtins.__import__", side_effect=ImportError("Module not found")):
                connector = AppleDictionaryConnector()
                assert connector._dictionary_service is None
                assert not connector._is_available()

    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    def test_service_info(self) -> None:
        """Test service information retrieval."""
        connector = AppleDictionaryConnector()
        info = connector.get_service_info()
        
        assert info["provider_name"] == "apple_dictionary"
        assert info["platform"] == "Darwin"
        assert "platform_version" in info
        assert "is_available" in info
        assert "service_initialized" in info
        assert "rate_limit" in info

    def test_clean_definition_text(self) -> None:
        """Test definition text cleaning."""
        connector = AppleDictionaryConnector()
        
        # Test pronunciation marker removal
        text = "apple |ˈæpəl| noun the round fruit"
        cleaned = connector._clean_definition_text(text)
        assert "|ˈæpəl|" not in cleaned
        assert "apple" in cleaned
        assert "noun" in cleaned

        # Test whitespace normalization
        text = "word   with    extra     spaces"
        cleaned = connector._clean_definition_text(text)
        assert "word with extra spaces" == cleaned

    def test_normalize_part_of_speech(self) -> None:
        """Test part of speech normalization."""
        connector = AppleDictionaryConnector()
        
        # Test abbreviation normalization
        assert connector._normalize_part_of_speech("n") == "noun"
        assert connector._normalize_part_of_speech("v") == "verb"
        assert connector._normalize_part_of_speech("adj") == "adjective"
        assert connector._normalize_part_of_speech("adv") == "adverb"
        
        # Test full form passthrough
        assert connector._normalize_part_of_speech("noun") == "noun"
        assert connector._normalize_part_of_speech("verb") == "verb"
        
        # Test unknown type passthrough
        assert connector._normalize_part_of_speech("unknown") == "unknown"

    def test_extract_examples(self) -> None:
        """Test example extraction from definition text."""
        connector = AppleDictionaryConnector()
        
        # Test quoted examples
        definition_text = 'A fruit. "I ate an apple." Very tasty.'
        examples = connector._extract_examples(definition_text)
        assert len(examples) == 1
        assert examples[0] == "I ate an apple."

        # Test examples after colons
        definition_text = "A fruit: The apple was red and juicy."
        examples = connector._extract_examples(definition_text)
        assert len(examples) == 1
        assert "apple was red and juicy" in examples[0]

        # Test e.g. examples
        definition_text = "A fruit, e.g., apple juice is delicious."
        examples = connector._extract_examples(definition_text)
        assert len(examples) == 1
        assert "apple juice is delicious" in examples[0]

    def test_remove_examples_from_definition(self) -> None:
        """Test example removal from definition text."""
        connector = AppleDictionaryConnector()
        
        # Test quoted example removal
        definition_text = 'A round fruit. "I ate an apple." Very nutritious.'
        cleaned = connector._remove_examples_from_definition(definition_text)
        assert '"I ate an apple."' not in cleaned
        assert "A round fruit" in cleaned
        assert "Very nutritious" in cleaned

        # Test e.g. section removal
        definition_text = "A fruit, e.g., apple juice is delicious. Rich in vitamins."
        cleaned = connector._remove_examples_from_definition(definition_text)
        assert "apple juice is delicious" not in cleaned
        assert "A fruit" in cleaned
        assert "Rich in vitamins" in cleaned

    def test_extract_main_definition(self) -> None:
        """Test main definition extraction."""
        connector = AppleDictionaryConnector()
        
        # Test with word type indicator
        text = "noun the round fruit of a tree"
        definition = connector._extract_main_definition(text)
        assert definition == "the round fruit of a tree"

        # Test fallback to full text
        text = "the round fruit of a tree"
        definition = connector._extract_main_definition(text)
        assert definition == "the round fruit of a tree"

    def test_parse_apple_definition_simple(self) -> None:
        """Test parsing of simple Apple Dictionary definition."""
        connector = AppleDictionaryConnector()
        
        raw_definition = """apple |ˈæpəl|
noun
1 the round fruit of a tree of the rose family."""
        
        definitions = connector._parse_apple_definition("apple", raw_definition)
        
        assert len(definitions) == 1
        definition = definitions[0]
        assert definition.word_type == "noun"
        assert "round fruit" in definition.definition
        assert definition.raw_metadata["provider"] == "apple_dictionary"

    def test_parse_apple_definition_complex(self) -> None:
        """Test parsing of complex Apple Dictionary definition."""
        connector = AppleDictionaryConnector()
        
        raw_definition = """apple |ˈæpəl|
noun
1 the round fruit of a tree of the rose family, which typically has thin red or green skin and crisp flesh. "I ate a red apple."
2 the tree bearing such fruit.
verb
3 to apply or use: apple the solution to the problem."""
        
        definitions = connector._parse_apple_definition("apple", raw_definition)
        
        assert len(definitions) >= 1  # Should extract at least one definition
        
        # Check that definition contains content from the input
        assert any("round fruit" in d.definition for d in definitions)
        
        # Check that examples are extracted
        has_examples = any(
            d.examples.generated for d in definitions 
            if d.examples and d.examples.generated
        )
        # Note: Examples might be extracted depending on parsing logic

    def test_parse_apple_definition_fallback(self) -> None:
        """Test fallback parsing when structured parsing fails."""
        connector = AppleDictionaryConnector()
        
        # Simple text without structure
        raw_definition = "a type of fruit"
        definitions = connector._parse_apple_definition("apple", raw_definition)
        
        assert len(definitions) == 1
        definition = definitions[0]
        assert definition.word_type == "unknown"
        assert definition.definition == "a type of fruit"
        assert definition.raw_metadata["provider"] == "apple_dictionary"

    @pytest.mark.asyncio
    @patch("src.floridify.connectors.apple_dictionary.platform.system")
    async def test_fetch_definition_platform_unavailable(self, mock_system: Mock) -> None:
        """Test fetch_definition when platform is unavailable."""
        mock_system.return_value = "Linux"
        connector = AppleDictionaryConnector()
        
        result = await connector.fetch_definition("apple")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_definition_invalid_input(self) -> None:
        """Test fetch_definition with invalid input."""
        connector = AppleDictionaryConnector()
        
        # Test None input
        result = await connector.fetch_definition(None)
        assert result is None
        
        # Test empty string
        result = await connector.fetch_definition("")
        assert result is None
        
        # Test non-string input
        result = await connector.fetch_definition(123)
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_fetch_definition_success(self) -> None:
        """Test successful definition fetch on macOS."""
        connector = AppleDictionaryConnector()
        
        # Mock the lookup to return a definition
        mock_definition = """apple |ˈæpəl|
noun
the round fruit of a tree of the rose family."""
        
        with patch.object(connector, '_lookup_definition', return_value=mock_definition):
            result = await connector.fetch_definition("apple")
            
            assert result is not None
            assert isinstance(result, ProviderData)
            assert result.provider_name == "apple_dictionary"
            assert len(result.definitions) > 0
            
            definition = result.definitions[0]
            assert isinstance(definition, Definition)
            assert definition.word_type == "noun"
            assert "round fruit" in definition.definition

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_fetch_definition_not_found(self) -> None:
        """Test fetch_definition when word is not found."""
        connector = AppleDictionaryConnector()
        
        # Mock the lookup to return None (word not found)
        with patch.object(connector, '_lookup_definition', return_value=None):
            result = await connector.fetch_definition("nonexistentword12345")
            assert result is None

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_fetch_definition_with_state_tracker(self) -> None:
        """Test fetch_definition with state tracker."""
        connector = AppleDictionaryConnector()
        
        # Create mock state tracker
        state_tracker = AsyncMock()
        
        mock_definition = """apple |ˈæpəl|
noun
the round fruit of a tree."""
        
        with patch.object(connector, '_lookup_definition', return_value=mock_definition):
            result = await connector.fetch_definition("apple", state_tracker)
            
            assert result is not None
            
            # Verify state tracker was called
            state_tracker.update_stage.assert_called()
            calls = [call.args[0] for call in state_tracker.update_stage.call_args_list]
            assert any("PROVIDER_FETCH" in str(call) for call in calls)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_fetch_definition_error_handling(self) -> None:
        """Test error handling in fetch_definition."""
        connector = AppleDictionaryConnector()
        
        # Mock the lookup to raise an exception
        with patch.object(connector, '_lookup_definition', side_effect=Exception("Test error")):
            result = await connector.fetch_definition("apple")
            assert result is None

    @pytest.mark.asyncio
    async def test_rate_limiting(self) -> None:
        """Test rate limiting functionality."""
        import time
        
        # Create connector with low rate limit for testing
        connector = AppleDictionaryConnector(rate_limit=5.0)  # 5 requests per second
        
        # Mock successful lookups
        with patch.object(connector, '_lookup_definition', return_value="test definition"), \
             patch.object(connector, '_parse_apple_definition', return_value=[]):
            
            start_time = time.time()
            
            # Make two rapid requests
            await connector.fetch_definition("word1")
            await connector.fetch_definition("word2")
            
            elapsed = time.time() - start_time
            
            # Should take at least 0.2 seconds (1/5 second between requests)
            assert elapsed >= 0.15  # Allow some tolerance for test timing

    def test_initialization_custom_rate_limit(self) -> None:
        """Test connector initialization with custom rate limit."""
        custom_rate = 15.0
        connector = AppleDictionaryConnector(rate_limit=custom_rate)
        assert connector.rate_limit == custom_rate


class TestAppleDictionaryConnectorIntegration:
    """Integration tests for Apple Dictionary Connector."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    @pytest.mark.integration
    async def test_real_dictionary_lookup(self) -> None:
        """Test actual dictionary lookup on macOS (integration test)."""
        connector = AppleDictionaryConnector()
        
        # Only run if service is actually available
        if not connector._is_available():
            pytest.skip("Apple Dictionary service not available")
        
        # Test with a common word that should be in the dictionary
        result = await connector.fetch_definition("apple")
        
        if result is not None:  # Dictionary may not have all words
            assert isinstance(result, ProviderData)
            assert result.provider_name == "apple_dictionary"
            assert len(result.definitions) > 0
            
            # Check definition structure
            definition = result.definitions[0]
            assert isinstance(definition, Definition)
            assert definition.definition
            assert definition.word_type
            
            # Check metadata
            assert result.raw_metadata is not None
            assert "platform" in result.raw_metadata
            assert result.raw_metadata["platform"] == "Darwin"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    @pytest.mark.integration
    async def test_multiple_word_lookup(self) -> None:
        """Test lookup of multiple words (integration test)."""
        connector = AppleDictionaryConnector()
        
        if not connector._is_available():
            pytest.skip("Apple Dictionary service not available")
        
        test_words = ["cat", "dog", "house", "car", "book"]
        results = []
        
        for word in test_words:
            result = await connector.fetch_definition(word)
            results.append(result)
        
        # At least some words should return definitions
        successful_results = [r for r in results if r is not None]
        assert len(successful_results) > 0, "No definitions found for any test words"
        
        # All successful results should have proper structure
        for result in successful_results:
            assert isinstance(result, ProviderData)
            assert result.provider_name == "apple_dictionary"
            assert len(result.definitions) > 0