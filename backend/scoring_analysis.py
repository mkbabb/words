#!/usr/bin/env python3
"""
Analyze the exact scoring pipeline to see where the failures occur.
"""

import jellyfish
from rapidfuzz import fuzz, process

# Test vocabulary 
test_vocabulary = [
    "ennui",
    "en coulisse", 
    "coulisse",
    "ennuie",
    "enquête",
    "english",
    "energy",
    "ensemble",
    "enthousiasme",
    "en route",
    "en effet", 
    "en fait",
    "bonjour",
    "hello",
    "monde"
]

def apply_length_correction(query: str, candidate: str, base_score: float, is_query_phrase: bool) -> float:
    """Exact implementation from fuzzy.py"""
    # No correction needed for perfect matches
    if base_score >= 0.99:
        return base_score

    # Pre-compute lengths and lowercase versions (minimize string operations)
    query_len = len(query)
    candidate_len = len(candidate)
    is_candidate_phrase = " " in candidate
    
    # Only compute lowercase versions when needed
    query_lower = query.lower()
    candidate_lower = candidate.lower()

    # Check if query is a prefix of the candidate (important for phrases)
    is_prefix_match = candidate_lower.startswith(query_lower)

    # Check if query matches the first word of a phrase exactly
    first_word_match = False
    if is_candidate_phrase and not is_query_phrase:
        # Find first space index instead of split() to avoid list allocation
        space_idx = candidate_lower.find(' ')
        if space_idx > 0:
            first_word_match = query_lower == candidate_lower[:space_idx]

    # Length ratio penalty for very different lengths
    min_len = min(query_len, candidate_len)
    max_len = max(query_len, candidate_len)
    length_ratio = min_len / max_len if max_len > 0 else 1.0

    # Phrase matching bonus/penalty
    phrase_penalty = 1.0
    if is_query_phrase and not is_candidate_phrase:
        # Query is phrase but candidate is not - significant penalty
        phrase_penalty = 0.7
    elif not is_query_phrase and is_candidate_phrase:
        # Query is word but candidate is phrase
        if is_prefix_match or first_word_match:
            # Strong bonus for prefix or first word matches
            phrase_penalty = 1.2
        else:
            # Only slight penalty for non-prefix matches
            phrase_penalty = 0.95
    elif is_query_phrase and is_candidate_phrase:
        # Both phrases - bonus for length similarity
        phrase_penalty = 1.1 if length_ratio > 0.6 else 1.0

    # Short fragment penalty (aggressive for very short candidates)
    if candidate_len <= 3 and query_len > 6:
        # Very short candidates for longer queries get heavy penalty
        short_penalty = 0.5
    elif candidate_len < query_len * 0.5:
        # Moderately short candidates get moderate penalty
        short_penalty = 0.75
    else:
        short_penalty = 1.0

    # Prefix match bonus
    prefix_bonus = 1.3 if is_prefix_match else 1.0

    # First word match bonus (for phrases)
    first_word_bonus = 1.2 if first_word_match else 1.0

    # Combined correction
    corrected_score = (
        base_score
        * length_ratio
        * phrase_penalty
        * short_penalty
        * prefix_bonus
        * first_word_bonus
    )

    # Ensure we don't exceed 1.0 or go below 0.0
    return max(0.0, min(1.0, corrected_score))

