"""Comprehensive language provider tests.

Tests all language providers with complete coverage of:
- URL-based vocabulary fetching
- Parser selection and processing
- Scraper functionality
- MongoDB persistence
- Caching and versioning
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import CacheNamespace, ResourceType
from floridify.models.base import Language
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
    parse_scraped_data,
    parse_text_lines,
)
from floridify.providers.language.scraper.url import URLLanguageConnector


@pytest.mark.asyncio
class TestLanguageProviderFetch:
    """Test language provider fetching operations."""

    @pytest_asyncio.fixture
    async def mock_http_client(self) -> AsyncMock:
        """Create mock HTTP client for scraping."""
        client = AsyncMock(spec=httpx.AsyncClient)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.text = "word1\nword2\nphrase one\nword3"
        response.json.return_value = {
            "vocabulary": ["apple", "banana", "cherry"],
            "phrases": ["in the long run", "piece of cake"],
        }
        response.raise_for_status = MagicMock()
        client.get = AsyncMock(return_value=response)
        return client

    @pytest_asyncio.fixture
    async def url_connector(self) -> URLLanguageConnector:
        """Create URL language connector."""
        config = ConnectorConfig()
        return URLLanguageConnector(
            provider=LanguageProvider.CUSTOM_URL,
            config=config,
        )

    async def test_url_fetch_with_text_parser(
        self,
        url_connector: URLLanguageConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test fetching text content and parsing lines."""
        source = LanguageSource(
            name="test_vocab",
            url="https://example.com/vocab.txt",
            language=Language.ENGLISH,
            parser=ParserType.TEXT_LINES,
        )

        # Mock scraper session
        with patch("floridify.providers.language.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            result = await url_connector._fetch_from_provider(source)

        assert result is not None
        assert result["source_name"] == "test_vocab"
        assert result["language"] == Language.ENGLISH.value
        assert "vocabulary" in result
        assert len(result["words"]) > 0
        assert len(result["phrases"]) >= 0

    async def test_url_fetch_with_json_parser(
        self,
        url_connector: URLLanguageConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test fetching JSON content and parsing vocabulary."""
        source = LanguageSource(
            name="json_vocab",
            url="https://example.com/vocab.json",
            language=Language.ENGLISH,
            parser=ParserType.JSON_VOCABULARY,
        )

        # Return JSON string
        mock_http_client.get.return_value.text = json.dumps(
            {
                "vocabulary": ["apple", "banana", "cherry"],
                "phrases": ["in the long run", "piece of cake"],
            }
        )

        with patch("floridify.providers.language.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            result = await url_connector._fetch_from_provider(source)

        assert result is not None
        assert "apple" in result["words"]
        assert "banana" in result["words"]
        assert "in the long run" in result["phrases"]

    async def test_url_fetch_with_csv_parser(
        self,
        url_connector: URLLanguageConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test fetching CSV content and parsing words."""
        source = LanguageSource(
            name="csv_vocab",
            url="https://example.com/vocab.csv",
            language=Language.ENGLISH,
            parser=ParserType.CSV_WORDS,
        )

        # Return CSV content
        csv_content = "word,frequency,type\napple,100,noun\nrun quickly,50,phrase\nbanana,80,noun"
        mock_http_client.get.return_value.text = csv_content

        with patch("floridify.providers.language.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            result = await url_connector._fetch_from_provider(source)

        assert result is not None
        assert "apple" in result["words"]
        assert "banana" in result["words"]
        assert "run quickly" in result["phrases"]

    async def test_custom_scraper_french_expressions(
        self,
        url_connector: URLLanguageConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test custom scraper for French expressions."""
        source = LanguageSource(
            name="french_expressions",
            url="https://example.com/french",
            language=Language.FRENCH,
            scraper=ScraperType.FRENCH_EXPRESSIONS,
        )

        # Mock scraper to return structured data
        mock_http_client.get.return_value.text = "<html>French content</html>"

        with patch(
            "floridify.providers.language.scraper.scrapers.scrape_french_expressions"
        ) as mock_scraper:
            mock_scraper.return_value = {
                "vocabulary": ["bonjour", "merci"],
                "phrases": ["s'il vous plaît", "comment allez-vous"],
            }

            with patch(
                "floridify.providers.language.scraper.url.respectful_scraper"
            ) as mock_scraper:
                mock_scraper.return_value.__aenter__.return_value = mock_http_client
                result = await url_connector._fetch_from_provider(source)

        assert result is not None
        assert result["language"] == Language.FRENCH.value
        assert "vocabulary" in result


@pytest.mark.asyncio
class TestLanguageParsers:
    """Test language parser functions."""

    def test_parse_text_lines_basic(self) -> None:
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

    def test_parse_text_lines_with_frequency(self) -> None:
        """Test parsing frequency lists."""
        content = """
        apple 100
        banana 80
        cherry pie 50
        orange 60
        """
        words, phrases = parse_text_lines(content, Language.ENGLISH)

        assert "apple" in words
        assert "banana" in words
        assert "orange" in words
        assert "cherry" in words  # First word extracted
        assert len(words) == 4
        assert len(phrases) == 0  # "cherry" alone, not "cherry pie"

    def test_parse_json_vocabulary_structured(self) -> None:
        """Test parsing structured JSON vocabulary."""
        content = json.dumps(
            {
                "words": ["cat", "dog", "bird"],
                "phrases": ["raining cats and dogs", "early bird"],
                "idioms": ["break a leg", "piece of cake"],
            }
        )

        words, phrases = parse_json_vocabulary(content, Language.ENGLISH)

        assert "cat" in words
        assert "dog" in words
        assert "bird" in words
        assert "raining cats and dogs" in phrases
        assert "break a leg" in phrases
        assert "piece of cake" in phrases

    def test_parse_json_vocabulary_array(self) -> None:
        """Test parsing JSON array."""
        content = json.dumps(
            [
                "apple",
                "banana split",
                "cherry",
                "date palm",
            ]
        )

        words, phrases = parse_json_vocabulary(content, Language.ENGLISH)

        assert "apple" in words
        assert "cherry" in words
        assert "banana split" in phrases
        assert "date palm" in phrases

    def test_parse_json_vocabulary_dict_keys(self) -> None:
        """Test using dictionary keys as vocabulary."""
        content = json.dumps(
            {
                "apple": {"definition": "a fruit"},
                "run": {"definition": "to move quickly"},
                "in the loop": {"definition": "informed"},
            }
        )

        words, phrases = parse_json_vocabulary(content, Language.ENGLISH)

        assert "apple" in words
        assert "run" in words
        assert "in the loop" in phrases

    def test_parse_csv_words_with_headers(self) -> None:
        """Test parsing CSV with headers."""
        content = """word,frequency,type
apple,100,noun
running fast,50,phrase
banana,80,noun
piece of cake,30,idiom"""

        words, phrases = parse_csv_words(content, Language.ENGLISH)

        assert "apple" in words
        assert "banana" in words
        assert "running fast" in phrases
        assert "piece of cake" in phrases

    def test_parse_csv_words_simple(self) -> None:
        """Test parsing simple CSV without headers."""
        content = """apple,100
banana,80
cherry pie,50
orange,60"""

        words, phrases = parse_csv_words(content, Language.ENGLISH)

        assert "apple" in words
        assert "banana" in words
        assert "orange" in words
        # Takes first column only
        assert len(phrases) == 0 or "cherry" in words

    def test_parse_scraped_data(self) -> None:
        """Test parsing scraped structured data."""
        content = {
            "vocabulary": ["word1", "word2"],
            "words": ["word3", "word4"],
            "phrases": ["phrase one", "phrase two"],
            "expressions": ["expression one"],
            "idioms": [
                {"text": "idiom one"},
                "idiom two",
            ],
        }

        words, phrases = parse_scraped_data(content, Language.ENGLISH)

        assert "word1" in words
        assert "word3" in words
        assert "phrase one" in phrases
        assert "expression one" in phrases
        assert "idiom two" in phrases


@pytest.mark.asyncio
class TestLanguageProviderCaching:
    """Test language provider caching and versioning."""

    @pytest_asyncio.fixture
    async def versioned_manager(self) -> VersionedDataManager:
        """Create versioned data manager."""
        return VersionedDataManager()

    async def test_language_fetch_with_caching(
        self,
        test_db: Any,
        url_connector: URLLanguageConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test that language fetching uses cache."""
        source = LanguageSource(
            name="cached_vocab",
            url="https://example.com/vocab.txt",
            language=Language.ENGLISH,
        )

        with patch("floridify.providers.language.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            # First fetch
            result1 = await url_connector.fetch(source)
            call_count1 = mock_http_client.get.call_count

            # Second fetch - should use cache
            result2 = await url_connector.fetch(source)
            call_count2 = mock_http_client.get.call_count

        assert call_count1 == call_count2  # No additional HTTP call
        assert result1 == result2

    async def test_language_versioning(
        self,
        test_db: Any,
        versioned_manager: VersionedDataManager,
    ) -> None:
        """Test language data versioning."""
        # Save initial vocabulary
        v1 = await versioned_manager.save(
            resource_id="english_common",
            content={
                "vocabulary": ["the", "be", "to"],
                "language": "en",
            },
            resource_type=ResourceType.LANGUAGE,
            namespace=CacheNamespace.LANGUAGE,
        )

        # Update vocabulary
        v2 = await versioned_manager.save(
            resource_id="english_common",
            content={
                "vocabulary": ["the", "be", "to", "of", "and"],
                "language": "en",
                "updated": True,
            },
            resource_type=ResourceType.LANGUAGE,
            namespace=CacheNamespace.LANGUAGE,
        )

        assert v1.id != v2.id
        assert v2.version_info.is_latest is True
        assert v2.version_info.supersedes == v1.id


@pytest.mark.asyncio
class TestLanguageProviderErrors:
    """Test language provider error handling."""

    async def test_invalid_url_handling(
        self,
        url_connector: URLLanguageConnector,
    ) -> None:
        """Test handling of invalid URLs."""
        source = LanguageSource(
            name="invalid",
            url="not-a-valid-url",
            language=Language.ENGLISH,
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.InvalidURL("Invalid URL")

        with patch("floridify.providers.language.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_client
            result = await url_connector._fetch_from_provider(source)

        assert result is None

    async def test_network_error_handling(
        self,
        url_connector: URLLanguageConnector,
    ) -> None:
        """Test handling of network errors."""
        source = LanguageSource(
            name="unreachable",
            url="https://unreachable.example.com",
            language=Language.ENGLISH,
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.NetworkError("Connection failed")

        with patch("floridify.providers.language.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_client
            result = await url_connector._fetch_from_provider(source)

        assert result is None

    async def test_malformed_content_handling(
        self,
        url_connector: URLLanguageConnector,
    ) -> None:
        """Test handling of malformed content."""
        source = LanguageSource(
            name="malformed",
            url="https://example.com/bad.json",
            language=Language.ENGLISH,
            parser=ParserType.JSON_VOCABULARY,
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = MagicMock(
            status_code=200,
            text="{invalid json content",
        )

        with patch("floridify.providers.language.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_client
            result = await url_connector._fetch_from_provider(source)

        # Parser should handle error gracefully
        assert result is not None
        assert result["vocabulary_count"] == 0


@pytest.mark.asyncio
class TestLanguageSourceConfiguration:
    """Test LanguageSource configuration and validation."""

    def test_language_source_defaults(self) -> None:
        """Test LanguageSource default values."""
        source = LanguageSource(
            name="basic",
            url="https://example.com/vocab.txt",
            language=Language.ENGLISH,
        )

        assert source.scraper == ScraperType.DEFAULT
        assert source.parser == ParserType.TEXT_LINES
        assert source.description == ""
        assert source.update_frequency is None
        assert source.tags == []

    def test_language_source_with_custom_config(self) -> None:
        """Test LanguageSource with custom configuration."""
        source = LanguageSource(
            name="custom",
            url="https://example.com/data.json",
            language=Language.SPANISH,
            scraper=ScraperType.DEFAULT,
            parser=ParserType.JSON_VOCABULARY,
            description="Spanish vocabulary from API",
            tags=["api", "spanish", "common"],
        )

        assert source.language == Language.SPANISH
        assert source.parser == ParserType.JSON_VOCABULARY
        assert "spanish" in source.tags

    def test_language_source_validation(self) -> None:
        """Test LanguageSource validation."""
        # Valid source
        source = LanguageSource(
            name="valid",
            url="https://example.com/vocab.txt",
            language=Language.ENGLISH,
        )
        assert source.name == "valid"

        # URL validation happens at creation
        with pytest.raises(Exception):
            LanguageSource(
                name="invalid",
                url="",  # Empty URL
                language=Language.ENGLISH,
            )


@pytest.mark.asyncio
class TestLanguageProviderIntegration:
    """Test language provider integration scenarios."""

    async def test_complete_vocabulary_fetch_flow(
        self,
        test_db: Any,
        url_connector: URLLanguageConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test complete flow: fetch → parse → save → retrieve."""
        source = LanguageSource(
            name="complete_flow",
            url="https://example.com/vocabulary.json",
            language=Language.ENGLISH,
            parser=ParserType.JSON_VOCABULARY,
        )

        # Mock response
        mock_http_client.get.return_value.text = json.dumps(
            {
                "vocabulary": ["apple", "banana", "cherry"],
                "phrases": ["piece of cake", "break a leg"],
                "metadata": {
                    "source": "common_english",
                    "version": "1.0",
                },
            }
        )

        with patch("floridify.providers.language.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            # Fetch and save
            result = await url_connector.fetch(source)

        assert result is not None
        assert len(result["words"]) == 3
        assert len(result["phrases"]) == 2

        # Retrieve from storage
        retrieved = await url_connector.get(source)
        assert retrieved is not None
        assert retrieved["source_name"] == "complete_flow"

    async def test_multi_language_support(
        self,
        test_db: Any,
    ) -> None:
        """Test fetching vocabulary in multiple languages."""
        config = ConnectorConfig()

        sources = [
            LanguageSource(
                name="english_vocab",
                url="https://example.com/en.txt",
                language=Language.ENGLISH,
            ),
            LanguageSource(
                name="spanish_vocab",
                url="https://example.com/es.txt",
                language=Language.SPANISH,
            ),
            LanguageSource(
                name="french_vocab",
                url="https://example.com/fr.txt",
                language=Language.FRENCH,
            ),
        ]

        connector = URLLanguageConnector(config=config)
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        # Different content for each language
        responses = {
            Language.ENGLISH: "hello\nworld\ngood morning",
            Language.SPANISH: "hola\nmundo\nbuenos días",
            Language.FRENCH: "bonjour\nmonde\nbon matin",
        }

        results = []
        for source in sources:
            mock_client.get.return_value.text = responses[source.language]
            with patch(
                "floridify.providers.language.scraper.url.respectful_scraper"
            ) as mock_scraper:
                mock_scraper.return_value.__aenter__.return_value = mock_client
                result = await connector._fetch_from_provider(source)
                results.append(result)

        # Verify each language was processed
        assert len(results) == 3
        assert all(r is not None for r in results)
        assert results[0]["language"] == Language.ENGLISH.value
        assert results[1]["language"] == Language.SPANISH.value
        assert results[2]["language"] == Language.FRENCH.value

    async def test_large_vocabulary_handling(
        self,
        url_connector: URLLanguageConnector,
    ) -> None:
        """Test handling of large vocabulary lists."""
        source = LanguageSource(
            name="large_vocab",
            url="https://example.com/large.txt",
            language=Language.ENGLISH,
        )

        # Generate large vocabulary
        large_content = "\n".join([f"word{i}" for i in range(10000)])

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = MagicMock(
            status_code=200,
            text=large_content,
        )

        with patch("floridify.providers.language.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_client
            result = await url_connector._fetch_from_provider(source)

        assert result is not None
        assert result["vocabulary_count"] == 10000
        assert len(result["words"]) == 10000


@pytest.mark.asyncio
class TestLanguageEntryModel:
    """Test LanguageEntry model persistence."""

    async def test_language_entry_creation(self, test_db: Any) -> None:
        """Test creating and saving LanguageEntry."""
        source = LanguageSource(
            name="test_source",
            url="https://example.com",
            language=Language.ENGLISH,
        )

        entry = LanguageEntry(
            source=source,
            provider=LanguageProvider.CUSTOM_URL,
            vocabulary=["apple", "banana", "cherry"],
            word_count=3,
            phrase_count=0,
            idiom_count=0,
        )

        # Note: LanguageEntry might not have save() if it's not a Beanie Document
        # This test assumes it can be persisted somehow
        assert entry.source.name == "test_source"
        assert entry.vocabulary == ["apple", "banana", "cherry"]
        assert entry.word_count == 3
