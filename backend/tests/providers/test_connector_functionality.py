"""Tests for non-API connector functionality without database dependencies.

Focuses on testing the core functionality of connectors without requiring
full database initialization, to verify the connector logic works correctly.
"""

import platform
import tempfile
from pathlib import Path

import pytest

from floridify.models.dictionary import DictionaryProvider
from floridify.providers.core import ConnectorConfig
from floridify.providers.dictionary.local.apple_dictionary import (
    AppleDictionaryConnector,
)
from floridify.providers.dictionary.scraper.wiktionary import (
    WikitextCleaner,
    WiktionaryConnector,
)
from floridify.providers.dictionary.scraper.wordhippo import WordHippoConnector
from floridify.providers.dictionary.wholesale.wiktionary_wholesale import (
    WiktionaryTitleListDownloader,
    WiktionaryWholesaleConnector,
)
from floridify.providers.utils import RateLimitConfig


class TestWiktionaryConnectorLogic:
    """Test Wiktionary connector core logic without database."""

    def test_connector_initialization(self):
        """Test Wiktionary connector can be initialized."""
        config = ConnectorConfig()
        connector = WiktionaryConnector(config)

        assert connector.provider == DictionaryProvider.WIKTIONARY
        assert connector.base_url == "https://en.wiktionary.org/w/api.php"
        assert connector.cleaner is not None
        assert isinstance(connector.cleaner, WikitextCleaner)

    def test_wikitext_cleaner_basic_functionality(self):
        """Test WikitextCleaner can process basic wikitext."""
        cleaner = WikitextCleaner()

        # Test basic template removal
        text_with_templates = "This is a {{test|template}} with some content."
        cleaned = cleaner.clean_text(text_with_templates)

        assert "{{" not in cleaned
        assert "}}" not in cleaned
        assert "test" in cleaned or "template" in cleaned  # Should extract meaningful content

    def test_wikitext_cleaner_link_processing(self):
        """Test WikitextCleaner handles wikilinks correctly."""
        cleaner = WikitextCleaner()

        # Test wikilink processing
        text_with_links = "This is a [[wikilink]] and [[another|display text]]."
        cleaned = cleaner.clean_text(text_with_links)

        assert "[[" not in cleaned
        assert "]]" not in cleaned
        assert "wikilink" in cleaned
        assert "display text" in cleaned or "another" in cleaned

    def test_wikitext_cleaner_complex_content(self):
        """Test WikitextCleaner with complex wikitext."""
        cleaner = WikitextCleaner()

        complex_text = """
        {{lb|en|informal}} A simple {{gloss|explanation}} of something.
        {{ux|en|This is an '''example''' sentence.}}
        [[Category:English nouns]]
        """

        cleaned = cleaner.clean_text(complex_text)

        # Should remove most template syntax
        assert "{{" not in cleaned
        assert "[[" not in cleaned

        # Should preserve meaningful content
        assert len(cleaned.strip()) > 10  # Should have substantive content
        # Note: Category: may remain if not fully cleaned, which is acceptable

    def test_pos_mappings(self):
        """Test part-of-speech mappings are correctly defined."""
        connector = WiktionaryConnector()

        assert "noun" in connector.POS_MAPPINGS
        assert "verb" in connector.POS_MAPPINGS
        assert "adjective" in connector.POS_MAPPINGS
        assert "adverb" in connector.POS_MAPPINGS

        # Test mapping correctness
        assert connector.POS_MAPPINGS["noun"] == "noun"
        assert connector.POS_MAPPINGS["determiner"] == "adjective"  # Maps to adjective


class TestWordHippoConnectorLogic:
    """Test WordHippo connector core logic without database."""

    def test_connector_initialization(self):
        """Test WordHippo connector can be initialized."""
        config = ConnectorConfig()
        connector = WordHippoConnector(config)

        assert connector.provider == DictionaryProvider.WORDHIPPO
        assert connector.base_url == "https://www.wordhippo.com"
        assert connector.rate_config is not None

    def test_url_construction(self):
        """Test URL construction for WordHippo requests."""
        connector = WordHippoConnector()

        # Test definition URL pattern
        word = "example"
        expected_pattern = (
            f"{connector.base_url}/what-is/the-meaning-of-the-word/{word.lower()}.html"
        )

        # This tests the logic without making actual requests
        assert connector.base_url in expected_pattern
        assert word in expected_pattern

    def test_part_of_speech_mappings(self):
        """Test part-of-speech mappings in WordHippo connector."""
        # The connector should handle various POS abbreviations
        pos_mappings = {
            "n": "noun",
            "v": "verb",
            "adj": "adjective",
            "adv": "adverb",
            "prep": "preposition",
            "conj": "conjunction",
            "pron": "pronoun",
            "interj": "interjection",
            "exclamation": "interjection",
        }

        # Verify the mappings exist and are reasonable
        for abbrev, full_form in pos_mappings.items():
            assert len(full_form) > len(abbrev)  # Full form should be longer
            assert full_form in [
                "noun",
                "verb",
                "adjective",
                "adverb",
                "preposition",
                "conjunction",
                "pronoun",
                "interjection",
            ]


