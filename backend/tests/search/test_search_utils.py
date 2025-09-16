"""Comprehensive tests for search utility functions."""

import pytest

from floridify.search.utils import apply_length_correction, calculate_default_frequency


class TestLengthCorrection:
    """Test apply_length_correction scoring function."""

    def test_perfect_match_no_correction(self):
        """Test that perfect matches get no correction."""
        score = apply_length_correction("test", "test", 0.99)
        assert score == 0.99

        score = apply_length_correction("perfect", "perfect", 1.0)
        assert score == 1.0

    def test_basic_length_ratio(self):
        """Test basic length ratio penalty."""
        # Similar lengths
        score = apply_length_correction("test", "tests", 0.8)
        assert 0.7 < score <= 0.8  # Slight penalty for length difference

        # Very different lengths
        score = apply_length_correction("a", "application", 0.8)
        assert score < 0.5  # Heavy penalty for huge length difference

    def test_prefix_match_bonus(self):
        """Test prefix match bonus."""
        # Query is prefix of candidate
        score = apply_length_correction("app", "application", 0.7)
        assert score > 0.7  # Should get prefix bonus

        # Not a prefix
        score = apply_length_correction("ppl", "application", 0.7)
        assert score <= 0.7  # No prefix bonus

    def test_phrase_matching(self):
        """Test phrase matching logic."""
        # Query is phrase, candidate is not - penalty
        score = apply_length_correction("hello world", "hello", 0.8, is_query_phrase=True)
        assert score < 0.8 * 0.7  # Phrase penalty applied

        # Query is word, candidate is phrase with prefix match - bonus
        score = apply_length_correction("hello", "hello world", 0.8)
        assert score > 0.8  # Prefix bonus for phrase

        # Both phrases with similar length - bonus
        score = apply_length_correction(
            "hello world", "hello universe", 0.8, is_query_phrase=True, is_candidate_phrase=True
        )
        assert score > 0.8  # Phrase bonus

    def test_first_word_match(self):
        """Test first word matching in phrases."""
        # Exact first word match
        score = apply_length_correction("hello", "hello beautiful world", 0.7)
        assert score > 0.7 * 1.2  # First word bonus

        # Partial first word match
        score = apply_length_correction("hell", "hello world", 0.7)
        assert score > 0.7  # Prefix bonus but not first word bonus

    def test_short_fragment_penalty(self):
        """Test penalty for very short candidates."""
        # Very short candidate for long query
        score = apply_length_correction("application", "app", 0.8)
        assert score < 0.8 * 0.5  # Heavy penalty

        # Moderately short candidate
        score = apply_length_correction("testing", "test", 0.8)
        assert score < 0.8  # Some penalty

        # Similar lengths
        score = apply_length_correction("test", "text", 0.8)
        assert score >= 0.8 * 0.75  # Minimal penalty

    def test_score_bounds(self):
        """Test that scores stay within bounds."""
        # Should never exceed 1.0
        score = apply_length_correction("test", "test", 0.95)
        assert score <= 1.0

        # With all bonuses
        score = apply_length_correction("hello", "hello world", 0.9)
        assert score <= 1.0

        # Should never go below 0.0
        score = apply_length_correction("verylongquery", "a", 0.1)
        assert score >= 0.0

    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        score = apply_length_correction("", "test", 0.5)
        assert score >= 0.0

        score = apply_length_correction("test", "", 0.5)
        assert score >= 0.0

    def test_phrase_detection(self):
        """Test automatic phrase detection."""
        # Should detect phrases automatically
        score1 = apply_length_correction("hello world", "hello", 0.8)
        score2 = apply_length_correction("hello world", "hello", 0.8, is_query_phrase=True)
        assert abs(score1 - score2) < 0.01  # Should be same with auto-detection

    def test_combined_corrections(self):
        """Test multiple corrections applied together."""
        # Long query, short candidate, no prefix match
        score = apply_length_correction("application", "cat", 0.6)
        assert score < 0.3  # Multiple penalties

        # Phrase query, word candidate, prefix match
        score = apply_length_correction("hello world", "hello", 0.7)
        # Gets phrase penalty but also some matching bonus
        assert 0.4 < score < 0.6

    @pytest.mark.parametrize(
        "query,candidate,base_score,expected_range",
        [
            ("test", "test", 1.0, (0.99, 1.0)),
            ("app", "application", 0.8, (0.8, 1.0)),  # Prefix bonus
            ("hello world", "hello", 0.8, (0.4, 0.6)),  # Phrase penalty
            ("a", "antidisestablishmentarianism", 0.5, (0.0, 0.2)),  # Huge length diff
            ("hello", "hello world", 0.7, (0.8, 1.0)),  # First word bonus
        ],
    )
    def test_parametrized_corrections(self, query, candidate, base_score, expected_range):
        """Parametrized tests for various correction scenarios."""
        score = apply_length_correction(query, candidate, base_score)
        assert expected_range[0] <= score <= expected_range[1]


