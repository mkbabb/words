#!/usr/bin/env python3
"""
Test the length correction algorithm to identify overly aggressive penalties.
"""

from rapidfuzz import fuzz, process


def apply_length_correction(query: str, candidate: str, base_score: float, is_query_phrase: bool) -> float:
    """Exact implementation from fuzzy.py"""
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

def analyze_length_correction_components():
    """Analyze individual components of length correction."""
    print("🔬 Analyzing Length Correction Components")
    print("=" * 70)
    
    # Test cases that might reveal overly aggressive penalties
    test_cases = [
        # (query, candidate, expected_base_score, description)
        ("enui", "ennui", 0.889, "Missing single character"),
        ("en coulise", "en coulisse", 0.952, "Missing single character in phrase"),  
        ("couli", "coulisse", 0.900, "Partial match - might be too aggressive"),
        ("couli", "coulis", 0.909, "Partial match vs exact shorter word"),
        ("en", "en coulisse", 0.500, "Very short query vs phrase"),
        ("enn", "ennui", 0.750, "Short partial vs full word"),
        ("coul", "coulisse", 0.857, "Partial match medium length"),
    ]
    
    for query, candidate, base_score, description in test_cases:
        print(f"\n🎯 Test: {description}")
        print(f"   '{query}' → '{candidate}' (base: {base_score:.3f})")
        print("-" * 50)
        
        is_query_phrase = " " in query.strip()
        is_candidate_phrase = " " in candidate.strip()
        
        # Calculate individual components
        query_len = len(query)
        candidate_len = len(candidate)
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
        
        # Phrase penalty
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
        
        # Short penalty
        if candidate_len <= 3 and query_len > 6:
            short_penalty = 0.5
        elif candidate_len < query_len * 0.5:
            short_penalty = 0.75
        else:
            short_penalty = 1.0
        
        prefix_bonus = 1.3 if is_prefix_match else 1.0
        first_word_bonus = 1.2 if first_word_match else 1.0
        
        # Calculate final score
        corrected_score = apply_length_correction(query, candidate, base_score, is_query_phrase)
        
        print("   Components:")
        print(f"     Length ratio: {length_ratio:.3f} (query: {query_len}, candidate: {candidate_len})")
        print(f"     Phrase penalty: {phrase_penalty:.3f}")
        print(f"     Short penalty: {short_penalty:.3f}")
        print(f"     Prefix bonus: {prefix_bonus:.3f} (is_prefix: {is_prefix_match})")
        print(f"     First word bonus: {first_word_bonus:.3f} (first_word: {first_word_match})")
        print(f"   Final score: {base_score:.3f} → {corrected_score:.3f}")
        
        # Check if penalties are too harsh
        total_penalty = (length_ratio * phrase_penalty * short_penalty * prefix_bonus * first_word_bonus)
        print(f"   Total multiplier: {total_penalty:.3f}")
        
        if corrected_score < 0.6 and base_score >= 0.8:
            print(f"   ⚠️  WARNING: High base score ({base_score:.3f}) reduced below threshold!")
        if total_penalty < 0.7:
            print(f"   ⚠️  WARNING: Very aggressive penalty (multiplier: {total_penalty:.3f})")

def test_problematic_scenarios():
    """Test scenarios where fuzzy search might be too aggressive."""
    print("\n🚨 Testing Potentially Problematic Scenarios")
    print("=" * 70)
    
    # French vocabulary focused on problematic words
    vocabulary = [
        "ennui", "ennuie", "ennuyé", "ennuyer",
        "en coulisse", "coulisse", "coulisser", "coulissé",
        "coulis", "couleur", "couloir", "couler",
        "enquête", "enquêter", "enquêteur", "enquete",
        "en route", "en effet", "en fait", "en avant",
        "ensemble", "enthousiasme", "english", "energy",
    ]
    
    # Queries that might show aggressive behavior
    problematic_queries = [
        ("couli", ["coulisse", "coulis"], "Should prefer longer partial match over shorter exact"),
        ("enu", ["ennui", "ennuie"], "Very short query might fail completely"),
        ("en coul", ["en coulisse", "en couleur"], "Phrase partial should work well"),
        ("enquê", ["enquête", "enquêter"], "Accent partial should work"),
        ("coul", ["coulisse", "couleur", "couloir", "coulis"], "Multiple good matches"),
    ]
    
    for query, expected_candidates, description in problematic_queries:
        print(f"\n🎯 {description}")
        print(f"   Query: '{query}' → Expected in: {expected_candidates}")
        print("-" * 50)
        
        # Get RapidFuzz results
        results = process.extract(
            query,
            vocabulary,
            limit=5,
            scorer=fuzz.WRatio,
            processor=lambda s: s.lower(),
        )
        
        print("   RapidFuzz results with length correction:")
        is_query_phrase = " " in query.strip()
        
        found_expected = False
        for i, (word, score, _) in enumerate(results):
            base_score = score / 100.0
            corrected_score = apply_length_correction(query, word, base_score, is_query_phrase)
            
            is_expected = word in expected_candidates
            if is_expected:
                found_expected = True
            
            marker = "✅" if is_expected else "  "
            threshold_marker = "✅" if corrected_score >= 0.6 else "❌"
            print(f"     {marker} {i+1}. '{word}': {base_score:.3f} → {corrected_score:.3f} {threshold_marker}")
        
        if not found_expected:
            print("   ❌ None of the expected candidates found in top 5!")

def test_threshold_sensitivity():
    """Test how sensitive the system is to threshold changes."""
    print("\n📊 Threshold Sensitivity for Edge Cases")
    print("=" * 70)
    
    vocabulary = ["ennui", "ennuie", "coulisse", "coulis", "enquête", "enquete", "en coulisse"]
    
    edge_cases = [
        ("enui", "ennui", "Single missing character"),
        ("couli", "coulisse", "Partial vs shorter exact match"),
        ("enquete", "enquête", "Missing diacritic"),
    ]
    
    thresholds = [0.4, 0.5, 0.6, 0.7, 0.8]
    
    for query, expected, description in edge_cases:
        print(f"\n🎯 {description}: '{query}' → '{expected}'")
        
        results = process.extract(query, vocabulary, limit=1, scorer=fuzz.WRatio, processor=lambda s: s.lower())
        
        if results and results[0][0] == expected:
            base_score = results[0][1] / 100.0
            is_query_phrase = " " in query.strip()
            corrected_score = apply_length_correction(query, expected, base_score, is_query_phrase)
            
            print(f"   Base score: {base_score:.3f}, Corrected: {corrected_score:.3f}")
            
            for threshold in thresholds:
                passes = corrected_score >= threshold
                status = "✅ PASS" if passes else "❌ FAIL"
                print(f"   {threshold:.1f}: {status}")
        else:
            print("   ❌ Expected word not found as top match")

if __name__ == "__main__":
    analyze_length_correction_components()
    test_problematic_scenarios() 
    test_threshold_sensitivity()