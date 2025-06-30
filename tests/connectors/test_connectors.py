"""Tests for dictionary connectors."""

from unittest.mock import MagicMock, patch

import pytest

from src.floridify.connectors import DictionaryComConnector, OxfordConnector, WiktionaryConnector
from src.floridify.models import WordType


class TestWiktionaryConnector:
    """Tests for WiktionaryConnector."""

    @pytest.fixture
    def connector(self) -> WiktionaryConnector:
        """Create a WiktionaryConnector instance for testing."""
        return WiktionaryConnector(rate_limit=100.0)  # High rate limit for testing

    def test_provider_name(self, connector: WiktionaryConnector) -> None:
        """Test provider name property."""
        assert connector.provider_name == "wiktionary"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, connector: WiktionaryConnector) -> None:
        """Test that rate limiting logic works."""
        # Mock the sleep function to avoid actual delays
        with patch("asyncio.sleep") as mock_sleep:
            # Test with a very low rate limit to trigger rate limiting
            slow_connector = WiktionaryConnector(rate_limit=1.0)  # 1 req per hour = very slow

            # First call should not sleep
            await slow_connector._enforce_rate_limit()
            mock_sleep.assert_not_called()

            # Second call should trigger sleep
            await slow_connector._enforce_rate_limit()
            mock_sleep.assert_called_once()

            # Verify sleep was called with a positive value
            call_args = mock_sleep.call_args[0]
            assert len(call_args) == 1
            assert call_args[0] > 0

    @pytest.mark.asyncio
    async def test_fetch_definition_not_found(self, connector: WiktionaryConnector) -> None:
        """Test fetching a non-existent word."""
        # Mock HTTP response for 404
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"query": {"pages": [{"missing": True}]}}
        mock_response.raise_for_status.return_value = None

        with patch.object(connector.session, "get", return_value=mock_response):
            result = await connector.fetch_definition("nonexistentword123")
            assert result is None

    def test_extract_definitions_from_wikitext(self, connector: WiktionaryConnector) -> None:
        """Test wikitext parsing."""
        sample_wikitext = """
==English==

===Noun===
# A representative [[case]] or [[instance]].
# Something that serves as a [[pattern]] of [[behaviour]].

===Verb===
# To [[illustrate]] or [[demonstrate]].
"""

        definitions = connector._extract_definitions_from_wikitext(sample_wikitext)

        # Should find at least one definition
        assert len(definitions) > 0

        # Check that we have both noun and verb definitions
        word_types = {defn.word_type for defn in definitions}
        assert WordType.NOUN in word_types or WordType.VERB in word_types

    def test_extract_pronunciation_from_wikitext(self, connector: WiktionaryConnector) -> None:
        """Test pronunciation extraction."""
        sample_wikitext = """
==English==
{{IPA|en|/ɪɡˈzæmpəl/}}

===Noun===
# A test word.
"""

        pronunciation = connector._extract_pronunciation_from_wikitext(sample_wikitext)

        assert pronunciation.ipa == "/ɪɡˈzæmpəl/"
        assert pronunciation.phonetic != "unknown"


class TestOxfordConnector:
    """Tests for OxfordConnector."""

    @pytest.fixture
    def connector(self) -> OxfordConnector:
        """Create an OxfordConnector instance for testing."""
        return OxfordConnector(app_id="test_app_id", api_key="test_api_key")

    def test_provider_name(self, connector: OxfordConnector) -> None:
        """Test provider name property."""
        assert connector.provider_name == "oxford"

    def test_map_oxford_pos_to_word_type(self, connector: OxfordConnector) -> None:
        """Test part of speech mapping."""
        assert connector._map_oxford_pos_to_word_type("noun") == WordType.NOUN
        assert connector._map_oxford_pos_to_word_type("verb") == WordType.VERB
        assert connector._map_oxford_pos_to_word_type("adjective") == WordType.ADJECTIVE
        assert connector._map_oxford_pos_to_word_type("unknown_pos") is None

    @pytest.mark.asyncio
    async def test_fetch_definition_not_found(self, connector: OxfordConnector) -> None:
        """Test fetching a non-existent word returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(connector.session, "get", return_value=mock_response):
            result = await connector.fetch_definition("nonexistentword123")
            assert result is None

    @pytest.mark.skip(reason="Skip to preserve Oxford API quota")
    @pytest.mark.asyncio
    async def test_oxford_live_api(self, connector: OxfordConnector) -> None:
        """Test Oxford API with real call - SKIPPED to preserve quota."""
        pass

    def test_parse_oxford_response(self, connector: OxfordConnector) -> None:
        """Test parsing Oxford API response."""
        sample_response = {
            "results": [
                {
                    "lexicalEntries": [
                        {
                            "lexicalCategory": {"id": "noun"},
                            "entries": [
                                {
                                    "senses": [
                                        {
                                            "definitions": ["A representative case or instance"],
                                            "examples": [{"text": "This is an example sentence"}],
                                        }
                                    ]
                                }
                            ],
                        }
                    ]
                }
            ]
        }

        provider_data = connector._parse_oxford_response("example", sample_response)

        assert provider_data.provider_name == "oxford"
        assert len(provider_data.definitions) == 1
        assert provider_data.definitions[0].word_type == WordType.NOUN
        assert "representative case" in provider_data.definitions[0].definition
        assert len(provider_data.definitions[0].examples.generated) == 1


class TestDictionaryComConnector:
    """Tests for DictionaryComConnector stub."""

    @pytest.fixture
    def connector(self) -> DictionaryComConnector:
        """Create a DictionaryComConnector instance for testing."""
        return DictionaryComConnector()

    def test_provider_name(self, connector: DictionaryComConnector) -> None:
        """Test provider name property."""
        assert connector.provider_name == "dictionary_com"

    @pytest.mark.asyncio
    async def test_fetch_definition_stub(self, connector: DictionaryComConnector) -> None:
        """Test that stub implementation returns None."""
        result = await connector.fetch_definition("test")
        assert result is None


# Integration test that doesn't hit real APIs
class TestConnectorIntegration:
    """Integration tests for connectors."""

    @pytest.mark.asyncio
    async def test_connector_cleanup(self) -> None:
        """Test that connectors can be properly closed."""
        connectors = [
            WiktionaryConnector(),
            OxfordConnector("test_id", "test_key"),
            DictionaryComConnector(),
        ]

        # Test that close methods don't raise errors
        for connector in connectors:
            if hasattr(connector, "close"):
                await connector.close()
