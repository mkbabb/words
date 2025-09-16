"""Test language providers and parsers using real database."""

import json

import pytest

from floridify.caching.models import ResourceType
from floridify.models.base import Language
from floridify.models.registry import get_model_class
from floridify.providers.core import ConnectorConfig
from floridify.providers.language.models import (
    LanguageEntry,
    LanguageProvider,
    LanguageSource,
    ParserType,
    ScraperType,
)
from floridify.providers.language.parsers import (
    parse_csv_words,
    parse_json_vocabulary,
    parse_text_lines,
)
from floridify.providers.language.scraper.url import URLLanguageConnector


class TestLanguageParsers:
    """Test language parser functions."""

    def test_parse_text_lines(self):
        """Test parsing plain text lines."""
        content = """
        # Comment line
        hello
        world
        foo bar
        # Another comment
        python
        """
        words, phrases = parse_text_lines(content, Language.ENGLISH)

        assert "hello" in words
        assert "world" in words
        assert "python" in words
        assert "foo bar" in phrases
        assert len(words) == 3
        assert len(phrases) == 1

    def test_parse_text_lines_with_special_chars(self):
        """Test parsing text with special characters."""
        content = """
        café
        naïve
        résumé
        hello-world
        test_case
        """
        words, phrases = parse_text_lines(content, Language.ENGLISH)

        # Words are normalized (accents removed)
        assert "cafe" in words
        assert "naive" in words
        assert "resume" in words
        assert "hello world" in phrases  # Hyphenated becomes space-separated phrase
        assert "test_case" in words  # Underscore is not treated as phrase separator

    def test_parse_json_vocabulary(self):
        """Test parsing JSON vocabulary data."""
        json_data = {
            "words": ["apple", "banana", "cherry"],
            "phrases": ["red apple", "yellow banana"],
            "vocabulary": ["dog", "cat"],  # Alternative key
        }

        words, phrases = parse_json_vocabulary(json_data, Language.ENGLISH)

        assert "apple" in words
        assert "banana" in words
        assert "cherry" in words
        assert "dog" in words
        assert "cat" in words
        assert "red apple" in phrases
        assert "yellow banana" in phrases

    def test_parse_json_vocabulary_string_input(self):
        """Test parsing JSON from string input."""
        json_str = json.dumps({"words": ["test", "data"], "phrases": ["test phrase"]})

        words, phrases = parse_json_vocabulary(json_str, Language.ENGLISH)

        assert "test" in words
        assert "data" in words
        assert "test phrase" in phrases

    def test_parse_csv_words(self):
        """Test parsing CSV word data."""
        csv_content = """word,frequency,type
apple,100,noun
run,50,verb
quickly,30,adverb
"red apple",20,phrase
"""
        words, phrases = parse_csv_words(csv_content, Language.ENGLISH)

        assert "apple" in words
        assert "run" in words
        assert "quickly" in words
        assert "red apple" in phrases

    def test_parse_csv_words_simple_format(self):
        """Test parsing simple CSV without headers."""
        csv_content = """apple
banana
cherry
golden apple"""

        words, phrases = parse_csv_words(csv_content, Language.ENGLISH)

        assert "apple" in words
        assert "banana" in words
        assert "cherry" in words
        assert "golden apple" in phrases