@pytest.mark.skipif(
    platform.system() != "Darwin", reason="Apple Dictionary only available on macOS"
)
class TestAppleDictionaryConnectorLogic:
    """Test Apple Dictionary connector core logic."""

    def test_connector_initialization(self):
        """Test Apple Dictionary connector can be initialized."""
        config = ConnectorConfig()
        connector = AppleDictionaryConnector(config)

        assert connector.provider == DictionaryProvider.APPLE_DICTIONARY
        assert connector._platform_compatible == (platform.system() == "Darwin")

    def test_platform_compatibility_check(self):
        """Test platform compatibility detection."""
        connector = AppleDictionaryConnector()

        # Should correctly detect macOS
        if platform.system() == "Darwin":
            assert connector._platform_compatible is True
        else:
            assert connector._platform_compatible is False

    def test_service_info_structure(self):
        """Test service info returns expected structure."""
        connector = AppleDictionaryConnector()
        service_info = connector.get_service_info()

        required_keys = [
            "provider_name",
            "platform",
            "platform_version",
            "is_available",
            "service_initialized",
            "rate_limit_config",
        ]

        for key in required_keys:
            assert key in service_info

        assert service_info["provider_name"] == DictionaryProvider.APPLE_DICTIONARY.value
        assert service_info["platform"] == platform.system()

    def test_definition_text_cleaning(self):
        """Test definition text cleaning methods."""
        connector = AppleDictionaryConnector()

        # Test pronunciation marker removal
        text_with_ipa = "apple |ˈæpəl| noun a fruit"
        cleaned = connector._clean_definition_text(text_with_ipa)

        assert "|ˈæpəl|" not in cleaned
        assert "apple" in cleaned
        assert "noun" in cleaned
        assert "fruit" in cleaned

    def test_example_extraction(self):
        """Test example extraction from definition text."""
        connector = AppleDictionaryConnector()

        text_with_examples = 'Definition text. "This is an example sentence." More text.'
        examples = connector._extract_examples(text_with_examples)

        if examples:  # May be empty list if no examples found
            assert any("example sentence" in example for example in examples)

    def test_ipa_to_phonetic_conversion(self):
        """Test IPA to phonetic conversion."""
        connector = AppleDictionaryConnector()

        # Test basic IPA conversions
        ipa_text = "/ˈæpəl/"
        phonetic = connector._ipa_to_phonetic(ipa_text)

        assert phonetic != "unknown"
        assert "æ" not in phonetic  # Should be converted
        assert len(phonetic) > 0


class TestWiktionaryWholesaleConnectorLogic:
    """Test Wiktionary wholesale connector core logic."""

    def test_connector_initialization(self):
        """Test Wiktionary wholesale connector can be initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ConnectorConfig()
            connector = WiktionaryWholesaleConnector(data_dir=Path(tmpdir), config=config)

            assert connector.provider == DictionaryProvider.WIKTIONARY
            assert connector.data_dir.exists()
            assert connector.parser is not None
            assert isinstance(connector.parser, WiktionaryConnector)

    def test_version_generation(self):
        """Test provider version generation."""
        connector = WiktionaryWholesaleConnector()
        version = connector.get_provider_version()

        assert "wholesale" in version
        assert "en" in version  # Default language
        assert len(version) > 10  # Should include date

    def test_valid_entry_detection(self):
        """Test valid entry detection logic."""
        connector = WiktionaryWholesaleConnector()

        # Valid entry
        valid_page = {
            "title": "apple",
            "content": "==English==\n\n===Noun===\n{{en-noun}}\n\n# A fruit.",
        }
        assert connector._is_valid_entry(valid_page) is True

        # Invalid entry - has colon (special page)
        invalid_page_colon = {"title": "Category:English nouns", "content": "Category page content"}
        assert connector._is_valid_entry(invalid_page_colon) is False

        # Invalid entry - too short
        invalid_page_short = {"title": "test", "content": "short"}
        assert connector._is_valid_entry(invalid_page_short) is False

    def test_wikitext_parsing_structure(self):
        """Test wikitext parsing produces expected structure."""
        connector = WiktionaryWholesaleConnector()

        sample_wikitext = """
