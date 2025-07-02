"""Unit tests for dictionary connectors."""

from unittest.mock import patch

import pytest

from src.floridify.connectors.wiktionary import WiktionaryConnector
from src.floridify.constants import DictionaryProvider
from src.floridify.models import ProviderData, Word, WordType


class TestWiktionaryConnector:
    """Test Wiktionary API connector."""

    @pytest.fixture
    def connector(self):
        """Create WiktionaryConnector instance."""
        return WiktionaryConnector()

    @pytest.fixture
    def mock_wiktionary_api_response(self):
        """Mock successful Wiktionary API response."""
        return {
            "query": {
                "pages": {
                    "12345": {
                        "pageid": 12345,
                        "title": "test",
                        "revisions": [{
                            "*": """==English==
===Noun===
{{en-noun}}
# A [[procedure]] intended to establish the [[quality]], [[performance]], or [[reliability]] of something.
#: {{ux|en|This is a '''test'''.}}
#: {{ux|en|We need to '''test''' this hypothesis.}}

===Verb===
{{en-verb}}
# To [[challenge]] or [[assess]].
#: {{ux|en|Let's '''test''' your knowledge.}}
"""
                        }]
                    }
                }
            }
        }

    @pytest.fixture
    def mock_empty_wiktionary_response(self):
        """Mock empty Wiktionary API response."""
        return {
            "query": {
                "pages": {
                    "-1": {
                        "missing": ""
                    }
                }
            }
        }

    @pytest.mark.asyncio
    async def test_successful_word_fetch(self, connector, mock_wiktionary_api_response, mock_httpx_client):
        """Test successful word definition fetch."""
        # Mock HTTP response
        mock_httpx_client.get.return_value.json.return_value = mock_wiktionary_api_response
        
        with patch.object(connector, '_http_client', mock_httpx_client):
            result = await connector.fetch_definition("test")
        
        # Verify result structure
        assert isinstance(result, ProviderData)
        assert result.provider == DictionaryProvider.WIKTIONARY
        assert result.word.text == "test"
        assert len(result.definitions) > 0
        
        # Check noun definition
        noun_def = next((d for d in result.definitions if d.word_type == WordType.NOUN), None)
        assert noun_def is not None
        assert "procedure" in noun_def.definition.lower()
        
        # Check verb definition
        verb_def = next((d for d in result.definitions if d.word_type == WordType.VERB), None)
        assert verb_def is not None
        assert "challenge" in verb_def.definition.lower()

    @pytest.mark.asyncio
    async def test_missing_word_fetch(self, connector, mock_empty_wiktionary_response, mock_httpx_client):
        """Test fetching non-existent word."""
        mock_httpx_client.get.return_value.json.return_value = mock_empty_wiktionary_response
        
        with patch.object(connector, '_http_client', mock_httpx_client):
            result = await connector.fetch_definition("nonexistent")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_api_error_handling(self, connector, mock_httpx_client):
        """Test API error handling."""
        # Mock HTTP error
        mock_httpx_client.get.side_effect = Exception("API Error")
        
        with patch.object(connector, '_http_client', mock_httpx_client):
            result = await connector.fetch_definition("test")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, connector, mock_httpx_client):
        """Test handling of malformed API responses."""
        # Mock malformed JSON response
        mock_httpx_client.get.return_value.json.return_value = {"invalid": "structure"}
        
        with patch.object(connector, '_http_client', mock_httpx_client):
            result = await connector.fetch_definition("test")
        
        assert result is None

    def test_wikitext_parsing(self, connector):
        """Test Wikitext markup parsing."""
        wikitext = """==English==
===Noun===
{{en-noun}}
# A [[procedure]] for [[testing]].
#: {{ux|en|This is a '''test'''.}}

===Verb===
{{en-verb}}
# To [[examine]] something.
"""
        
        definitions = connector._parse_wikitext(wikitext, "test")
        
        assert len(definitions) == 2
        
        # Check noun definition
        noun_def = definitions[0]
        assert noun_def.word_type == WordType.NOUN
        assert "procedure" in noun_def.definition
        
        # Check verb definition
        verb_def = definitions[1]
        assert verb_def.word_type == WordType.VERB
        assert "examine" in verb_def.definition

    def test_example_extraction(self, connector):
        """Test example sentence extraction from wikitext."""
        wikitext = """===Noun===
# A test definition.
#: {{ux|en|This is a '''test''' sentence.}}
#: {{ux|en|Another '''test''' example.}}
"""
        
        definitions = connector._parse_wikitext(wikitext, "test")
        definition = definitions[0]
        
        assert len(definition.examples.generated) == 2
        assert "This is a test sentence." in definition.examples.generated[0].sentence
        assert "Another test example." in definition.examples.generated[1].sentence

    def test_pronunciation_extraction(self, connector):
        """Test pronunciation extraction from wikitext."""
        wikitext = """==English==
===Pronunciation===
* {{IPA|en|/tɛst/}}
* {{audio|en|test.ogg}}

===Noun===
# A test.
"""
        
        pronunciation = connector._extract_pronunciation(wikitext)
        
        assert pronunciation.phonetic == "/tɛst/"

    @pytest.mark.asyncio
    async def test_rate_limiting(self, connector, mock_httpx_client):
        """Test rate limiting implementation."""
        mock_httpx_client.get.return_value.json.return_value = {"query": {"pages": {}}}
        
        with patch.object(connector, '_http_client', mock_httpx_client):
            # Make multiple rapid requests
            tasks = [connector.fetch_definition(f"word{i}") for i in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should complete without rate limit errors
        assert len(results) == 5
        assert all(not isinstance(r, Exception) for r in results)

    def test_url_construction(self, connector):
        """Test API URL construction."""
        url = connector._build_api_url("test")
        
        assert "api.php" in url
        assert "action=query" in url
        assert "titles=test" in url
        assert "prop=revisions" in url

    def test_word_validation(self, connector):
        """Test input word validation."""
        # Valid words
        assert connector._validate_word("test")
        assert connector._validate_word("hello-world")
        assert connector._validate_word("café")
        
        # Invalid words
        assert not connector._validate_word("")
        assert not connector._validate_word("   ")
        assert not connector._validate_word("test@#$")


class TestOxfordConnectorStub:
    """Test stub for Oxford Dictionary connector."""

    def test_oxford_connector_import(self):
        """Test Oxford connector can be imported (stub)."""
        try:
            from src.floridify.connectors.oxford import OxfordConnector
            assert OxfordConnector is not None
        except ImportError:
            pytest.skip("Oxford connector not implemented")

    @pytest.mark.asyncio
    async def test_oxford_connector_interface(self):
        """Test Oxford connector implements expected interface (stub)."""
        try:
            from src.floridify.connectors.oxford import OxfordConnector
            
            connector = OxfordConnector()
            
            # Should implement fetch_definition method
            assert hasattr(connector, 'fetch_definition')
            assert callable(getattr(connector, 'fetch_definition'))
            
            # Should handle missing API credentials gracefully
            result = await connector.fetch_definition("test")
            # Result should be None or raise appropriate exception
            
        except ImportError:
            pytest.skip("Oxford connector not implemented")


class TestDictionaryComConnectorStub:
    """Test stub for Dictionary.com connector."""

    def test_dictionary_com_connector_import(self):
        """Test Dictionary.com connector can be imported (stub)."""
        try:
            from src.floridify.connectors.dictionary_com import DictionaryComConnector
            assert DictionaryComConnector is not None
        except ImportError:
            pytest.skip("Dictionary.com connector not implemented")

    @pytest.mark.asyncio
    async def test_dictionary_com_connector_interface(self):
        """Test Dictionary.com connector implements expected interface (stub)."""
        try:
            from src.floridify.connectors.dictionary_com import DictionaryComConnector
            
            connector = DictionaryComConnector()
            
            # Should implement fetch_definition method
            assert hasattr(connector, 'fetch_definition')
            assert callable(getattr(connector, 'fetch_definition'))
            
            # Should handle API requests gracefully
            result = await connector.fetch_definition("test")
            # Result should be None or valid ProviderData
            
        except ImportError:
            pytest.skip("Dictionary.com connector not implemented")


class TestConnectorIntegration:
    """Test connector integration patterns."""

    def test_provider_data_structure(self):
        """Test all connectors return compatible ProviderData."""
        # This ensures all connectors follow the same interface
        from src.floridify.models import Definition, Examples, Pronunciation, ProviderData
        
        # Test valid ProviderData creation
        provider_data = ProviderData(
            provider=DictionaryProvider.WIKTIONARY,
            word=Word(text="test"),
            definitions=[
                Definition(
                    word_type=WordType.NOUN,
                    definition="A test definition",
                    examples=Examples(),
                    synonyms=[]
                )
            ],
            pronunciation=Pronunciation(phonetic="/test/"),
            metadata={"source": "test"}
        )
        
        assert provider_data.provider == DictionaryProvider.WIKTIONARY
        assert provider_data.word.text == "test"
        assert len(provider_data.definitions) == 1

    @pytest.mark.asyncio
    async def test_connector_error_consistency(self):
        """Test all connectors handle errors consistently."""
        # All connectors should return None on error, not raise exceptions
        connector = WiktionaryConnector()
        
        # Mock network error
        with patch.object(connector, '_http_client') as mock_client:
            mock_client.get.side_effect = Exception("Network error")
            
            result = await connector.fetch_definition("test")
            assert result is None

    def test_word_normalization_consistency(self):
        """Test word normalization is consistent across connectors."""
        connector = WiktionaryConnector()
        
        # Test various word forms
        test_cases = [
            ("Test", "test"),
            ("  word  ", "word"),
            ("UPPER", "upper"),
            ("café", "café"),  # Preserve diacritics
        ]
        
        for input_word, expected in test_cases:
            normalized = connector._normalize_word(input_word)
            assert normalized == expected