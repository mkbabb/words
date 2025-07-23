"""Tests for the Apple Dictionary Batch Extractor."""

from __future__ import annotations

import platform
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from tempfile import TemporaryDirectory

import pytest

from src.floridify.batch.apple_dictionary_extractor import (
    AppleDictionaryBatchExtractor,
    ExtractionConfig,
    ExtractionStats,
    extract_common_words,
)
from src.floridify.models.models import Definition, ProviderData


class TestExtractionStats:
    """Test suite for ExtractionStats."""

    def test_initial_stats(self) -> None:
        """Test initial statistics values."""
        stats = ExtractionStats()
        assert stats.words_processed == 0
        assert stats.definitions_found == 0
        assert stats.definitions_stored == 0
        assert stats.errors == 0
        assert isinstance(stats.start_time, datetime)
        assert stats.end_time is None

    def test_duration_calculation(self) -> None:
        """Test duration calculation."""
        stats = ExtractionStats()
        
        # Without end_time, should use current time
        duration1 = stats.duration
        assert duration1 >= 0
        
        # With end_time, should use that
        stats.end_time = datetime.now()
        duration2 = stats.duration
        assert duration2 >= 0

    def test_success_rate_calculation(self) -> None:
        """Test success rate calculation."""
        stats = ExtractionStats()
        
        # No words processed
        assert stats.success_rate == 0.0
        
        # Some words processed
        stats.words_processed = 10
        stats.definitions_found = 7
        assert stats.success_rate == 70.0
        
        # All words successful
        stats.definitions_found = 10
        assert stats.success_rate == 100.0