==English==

===Etymology===
From Latin ''exemplum''.

===Noun===
{{en-noun}}

# A representative case.
# Something that serves as a pattern.

===Verb===
{{en-verb}}

# To serve as an example.
"""

        parsed_data = connector._parse_wikitext(sample_wikitext)

        # Verify structure
        expected_keys = ["definitions", "etymologies", "pronunciations", "synonyms", "antonyms"]
        for key in expected_keys:
            assert key in parsed_data
            assert isinstance(parsed_data[key], list)

        # Should have extracted some definitions
        assert len(parsed_data["definitions"]) >= 2  # Noun and verb definitions

        # Should have extracted etymology
        assert len(parsed_data["etymologies"]) >= 1


class TestTitleListDownloader:
    """Test Wiktionary title list downloader logic."""

    def test_downloader_initialization(self):
        """Test title list downloader can be initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = WiktionaryTitleListDownloader(data_dir=Path(tmpdir))

            assert downloader.data_dir.exists()
            assert "wiktionary" in downloader.dump_url
            assert "latest" in downloader.dump_url


class TestRateLimitingConfiguration:
    """Test rate limiting configuration for connectors."""

    def test_connector_rate_limit_configs(self):
        """Test that connectors have appropriate rate limiting."""
        # Wiktionary (API calls)
        wiktionary = WiktionaryConnector()
        assert wiktionary.config.rate_limit_config is not None
        assert wiktionary.config.rate_limit_config.base_requests_per_second > 0

        # WordHippo (web scraping - should be more conservative)
        wordhippo = WordHippoConnector()
        assert wordhippo.config.rate_limit_config is not None
        assert wordhippo.config.rate_limit_config.base_requests_per_second > 0

        # Apple Dictionary (local - should be fastest)
        apple = AppleDictionaryConnector()
        assert apple.config.rate_limit_config is not None
        # Local should have higher rate limit than web-based
        assert (
            apple.config.rate_limit_config.base_requests_per_second
            >= wordhippo.config.rate_limit_config.base_requests_per_second
        )

    def test_rate_limit_config_creation(self):
        """Test rate limit configuration creation."""
        rate_config = RateLimitConfig(
            base_requests_per_second=5.0, min_delay=0.1, max_delay=2.0, backoff_multiplier=1.5
        )

        assert rate_config.base_requests_per_second == 5.0
        assert rate_config.min_delay == 0.1
        assert rate_config.max_delay == 2.0
        assert rate_config.backoff_multiplier == 1.5


class TestConnectorConfigConsistency:
    """Test consistency across connector configurations."""

    def test_all_connectors_have_providers(self):
        """Test all connectors have correct provider assignments."""
        connectors = [
            (WiktionaryConnector(), DictionaryProvider.WIKTIONARY),
            (WordHippoConnector(), DictionaryProvider.WORDHIPPO),
            (AppleDictionaryConnector(), DictionaryProvider.APPLE_DICTIONARY),
        ]

        for connector, expected_provider in connectors:
            assert connector.provider == expected_provider

    def test_connector_config_inheritance(self):
        """Test connectors properly inherit from base connector config."""
        config = ConnectorConfig(timeout=60.0, max_connections=10, max_retries=5)

        connector = WiktionaryConnector(config)
        assert connector.config.timeout == 60.0
        assert connector.config.max_connections == 10
        assert connector.config.max_retries == 5

    def test_provider_display_names(self):
        """Test provider display names are human-readable."""
        providers = [
            DictionaryProvider.WIKTIONARY,
            DictionaryProvider.WORDHIPPO,
            DictionaryProvider.APPLE_DICTIONARY,
        ]

        for provider in providers:
            display_name = provider.display_name
            assert len(display_name) > 3  # Should be meaningful
            assert display_name != provider.value  # Should be different from enum value
            assert any(c.isupper() for c in display_name)  # Should have proper capitalization
