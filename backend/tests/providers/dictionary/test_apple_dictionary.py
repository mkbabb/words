"""Tests for AppleDictionary connector.

Tests cover platform compatibility, PyObjC integration, regex parsing, and full pipeline.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from floridify.models.dictionary import DictionaryProvider
from floridify.providers.dictionary.local.apple_dictionary import (
    AppleDictionaryConnector,
)
from floridify.providers.dictionary.models import DictionaryProviderEntry

# Sample raw definition from Apple Dictionary (realistic format)
SAMPLE_RAW_DEFINITION = """apple |ˈapəl|
noun
a round fruit with red or green skin and crisp flesh: "she picked an apple from the tree"
• the tree that bears apples, with hard pale timber: "an apple orchard"
ORIGIN Old English æppel, from Germanic origin."""

SAMPLE_RAW_DEFINITION_VERB = """run |rən|
verb
move at a speed faster than a walk: "he ran across the field"
• (of a machine) operate or function: "the engine runs smoothly"
• manage or organize: e.g., "she runs a small business"
ORIGIN Old English rinnan, of Germanic origin."""

SAMPLE_RAW_DEFINITION_MINIMAL = """test
noun
a procedure intended to establish quality"""


class TestAppleDictionaryPlatformCompatibility:
    """Tests for platform compatibility checks."""

    def test_init_on_darwin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test connector initialization on macOS (Darwin)."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")

        mock_dict_service = MagicMock()
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            connector = AppleDictionaryConnector()

            assert connector._platform_compatible is True
            assert connector.provider == DictionaryProvider.APPLE_DICTIONARY

    def test_init_on_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test connector initialization on Linux (not supported)."""
        monkeypatch.setattr("platform.system", lambda: "Linux")

        connector = AppleDictionaryConnector()

        assert connector._platform_compatible is False
        assert connector._dictionary_service is None

    def test_init_on_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test connector initialization on Windows (not supported)."""
        monkeypatch.setattr("platform.system", lambda: "Windows")

        connector = AppleDictionaryConnector()

        assert connector._platform_compatible is False
        assert connector._dictionary_service is None

    def test_is_available_when_platform_compatible(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _is_available() returns True on compatible platform."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")

        mock_dict_service = MagicMock()
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            connector = AppleDictionaryConnector()

            assert connector._is_available() is True

    def test_is_available_when_platform_incompatible(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _is_available() returns False on incompatible platform."""
        monkeypatch.setattr("platform.system", lambda: "Linux")

        connector = AppleDictionaryConnector()

        assert connector._is_available() is False


class TestAppleDictionaryImportHandling:
    """Tests for PyObjC import error handling."""

    def test_init_with_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test graceful handling when PyObjC cannot be imported."""
        monkeypatch.setattr("platform.system", lambda: "Linux")

        connector = AppleDictionaryConnector()

        assert connector._platform_compatible is False
        assert connector._dictionary_service is None
        assert connector._is_available() is False

        result = connector._lookup_definition("test")
        assert result is None


class TestAppleDictionaryTextCleaning:
    """Tests for text cleaning and regex operations."""

    @pytest.fixture
    def connector(self, monkeypatch: pytest.MonkeyPatch) -> AppleDictionaryConnector:
        """Create connector instance (platform-agnostic for testing)."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        mock_dict_service = MagicMock()
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            return AppleDictionaryConnector()

    def test_clean_definition_text_removes_pronunciation(
        self, connector: AppleDictionaryConnector
    ) -> None:
        """Test that pronunciation markers are removed."""
        text = "apple |ˈapəl| noun a round fruit"
        result = connector._clean_definition_text(text)

        assert "|ˈapəl|" not in result
        assert "apple" in result
        assert "noun" in result

    def test_clean_definition_text_normalizes_whitespace(
        self, connector: AppleDictionaryConnector
    ) -> None:
        """Test whitespace normalization."""
        text = "word   with    extra     spaces"
        result = connector._clean_definition_text(text)

        assert result == "word with extra spaces"

    def test_clean_definition_text_strips_result(self, connector: AppleDictionaryConnector) -> None:
        """Test that result is stripped."""
        text = "   leading and trailing   "
        result = connector._clean_definition_text(text)

        assert result == "leading and trailing"

    def test_extract_main_definition_with_noun(self, connector: AppleDictionaryConnector) -> None:
        """Test extracting definition after 'noun' marker."""
        text = "apple noun a round fruit with red skin"
        result = connector._extract_main_definition(text)

        assert result == "a round fruit with red skin"

    def test_extract_main_definition_with_verb(self, connector: AppleDictionaryConnector) -> None:
        """Test extracting definition after 'verb' marker."""
        text = "run verb move at a speed faster than a walk"
        result = connector._extract_main_definition(text)

        assert result == "move at a speed faster than a walk"

    def test_extract_main_definition_with_adjective(
        self, connector: AppleDictionaryConnector
    ) -> None:
        """Test extracting definition after 'adjective' marker."""
        text = "happy adjective feeling or showing pleasure"
        result = connector._extract_main_definition(text)

        assert result == "feeling or showing pleasure"

    def test_extract_main_definition_fallback(self, connector: AppleDictionaryConnector) -> None:
        """Test fallback when no POS marker found."""
        text = "some definition without markers"
        result = connector._extract_main_definition(text)

        assert result == "some definition without markers"


