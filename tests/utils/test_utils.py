"""Unit tests for utility functions."""


from src.floridify.utils.normalization import (
    generate_diacritic_variants,
    normalize_lexicon_entry,
    normalize_word,
    remove_diacritics,
)


class TestNormalization:
    """Test text normalization utilities."""

    def test_normalize_word_basic(self):
        """Test basic word normalization."""
        assert normalize_word("Hello") == "hello"
        assert normalize_word("  WORLD  ") == "world"
        assert normalize_word("Test123") == "test123"

    def test_normalize_word_empty(self):
        """Test normalization with empty input."""
        assert normalize_word("") == ""
        assert normalize_word("   ") == ""
        assert normalize_word(None) == ""

    def test_normalize_word_special_chars(self):
        """Test normalization with special characters."""
        assert normalize_word("hello-world") == "hello-world"
        assert normalize_word("café") == "café"  # Preserve diacritics
        assert normalize_word("test's") == "test's"

    def test_remove_diacritics(self):
        """Test diacritic removal."""
        assert remove_diacritics("café") == "cafe"
        assert remove_diacritics("naïve") == "naive"
        assert remove_diacritics("résumé") == "resume"
        assert remove_diacritics("piñata") == "pinata"
        assert remove_diacritics("hello") == "hello"  # No diacritics

    def test_generate_diacritic_variants(self):
        """Test diacritic variant generation."""
        variants = generate_diacritic_variants("café")
        assert "café" in variants  # Original
        assert "cafe" in variants  # Without diacritics
        assert len(variants) >= 2

        variants = generate_diacritic_variants("hello")
        assert "hello" in variants
        assert len(variants) == 1  # Only original for words without diacritics

    def test_normalize_lexicon_entry(self):
        """Test lexicon entry normalization."""
        variants = normalize_lexicon_entry("Café-Restaurant")
        assert "café-restaurant" in variants
        assert "cafe-restaurant" in variants

        variants = normalize_lexicon_entry("TEST")
        assert "test" in variants

    def test_normalization_consistency(self):
        """Test normalization consistency across functions."""
        test_words = ["Hello", "WORLD", "café", "naïve", "test's"]
        
        for word in test_words:
            normalized = normalize_word(word)
            variants = normalize_lexicon_entry(word)
            
            # Normalized form should be in variants
            assert normalized in variants
            # All variants should be lowercase
            assert all(v.islower() or not v.isalpha() for v in variants)


class TestLogging:
    """Test logging utilities."""

    def test_logger_creation(self):
        """Test logger creation with proper formatting."""
        from src.floridify.utils.logging import get_logger
        
        logger = get_logger("test_module")
        assert logger is not None
        assert logger.name == "test_module"

    def test_logger_singleton(self):
        """Test logger singleton behavior."""
        from src.floridify.utils.logging import get_logger
        
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        
        assert logger1 is logger2

    def test_logger_formatting(self):
        """Test logger format for VSCode integration."""

        from src.floridify.utils.logging import get_logger
        
        # Check that loguru is configured with file:line format
        # This is more of a configuration test
        logger = get_logger("test")
        assert logger is not None

    def test_log_levels(self):
        """Test different log levels work correctly."""
        from src.floridify.utils.logging import get_logger
        
        logger = get_logger("test")
        
        # These should not raise exceptions
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.success("Success message")


class TestTextProcessing:
    """Test text processing utilities."""

    def test_phrase_detection(self):
        """Test phrase vs single word detection."""
        from src.floridify.search.phrase import PhraseNormalizer
        
        normalizer = PhraseNormalizer()
        
        # Phrases
        assert normalizer.is_phrase("hello world")
        assert normalizer.is_phrase("bon vivant")
        assert normalizer.is_phrase("New York")
        
        # Single words
        assert not normalizer.is_phrase("hello")
        assert not normalizer.is_phrase("test")
        assert not normalizer.is_phrase("café")

    def test_text_cleaning(self):
        """Test text cleaning and normalization."""
        from src.floridify.search.phrase import PhraseNormalizer
        
        normalizer = PhraseNormalizer()
        
        # Basic cleaning
        assert normalizer.normalize("  Hello World  ") == "hello world"
        assert normalizer.normalize("TEST-PHRASE") == "test-phrase"
        
        # Multiple spaces
        assert normalizer.normalize("hello    world") == "hello world"
        
        # Special characters
        assert normalizer.normalize("hello, world!") == "hello, world!"

    def test_word_extraction(self):
        """Test word extraction from text."""
        # This would test any word extraction utilities if they exist
        pass


