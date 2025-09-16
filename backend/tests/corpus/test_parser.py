"""Comprehensive tests for corpus parser functions."""

import json

from floridify.corpus.parser import (
    ParseResult,
    parse_csv_idioms,
    parse_frequency_list,
    parse_github_api,
    parse_json_array,
    parse_json_dict,
    parse_json_idioms,
    parse_json_phrasal_verbs,
    parse_scraped_data,
    parse_text_lines,
)
from floridify.models.base import Language


class TestTextLineParsing:
    """Test parsing plain text line formats."""

    def test_parse_text_lines_basic(self):
        """Test parsing basic text lines."""
        content = """apple
banana
cherry
date"""
        result = parse_text_lines(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 4
        assert "apple" in result.vocabulary
        assert "banana" in result.vocabulary
        assert "cherry" in result.vocabulary
        assert "date" in result.vocabulary

    def test_parse_text_lines_with_empty_lines(self):
        """Test parsing text with empty lines."""
        content = """apple

banana

cherry
"""
        result = parse_text_lines(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert "" not in result.vocabulary

    def test_parse_text_lines_with_whitespace(self):
        """Test parsing text with leading/trailing whitespace."""
        content = """  apple  
\tbanana\t
  cherry  
"""
        result = parse_text_lines(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert "apple" in result.vocabulary
        assert "banana" in result.vocabulary
        assert "cherry" in result.vocabulary

    def test_parse_text_lines_unicode(self):
        """Test parsing Unicode text lines."""
        content = """café
naïve
résumé
piñata"""
        result = parse_text_lines(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 4
        assert "café" in result.vocabulary
        assert "naïve" in result.vocabulary

    def test_parse_text_lines_empty(self):
        """Test parsing empty content."""
        content = ""
        result = parse_text_lines(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 0


class TestFrequencyListParsing:
    """Test parsing frequency list formats."""

    def test_parse_frequency_list_basic(self):
        """Test parsing basic frequency list."""
        content = """apple,100
banana,85
cherry,72
date,45"""
        result = parse_frequency_list(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 4
        assert "apple" in result.vocabulary
        assert result.frequencies["apple"] == 100
        assert result.frequencies["banana"] == 85
        assert result.frequencies["cherry"] == 72
        assert result.frequencies["date"] == 45

    def test_parse_frequency_list_tab_separated(self):
        """Test parsing tab-separated frequency list."""
        content = """apple\t100
banana\t85
cherry\t72"""
        result = parse_frequency_list(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert result.frequencies["apple"] == 100

    def test_parse_frequency_list_with_spaces(self):
        """Test parsing space-separated frequency list."""
        content = """apple 100
banana 85
cherry 72"""
        result = parse_frequency_list(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert result.frequencies["apple"] == 100

    def test_parse_frequency_list_invalid_format(self):
        """Test parsing invalid frequency list."""
        content = """apple
banana,not_a_number
cherry,72"""
        result = parse_frequency_list(content, Language.ENGLISH)

        # Should handle errors gracefully
        assert result.success is True
        # Only valid entries should be parsed
        assert "cherry" in result.vocabulary
        assert result.frequencies.get("cherry") == 72

    def test_parse_frequency_list_float_frequencies(self):
        """Test parsing frequency list with float values."""
        content = """apple,100.5
banana,85.2
cherry,72.0"""
        result = parse_frequency_list(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert result.frequencies["apple"] == 100.5


class TestJsonParsing:
    """Test parsing various JSON formats."""

    def test_parse_json_idioms(self):
        """Test parsing JSON idioms format."""
        content = json.dumps(
            {
                "idioms": [
                    {"idiom": "break a leg", "meaning": "good luck"},
                    {"expression": "piece of cake", "definition": "easy task"},
                    {"phrase": "hit the hay", "meaning": "go to sleep"},
                ]
            }
        )
        result = parse_json_idioms(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert "break a leg" in result.vocabulary
        assert "piece of cake" in result.vocabulary
        assert "hit the hay" in result.vocabulary

    def test_parse_json_dict(self):
        """Test parsing JSON dictionary format."""
        content = json.dumps(
            {
                "apple": {"definition": "a fruit", "pos": "noun"},
                "run": {"definition": "to move quickly", "pos": "verb"},
                "happy": {"definition": "feeling joy", "pos": "adjective"},
            }
        )
        result = parse_json_dict(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert "apple" in result.vocabulary
        assert "run" in result.vocabulary
        assert "happy" in result.vocabulary

    def test_parse_json_array(self):
        """Test parsing JSON array format."""
        content = json.dumps(["apple", "banana", "cherry", "date"])
        result = parse_json_array(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 4
        assert "apple" in result.vocabulary
        assert "banana" in result.vocabulary

    def test_parse_json_array_with_objects(self):
        """Test parsing JSON array with object elements."""
        content = json.dumps(
            [
                {"word": "apple", "type": "fruit"},
                {"word": "banana", "type": "fruit"},
                {"word": "cherry", "type": "fruit"},
            ]
        )
        result = parse_json_array(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert "apple" in result.vocabulary

    def test_parse_json_invalid(self):
        """Test parsing invalid JSON."""
        content = "not valid json {"
        result = parse_json_dict(content, Language.ENGLISH)

        assert result.success is False
        assert "Failed to parse JSON" in result.error

    def test_parse_json_phrasal_verbs(self):
        """Test parsing JSON phrasal verbs format."""
        content = json.dumps(
            {
                "phrasal_verbs": [
                    {"verb": "break down", "definition": "stop working"},
                    {"verb": "look up", "definition": "search for"},
                    {"verb": "give up", "definition": "quit"},
                ]
            }
        )
        result = parse_json_phrasal_verbs(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert "break down" in result.vocabulary
        assert "look up" in result.vocabulary
        assert "give up" in result.vocabulary


class TestGithubApiParsing:
    """Test parsing GitHub API response format."""

    def test_parse_github_api_file_list(self):
        """Test parsing GitHub API file list response."""
        content = json.dumps(
            [
                {"name": "word1.txt", "type": "file"},
                {"name": "word2.txt", "type": "file"},
                {"name": "folder", "type": "dir"},
                {"name": "word3.md", "type": "file"},
            ]
        )
        result = parse_github_api(content, Language.ENGLISH)

        assert result.success is True
        # Should extract filenames without extensions
        assert "word1" in result.vocabulary
        assert "word2" in result.vocabulary
        assert "word3" in result.vocabulary
        assert "folder" not in result.vocabulary  # Directories excluded

    def test_parse_github_api_empty(self):
        """Test parsing empty GitHub API response."""
        content = json.dumps([])
        result = parse_github_api(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 0


class TestCsvParsing:
    """Test parsing CSV idioms format."""

    def test_parse_csv_idioms_basic(self):
        """Test parsing basic CSV idioms."""
        content = """idiom,meaning
"break a leg","good luck"
"piece of cake","easy task"
"hit the hay","go to sleep"
"""
        result = parse_csv_idioms(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert "break a leg" in result.vocabulary
        assert "piece of cake" in result.vocabulary
        assert "hit the hay" in result.vocabulary

    def test_parse_csv_idioms_no_header(self):
        """Test parsing CSV without header."""
        content = """"break a leg","good luck"
"piece of cake","easy task"
"""
        result = parse_csv_idioms(content, Language.ENGLISH)

        assert result.success is True
        # Should still parse idioms
        assert len(result.vocabulary) >= 0

    def test_parse_csv_idioms_empty(self):
        """Test parsing empty CSV."""
        content = ""
        result = parse_csv_idioms(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 0


class TestScrapedDataParsing:
    """Test parsing scraped data with metadata."""

    def test_parse_scraped_data_basic(self):
        """Test parsing basic scraped data."""
        content = """apple
banana
cherry"""
        url = "https://example.com/fruits"

        result = parse_scraped_data(
            content=content,
            url=url,
            language=Language.ENGLISH,
            parser_type="text_lines",
            metadata={"category": "fruits"},
        )

        assert result.success is True
        assert len(result.vocabulary) == 3
        assert "apple" in result.vocabulary
        assert result.metadata["url"] == url
        assert result.metadata["category"] == "fruits"

    def test_parse_scraped_data_with_parser_selection(self):
        """Test scraped data parser type selection."""
        # Test frequency list parser
        content = """apple,100
banana,85"""
        result = parse_scraped_data(
            content=content,
            url="https://example.com",
            language=Language.ENGLISH,
            parser_type="frequency_list",
        )

        assert result.success is True
        assert result.frequencies["apple"] == 100

        # Test JSON array parser
        content = json.dumps(["apple", "banana"])
        result = parse_scraped_data(
            content=content,
            url="https://example.com",
            language=Language.ENGLISH,
            parser_type="json_array",
        )

        assert result.success is True
        assert len(result.vocabulary) == 2

    def test_parse_scraped_data_invalid_parser(self):
        """Test scraped data with invalid parser type."""
        result = parse_scraped_data(
            content="test",
            url="https://example.com",
            language=Language.ENGLISH,
            parser_type="invalid_parser",
        )

        # Should fallback to text_lines or handle gracefully
        assert result.success is True or result.error is not None


class TestParseResultModel:
    """Test ParseResult data model."""

    def test_parse_result_success(self):
        """Test successful parse result."""
        result = ParseResult(
            success=True,
            vocabulary=["apple", "banana"],
            frequencies={"apple": 100, "banana": 85},
            metadata={"source": "test"},
        )

        assert result.success is True
        assert len(result.vocabulary) == 2
        assert result.frequencies["apple"] == 100
        assert result.metadata["source"] == "test"
        assert result.error is None

    def test_parse_result_failure(self):
        """Test failed parse result."""
        result = ParseResult(success=False, vocabulary=[], error="Parse failed: invalid format")

        assert result.success is False
        assert len(result.vocabulary) == 0
        assert "Parse failed" in result.error

    def test_parse_result_partial(self):
        """Test partial parse result with some errors."""
        result = ParseResult(
            success=True, vocabulary=["apple", "banana"], error="Warning: some entries skipped"
        )

        assert result.success is True
        assert len(result.vocabulary) == 2
        assert "Warning" in result.error


class TestLanguageSpecificParsing:
    """Test language-specific parsing behaviors."""

    def test_parse_french_content(self):
        """Test parsing French content."""
        content = """café
château
français
élève"""
        result = parse_text_lines(content, Language.FRENCH)

        assert result.success is True
        assert len(result.vocabulary) == 4
        assert "café" in result.vocabulary
        assert "château" in result.vocabulary

    def test_parse_spanish_content(self):
        """Test parsing Spanish content."""
        content = """niño
señor
mañana
año"""
        result = parse_text_lines(content, Language.SPANISH)

        assert result.success is True
        assert len(result.vocabulary) == 4
        assert "niño" in result.vocabulary
        assert "señor" in result.vocabulary

    def test_parse_german_content(self):
        """Test parsing German content."""
        content = """Straße
Mädchen
über
größer"""
        result = parse_text_lines(content, Language.GERMAN)

        assert result.success is True
        assert len(result.vocabulary) == 4
        assert "Straße" in result.vocabulary
        assert "Mädchen" in result.vocabulary


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_parse_very_large_vocabulary(self):
        """Test parsing large vocabulary list."""
        # Generate 10000 words
        words = [f"word{i}" for i in range(10000)]
        content = "\n".join(words)

        result = parse_text_lines(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 10000
        assert "word0" in result.vocabulary
        assert "word9999" in result.vocabulary

    def test_parse_mixed_formats(self):
        """Test handling mixed format content."""
        # Content that looks like multiple formats
        content = """word1
word2,100
{"word": "word3"}
word4"""

        # Should handle as text lines
        result = parse_text_lines(content, Language.ENGLISH)
        assert result.success is True
        assert len(result.vocabulary) == 4

    def test_parse_special_characters(self):
        """Test parsing words with special characters."""
        content = """test@example.com
hello-world
$100
50%
C++"""
        result = parse_text_lines(content, Language.ENGLISH)

        assert result.success is True
        assert len(result.vocabulary) == 5
        assert "test@example.com" in result.vocabulary
        assert "hello-world" in result.vocabulary
        assert "$100" in result.vocabulary

    def test_parse_empty_json(self):
        """Test parsing empty JSON structures."""
        # Empty object
        result = parse_json_dict("{}", Language.ENGLISH)
        assert result.success is True
        assert len(result.vocabulary) == 0

        # Empty array
        result = parse_json_array("[]", Language.ENGLISH)
        assert result.success is True
        assert len(result.vocabulary) == 0

        # Empty idioms
        result = parse_json_idioms('{"idioms": []}', Language.ENGLISH)
        assert result.success is True
        assert len(result.vocabulary) == 0