class TestAppleDictionaryExampleExtraction:
    """Tests for example extraction from definitions."""

    @pytest.fixture
    def connector(self, monkeypatch: pytest.MonkeyPatch) -> AppleDictionaryConnector:
        """Create connector instance."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        mock_dict_service = MagicMock()
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            return AppleDictionaryConnector()

    def test_extract_examples_with_quotes(self, connector: AppleDictionaryConnector) -> None:
        """Test extraction of quoted examples."""
        text = 'a round fruit: "she picked an apple from the tree"'
        examples = connector._extract_examples(text)

        assert len(examples) > 0
        assert "she picked an apple from the tree" in examples

    def test_extract_examples_with_eg(self, connector: AppleDictionaryConnector) -> None:
        """Test extraction of examples after 'e.g.'"""
        text = "manage or organize: e.g., she runs a small business."
        examples = connector._extract_examples(text)

        assert isinstance(examples, list)

    def test_extract_examples_filters_short_matches(
        self, connector: AppleDictionaryConnector
    ) -> None:
        """Test that very short matches are filtered out."""
        text = 'a fruit: "an" or "the"'
        examples = connector._extract_examples(text)

        short_examples = [ex for ex in examples if len(ex) <= 5]
        assert len(short_examples) == 0

    def test_extract_examples_empty_text(self, connector: AppleDictionaryConnector) -> None:
        """Test extraction from empty text."""
        examples = connector._extract_examples("")

        assert examples == []

    def test_remove_examples_from_definition_quotes(
        self, connector: AppleDictionaryConnector
    ) -> None:
        """Test removal of quoted examples."""
        text = 'a round fruit: "she picked an apple"'
        result = connector._remove_examples_from_definition(text)

        assert '"she picked an apple"' not in result
        assert "a round fruit" in result

    def test_remove_examples_from_definition_eg(self, connector: AppleDictionaryConnector) -> None:
        """Test removal of e.g. sections."""
        text = "manage or organize: e.g., she runs a business."
        result = connector._remove_examples_from_definition(text)

        assert "e.g." not in result


class TestAppleDictionaryPronunciationExtraction:
    """Tests for pronunciation and IPA extraction via _parse_definition_text."""

    @pytest.fixture
    def connector(self, monkeypatch: pytest.MonkeyPatch) -> AppleDictionaryConnector:
        """Create connector instance."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        mock_dict_service = MagicMock()
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            return AppleDictionaryConnector()

    def test_parse_extracts_pronunciation(self, connector: AppleDictionaryConnector) -> None:
        """Test extraction of IPA pronunciation via _parse_definition_text."""
        _, pronunciation, _ = connector._parse_definition_text("apple |ˈapəl| noun a fruit")
        assert pronunciation == "ˈapəl"

    def test_parse_no_pronunciation(self, connector: AppleDictionaryConnector) -> None:
        """Test when no IPA present."""
        _, pronunciation, _ = connector._parse_definition_text("test noun a procedure")
        assert pronunciation is None

    def test_ipa_to_phonetic_conversion(self, connector: AppleDictionaryConnector) -> None:
        """Test IPA to phonetic conversion."""
        ipa = "ˈæpəl"
        phonetic = connector._ipa_to_phonetic(ipa)

        assert "ˈ" not in phonetic
        assert "æ" not in phonetic
        assert "ə" not in phonetic

    def test_ipa_to_phonetic_with_various_symbols(
        self, connector: AppleDictionaryConnector
    ) -> None:
        """Test IPA conversion with various phonetic symbols."""
        test_cases = [
            ("æ", "a"),
            ("ə", "uh"),
            ("ɪ", "i"),
            ("ʊ", "u"),
            ("ˈ", ""),
            ("ˌ", ""),
        ]

        for ipa_char, expected in test_cases:
            result = connector._ipa_to_phonetic(ipa_char)
            assert result == expected