def simulate_rapidfuzz_pipeline():
    """Simulate the exact RapidFuzz pipeline from the code."""
    print("🔬 Simulating RapidFuzz Pipeline")
    print("=" * 60)
    
    DEFAULT_MIN_SCORE = 0.6  # From constants.py
    
    test_cases = [
        ("enui", "ennui"),
        ("en coulise", "en coulisse"),
    ]
    
    for query, expected in test_cases:
        print(f"\n🎯 Query: '{query}' → Expected: '{expected}'")
        print("-" * 40)
        
        # Step 1: Get RapidFuzz results (simulating _search_rapidfuzz)
        words = test_vocabulary
        results = process.extract(
            query,
            words,
            limit=min(10, len(words)),
            scorer=fuzz.WRatio,
            processor=lambda s: s.lower(),
        )
        
        print("Step 1: Raw RapidFuzz results:")
        for result in results:
            if len(result) == 3:
                word, score, _ = result
            else:
                word, score = result
            print(f"  '{word}': {score}/100 ({score/100:.3f})")
        
        print("\nStep 2: Apply length correction and filter:")
        is_query_phrase = " " in query.strip()
        
        matches = []
        for result in results:
            if len(result) == 3:
                word, score, _ = result
            else:
                word, score = result

            # Convert 0-100 score to 0.0-1.0
            base_score = score / 100.0

            # Apply length-aware scoring correction
            corrected_score = apply_length_correction(
                query, word, base_score, is_query_phrase
            )
            
            matches.append((word, base_score, corrected_score))
            
            marker = "✅" if word == expected else "  "
            print(f"  {marker} '{word}': {base_score:.3f} → {corrected_score:.3f}")
        
        print(f"\nStep 3: Filter by minimum score ({DEFAULT_MIN_SCORE}):")
        filtered_matches = [(word, corr_score) for word, base_score, corr_score in matches if corr_score >= DEFAULT_MIN_SCORE]
        
        if not filtered_matches:
            print("  ❌ NO MATCHES after filtering!")
        else:
            # Sort by corrected scores
            filtered_matches.sort(key=lambda x: x[1], reverse=True)
            for word, score in filtered_matches:
                marker = "✅" if word == expected else "  "
                print(f"  {marker} '{word}': {score:.3f}")
        
        # Check if expected word passed
        expected_passed = any(word == expected for word, score in filtered_matches)
        print(f"\n{'✅' if expected_passed else '❌'} Expected word {'PASSED' if expected_passed else 'FAILED'} filtering")
        print("=" * 60)

def analyze_jaro_winkler_pipeline():
    """Analyze Jaro-Winkler pipeline."""
    print("🔬 Simulating Jaro-Winkler Pipeline")
    print("=" * 60)
    
    DEFAULT_MIN_SCORE = 0.6
    
    test_cases = [
        ("enui", "ennui"),
        ("en coulise", "en coulisse"),
    ]
    
    for query, expected in test_cases:
        print(f"\n🎯 Query: '{query}' → Expected: '{expected}'")
        print("-" * 40)
        
        matches = []
        for word in test_vocabulary:
            word_lower = word.lower()
            score = jellyfish.jaro_winkler_similarity(query, word_lower)
            matches.append((word, score))
        
        # Sort by score
        matches.sort(key=lambda x: x[1], reverse=True)
        
        print("Jaro-Winkler results:")
        for word, score in matches:
            marker = "✅" if word == expected else "  "
            threshold_marker = "✅" if score >= DEFAULT_MIN_SCORE else "❌"
            print(f"  {marker} {threshold_marker} '{word}': {score:.3f}")
        
        # Check filtering
        filtered_matches = [(word, score) for word, score in matches if score >= DEFAULT_MIN_SCORE]
        expected_passed = any(word == expected for word, score in filtered_matches)
        print(f"\n{'✅' if expected_passed else '❌'} Expected word {'PASSED' if expected_passed else 'FAILED'} filtering")
        print("=" * 60)

def test_different_thresholds():
    """Test what happens with different minimum score thresholds."""
    print("📊 Testing Different Score Thresholds")
    print("=" * 60)
    
    test_cases = [
        ("enui", "ennui"),
        ("en coulise", "en coulisse"),
    ]
    
    thresholds = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    
    for query, expected in test_cases:
        print(f"\n🎯 Query: '{query}' → Expected: '{expected}'")
        print("-" * 40)
        
        # Get RapidFuzz score for the expected match
        results = process.extract(
            query,
            test_vocabulary,
            limit=len(test_vocabulary),
            scorer=fuzz.WRatio,
            processor=lambda s: s.lower(),
        )
        
        expected_result = next((r for r in results if r[0] == expected), None)
        if expected_result:
            base_score = expected_result[1] / 100.0
            is_query_phrase = " " in query.strip()
            corrected_score = apply_length_correction(query, expected, base_score, is_query_phrase)
            
            print("Expected word scores:")
            print(f"  Raw RapidFuzz: {base_score:.3f}")
            print(f"  After correction: {corrected_score:.3f}")
            print("\nThreshold analysis:")
            
            for threshold in thresholds:
                passed = corrected_score >= threshold
                print(f"  {threshold:.1f}: {'✅ PASS' if passed else '❌ FAIL'}")
        else:
            print(f"Expected word '{expected}' not found in RapidFuzz results!")
        
        print()

if __name__ == "__main__":
    simulate_rapidfuzz_pipeline()
    analyze_jaro_winkler_pipeline()
    test_different_thresholds()