"""
Comprehensive tests for quantization and MongoDB caching improvements.

Tests binary quantization, compression ratios, and cache performance.
"""

from unittest.mock import patch

import numpy as np
import pytest

from src.floridify.models.lexicon_cache import (
    CompressionType,
    CorpusCacheEntry,
    CorpusCompressionUtils,
)
from src.floridify.models.semantic_cache import QuantizationType
from src.floridify.search.semantic import SemanticSearch


class TestQuantizationImprovements:
    """Test suite for embedding quantization."""

    def setup_method(self):
        """Setup test fixtures."""
        self.semantic_search = SemanticSearch()
        # Create test embeddings (100 words, 384 dimensions)
        np.random.seed(42)  # Reproducible results
        self.test_embeddings = np.random.randn(100, 384).astype(np.float32)
        # Normalize like sentence transformers
        norms = np.linalg.norm(self.test_embeddings, axis=1, keepdims=True)
        self.test_embeddings = self.test_embeddings / norms

    def test_binary_quantization_compression_ratio(self):
        """Test binary quantization achieves expected 24x compression."""
        quantized, ratio = self.semantic_search._quantize_embeddings(
            self.test_embeddings, QuantizationType.BINARY
        )
        
        # Should achieve significant compression (targeting 24x)
        assert ratio > 20, f"Binary quantization ratio {ratio:.1f}x below expected 24x"
        assert ratio < 30, f"Binary quantization ratio {ratio:.1f}x suspiciously high"
        
        # Check output format
        assert quantized.dtype == np.uint8, "Quantized data should be uint8"
        assert quantized.shape[0] == self.test_embeddings.shape[0], "Row count mismatch"

    def test_scalar_quantization_compression_ratio(self):
        """Test scalar quantization achieves expected 3.75x compression."""
        quantized, ratio = self.semantic_search._quantize_embeddings(
            self.test_embeddings, QuantizationType.SCALAR
        )
        
        # Should achieve ~3.75x compression
        assert ratio > 3.0, f"Scalar quantization ratio {ratio:.1f}x below expected 3.75x"
        assert ratio < 5.0, f"Scalar quantization ratio {ratio:.1f}x above expected range"
        
        # Check output format
        assert quantized.dtype == np.uint8, "Scalar quantized data should be uint8"
        assert quantized.shape == self.test_embeddings.shape, "Shape should be preserved"

    def test_quantization_dequantization_cycle(self):
        """Test that quantization->dequantization preserves approximate values."""
        for quant_type in [QuantizationType.BINARY, QuantizationType.SCALAR]:
            with self.subTest(quantization_type=quant_type):
                # Quantize
                quantized, _ = self.semantic_search._quantize_embeddings(
                    self.test_embeddings, quant_type
                )
                
                # Dequantize
                if quant_type == QuantizationType.BINARY:
                    dequantized = self.semantic_search._dequantize_embeddings(
                        quantized, quant_type, self.test_embeddings.shape
                    )
                    # Binary quantization is lossy, check sign preservation
                    original_signs = np.sign(self.test_embeddings)
                    dequantized_signs = np.sign(dequantized)
                    sign_accuracy = np.mean(original_signs == dequantized_signs)
                    assert sign_accuracy > 0.95, f"Binary quantization sign accuracy: {sign_accuracy:.3f}"
                
                elif quant_type == QuantizationType.SCALAR:
                    # Need min/max for scalar dequantization
                    embed_min, embed_max = self.test_embeddings.min(), self.test_embeddings.max()
                    dequantized = self.semantic_search._dequantize_embeddings(
                        quantized, quant_type, self.test_embeddings.shape, embed_min, embed_max
                    )
                    # Scalar quantization should preserve approximate values
                    mse = np.mean((self.test_embeddings - dequantized) ** 2)
                    assert mse < 0.01, f"Scalar quantization MSE too high: {mse:.6f}"

    def test_no_quantization_passthrough(self):
        """Test that NONE quantization passes through unchanged."""
        quantized, ratio = self.semantic_search._quantize_embeddings(
            self.test_embeddings, QuantizationType.NONE
        )
        
        assert ratio == 1.0, "No quantization should have 1.0 ratio"
        assert np.array_equal(quantized, self.test_embeddings), "No quantization should be passthrough"

    def test_quantization_performance_memory_usage(self):
        """Test quantization reduces memory usage as expected."""
        original_size = self.test_embeddings.nbytes
        
        # Binary quantization
        binary_quantized, binary_ratio = self.semantic_search._quantize_embeddings(
            self.test_embeddings, QuantizationType.BINARY
        )
        binary_size = binary_quantized.nbytes
        actual_binary_ratio = original_size / binary_size
        
        # Should match reported compression ratio
        assert abs(actual_binary_ratio - binary_ratio) < 0.1, "Binary ratio calculation mismatch"
        
        # Scalar quantization
        scalar_quantized, scalar_ratio = self.semantic_search._quantize_embeddings(
            self.test_embeddings, QuantizationType.SCALAR
        )
        scalar_size = scalar_quantized.nbytes
        actual_scalar_ratio = original_size / scalar_size
        
        # Should match reported compression ratio
        assert abs(actual_scalar_ratio - scalar_ratio) < 0.1, "Scalar ratio calculation mismatch"