class TestAppleDictionaryDefinitionParsing:
    """Tests for definition parsing via _parse_definition_text."""

    @pytest.fixture
    def connector(self, monkeypatch: pytest.MonkeyPatch) -> AppleDictionaryConnector:
        """Create connector instance."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        mock_dict_service = MagicMock()
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            return AppleDictionaryConnector()

    def test_parse_noun(self, connector: AppleDictionaryConnector) -> None:
        """Test definition parsing for noun."""
        definitions, _, _ = connector._parse_definition_text(SAMPLE_RAW_DEFINITION)

        assert len(definitions) > 0
        assert definitions[0]["part_of_speech"] == "noun"
        assert len(definitions[0]["text"]) > 0

    def test_parse_verb(self, connector: AppleDictionaryConnector) -> None:
        """Test definition parsing for verb."""
        definitions, _, _ = connector._parse_definition_text(SAMPLE_RAW_DEFINITION_VERB)

        assert len(definitions) > 0
        assert definitions[0]["part_of_speech"] == "verb"

    def test_parse_includes_examples(self, connector: AppleDictionaryConnector) -> None:
        """Test that parsed definitions include examples."""
        definitions, _, _ = connector._parse_definition_text(SAMPLE_RAW_DEFINITION)

        assert len(definitions) > 0
        assert isinstance(definitions[0].get("examples"), list)

    def test_parse_empty_text(self, connector: AppleDictionaryConnector) -> None:
        """Test parsing empty text."""
        definitions, _, _ = connector._parse_definition_text("")

        assert definitions == []

    def test_parse_minimal(self, connector: AppleDictionaryConnector) -> None:
        """Test parsing minimal definition text."""
        definitions, _, _ = connector._parse_definition_text(SAMPLE_RAW_DEFINITION_MINIMAL)

        assert len(definitions) > 0
        assert definitions[0]["part_of_speech"] == "noun"


class TestAppleDictionaryEtymologyParsing:
    """Tests for etymology extraction via _parse_definition_text."""

    @pytest.fixture
    def connector(self, monkeypatch: pytest.MonkeyPatch) -> AppleDictionaryConnector:
        """Create connector instance."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        mock_dict_service = MagicMock()
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            return AppleDictionaryConnector()

    def test_parse_extracts_etymology(self, connector: AppleDictionaryConnector) -> None:
        """Test etymology extraction with ORIGIN marker."""
        _, _, etymology = connector._parse_definition_text(SAMPLE_RAW_DEFINITION)

        assert etymology is not None
        assert len(etymology) > 0

    def test_parse_no_etymology(self, connector: AppleDictionaryConnector) -> None:
        """Test when no ORIGIN marker present."""
        _, _, etymology = connector._parse_definition_text("test noun a procedure")

        assert etymology is None


class TestAppleDictionaryLookup:
    """Tests for the dictionary lookup functionality."""

    @pytest.fixture
    def connector(self, monkeypatch: pytest.MonkeyPatch) -> AppleDictionaryConnector:
        """Create connector instance."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        mock_dict_service = MagicMock(return_value="test definition")
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            connector = AppleDictionaryConnector()
            connector._dictionary_service = mock_dict_service
            return connector

    def test_lookup_definition_success(self, connector: AppleDictionaryConnector) -> None:
        """Test successful dictionary lookup."""
        result = connector._lookup_definition("apple")

        assert result is not None
        assert isinstance(result, str)

    def test_lookup_definition_not_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test lookup when service not available."""
        monkeypatch.setattr("platform.system", lambda: "Linux")
        connector = AppleDictionaryConnector()

        result = connector._lookup_definition("apple")

        assert result is None

    def test_lookup_definition_with_exception(self, connector: AppleDictionaryConnector) -> None:
        """Test lookup handles exceptions gracefully."""
        connector._dictionary_service = MagicMock(side_effect=Exception("Lookup failed"))

        result = connector._lookup_definition("apple")

        assert result is None