class TestDefaultFrequency:
    """Test calculate_default_frequency heuristic function."""

    def test_empty_word(self):
        """Test handling of empty input."""
        freq = calculate_default_frequency("")
        assert freq == 1

    def test_length_based_scoring(self):
        """Test that shorter words get higher frequency."""
        # Very short words
        freq_short = calculate_default_frequency("a")
        freq_medium = calculate_default_frequency("hello")
        freq_long = calculate_default_frequency("antidisestablishmentarianism")

        assert freq_short > freq_medium > freq_long

    def test_common_suffixes(self):
        """Test bonus for common suffixes."""
        # Words with common suffixes
        freq_ing = calculate_default_frequency("testing")
        freq_ed = calculate_default_frequency("tested")
        freq_ly = calculate_default_frequency("quickly")

        # Same length word without suffix
        freq_no_suffix = calculate_default_frequency("zzzzzzz")

        assert freq_ing > freq_no_suffix
        assert freq_ed > freq_no_suffix
        assert freq_ly > freq_no_suffix

    def test_common_prefixes(self):
        """Test bonus for common prefixes."""
        # Words with common prefixes
        freq_un = calculate_default_frequency("unhappy")
        freq_re = calculate_default_frequency("restart")
        freq_pre = calculate_default_frequency("preview")

        # Same length word without prefix
        freq_no_prefix = calculate_default_frequency("zzzzzzz")

        assert freq_un > freq_no_prefix
        assert freq_re > freq_no_prefix
        assert freq_pre > freq_no_prefix

    def test_phrase_handling(self):
        """Test frequency calculation for phrases."""
        # Two-word phrases are common
        freq_two = calculate_default_frequency("hello world")

        # Three-word phrases moderate
        freq_three = calculate_default_frequency("hello beautiful world")

        # Long phrases less common
        freq_long = calculate_default_frequency("the quick brown fox jumps over the lazy dog")

        assert freq_two > freq_three > freq_long

    def test_vowel_density(self):
        """Test vowel density bonus."""
        # Balanced vowel ratio
        freq_balanced = calculate_default_frequency("hello")  # 2/5 = 0.4

        # Too many consonants
        freq_consonants = calculate_default_frequency("bcdfg")  # 0/5 = 0

        # Too many vowels
        freq_vowels = calculate_default_frequency("aeiou")  # 5/5 = 1.0

        # Balanced should score higher
        assert freq_balanced > freq_consonants
        assert freq_balanced > freq_vowels

    def test_case_insensitive(self):
        """Test that frequency is case-insensitive."""
        freq_lower = calculate_default_frequency("hello")
        freq_upper = calculate_default_frequency("HELLO")
        freq_mixed = calculate_default_frequency("HeLLo")

        assert freq_lower == freq_upper == freq_mixed

    def test_minimum_score(self):
        """Test that minimum score is always 1."""
        # Even with all penalties
        freq = calculate_default_frequency("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")
        assert freq >= 1

    def test_suffix_priority(self):
        """Test that first matching suffix is used."""
        # "testing" ends with both "ing" and "g"
        freq = calculate_default_frequency("testing")

        # Should get "ing" bonus (150), not just any suffix
        assert freq > 1000  # Base score minus penalties plus suffix bonus

    def test_prefix_suffix_combination(self):
        """Test words with both prefix and suffix."""
        # "undoing" has both "un" prefix and "ing" suffix
        freq = calculate_default_frequency("undoing")

        # Should get bonuses for both
        freq_no_affix = calculate_default_frequency("zzzzzz")  # Same length, no affixes

        assert freq > freq_no_affix

    def test_real_world_words(self):
        """Test frequency calculation for real words."""
        # Common words should score high
        freq_the = calculate_default_frequency("the")
        freq_and = calculate_default_frequency("and")

        # Less common words
        freq_uncommon = calculate_default_frequency("sesquipedalian")
        freq_rare = calculate_default_frequency("pneumonoultramicroscopicsilicovolcanoconiosis")

        assert freq_the > freq_uncommon
        assert freq_and > freq_uncommon
        assert freq_uncommon > freq_rare

    @pytest.mark.parametrize(
        "word,min_freq",
        [
            ("a", 900),  # Very short
            ("the", 900),  # Common short word
            ("testing", 800),  # Common suffix
            ("unhappy", 700),  # Common prefix
            ("hello world", 600),  # Two-word phrase
            ("antidisestablishmentarianism", 100),  # Very long
            ("", 1),  # Empty
            ("bcdfg", 500),  # No vowels
        ],
    )
    def test_parametrized_frequencies(self, word, min_freq):
        """Parametrized tests for frequency ranges."""
        freq = calculate_default_frequency(word)
        assert freq >= min_freq

    def test_frequency_ordering(self):
        """Test relative ordering of frequencies."""
        words = [
            "a",  # Very short
            "the",  # Common
            "test",  # Medium
            "testing",  # With suffix
            "untested",  # With prefix
            "hello world",  # Phrase
            "antidisestablishmentarianism",  # Very long
        ]

        frequencies = [calculate_default_frequency(w) for w in words]

        # Check some expected orderings
        assert frequencies[0] > frequencies[6]  # "a" > very long word
        assert frequencies[3] > frequencies[2]  # "testing" > "test" (suffix bonus)
        assert frequencies[4] > frequencies[2]  # "untested" > "test" (prefix bonus)

    def test_edge_cases(self):
        """Test edge cases in frequency calculation."""
        # Single character
        assert calculate_default_frequency("x") >= 1

        # Only spaces
        assert calculate_default_frequency("   ") >= 1

        # Numbers and special chars (treated as text)
        assert calculate_default_frequency("123") >= 1
        assert calculate_default_frequency("@#$") >= 1

        # Very long phrase
        long_phrase = " ".join(["word"] * 20)
        assert calculate_default_frequency(long_phrase) >= 1

        # Word with multiple possible suffixes
        freq = calculate_default_frequency("happiness")  # Has "ness"
        assert freq > 700  # Should get suffix bonus