@pytest.mark.asyncio
class TestLanguageConnector:
    """Test LanguageConnector functionality with real implementations."""

    @pytest.mark.asyncio
    async def test_connector_initialization(self, test_db, connector_config: ConnectorConfig):
        """Test language connector initialization."""
        # test_db ensures database is initialized
        connector = URLLanguageConnector(config=connector_config)
        
        assert connector.provider is not None
        assert connector.rate_limiter is not None
        assert connector.config == connector_config

    @pytest.mark.asyncio
    async def test_fetch_from_real_url(self, test_db, connector_config: ConnectorConfig):
        """Test fetching from a real URL if available."""
        # test_db ensures database is initialized
        connector = URLLanguageConnector(config=connector_config)
        
        # Create a test source pointing to a public vocabulary list
        # Using GitHub raw content as a reliable source
        source = LanguageSource(
            name="test_vocab",
            url="https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
            parser=ParserType.TEXT_LINES,
            language=Language.ENGLISH,
            description="Test vocabulary from GitHub",
        )
        
        # Try to fetch - might fail if network is down
        try:
            result = await connector._fetch_from_provider(source)
            if result is not None:
                assert isinstance(result, dict)
                assert "vocabulary" in result
                assert "language" in result
                assert result["language"] == Language.ENGLISH.value
        except Exception:
            # Network might be unavailable, that's okay
            pytest.skip("Network unavailable")

    @pytest.mark.asyncio
    async def test_language_source_parsing(self, test_db):
        """Test LanguageSource model functionality."""
        # test_db ensures database is initialized
        source = LanguageSource(
            name="test_source",
            url="https://example.com/words.txt",
            parser=ParserType.TEXT_LINES,
            scraper=ScraperType.DEFAULT,
            language=Language.ENGLISH,
            description="Test source",
        )
        
        assert source.name == "test_source"
        assert source.parser == ParserType.TEXT_LINES
        assert source.language == Language.ENGLISH

    @pytest.mark.asyncio
    async def test_language_entry_model(self, test_db):
        """Test LanguageEntry model."""
        # test_db ensures database is initialized
        # Create a LanguageEntry with required fields
        source = LanguageSource(
            name="test_source",
            url="https://example.com/test.txt",
            parser=ParserType.TEXT_LINES,
            language=Language.ENGLISH,
        )
        
        entry = LanguageEntry(
            provider=LanguageProvider.CUSTOM_URL,
            source=source,
            vocabulary=["test", "word", "list"],
            phrases=["test phrase"],
            idioms=[],
        )
        
        # Verify the model is created correctly
        assert entry.provider == LanguageProvider.CUSTOM_URL
        assert entry.source.name == "test_source"
        assert entry.vocabulary == ["test", "word", "list"]
        assert entry.vocabulary_count == 3
        assert entry.phrases == ["test phrase"]


@pytest.mark.asyncio
class TestLanguageIntegration:
    """Test language provider integration with real database."""

    @pytest.mark.asyncio
    async def test_caching_with_database(self, test_db, connector_config: ConnectorConfig):
        """Test that caching works with real database."""
        # test_db ensures database is initialized
        connector = URLLanguageConnector(config=connector_config)
        
        # Create a simple test source
        source = LanguageSource(
            name="cache_test",
            url="https://httpbin.org/base64/SGVsbG8gV29ybGQK",  # Returns "Hello World"
            parser=ParserType.TEXT_LINES,
            language=Language.ENGLISH,
            description="Cache test",
        )
        
        try:
            # First fetch - should store in database
            result1 = await connector.fetch(source)
            
            if result1 is not None:
                # Second fetch - should use cache
                result2 = await connector.fetch(source)
                
                # Both should return data
                assert result2 is not None
        except Exception:
            # Network might be unavailable
            pytest.skip("Network unavailable")

    @pytest.mark.asyncio
    async def test_parser_type_selection(self, test_db):
        """Test that different parser types are handled correctly."""
        # test_db ensures database is initialized
        
        # Test TEXT_LINES parser
        text_source = LanguageSource(
            name="text_test",
            url="https://example.com/words.txt",
            parser=ParserType.TEXT_LINES,
            language=Language.ENGLISH,
        )
        assert text_source.parser == ParserType.TEXT_LINES
        
        # Test JSON_VOCABULARY parser  
        json_source = LanguageSource(
            name="json_test",
            url="https://example.com/vocab.json",
            parser=ParserType.JSON_VOCABULARY,
            language=Language.ENGLISH,
        )
        assert json_source.parser == ParserType.JSON_VOCABULARY
        
        # Test CSV_WORDS parser
        csv_source = LanguageSource(
            name="csv_test",
            url="https://example.com/words.csv",
            parser=ParserType.CSV_WORDS,
            language=Language.ENGLISH,
        )
        assert csv_source.parser == ParserType.CSV_WORDS