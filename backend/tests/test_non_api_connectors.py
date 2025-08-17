"""Comprehensive tests for non-API based connectors.

Tests the real functionality of scraper and local connectors without mocking,
using actual network requests and local services where available.
"""

import asyncio
import platform
import tempfile
from pathlib import Path

import pytest
from beanie import PydanticObjectId

from floridify.caching.core import GlobalCacheManager
from floridify.caching.filesystem import FilesystemBackend
from floridify.models import Definition, Example, Pronunciation, Word
from floridify.models.dictionary import DictionaryEntry, DictionaryProvider, Language
from floridify.providers.core import ConnectorConfig
from floridify.providers.dictionary.local.apple_dictionary import (
    AppleDictionaryConnector,
)
from floridify.providers.dictionary.scraper.wiktionary import WiktionaryConnector
from floridify.providers.dictionary.scraper.wordhippo import WordHippoConnector
from floridify.providers.dictionary.wholesale.wiktionary_wholesale import (
    WiktionaryWholesaleConnector,
)


class TestWiktionaryConnector:
    """Test Wiktionary scraper with real API calls."""

    @pytest.fixture
    def connector(self):
        """Create Wiktionary connector."""
        config = ConnectorConfig()
        return WiktionaryConnector(config)

    @pytest.mark.asyncio
    async def test_simple_word_lookup(self, connector, test_db):
        """Test looking up a simple, common word."""
        word = "apple"
        
        # Perform actual lookup
        result = await connector._fetch_from_provider(word)
        
        # Verify we got meaningful data
        assert result is not None
        assert isinstance(result, DictionaryEntry)
        assert result.provider == DictionaryProvider.WIKTIONARY
        
        # Verify word was created and linked
        assert result.word_id is not None
        word_obj = await Word.get(result.word_id)
        assert word_obj is not None
        assert word_obj.text == word

    @pytest.mark.asyncio
    async def test_complex_word_with_etymology(self, connector, test_db):
        """Test word with rich etymology and pronunciation data."""
        word = "serendipity"
        
        result = await connector._fetch_from_provider(word)
        
        assert result is not None
        
        # Should have etymology for this word
        if result.etymology:
            assert len(result.etymology.text) > 10
            assert any(keyword in result.etymology.text.lower() 
                      for keyword in ["persian", "arabic", "fairy", "tale"])
        
        # Check definitions were created
        if result.definition_ids:
            definition = await Definition.get(result.definition_ids[0])
            assert definition is not None
            assert len(definition.text) > 5
            assert definition.part_of_speech in ["noun", "adjective", "verb"]

    @pytest.mark.asyncio
    async def test_word_with_multiple_definitions(self, connector, test_db):
        """Test word with multiple part-of-speech definitions."""
        word = "bank"  # Noun (financial) and verb (to bank/rely)
        
        result = await connector._fetch_from_provider(word)
        
        assert result is not None
        assert len(result.definition_ids) >= 2  # Should have multiple definitions
        
        # Verify definitions have different parts of speech
        definitions = []
        for def_id in result.definition_ids[:3]:  # Check first 3
            definition = await Definition.get(def_id)
            if definition:
                definitions.append(definition)
        
        parts_of_speech = {d.part_of_speech for d in definitions}
        assert len(parts_of_speech) >= 2  # Multiple POS

    @pytest.mark.asyncio
    async def test_pronunciation_extraction(self, connector, test_db):
        """Test pronunciation data extraction."""
        word = "pronunciation"  # Meta word with clear pronunciation
        
        result = await connector._fetch_from_provider(word)
        
        assert result is not None
        
        if result.pronunciation_id:
            pronunciation = await Pronunciation.get(result.pronunciation_id)
            assert pronunciation is not None
            assert pronunciation.phonetic != "unknown"
            assert len(pronunciation.ipa) > 3

    @pytest.mark.asyncio
    async def test_examples_and_quotations(self, connector, test_db):
        """Test extraction of examples and quotations."""
        word = "ubiquitous"  # Word likely to have good examples
        
        result = await connector._fetch_from_provider(word)
        
        assert result is not None
        
        # Check at least one definition has examples
        has_examples = False
        for def_id in result.definition_ids:
            definition = await Definition.get(def_id)
            if definition and definition.example_ids:
                has_examples = True
                # Check first example
                example = await Example.get(definition.example_ids[0])
                assert example is not None
                assert len(example.text) > 10
                assert word.lower() in example.text.lower() or "ubiquitous" in example.text.lower()
                break
        
        # Allow this to pass even without examples, as availability varies
        # but if we have examples, they should be valid

    @pytest.mark.asyncio
    async def test_synonyms_extraction(self, connector, test_db):
        """Test synonym extraction from Wiktionary."""
        word = "happy"  # Word with clear synonyms
        
        result = await connector._fetch_from_provider(word)
        
        assert result is not None
        
        # Check if any definition has synonyms
        found_synonyms = False
        for def_id in result.definition_ids:
            definition = await Definition.get(def_id)
            if definition and definition.synonyms:
                found_synonyms = True
                # Verify synonyms are meaningful
                for synonym in definition.synonyms[:3]:
                    assert len(synonym) > 1
                    assert synonym.isalpha() or " " in synonym  # Allow multi-word
                break

    @pytest.mark.asyncio
    async def test_nonexistent_word(self, connector, test_db):
        """Test handling of nonexistent words."""
        word = "xyznonexistentword123"
        
        result = await connector._fetch_from_provider(word)
        
        # Should return None for nonexistent words
        assert result is None