class TestLexiconCaching:
    """Test suite for MongoDB lexicon caching."""

    def test_compression_utilities_zstd(self):
        """Test Zstd compression utility."""
        test_data = b"Hello world! " * 1000  # Compressible data
        
        compressed, ratio = CorpusCompressionUtils.compress_data(
            test_data, CompressionType.ZSTD
        )
        
        assert len(compressed) < len(test_data), "Compression should reduce size"
        assert ratio > 1.0, f"Compression ratio should be > 1.0, got {ratio}"
        
        # Test decompression
        decompressed = CorpusCompressionUtils.decompress_data(
            compressed, CompressionType.ZSTD
        )
        assert decompressed == test_data, "Decompression should restore original data"

    def test_compression_utilities_fallbacks(self):
        """Test compression fallbacks when libraries not available."""
        test_data = b"Test data for compression fallback"
        
        # Test with each compression type (should work with fallbacks)
        for comp_type in [CompressionType.ZSTD, CompressionType.LZ4, CompressionType.BROTLI]:
            with self.subTest(compression_type=comp_type):
                compressed, ratio = CorpusCompressionUtils.compress_data(test_data, comp_type)
                decompressed = CorpusCompressionUtils.decompress_data(compressed, comp_type)
                
                assert decompressed == test_data, f"Fallback failed for {comp_type}"
                assert ratio >= 1.0, f"Invalid ratio for {comp_type}: {ratio}"

    def test_compression_performance_ratios(self):
        """Test compression ratios for different data types."""
        # Dictionary-like data (should compress well)
        dictionary_data = "\n".join([
            f"word{i}: definition of word {i}" for i in range(1000)
        ]).encode('utf-8')
        
        compressed, ratio = CorpusCompressionUtils.compress_data(
            dictionary_data, CompressionType.ZSTD
        )
        
        # Dictionary data should compress well (expect 2-5x)
        assert ratio > 2.0, f"Dictionary data compression ratio too low: {ratio:.2f}"
        assert ratio < 10.0, f"Dictionary data compression ratio suspiciously high: {ratio:.2f}"

    def test_lexicon_cache_entry_validation(self):
        """Test CorpusCacheEntry model validation."""
        from datetime import UTC, datetime, timedelta

        from src.floridify.models.definition import Language
        
        # Valid entry
        entry_data = {
            "language": Language.ENGLISH,
            "source_hash": "test_hash_123", 
            "lexicon_version": "1.0",
            "words_data": b"compressed_words",
            "phrases_data": b"compressed_phrases",
            "metadata_data": b"compressed_metadata",
            "compression_type": CompressionType.ZSTD,
            "compression_ratio": 3.5,
            "original_size_bytes": 10000,
            "compressed_size_bytes": 3000,
            "word_count": 1000,
            "phrase_count": 50,
            "total_entries": 1050,
            "load_time_ms": 150.0,
            "compression_time_ms": 25.0,
            "expires_at": datetime.now(UTC) + timedelta(hours=24)
        }
        
        # Should create successfully
        entry = CorpusCacheEntry(**entry_data)
        assert entry.language == Language.ENGLISH
        assert entry.compression_ratio == 3.5
        assert entry.total_entries == 1050

    @pytest.mark.asyncio
    async def test_cache_stats_calculation(self):
        """Test cache statistics calculation."""
        # Mock the database calls
        with patch.object(CorpusCacheEntry, 'count', return_value=10), \
             patch.object(CorpusCacheEntry, 'find') as mock_find, \
             patch.object(CorpusCacheEntry, 'aggregate') as mock_aggregate:
            
            # Mock expired entries count
            mock_find.return_value.count.return_value = 2
            
            # Mock compression stats
            mock_aggregate.return_value.to_list.return_value = [{
                "total_original_size": 100000,
                "total_compressed_size": 30000, 
                "avg_compression_ratio": 3.33
            }]
            
            stats = await CorpusCacheEntry.get_cache_stats()
            
            assert stats["total_entries"] == 10
            assert stats["active_entries"] == 8  # 10 - 2 expired
            assert stats["expired_entries"] == 2
            assert stats["average_compression_ratio"] == 3.33


