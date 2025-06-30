"""
Tests for lexicon loading and management.

Comprehensive testing of LexiconLoader with multiple sources and languages.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.floridify.search.lexicon import (
    Language,
    LexiconData,
    LexiconLoader,
    LexiconSource,
)
from src.floridify.search.phrase import MultiWordExpression


class TestLexiconData:
    """Test LexiconData structure."""

    def test_creation(self) -> None:
        """Test creation of LexiconData objects."""

        phrases = [
            MultiWordExpression(
                text="hello world",
                normalized="hello world",
                word_count=2,
            )
        ]

        data = LexiconData(
            words=["hello", "world"],
            phrases=phrases,
            metadata={"source": "test"},
            language=Language.ENGLISH,
            source=LexiconSource.DWYL_ENGLISH_WORDS,
            total_entries=3,
            last_updated="2024-01-01",
        )

        assert data.words == ["hello", "world"]
        assert len(data.phrases) == 1
        assert data.phrases[0].text == "hello world"
        assert data.metadata == {"source": "test"}
        assert data.language == Language.ENGLISH
        assert data.source == LexiconSource.DWYL_ENGLISH_WORDS
        assert data.total_entries == 3
        assert data.last_updated == "2024-01-01"

    def test_defaults(self) -> None:
        """Test default values in LexiconData."""

        data = LexiconData(
            words=["test"],
            phrases=[],
            metadata={},
            language=Language.ENGLISH,
            source=LexiconSource.DWYL_ENGLISH_WORDS,
        )

        assert data.total_entries == 0  # Default
        assert data.last_updated == ""  # Default


class TestLexiconLoader:
    """Test LexiconLoader functionality."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path: Path) -> Path:
        """Create temporary cache directory for testing."""
        cache_dir = tmp_path / "lexicon_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @pytest.fixture
    def loader(self, temp_cache_dir: Path) -> LexiconLoader:
        """Create lexicon loader for testing."""
        return LexiconLoader(temp_cache_dir)

    def test_initialization(self, temp_cache_dir: Path) -> None:
        """Test lexicon loader initialization."""

        loader = LexiconLoader(temp_cache_dir)

        assert loader.cache_dir == temp_cache_dir
        assert loader.lexicon_dir == temp_cache_dir / "lexicons"
        assert loader.index_dir == temp_cache_dir / "index"

        # Directories should be created
        assert loader.lexicon_dir.exists()
        assert loader.index_dir.exists()

        # Should be empty initially
        assert len(loader.lexicons) == 0
        assert len(loader._all_words) == 0
        assert len(loader._all_phrases) == 0

    def test_source_urls_configuration(self, loader: LexiconLoader) -> None:
        """Test that source URLs are properly configured."""

        # Should have URLs for key sources
        assert LexiconSource.DWYL_ENGLISH_WORDS in loader._source_urls
        assert LexiconSource.GOOGLE_10K_ENGLISH in loader._source_urls
        assert LexiconSource.ENGLISH_IDIOMS in loader._source_urls

        # Check URL structure
        dwyl_config = loader._source_urls[LexiconSource.DWYL_ENGLISH_WORDS]
        assert "url" in dwyl_config
        assert "format" in dwyl_config
        assert dwyl_config["format"] == "text_lines"

    def test_get_sources_for_language(self, loader: LexiconLoader) -> None:
        """Test getting appropriate sources for languages."""

        # English should have multiple sources
        en_sources = loader._get_sources_for_language(Language.ENGLISH)
        assert len(en_sources) >= 2
        assert LexiconSource.DWYL_ENGLISH_WORDS in en_sources
        assert LexiconSource.GOOGLE_10K_ENGLISH in en_sources

        # French should have at least one source
        fr_sources = loader._get_sources_for_language(Language.FRENCH)
        assert len(fr_sources) >= 1

        # Spanish should have sources (implementation supports Spanish)
        spanish_sources = loader._get_sources_for_language(Language.SPANISH)
        assert len(spanish_sources) >= 1

    def test_parse_text_lines(self, loader: LexiconLoader) -> None:
        """Test parsing simple text file format."""

        text_content = """hello
world
machine learning
natural language
# This is a comment
state-of-the-art

   # Another comment with spaces
test word
"""

        words, phrases = loader._parse_text_lines(text_content, Language.ENGLISH)

        # Should extract single words
        assert "hello" in words
        assert "world" in words

        # Should extract phrases
        phrase_texts = [p.normalized for p in phrases]
        assert "machine learning" in phrase_texts
        assert "natural language" in phrase_texts
        assert "test word" in phrase_texts
        assert "state-of-the-art" in phrase_texts

        # Should skip comments and empty lines
        assert "# This is a comment" not in words
        assert "" not in words

    def test_parse_json_idioms(self, loader: LexiconLoader) -> None:
        """Test parsing JSON idiom format."""

        # Test with list format
        json_data = ["break a leg", "piece of cake", "hit the books"]
        json_content = json.dumps(json_data)

        words, phrases = loader._parse_json_idioms(json_content, Language.ENGLISH)

        # Should not extract single words from idiom sources
        assert len(words) == 0

        # Should extract idioms as phrases
        phrase_texts = [p.normalized for p in phrases]
        assert "break a leg" in phrase_texts
        assert "piece of cake" in phrase_texts
        assert "hit the books" in phrase_texts

        # Should mark as idioms
        for phrase in phrases:
            assert phrase.is_idiom

    def test_parse_json_idioms_dict_format(self, loader: LexiconLoader) -> None:
        """Test parsing JSON with dictionary format."""

        # Test with nested dict format
        json_data = {
            "idioms": [
                {"idiom": "break a leg", "meaning": "good luck"},
                {"phrase": "piece of cake", "meaning": "easy"},
                {"text": "hit the books", "meaning": "study"},
            ]
        }
        json_content = json.dumps(json_data)

        words, phrases = loader._parse_json_idioms(json_content, Language.ENGLISH)

        phrase_texts = [p.normalized for p in phrases]
        assert "break a leg" in phrase_texts
        assert "piece of cake" in phrase_texts
        assert "hit the books" in phrase_texts

    @pytest.mark.asyncio
    async def test_load_from_cache(self, loader: LexiconLoader) -> None:
        """Test loading lexicon data from cache."""

        # Create mock cached data
        test_data = LexiconData(
            words=["hello", "world"],
            phrases=[],
            metadata={"test": True},
            language=Language.ENGLISH,
            source=LexiconSource.DWYL_ENGLISH_WORDS,
        )

        # Save to cache
        cache_file = loader.index_dir / "en_lexicon.pkl"
        import pickle

        with cache_file.open("wb") as f:
            pickle.dump(test_data, f)

        # Load from cache
        await loader._load_language(Language.ENGLISH)

        # Should have loaded cached data
        assert Language.ENGLISH in loader.lexicons
        cached_data = loader.lexicons[Language.ENGLISH]
        assert cached_data.words == ["hello", "world"]
        assert cached_data.metadata == {"test": True}

    @pytest.mark.asyncio
    async def test_load_from_sources_mocked(self, loader: LexiconLoader) -> None:
        """Test loading from sources with mocked HTTP calls."""

        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "hello\nworld\nhello world\n"
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            loader._http_client = mock_client

            # Load English sources
            lexicon_data = await loader._load_from_sources(Language.ENGLISH)

            # Should have loaded data
            assert len(lexicon_data.words) > 0
            assert "hello" in lexicon_data.words
            assert "world" in lexicon_data.words

            # Should have phrases
            phrase_texts = [p.normalized for p in lexicon_data.phrases]
            assert "hello world" in phrase_texts

    @pytest.mark.asyncio
    async def test_load_languages_integration(self, loader: LexiconLoader) -> None:
        """Test loading multiple languages with mocked sources."""

        # Mock the source loading to avoid network calls
        async def mock_load_source(source, language):
            if language == Language.ENGLISH:
                return ["hello", "world"], [MultiWordExpression("hello world", "hello world", 2)]
            elif language == Language.FRENCH:
                return ["bonjour", "monde"], [
                    MultiWordExpression(
                        text="bonjour monde", normalized="bonjour monde", word_count=2
                    )
                ]
            return [], []

        with patch.object(loader, "_load_source", side_effect=mock_load_source):
            await loader.load_languages([Language.ENGLISH, Language.FRENCH])

            # Should have loaded both languages
            assert Language.ENGLISH in loader.lexicons
            assert Language.FRENCH in loader.lexicons

            # Check English data
            en_data = loader.lexicons[Language.ENGLISH]
            assert "hello" in en_data.words
            assert "world" in en_data.words

            # Check French data
            fr_data = loader.lexicons[Language.FRENCH]
            assert "bonjour" in fr_data.words
            assert "monde" in fr_data.words

            # Check unified indices
            all_words = loader.get_all_words()
            assert "hello" in all_words
            assert "bonjour" in all_words

            all_phrases = loader.get_all_phrases()
            assert "hello world" in all_phrases
            assert "bonjour monde" in all_phrases

    def test_get_words_and_phrases(self, loader: LexiconLoader) -> None:
        """Test getting words and phrases after manual setup."""

        # Manually add test data
        loader.lexicons[Language.ENGLISH] = LexiconData(
            words=["hello", "world"],
            phrases=[
                MultiWordExpression(text="hello world", normalized="hello world", word_count=2),
                MultiWordExpression("machine learning", "machine learning", 2),
            ],
            metadata={},
            language=Language.ENGLISH,
            source=LexiconSource.DWYL_ENGLISH_WORDS,
        )

        loader._rebuild_unified_indices()

        # Test getters
        all_words = loader.get_all_words()
        assert "hello" in all_words
        assert "world" in all_words

        all_phrases = loader.get_all_phrases()
        assert "hello world" in all_phrases
        assert "machine learning" in all_phrases

        phrase_objects = loader.get_phrases()
        assert len(phrase_objects) == 2
        assert all(isinstance(p, MultiWordExpression) for p in phrase_objects)

    def test_get_language_specific_data(self, loader: LexiconLoader) -> None:
        """Test getting data for specific languages."""

        # Add test data for multiple languages
        loader.lexicons[Language.ENGLISH] = LexiconData(
            words=["hello", "world"],
            phrases=[
                MultiWordExpression(text="hello world", normalized="hello world", word_count=2)
            ],
            metadata={},
            language=Language.ENGLISH,
            source=LexiconSource.DWYL_ENGLISH_WORDS,
        )

        loader.lexicons[Language.FRENCH] = LexiconData(
            words=["bonjour", "monde"],
            phrases=[
                MultiWordExpression(text="bonjour monde", normalized="bonjour monde", word_count=2)
            ],
            metadata={},
            language=Language.FRENCH,
            source=LexiconSource.COFINLEY_FRENCH_FREQ,
        )

        # Test English-specific data
        en_words = loader.get_words_for_language(Language.ENGLISH)
        assert "hello" in en_words
        assert "bonjour" not in en_words

        en_phrases = loader.get_phrases_for_language(Language.ENGLISH)
        en_phrase_texts = [p.normalized for p in en_phrases]
        assert "hello world" in en_phrase_texts
        assert "bonjour monde" not in en_phrase_texts

        # Test French-specific data
        fr_words = loader.get_words_for_language(Language.FRENCH)
        assert "bonjour" in fr_words
        assert "hello" not in fr_words

        # Test non-existent language
        es_words = loader.get_words_for_language(Language.SPANISH)
        assert len(es_words) == 0

    def test_statistics(self, loader: LexiconLoader) -> None:
        """Test getting lexicon statistics."""

        # Add test data
        loader.lexicons[Language.ENGLISH] = LexiconData(
            words=["hello", "world"],
            phrases=[
                MultiWordExpression(text="hello world", normalized="hello world", word_count=2)
            ],
            metadata={"loaded_sources": ["test_source"]},
            language=Language.ENGLISH,
            source=LexiconSource.DWYL_ENGLISH_WORDS,
            total_entries=3,
        )

        loader._rebuild_unified_indices()

        stats = loader.get_statistics()

        assert isinstance(stats, dict)
        assert "total_words" in stats
        assert "total_phrases" in stats
        assert "languages" in stats

        assert stats["total_words"] == 2
        assert stats["total_phrases"] == 1

        # Check language-specific stats
        assert "en" in stats["languages"]
        en_stats = stats["languages"]["en"]
        assert en_stats["words"] == 2
        assert en_stats["phrases"] == 1
        assert en_stats["total_entries"] == 3
        assert "test_source" in en_stats["sources"]

    def test_deduplication(self, loader: LexiconLoader) -> None:
        """Test deduplication of words and phrases."""

        # Create data with duplicates
        duplicate_phrases = [
            MultiWordExpression(text="hello world", normalized="hello world", word_count=2),
            MultiWordExpression("Hello World", "hello world", 2),  # Same normalized form
            MultiWordExpression("machine learning", "machine learning", 2),
        ]

        loader.lexicons[Language.ENGLISH] = LexiconData(
            words=["hello", "world", "hello", "test"],  # Duplicates
            phrases=duplicate_phrases,
            metadata={},
            language=Language.ENGLISH,
            source=LexiconSource.DWYL_ENGLISH_WORDS,
        )

        loader._rebuild_unified_indices()

        # Words should be deduplicated
        all_words = loader.get_all_words()
        assert len(all_words) == 3  # hello, world, test (no duplicates)
        assert "hello" in all_words
        assert "world" in all_words
        assert "test" in all_words

        # Phrases should be deduplicated by normalized form
        all_phrases = loader.get_all_phrases()
        assert len(all_phrases) == 2  # hello world, machine learning
        assert "hello world" in all_phrases
        assert "machine learning" in all_phrases

    @pytest.mark.asyncio
    async def test_cleanup(self, loader: LexiconLoader) -> None:
        """Test cleanup of resources."""

        # Mock HTTP client
        mock_client = AsyncMock()
        loader._http_client = mock_client

        await loader.close()

        # Should close HTTP client
        mock_client.aclose.assert_called_once()
        assert loader._http_client is None

    def test_error_handling_invalid_json(self, loader: LexiconLoader) -> None:
        """Test handling of invalid JSON data."""

        invalid_json = "{ invalid json content"

        words, phrases = loader._parse_json_idioms(invalid_json, Language.ENGLISH)

        # Should return empty results for invalid JSON
        assert len(words) == 0
        assert len(phrases) == 0

    def test_error_handling_empty_content(self, loader: LexiconLoader) -> None:
        """Test handling of empty content."""

        # Empty text content
        words, phrases = loader._parse_text_lines("", Language.ENGLISH)
        assert len(words) == 0
        assert len(phrases) == 0

        # Empty JSON content
        words, phrases = loader._parse_json_idioms("{}", Language.ENGLISH)
        assert len(words) == 0
        assert len(phrases) == 0

    @pytest.mark.asyncio
    async def test_http_client_initialization(self, loader: LexiconLoader) -> None:
        """Test HTTP client initialization during loading."""

        # Mock successful HTTP response
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "test\nword\n"
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            await loader.load_languages([Language.ENGLISH])

            # HTTP client should be initialized
            assert loader._http_client is not None

    def test_phrase_metadata_preservation(self, loader: LexiconLoader) -> None:
        """Test that phrase metadata is preserved correctly."""

        test_phrases = [
            MultiWordExpression(
                text="break a leg",
                normalized="break a leg",
                word_count=3,
                is_idiom=True,
                language="en",
                frequency=0.5,
            ),
            MultiWordExpression(
                text="machine learning",
                normalized="machine learning",
                word_count=2,
                is_idiom=False,
                language="en",
                frequency=0.8,
            ),
        ]

        loader.lexicons[Language.ENGLISH] = LexiconData(
            words=[],
            phrases=test_phrases,
            metadata={},
            language=Language.ENGLISH,
            source=LexiconSource.ENGLISH_IDIOMS,
        )

        loader._rebuild_unified_indices()

        phrase_objects = loader.get_phrases()

        # Find specific phrases and check metadata
        break_leg = next((p for p in phrase_objects if p.text == "break a leg"), None)
        assert break_leg is not None
        assert break_leg.is_idiom
        assert break_leg.word_count == 3
        assert break_leg.frequency == 0.5

        ml = next((p for p in phrase_objects if p.text == "machine learning"), None)
        assert ml is not None
        assert not ml.is_idiom
        assert ml.word_count == 2
        assert ml.frequency == 0.8
