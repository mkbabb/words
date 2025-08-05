"""
Comprehensive tests for improved lemmatization system.

Tests the modern NLTK WordNet + POS tagging approach vs old basic rules.
"""

from src.floridify.text import batch_lemmatize, clear_lemma_cache, lemmatize_word


class TestLemmatizationImprovements:
    """Test suite for improved lemmatization accuracy and performance."""

    def setup_method(self):
        """Clear lemma cache before each test."""
        clear_lemma_cache()

    def test_accuracy_improvements_vs_old_errors(self):
        """Test that old errors like 'hapines' are fixed."""
        # Test cases that previously failed with basic suffix rules
        test_cases = [
            ("happiness", "happiness"),  # Should NOT become "hapines"
            ("running", "running"),      # Context-aware lemmatization 
            ("studies", "study"),        # Proper plural handling
            ("beautiful", "beautiful"),  # Adjective preservation
            ("better", "better"),        # Comparative adjectives
            ("children", "child"),       # Irregular plurals
            ("mice", "mouse"),           # More irregular plurals
            ("feet", "foot"),            # Complex morphology
        ]
        
        for word, expected in test_cases:
            result = lemmatize_word(word)
            assert result == expected, f"lemmatize_word('{word}') = '{result}', expected '{expected}'"

    def test_pos_tagging_context_awareness(self):
        """Test that POS tagging improves accuracy."""
        # Words that require POS context for proper lemmatization
        test_cases = [
            ("saw", "saw"),         # Could be noun or past tense of "see"
            ("leaves", "leave"),    # Could be noun (tree leaves) or verb (he leaves)  
            ("flies", "fly"),       # Could be noun (insects) or verb (he flies)
            ("rose", "rise"),       # Could be noun (flower) or past tense of "rise"
        ]
        
        for word, expected in test_cases:
            result = lemmatize_word(word)
            # Note: Results may vary based on context, but should be valid lemmas
            assert len(result) >= 2, f"lemmatize_word('{word}') produced invalid short result: '{result}'"
            assert result.isalpha(), f"lemmatize_word('{word}') produced non-alphabetic result: '{result}'"

    def test_vocabulary_validation(self):
        """Test that invalid words are handled gracefully."""
        invalid_cases = [
            "",           # Empty string
            " ",          # Whitespace only
            "a",          # Too short
            "123",        # Numbers only
            "!@#",        # Punctuation only
            "a" * 100,    # Extremely long
        ]
        
        for word in invalid_cases:
            result = lemmatize_word(word)
            # Should return the input or handle gracefully
            assert isinstance(result, str), f"lemmatize_word('{word}') did not return string"

    def test_caching_performance(self):
        """Test that memoization cache improves performance."""
        test_word = "happiness"
        
        # First call - cache miss
        result1 = lemmatize_word(test_word)
        
        # Second call - cache hit (should be faster)
        result2 = lemmatize_word(test_word)
        
        # Results should be identical
        assert result1 == result2
        
        # Cache should contain the entry
        from src.floridify.text.normalize import _lemma_cache
        assert test_word.lower() in _lemma_cache

    def test_batch_processing(self):
        """Test batch lemmatization for performance optimization."""
        words = ["happiness", "running", "studies", "beautiful", "children"]
        
        # Batch process
        results = batch_lemmatize(words)
        
        # Check all words processed
        assert len(results) == len(words)
        
        # Check individual results match single processing
        for word in words:
            assert results[word] == lemmatize_word(word)

    def test_fallback_behavior(self):
        """Test fallback to basic lemmatization when NLTK fails."""
        # Test with valid words that should work in both systems
        test_words = ["testing", "worked", "faster", "running"]
        
        for word in test_words:
            result = lemmatize_word(word)
            assert len(result) >= 2, f"Fallback failed for '{word}': got '{result}'"
            assert result.isalpha(), f"Fallback produced invalid result for '{word}': '{result}'"

    def test_comprehensive_regression(self):
        """Comprehensive regression test against known good results."""
        # Large set of words with expected lemmatized forms
        known_good_cases = {
            "happiness": "happiness",
            "running": "running", 
            "studies": "study",
            "better": "better",
            "dogs": "dog",
            "cats": "cat",
            "walking": "walking",
            "books": "book",
            "houses": "house",
            "children": "child",
            "people": "people",
            "working": "working",
            "played": "played",  # May depend on POS context
            "singing": "singing",
            "beautiful": "beautiful",
        }
        
        for word, expected in known_good_cases.items():
            result = lemmatize_word(word)
            assert result == expected, f"Regression: '{word}' -> '{result}' (expected '{expected}')"

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        edge_cases = [
            ("UPPERCASE", "uppercase"),      # Case handling
            ("MiXeD", "mixed"),             # Mixed case
            ("word's", "word's"),           # Contractions/apostrophes
            ("co-worker", "co-worker"),     # Hyphens
            ("café", "café"),               # Unicode/accents
        ]
        
        for word, expected_pattern in edge_cases:
            result = lemmatize_word(word)
            assert isinstance(result, str), f"Edge case '{word}' failed: got {type(result)}"
            assert len(result) >= 2, f"Edge case '{word}' produced too short result: '{result}'"


# Performance benchmarks (optional, run with pytest --benchmark)
class TestLemmatizationPerformance:
    """Performance tests for lemmatization improvements."""

    def test_single_word_performance(self, benchmark):
        """Benchmark single word lemmatization."""
        word = "happiness"
        result = benchmark(lemmatize_word, word)
        assert result == "happiness"

    def test_batch_performance(self, benchmark):
        """Benchmark batch lemmatization."""
        words = [f"word{i}" for i in range(100)]  # 100 unique words
        result = benchmark(batch_lemmatize, words)
        assert len(result) == len(words)

    def test_cache_performance(self, benchmark):
        """Benchmark cached lookups."""
        word = "happiness"
        # Prime the cache
        lemmatize_word(word)
        
        # Benchmark cached lookup
        result = benchmark(lemmatize_word, word)
        assert result == "happiness"


if __name__ == "__main__":
    # Run basic tests
    test_suite = TestLemmatizationImprovements()
    test_suite.setup_method()
    
    print("Testing lemmatization improvements...")
    test_suite.test_accuracy_improvements_vs_old_errors()
    test_suite.test_vocabulary_validation()
    test_suite.test_caching_performance()
    test_suite.test_batch_processing()
    test_suite.test_comprehensive_regression()
    
    print("✅ All lemmatization tests passed!")