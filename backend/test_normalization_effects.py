#!/usr/bin/env python3
"""
Test how different normalization strategies affect fuzzy search results.
"""

import re
import unicodedata

from rapidfuzz import fuzz, process


def normalize_fast_original(text: str, lowercase: bool = True) -> str:
    """Original normalize_fast from the codebase."""
    if not text:
        return ""

    # Unicode normalization table from constants
    UNICODE_TO_ASCII = str.maketrans({
        "—": "-", "–": "-", "‒": "-", "―": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "‚": "'", "„": '"', "´": "'", "`": "'",
        "\xa0": " ", "\u2009": " ", "\u200a": " ",
    })
    
    # Quick Unicode normalization
    text = unicodedata.normalize("NFC", text)

    # Quick character replacement
    text = text.translate(UNICODE_TO_ASCII)

    # Remove excessive punctuation
    text = re.sub(r"[^\w\s\'-]", " ", text)

    # Quick whitespace normalization
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Lowercase if requested
    if lowercase:
        text = text.lower()

    return text

def normalize_fast_with_diacritics(text: str, lowercase: bool = True) -> str:
    """Enhanced normalize_fast that also removes diacritics."""
    if not text:
        return ""

    # Unicode normalization table from constants
    UNICODE_TO_ASCII = str.maketrans({
        "—": "-", "–": "-", "‒": "-", "―": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "‚": "'", "„": '"', "´": "'", "`": "'",
        "\xa0": " ", "\u2009": " ", "\u200a": " ",
    })
    
    # Quick Unicode normalization
    text = unicodedata.normalize("NFC", text)

    # Quick character replacement
    text = text.translate(UNICODE_TO_ASCII)
    
    # Remove diacritics
    text = remove_diacritics(text)

    # Remove excessive punctuation
    text = re.sub(r"[^\w\s\'-]", " ", text)

    # Quick whitespace normalization
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Lowercase if requested
    if lowercase:
        text = text.lower()

    return text

def remove_diacritics(text: str) -> str:
    """Remove diacritics from text while preserving base characters."""
    # Normalize to NFD (decomposed form)
    nfd_text = unicodedata.normalize("NFD", text)
    
    # Remove combining marks (diacritics)
    without_diacritics = "".join(
        char for char in nfd_text if unicodedata.category(char) != "Mn"
    )
    
    # Normalize back to NFC (composed form)
    return unicodedata.normalize("NFC", without_diacritics)

def apply_length_correction(query: str, candidate: str, base_score: float, is_query_phrase: bool) -> float:
    """Length correction from fuzzy.py"""
    if base_score >= 0.99:
        return base_score

    query_len = len(query)
    candidate_len = len(candidate)
    is_candidate_phrase = " " in candidate
    
    query_lower = query.lower()
    candidate_lower = candidate.lower()

    is_prefix_match = candidate_lower.startswith(query_lower)

    first_word_match = False
    if is_candidate_phrase and not is_query_phrase:
        space_idx = candidate_lower.find(' ')
        if space_idx > 0:
            first_word_match = query_lower == candidate_lower[:space_idx]

    min_len = min(query_len, candidate_len)
    max_len = max(query_len, candidate_len)
    length_ratio = min_len / max_len if max_len > 0 else 1.0

    phrase_penalty = 1.0
    if is_query_phrase and not is_candidate_phrase:
        phrase_penalty = 0.7
    elif not is_query_phrase and is_candidate_phrase:
        if is_prefix_match or first_word_match:
            phrase_penalty = 1.2
        else:
            phrase_penalty = 0.95
    elif is_query_phrase and is_candidate_phrase:
        phrase_penalty = 1.1 if length_ratio > 0.6 else 1.0

    if candidate_len <= 3 and query_len > 6:
        short_penalty = 0.5
    elif candidate_len < query_len * 0.5:
        short_penalty = 0.75
    else:
        short_penalty = 1.0

    prefix_bonus = 1.3 if is_prefix_match else 1.0
    first_word_bonus = 1.2 if first_word_match else 1.0

    corrected_score = (
        base_score * length_ratio * phrase_penalty * 
        short_penalty * prefix_bonus * first_word_bonus
    )

    return max(0.0, min(1.0, corrected_score))