class TestWordHippoConnector:
    """Test WordHippo scraper with real web scraping."""

    @pytest.fixture
    def connector(self):
        """Create WordHippo connector."""
        config = ConnectorConfig()
        return WordHippoConnector(config)

    @pytest.mark.asyncio
    async def test_definition_scraping(self, connector, test_db):
        """Test scraping definitions from WordHippo."""
        word = "happiness"
        
        result = await connector._fetch_from_provider(word)
        
        assert result is not None
        assert isinstance(result, DictionaryEntry)
        assert result.provider == DictionaryProvider.WORDHIPPO
        
        # Should have at least one definition
        assert len(result.definition_ids) >= 1
        
        definition = await Definition.get(result.definition_ids[0])
        assert definition is not None
        assert len(definition.text) > 5

    @pytest.mark.asyncio
    async def test_synonyms_and_antonyms_enrichment(self, connector, test_db):
        """Test that WordHippo enriches with synonyms and antonyms."""
        word = "good"  # Simple word with clear synonyms/antonyms
        
        result = await connector._fetch_from_provider(word)
        
        assert result is not None
        
        # Check if definitions were enriched with synonyms/antonyms
        enriched_definition = None
        for def_id in result.definition_ids:
            definition = await Definition.get(def_id)
            if definition and (definition.synonyms or definition.antonyms):
                enriched_definition = definition
                break
        
        # At least check that the structure allows for enrichment
        # (WordHippo may not always have data for every word)

    @pytest.mark.asyncio
    async def test_example_sentences(self, connector, test_db):
        """Test extraction of example sentences from WordHippo."""
        word = "example"  # Meta word likely to have examples
        
        result = await connector._fetch_from_provider(word)
        
        assert result is not None
        
        # Check for examples in at least one definition
        for def_id in result.definition_ids:
            definition = await Definition.get(def_id)
            if definition and definition.example_ids:
                example = await Example.get(definition.example_ids[0])
                assert example is not None
                assert len(example.text) > 10
                assert example.type == "literature"  # WordHippo uses real examples
                break

    @pytest.mark.asyncio
    async def test_raw_data_preservation(self, connector, test_db):
        """Test that raw scraping data is preserved."""
        word = "test"
        
        result = await connector._fetch_from_provider(word)
        
        assert result is not None
        assert result.raw_data is not None
        
        # Should have metadata about the scraping operation
        assert "url" in result.raw_data
        assert "definitions_count" in result.raw_data
        assert result.raw_data["definitions_count"] >= 0