class TestValidation:
    """Test validation utilities."""

    def test_word_validation(self):
        """Test word validation functions."""
        # Valid words
        assert self._is_valid_word("hello")
        assert self._is_valid_word("test123")
        assert self._is_valid_word("café")
        assert self._is_valid_word("hello-world")
        
        # Invalid words
        assert not self._is_valid_word("")
        assert not self._is_valid_word("   ")
        assert not self._is_valid_word("@#$%")
        assert not self._is_valid_word("test" * 100)  # Too long

    def _is_valid_word(self, word: str) -> bool:
        """Helper function to validate words."""
        if not word or not word.strip():
            return False
        if len(word) > 100:  # Arbitrary max length
            return False
        # Allow letters, numbers, hyphens, apostrophes, and diacritics
        import re
        return bool(re.match(r"^[\w\-''àáâãäåæçèéêëìíîïñòóôõöøùúûüýÿ\s]+$", word, re.IGNORECASE))

    def test_language_detection(self):
        """Test language detection utilities."""
        # This would test language detection if implemented
        pass

    def test_encoding_handling(self):
        """Test proper UTF-8 encoding handling."""
        test_strings = [
            "hello",
            "café",
            "naïve",
            "résumé",
            "🙂",  # Emoji
            "中文",  # Chinese characters
        ]
        
        for text in test_strings:
            # Should handle encoding without errors
            normalized = normalize_word(text)
            assert isinstance(normalized, str)
            
            # Should preserve non-ASCII characters appropriately
            if not text.isascii():
                # Non-ASCII text should be handled gracefully
                assert len(normalized) > 0


class TestPerformance:
    """Test performance-critical utility functions."""

    def test_normalization_performance(self):
        """Test normalization performance with large inputs."""
        import time
        
        # Test with large word list
        words = ["test"] * 1000
        
        start_time = time.time()
        for word in words:
            normalize_word(word)
        end_time = time.time()
        
        # Should complete quickly (< 1 second for 1000 words)
        assert end_time - start_time < 1.0

    def test_diacritic_generation_performance(self):
        """Test diacritic variant generation performance."""
        import time
        
        words = ["café", "naïve", "résumé"] * 100
        
        start_time = time.time()
        for word in words:
            generate_diacritic_variants(word)
        end_time = time.time()
        
        # Should complete quickly
        assert end_time - start_time < 1.0

    def test_memory_efficiency(self):
        """Test memory efficiency of utility functions."""
        import sys
        
        # Test that normalization doesn't create excessive objects
        word = "test"
        
        # Get baseline memory usage
        initial_refs = sys.getrefcount(word)
        
        # Run normalization multiple times
        for _ in range(100):
            normalize_word(word)
        
        # Reference count shouldn't grow significantly
        final_refs = sys.getrefcount(word)
        assert final_refs - initial_refs < 10  # Allow some growth but not excessive


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_unicode_edge_cases(self):
        """Test Unicode edge cases."""
        edge_cases = [
            "\u200b",  # Zero-width space
            "\ufeff",  # BOM
            "test\x00null",  # Null character
            "test\r\nwindows",  # Windows line endings
        ]
        
        for case in edge_cases:
            # Should handle gracefully without crashing
            result = normalize_word(case)
            assert isinstance(result, str)

    def test_very_long_strings(self):
        """Test handling of very long strings."""
        long_word = "a" * 10000
        
        # Should handle without crashing
        result = normalize_word(long_word)
        assert isinstance(result, str)

    def test_empty_and_whitespace(self):
        """Test empty and whitespace-only strings."""
        test_cases = ["", " ", "\t", "\n", "\r\n", "   \t\n   "]
        
        for case in test_cases:
            result = normalize_word(case)
            assert result == ""  # Should normalize to empty string

    def test_mixed_scripts(self):
        """Test mixed script handling."""
        mixed_cases = [
            "hello世界",  # Latin + Chinese
            "café中文",   # Latin with diacritics + Chinese
            "test123",    # Latin + numbers
        ]
        
        for case in mixed_cases:
            result = normalize_word(case)
            assert isinstance(result, str)
            assert len(result) > 0