def test_normalization_strategies():
    """Test different normalization approaches on the problematic cases."""
    print("🧪 Testing Normalization Strategies")
    print("=" * 70)
    
    # Test vocabulary with diacritic words
    french_vocabulary = [
        # Target words
        "ennui", "en coulisse", "enquête", "coulisse",
        
        # Diacritic variants
        "enquete",  # without accent
        "enquêter", "enquêteur",
        
        # Similar words that might interfere
        "ennuie", "ennuyé", "ennuyer", 
        "coulis", "couleur", "couloir",
        "coulisser", "coulissé", "coulissant",
        
        # French phrases
        "en route", "en effet", "en fait", "en avant",
        "en couleur", "en couleurs",
        
        # Other words for context
        "bonjour", "français", "café", "résumé", "naïve",
        "château", "pâte", "être", "même", "où",
    ]
    
    test_cases = [
        ("enui", "ennui", "Missing n"),
        ("en coulise", "en coulisse", "Missing s"),
        ("enquete", "enquête", "Missing accent"),
        ("couli", "coulisse", "Partial word"),
        ("francais", "français", "Missing cedilla"),
        ("cafe", "café", "Missing accent"),  
        ("resume", "résumé", "Missing accents"),
        ("chateau", "château", "Missing circumflex"),
        ("ou", "où", "Missing accent"),
    ]
    
    strategies = [
        ("Original (no diacritic removal)", normalize_fast_original),
        ("Enhanced (with diacritic removal)", normalize_fast_with_diacritics),
    ]
    
    for strategy_name, normalize_func in strategies:
        print(f"\n📊 Strategy: {strategy_name}")
        print("-" * 50)
        
        # Normalize vocabulary with current strategy
        normalized_vocab = [normalize_func(word) for word in french_vocabulary]
        
        # Show what normalization does to some key words
        sample_normalizations = [
            ("enquête", normalize_func("enquête")),
            ("français", normalize_func("français")), 
            ("résumé", normalize_func("résumé")),
            ("château", normalize_func("château")),
        ]
        print("Sample normalizations:")
        for orig, norm in sample_normalizations:
            print(f"  '{orig}' → '{norm}'")
        print()
        
        DEFAULT_MIN_SCORE = 0.6
        passing_tests = 0
        
        for query, expected, description in test_cases:
            normalized_query = normalize_func(query)
            
            # Find expected word in normalized vocabulary
            expected_norm = normalize_func(expected)
            if expected_norm not in normalized_vocab:
                print(f"  ❌ {description}: Expected word '{expected}' not in normalized vocabulary")
                continue
            
            # Get RapidFuzz results
            results = process.extract(
                normalized_query,
                normalized_vocab,
                limit=5,
                scorer=fuzz.WRatio,
                processor=lambda s: s,  # Already normalized
            )
            
            # Find the expected match
            expected_result = None
            expected_rank = None
            for i, (word, score, _) in enumerate(results):
                if word == expected_norm:
                    expected_result = (word, score)
                    expected_rank = i + 1
                    break
            
            if not expected_result:
                print(f"  ❌ {description}: '{query}' → Expected '{expected}' not found in top 5")
                continue
                
            # Apply length correction
            base_score = expected_result[1] / 100.0
            is_query_phrase = " " in query.strip()
            corrected_score = apply_length_correction(query, expected, base_score, is_query_phrase)
            
            # Check if it passes threshold
            passes = corrected_score >= DEFAULT_MIN_SCORE
            status = "✅ PASS" if passes else "❌ FAIL"
            
            if passes:
                passing_tests += 1
            
            print(f"  {status} {description}: '{query}' → '{expected}' (rank #{expected_rank}, score: {corrected_score:.3f})")
        
        print(f"\n  Summary: {passing_tests}/{len(test_cases)} tests passed")

def test_threshold_analysis():
    """Analyze what threshold would work best."""
    print("\n🎯 Threshold Analysis")
    print("=" * 70)
    
    # Test with enhanced normalization
    french_vocabulary = [
        "ennui", "en coulisse", "enquête", "coulisse", "français", 
        "café", "résumé", "château", "où", "être", "même",
        "ennuie", "ennuyé", "enqueter", "enqueteur", "coulis", 
        "couleur", "couloir", "en route", "en effet", "bonjour",
    ]
    
    test_cases = [
        ("enui", "ennui"),
        ("en coulise", "en coulisse"),
        ("enquete", "enquête"),
        ("francais", "français"),
        ("cafe", "café"),
        ("resume", "résumé"),
    ]
    
    # Normalize vocabulary
    normalized_vocab = [normalize_fast_with_diacritics(word) for word in french_vocabulary]
    
    print("Testing different thresholds:")
    thresholds = [0.4, 0.5, 0.6, 0.7, 0.8]
    
    for threshold in thresholds:
        passing_count = 0
        print(f"\n📊 Threshold: {threshold}")
        
        for query, expected in test_cases:
            normalized_query = normalize_fast_with_diacritics(query)
            expected_norm = normalize_fast_with_diacritics(expected)
            
            if expected_norm not in normalized_vocab:
                continue
                
            results = process.extract(
                normalized_query,
                normalized_vocab,
                limit=1,
                scorer=fuzz.WRatio,
            )
            
            if results and results[0][0] == expected_norm:
                base_score = results[0][1] / 100.0
                is_query_phrase = " " in query.strip()
                corrected_score = apply_length_correction(query, expected, base_score, is_query_phrase)
                
                passes = corrected_score >= threshold
                if passes:
                    passing_count += 1
                
                status = "✅" if passes else "❌"
                print(f"  {status} '{query}' → '{expected}': {corrected_score:.3f}")
        
        print(f"  → {passing_count}/{len(test_cases)} passed")

if __name__ == "__main__":
    test_normalization_strategies()
    test_threshold_analysis()