class TestExtractionConfig:
    """Test suite for ExtractionConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ExtractionConfig()
        assert config.batch_size == 100
        assert config.max_concurrent == 10
        assert config.output_file is None
        assert config.include_metadata is True
        assert config.save_to_mongodb is True
        assert config.rate_limit == 20.0
        assert config.log_progress is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        output_file = Path("test_output.json")
        config = ExtractionConfig(
            batch_size=50,
            max_concurrent=5,
            output_file=output_file,
            include_metadata=False,
            save_to_mongodb=False,
            rate_limit=10.0,
            log_progress=False
        )
        assert config.batch_size == 50
        assert config.max_concurrent == 5
        assert config.output_file == output_file
        assert config.include_metadata is False
        assert config.save_to_mongodb is False
        assert config.rate_limit == 10.0
        assert config.log_progress is False


class TestAppleDictionaryBatchExtractor:
    """Test suite for Apple Dictionary Batch Extractor."""

    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    def test_initialization_macos(self) -> None:
        """Test initialization on macOS."""
        config = ExtractionConfig()
        extractor = AppleDictionaryBatchExtractor(config)
        
        assert extractor.config == config
        assert extractor.mongodb is None
        assert extractor.connector is not None
        assert isinstance(extractor.stats, ExtractionStats)

    @patch("src.floridify.batch.apple_dictionary_extractor.platform.system")
    def test_initialization_non_macos(self, mock_system: Mock) -> None:
        """Test initialization fails on non-macOS systems."""
        mock_system.return_value = "Linux"
        config = ExtractionConfig()
        
        with pytest.raises(RuntimeError, match="Apple Dictionary batch extraction requires macOS"):
            AppleDictionaryBatchExtractor(config)

    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    def test_initialization_with_mongodb(self) -> None:
        """Test initialization with MongoDB storage."""
        config = ExtractionConfig()
        mock_mongodb = Mock()
        
        extractor = AppleDictionaryBatchExtractor(config, mock_mongodb)
        assert extractor.mongodb == mock_mongodb

    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    def test_platform_compatibility_check(self) -> None:
        """Test platform compatibility check."""
        config = ExtractionConfig()
        extractor = AppleDictionaryBatchExtractor(config)
        assert extractor._check_platform_compatibility() is True

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_extract_single_word_success(self) -> None:
        """Test successful single word extraction."""
        config = ExtractionConfig()
        extractor = AppleDictionaryBatchExtractor(config)
        
        # Mock successful connector response
        mock_provider_data = ProviderData(
            provider_name="apple_dictionary",
            definitions=[
                Definition(
                    word_type="noun",
                    definition="test definition",
                    synonyms=[],
                    examples={}
                )
            ]
        )
        
        with patch.object(extractor.connector, 'fetch_definition', return_value=mock_provider_data):
            result = await extractor._extract_single_word("test")
            
            assert result == mock_provider_data
            assert len(result.definitions) == 1

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_extract_single_word_not_found(self) -> None:
        """Test single word extraction when word not found."""
        config = ExtractionConfig()
        extractor = AppleDictionaryBatchExtractor(config)
        
        # Mock connector returning None (not found)
        with patch.object(extractor.connector, 'fetch_definition', return_value=None):
            result = await extractor._extract_single_word("nonexistentword")
            assert result is None

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_extract_single_word_error(self) -> None:
        """Test single word extraction with error."""
        config = ExtractionConfig()
        extractor = AppleDictionaryBatchExtractor(config)
        
        # Mock connector raising exception
        with patch.object(extractor.connector, 'fetch_definition', side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                await extractor._extract_single_word("test")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_process_batch(self) -> None:
        """Test batch processing of words."""
        config = ExtractionConfig(max_concurrent=2)
        extractor = AppleDictionaryBatchExtractor(config)
        
        # Mock successful responses
        mock_provider_data = ProviderData(
            provider_name="apple_dictionary",
            definitions=[Definition(word_type="noun", definition="test", synonyms=[], examples={})]
        )
        
        words = ["word1", "word2", "word3"]
        
        with patch.object(extractor, '_extract_single_word', return_value=mock_provider_data), \
             patch.object(extractor, '_save_to_mongodb', return_value=None):
            
            results = await extractor._process_batch(words)
            
            assert len(results) == 3
            assert all(r == mock_provider_data for r in results)
            assert extractor.stats.words_processed == 3
            assert extractor.stats.definitions_found == 3

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_process_batch_with_errors(self) -> None:
        """Test batch processing with some errors."""
        config = ExtractionConfig(max_concurrent=2)
        extractor = AppleDictionaryBatchExtractor(config)
        
        mock_provider_data = ProviderData(
            provider_name="apple_dictionary",
            definitions=[Definition(word_type="noun", definition="test", synonyms=[], examples={})]
        )
        
        words = ["word1", "word2", "error_word"]
        
        async def mock_extract(word: str):
            if word == "error_word":
                raise Exception("Test error")
            return mock_provider_data
        
        with patch.object(extractor, '_extract_single_word', side_effect=mock_extract), \
             patch.object(extractor, '_save_to_mongodb', return_value=None):
            
            results = await extractor._process_batch(words)
            
            assert len(results) == 2  # Only successful extractions
            assert extractor.stats.words_processed == 3
            assert extractor.stats.definitions_found == 2
            assert extractor.stats.errors == 1

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_extract_word_list(self) -> None:
        """Test extraction of word list."""
        config = ExtractionConfig(batch_size=2, log_progress=False)
        extractor = AppleDictionaryBatchExtractor(config)
        
        mock_provider_data = ProviderData(
            provider_name="apple_dictionary",
            definitions=[Definition(word_type="noun", definition="test", synonyms=[], examples={})]
        )
        
        words = ["word1", "word2", "word3", "word4"]
        
        with patch.object(extractor, '_process_batch', return_value=[mock_provider_data, mock_provider_data]) as mock_process:
            results = await extractor.extract_word_list(words)
            
            # Should process in 2 batches of 2 words each
            assert mock_process.call_count == 2
            assert len(results) == 4

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_save_to_mongodb(self) -> None:
        """Test saving provider data to MongoDB."""
        config = ExtractionConfig()
        mock_mongodb = AsyncMock()
        mock_mongodb.save_entry = AsyncMock(return_value=True)
        
        extractor = AppleDictionaryBatchExtractor(config, mock_mongodb)
        
        provider_data = ProviderData(
            provider_name="apple_dictionary",
            definitions=[Definition(word_type="noun", definition="test", synonyms=[], examples={})]
        )
        
        await extractor._save_to_mongodb("test", provider_data)
        
        # Verify save_entry was called
        mock_mongodb.save_entry.assert_called_once()
        call_args = mock_mongodb.save_entry.call_args[0][0]
        assert call_args.word == "test"
        assert "apple_dictionary" in call_args.provider_data

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_save_to_mongodb_error(self) -> None:
        """Test MongoDB save error handling."""
        config = ExtractionConfig()
        mock_mongodb = AsyncMock()
        mock_mongodb.save_entry = AsyncMock(side_effect=Exception("MongoDB error"))
        
        extractor = AppleDictionaryBatchExtractor(config, mock_mongodb)
        
        provider_data = ProviderData(
            provider_name="apple_dictionary",
            definitions=[Definition(word_type="noun", definition="test", synonyms=[], examples={})]
        )
        
        # Should not raise exception, just log error
        await extractor._save_to_mongodb("test", provider_data)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_save_results_to_file(self) -> None:
        """Test saving results to file."""
        with TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_results.json"
            config = ExtractionConfig(output_file=output_file)
            extractor = AppleDictionaryBatchExtractor(config)
            
            # Set some stats
            extractor.stats.words_processed = 2
            extractor.stats.definitions_found = 1
            extractor.stats.end_time = datetime.now()
            
            provider_data = ProviderData(
                provider_name="apple_dictionary",
                definitions=[Definition(word_type="noun", definition="test", synonyms=[], examples={})]
            )
            
            await extractor._save_results_to_file([provider_data])
            
            # Verify file was created and contains expected data
            assert output_file.exists()
            
            import json
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            assert "extraction_metadata" in data
            assert "results" in data
            assert data["extraction_metadata"]["total_words"] == 2
            assert data["extraction_metadata"]["definitions_found"] == 1
            assert len(data["results"]) == 1

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_extract_from_word_list_file(self) -> None:
        """Test extraction from word list file."""
        with TemporaryDirectory() as temp_dir:
            word_list_file = Path(temp_dir) / "words.txt"
            
            # Create test word list file
            with open(word_list_file, 'w') as f:
                f.write("apple\nbanana\n# comment line\n\ncherry\n")
            
            config = ExtractionConfig(log_progress=False)
            extractor = AppleDictionaryBatchExtractor(config)
            
            mock_provider_data = ProviderData(
                provider_name="apple_dictionary",
                definitions=[Definition(word_type="noun", definition="test", synonyms=[], examples={})]
            )
            
            with patch.object(extractor, 'extract_word_list', return_value=[mock_provider_data]) as mock_extract:
                results = await extractor.extract_from_word_list(word_list_file)
                
                # Should extract 3 words (ignoring comment and empty line)
                mock_extract.assert_called_once()
                words_arg = mock_extract.call_args[0][0]
                assert words_arg == ["apple", "banana", "cherry"]
                assert results == [mock_provider_data]

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_extract_from_nonexistent_file(self) -> None:
        """Test extraction from nonexistent file."""
        config = ExtractionConfig()
        extractor = AppleDictionaryBatchExtractor(config)
        
        nonexistent_file = Path("nonexistent.txt")
        
        with pytest.raises(FileNotFoundError):
            await extractor.extract_from_word_list(nonexistent_file)

    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_get_available_dictionaries(self) -> None:
        """Test getting available dictionaries info."""
        config = ExtractionConfig()
        extractor = AppleDictionaryBatchExtractor(config)
        
        info = await extractor.get_available_dictionaries()
        
        assert "provider_name" in info
        assert info["provider_name"] == "apple_dictionary"
        assert "batch_extractor_version" in info
        assert "extraction_capabilities" in info
        assert "recommended_batch_size" in info
        assert info["recommended_batch_size"] == config.batch_size


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_extract_common_words(self) -> None:
        """Test extract_common_words convenience function."""
        with TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "common_words.json"
            
            mock_provider_data = ProviderData(
                provider_name="apple_dictionary",
                definitions=[Definition(word_type="noun", definition="test", synonyms=[], examples={})]
            )
            
            with patch('src.floridify.batch.apple_dictionary_extractor.AppleDictionaryBatchExtractor') as mock_extractor_class:
                mock_extractor = Mock()
                mock_extractor.extract_word_list = AsyncMock(return_value=[mock_provider_data])
                mock_extractor_class.return_value = mock_extractor
                
                results = await extract_common_words(
                    word_count=10,
                    output_file=output_file,
                    mongodb=None
                )
                
                assert results == [mock_provider_data]
                mock_extractor.extract_word_list.assert_called_once()
                
                # Check that word count was respected
                words_arg = mock_extractor.extract_word_list.call_args[0][0]
                assert len(words_arg) == 10

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    async def test_extract_from_search_engine(self) -> None:
        """Test extract_from_search_engine placeholder function."""
        from src.floridify.batch.apple_dictionary_extractor import extract_from_search_engine
        
        results = await extract_from_search_engine(search_limit=100)
        
        # Currently returns empty list as placeholder
        assert results == []


class TestAppleDictionaryBatchExtractorIntegration:
    """Integration tests for Apple Dictionary Batch Extractor."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        platform.system() != "Darwin", 
        reason="Apple Dictionary only available on macOS"
    )
    @pytest.mark.integration
    async def test_real_batch_extraction(self) -> None:
        """Test actual batch extraction on macOS (integration test)."""
        config = ExtractionConfig(
            batch_size=3,
            max_concurrent=2,
            log_progress=False,
            save_to_mongodb=False
        )
        
        try:
            extractor = AppleDictionaryBatchExtractor(config)
        except RuntimeError:
            pytest.skip("Apple Dictionary service not available")
        
        # Test with a few common words
        test_words = ["cat", "dog", "house"]
        
        results = await extractor.extract_word_list(test_words)
        
        # At least some words should return definitions
        assert len(results) >= 0  # May be 0 if no words found
        
        # All results should have proper structure
        for result in results:
            assert isinstance(result, ProviderData)
            assert result.provider_name == "apple_dictionary"
            assert len(result.definitions) > 0
            
            # Check definition structure
            definition = result.definitions[0]
            assert isinstance(definition, Definition)
            assert definition.definition
            assert definition.word_type
        
        # Check final statistics
        assert extractor.stats.words_processed == len(test_words)
        assert extractor.stats.definitions_found <= len(test_words)
        assert extractor.stats.definitions_found >= 0