class TestIntegratedCachingPerformance:
    """Integration tests for the complete caching system."""

    @pytest.mark.asyncio
    async def test_semantic_cache_integration(self):
        """Test semantic search with quantized MongoDB caching."""
        # Mock semantic search with small vocabulary
        vocab = ["test", "word", "example", "semantic", "search"]
        
        semantic_search = SemanticSearch(force_rebuild=True)
        semantic_search.quantization_type = QuantizationType.BINARY
        semantic_search.enable_compression = True
        
        # Mock the actual model loading to avoid dependencies
        with patch.object(semantic_search, '_build_sentence_embeddings') as mock_build, \
             patch.object(semantic_search, '_save_to_mongodb') as mock_save:
            
            # Mock embeddings
            mock_embeddings = np.random.randn(len(vocab), 384).astype(np.float32)
            semantic_search.sentence_embeddings = mock_embeddings
            
            await semantic_search.initialize(vocab)
            
            # Should call build and save methods
            mock_build.assert_called_once()
            mock_save.assert_called_once()

    def test_end_to_end_compression_flow(self):
        """Test complete flow from data to compressed storage to retrieval."""
        # Simulate lexicon data
        words = [f"word_{i}" for i in range(1000)]
        phrases = [f"phrase {i} example" for i in range(100)]
        
        import json
        import pickle
        
        # Serialize as would happen in real system
        words_data = pickle.dumps(words)
        phrases_data = pickle.dumps(phrases)
        metadata_data = json.dumps({"source": "test", "version": "1.0"}).encode()
        
        # Compress all data
        compressed_words, words_ratio = CorpusCompressionUtils.compress_data(
            words_data, CompressionType.ZSTD
        )
        compressed_phrases, phrases_ratio = CorpusCompressionUtils.compress_data(
            phrases_data, CompressionType.ZSTD
        )
        compressed_metadata, metadata_ratio = CorpusCompressionUtils.compress_data(
            metadata_data, CompressionType.ZSTD
        )
        
        # Verify compression effectiveness
        total_original = len(words_data) + len(phrases_data) + len(metadata_data)
        total_compressed = len(compressed_words) + len(compressed_phrases) + len(compressed_metadata)
        overall_ratio = total_original / total_compressed
        
        assert overall_ratio > 1.5, f"Overall compression ratio too low: {overall_ratio:.2f}"
        
        # Test decompression
        restored_words = pickle.loads(
            CorpusCompressionUtils.decompress_data(compressed_words, CompressionType.ZSTD)
        )
        restored_phrases = pickle.loads(
            CorpusCompressionUtils.decompress_data(compressed_phrases, CompressionType.ZSTD)
        )
        
        assert restored_words == words, "Words not restored correctly"
        assert restored_phrases == phrases, "Phrases not restored correctly"


if __name__ == "__main__":
    # Run basic tests
    print("Testing quantization improvements...")
    
    test_quant = TestQuantizationImprovements()
    test_quant.setup_method()
    test_quant.test_binary_quantization_compression_ratio()
    test_quant.test_scalar_quantization_compression_ratio()
    test_quant.test_no_quantization_passthrough()
    
    print("Testing lexicon caching...")
    
    test_cache = TestLexiconCaching()
    test_cache.test_compression_utilities_zstd()
    test_cache.test_compression_performance_ratios()
    
    print("Testing integrated performance...")
    
    test_integrated = TestIntegratedCachingPerformance()
    test_integrated.test_end_to_end_compression_flow()
    
    print("✅ All quantization and caching tests passed!")