class TestAppleDictionaryFetchFromProvider:
    """Tests for the full fetch pipeline returning DictionaryProviderEntry."""

    @pytest.fixture
    def connector(self, monkeypatch: pytest.MonkeyPatch) -> AppleDictionaryConnector:
        """Create connector instance with mocked lookup."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        mock_dict_service = MagicMock()
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            connector = AppleDictionaryConnector()
            connector._lookup_definition = MagicMock(return_value=SAMPLE_RAW_DEFINITION)
            return connector

    @pytest.mark.asyncio
    async def test_fetch_from_provider_success(self, connector: AppleDictionaryConnector) -> None:
        """Test successful fetch from provider returns DictionaryProviderEntry."""
        result = await connector._fetch_from_provider("apple")

        assert result is not None
        assert isinstance(result, DictionaryProviderEntry)
        assert result.word == "apple"
        assert result.provider == DictionaryProvider.APPLE_DICTIONARY.value
        assert len(result.definitions) > 0
        assert result.definitions[0]["part_of_speech"] == "noun"

    @pytest.mark.asyncio
    async def test_fetch_from_provider_empty_word(
        self, connector: AppleDictionaryConnector
    ) -> None:
        """Test fetch with empty word."""
        result = await connector._fetch_from_provider("")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_not_found(self, connector: AppleDictionaryConnector) -> None:
        """Test fetch when word not found."""
        connector._lookup_definition = MagicMock(return_value=None)

        result = await connector._fetch_from_provider("nonexistentword")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_service_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fetch when service is unavailable."""
        monkeypatch.setattr("platform.system", lambda: "Linux")
        connector = AppleDictionaryConnector()

        result = await connector._fetch_from_provider("apple")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_with_state_tracker(
        self, connector: AppleDictionaryConnector
    ) -> None:
        """Test fetch with state tracker updates."""
        from floridify.core.state_tracker import StateTracker

        state_tracker = StateTracker()
        result = await connector._fetch_from_provider("apple", state_tracker=state_tracker)

        assert result is not None
        assert isinstance(result, DictionaryProviderEntry)

    @pytest.mark.asyncio
    async def test_fetch_includes_pronunciation(self, connector: AppleDictionaryConnector) -> None:
        """Test that pronunciation is extracted from raw definition."""
        result = await connector._fetch_from_provider("apple")

        assert result is not None
        assert result.pronunciation == "ˈapəl"

    @pytest.mark.asyncio
    async def test_fetch_includes_etymology(self, connector: AppleDictionaryConnector) -> None:
        """Test that etymology is extracted from raw definition."""
        result = await connector._fetch_from_provider("apple")

        assert result is not None
        assert result.etymology is not None
        assert "Old English" in result.etymology


class TestAppleDictionaryServiceInfo:
    """Tests for service information."""

    def test_get_service_info_darwin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test service info on Darwin platform."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        monkeypatch.setattr("platform.mac_ver", lambda: ("14.0", ("", "", ""), ""))

        mock_dict_service = MagicMock()
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            connector = AppleDictionaryConnector()

            info = connector.get_service_info()

            assert info["provider_name"] == DictionaryProvider.APPLE_DICTIONARY.value
            assert info["platform"] == "Darwin"
            assert info["platform_version"] == "14.0"
            assert info["is_available"] is True

    def test_get_service_info_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test service info on Linux platform."""
        monkeypatch.setattr("platform.system", lambda: "Linux")

        connector = AppleDictionaryConnector()
        info = connector.get_service_info()

        assert info["platform"] == "Linux"
        assert info["is_available"] is False


class TestAppleDictionaryIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.asyncio
    async def test_full_pipeline_darwin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete pipeline on Darwin returns DictionaryProviderEntry."""
        monkeypatch.setattr("platform.system", lambda: "Darwin")

        mock_dict_service = MagicMock(return_value=SAMPLE_RAW_DEFINITION)
        with patch.dict(
            "sys.modules", {"CoreServices": MagicMock(DCSCopyTextDefinition=mock_dict_service)}
        ):
            connector = AppleDictionaryConnector()
            connector._dictionary_service = mock_dict_service

            result = await connector._fetch_from_provider("apple")

            assert result is not None
            assert isinstance(result, DictionaryProviderEntry)
            assert result.word == "apple"
            assert len(result.definitions) > 0
            assert result.pronunciation is not None
            assert result.etymology is not None
            assert result.raw_data is not None

    @pytest.mark.asyncio
    async def test_full_pipeline_non_darwin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete pipeline on non-Darwin platform."""
        monkeypatch.setattr("platform.system", lambda: "Linux")

        connector = AppleDictionaryConnector()
        result = await connector._fetch_from_provider("apple")

        assert result is None