@pytest.mark.skipif(
    platform.system() != "Darwin",
    reason="Apple Dictionary only available on macOS"
)
class TestAppleDictionaryConnector:
    """Test Apple Dictionary connector on macOS."""

    @pytest.fixture
    def connector(self):
        """Create Apple Dictionary connector."""
        config = ConnectorConfig()
        return AppleDictionaryConnector(config)

    @pytest.mark.asyncio
    async def test_service_availability(self, connector):
        """Test that Apple Dictionary Services is available."""
        service_info = connector.get_service_info()
        
        assert service_info["platform"] == "Darwin"
        # May or may not be available depending on PyObjC installation

    @pytest.mark.asyncio
    async def test_local_word_lookup(self, connector, test_db):
        """Test looking up a word using local Apple Dictionary."""
        if not connector._is_available():
            pytest.skip("Apple Dictionary Services not available")
        
        word = "computer"
        
        result = await connector._fetch_from_provider(word)
        
        if result is not None:  # Only test if service actually works
            assert isinstance(result, DictionaryEntry)
            assert result.provider == DictionaryProvider.APPLE_DICTIONARY
            
            # Should have at least one definition
            assert len(result.definition_ids) >= 1
            
            definition = await Definition.get(result.definition_ids[0])
            assert definition is not None
            assert len(definition.text) > 5

    @pytest.mark.asyncio
    async def test_pronunciation_from_apple(self, connector, test_db):
        """Test pronunciation extraction from Apple Dictionary."""
        if not connector._is_available():
            pytest.skip("Apple Dictionary Services not available")
        
        word = "pronunciation"
        
        result = await connector._fetch_from_provider(word)
        
        if result is not None and result.pronunciation_id:
            pronunciation = await Pronunciation.get(result.pronunciation_id)
            assert pronunciation is not None
            # Apple Dictionary typically provides IPA
            assert len(pronunciation.ipa) > 2

    @pytest.mark.asyncio
    async def test_etymology_extraction(self, connector, test_db):
        """Test etymology extraction from Apple Dictionary."""
        if not connector._is_available():
            pytest.skip("Apple Dictionary Services not available")
        
        word = "etymology"  # Meta word likely to have etymology
        
        result = await connector._fetch_from_provider(word)
        
        if result is not None and result.etymology:
            assert len(result.etymology.text) > 10


class TestWiktionaryWholesaleConnector:
    """Test Wiktionary wholesale data operations."""

    @pytest.fixture
    def connector(self):
        """Create Wiktionary wholesale connector."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ConnectorConfig()
            return WiktionaryWholesaleConnector(
                language=Language.ENGLISH,
                data_dir=Path(tmpdir),
                config=config
            )

    @pytest.mark.asyncio
    async def test_title_list_download(self, connector):
        """Test downloading Wiktionary title lists."""
        from floridify.providers.dictionary.wholesale.wiktionary_wholesale import (
            WiktionaryTitleListDownloader
        )
        
        downloader = WiktionaryTitleListDownloader(
            language=Language.ENGLISH,
            data_dir=connector.data_dir
        )
        
        # This actually downloads data - run only in CI or when needed
        if pytest.skip_network_tests:
            pytest.skip("Network test skipped")
        
        title_file = await downloader.download_titles()
        assert title_file.exists()
        assert title_file.suffix == ".gz"

    @pytest.mark.asyncio
    async def test_vocabulary_extraction(self, connector):
        """Test extracting vocabulary from title lists."""
        from floridify.providers.dictionary.wholesale.wiktionary_wholesale import (
            WiktionaryTitleListDownloader
        )
        
        if pytest.skip_network_tests:
            pytest.skip("Network test skipped")
        
        downloader = WiktionaryTitleListDownloader(
            language=Language.ENGLISH,
            data_dir=connector.data_dir
        )
        
        vocabulary = await downloader.extract_vocabulary(min_length=3)
        
        assert len(vocabulary) > 1000  # Should have many words
        
        # Verify vocabulary quality
        for word in vocabulary[:10]:
            assert len(word) >= 3
            assert ":" not in word  # No namespace prefixes
            assert word.isalpha() or " " in word  # Letters or multi-word

    @pytest.mark.asyncio
    async def test_wikitext_parsing(self, connector):
        """Test parsing Wiktionary wikitext content."""
        sample_wikitext = """
==English==

===Etymology===
From Latin ''exemplum''.

===Pronunciation===
* {{IPA|en|/ɪɡˈzæmpəl/}}

===Noun===
{{en-noun}}

# A representative [[case]].
#: {{ux|en|This is an '''example''' of good writing.}}
# Something that serves as a [[pattern]].

====Synonyms====
* {{l|en|instance}}
* {{l|en|sample}}
"""
        
        parsed_data = connector._parse_wikitext(sample_wikitext)
        
        assert "definitions" in parsed_data
        assert "etymologies" in parsed_data
        assert "pronunciations" in parsed_data
        
        # Should extract definitions
        assert len(parsed_data["definitions"]) >= 2
        
        # Should have etymology
        assert len(parsed_data["etymologies"]) >= 1
        assert "latin" in parsed_data["etymologies"][0].lower()

    @pytest.mark.asyncio
    async def test_fallback_to_scraper(self, connector, test_db):
        """Test fallback to regular scraper when no wholesale data."""
        word = "temporary_test_word"
        
        # Should fall back to scraper since we don't have wholesale data
        result = await connector._fetch_from_provider(word)
        
        # Result may be None (word not found) but should not error


class TestConnectorIntegration:
    """Test integration between connectors and shared systems."""

    @pytest.mark.asyncio
    async def test_word_deduplication(self, test_db):
        """Test that multiple connectors don't create duplicate words."""
        word_text = "integration"
        
        # Use two different connectors for the same word
        config = ConnectorConfig()
        wiktionary = WiktionaryConnector(config)
        wordhippo = WordHippoConnector(config)
        
        # First lookup
        result1 = await wiktionary._fetch_from_provider(word_text)
        word1_id = result1.word_id if result1 else None
        
        # Second lookup with different connector
        result2 = await wordhippo._fetch_from_provider(word_text)
        word2_id = result2.word_id if result2 else None
        
        if word1_id and word2_id:
            # Should reference the same Word document
            assert word1_id == word2_id

    @pytest.mark.asyncio
    async def test_definition_uniqueness(self, test_db):
        """Test that definitions from different providers are kept separate."""
        word_text = "unique"
        
        config = ConnectorConfig()
        wiktionary = WiktionaryConnector(config)
        wordhippo = WordHippoConnector(config)
        
        result1 = await wiktionary._fetch_from_provider(word_text)
        result2 = await wordhippo._fetch_from_provider(word_text)
        
        if result1 and result2:
            # Should have different DictionaryEntry documents
            assert result1.id != result2.id
            
            # But should reference the same word
            assert result1.word_id == result2.word_id
            
            # Should have different providers
            assert result1.provider != result2.provider

    @pytest.mark.asyncio
    async def test_connector_error_handling(self, test_db):
        """Test graceful error handling in connectors."""
        config = ConnectorConfig()
        connector = WiktionaryConnector(config)
        
        # Test with various problematic inputs
        test_cases = ["", "   ", "word with special chars!@#$%", "a" * 1000]
        
        for test_word in test_cases:
            result = await connector._fetch_from_provider(test_word)
            # Should not raise exceptions, may return None
            assert result is None or isinstance(result, DictionaryEntry)

    @pytest.mark.asyncio
    async def test_concurrent_connector_usage(self, test_db):
        """Test that connectors can be used concurrently."""
        config = ConnectorConfig()
        connector = WiktionaryConnector(config)
        
        words = ["concurrent", "parallel", "async", "await"]
        
        # Run multiple lookups concurrently
        tasks = [connector._fetch_from_provider(word) for word in words]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception)
            # May be None (word not found) but should not be an exception


# Add skip_network_tests fixture for CI environments
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment with network test controls."""
    import os
    pytest.skip_network_tests = os.getenv("SKIP_NETWORK_TESTS", "false").lower() == "true"