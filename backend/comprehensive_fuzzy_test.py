#!/usr/bin/env python3
"""
Comprehensive test of fuzzy search with real French vocabulary to identify the problem.
"""

import jellyfish
from rapidfuzz import fuzz, process

# More comprehensive French vocabulary including the problematic cases
french_vocabulary = [
    # Core test words
    "ennui",
    "en coulisse",
    "coulisse",
    
    # Similar sounding/looking words that might interfere
    "ennuie", "ennuyé", "ennuyer", "ennuyeux", "ennuyeuse",
    "enquête", "enquêter", "enquêteur", 
    "enrôler", "enregistrer", "enrichir",
    "ensemble", "enthousiasme", "enthousiaste",
    "energy", "english", "enjoy",
    
    # French phrases starting with "en"
    "en route", "en effet", "en fait", "en plus", "en cours",
    "en train", "en avant", "en arrière", "en haut", "en bas",
    "en dehors", "en dedans", "en face", "en ligne",
    "en couleur", "en couleurs",
    
    # Words similar to "coulisse"  
    "coulisser", "coulissé", "coulissant", "coulissante",
    "couloir", "couleurs", "coulis", "couler",
    
    # Other French vocabulary for context
    "bonjour", "bonsoir", "salut", "merci", "s'il vous plaît",
    "oui", "non", "peut-être", "toujours", "jamais",
    "maintenant", "aujourd'hui", "hier", "demain",
    "monde", "maison", "famille", "ami", "amie",
    "temps", "jour", "nuit", "matin", "soir",
]

def comprehensive_fuzzy_test():
    """Run comprehensive tests with the full French vocabulary."""
    print("🧪 Comprehensive Fuzzy Search Test")
    print("=" * 70)
    print(f"Testing with {len(french_vocabulary)} French words")
    print()
    
    DEFAULT_MIN_SCORE = 0.6
    
    # Test cases that are reportedly failing
    failing_test_cases = [
        ("enui", "ennui", "Missing 'n' in 'ennui'"),
        ("en coulise", "en coulisse", "Missing 's' in 'en coulisse'"),
        ("couli", "coulisse", "Abbreviated form of 'coulisse'"),
        ("enquete", "enquête", "Missing accent in 'enquête'"),
    ]
    
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
    
    for query, expected, description in failing_test_cases:
        print(f"🎯 Test: {description}")
        print(f"   Query: '{query}' → Expected: '{expected}'")
        print("-" * 50)
        
        # Test RapidFuzz WRatio (used in the real implementation)
        results = process.extract(
            query,
            french_vocabulary,
            limit=len(french_vocabulary),
            scorer=fuzz.WRatio,
            processor=lambda s: s.lower(),
        )
        
        # Find the expected match
        expected_result = next((r for r in results if r[0] == expected), None)
        if not expected_result:
            print(f"   ❌ Expected word '{expected}' not found in RapidFuzz results at all!")
            continue
        
        expected_rank = results.index(expected_result) + 1
        base_score = expected_result[1] / 100.0
        is_query_phrase = " " in query.strip()
        corrected_score = apply_length_correction(query, expected, base_score, is_query_phrase)
        
        print(f"   📊 Expected match ranking: #{expected_rank}")
        print(f"   📊 Raw RapidFuzz score: {base_score:.3f}")
        print(f"   📊 After length correction: {corrected_score:.3f}")
        print(f"   📊 Passes threshold ({DEFAULT_MIN_SCORE}): {'✅ YES' if corrected_score >= DEFAULT_MIN_SCORE else '❌ NO'}")
        
        # Show top 5 matches
        print("   🔍 Top 5 matches:")
        for i, (word, score, _) in enumerate(results[:5]):
            base = score / 100.0
            corrected = apply_length_correction(query, word, base, is_query_phrase)
            marker = "✅" if word == expected else "  "
            threshold_marker = "✅" if corrected >= DEFAULT_MIN_SCORE else "❌"
            print(f"      {marker} {i+1}. '{word}': {base:.3f} → {corrected:.3f} {threshold_marker}")
        
        # Test Jaro-Winkler as well
        jw_score = jellyfish.jaro_winkler_similarity(query.lower(), expected.lower())
        print(f"   📊 Jaro-Winkler score: {jw_score:.3f}")
        print(f"   📊 JW passes threshold: {'✅ YES' if jw_score >= DEFAULT_MIN_SCORE else '❌ NO'}")
        
        print()

def test_threshold_sensitivity():
    """Test sensitivity to different minimum score thresholds."""
    print("📊 Threshold Sensitivity Analysis")
    print("=" * 70)
    
    test_cases = [
        ("enui", "ennui"),
        ("en coulise", "en coulisse"),
        ("couli", "coulisse"),
        ("enquete", "enquête"),
    ]
    
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    
    def apply_length_correction(query: str, candidate: str, base_score: float, is_query_phrase: bool) -> float:
        """Simplified version"""
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
    
    for query, expected in test_cases:
        print(f"🎯 '{query}' → '{expected}'")
        
        # Get RapidFuzz score
        results = process.extract(query, french_vocabulary, limit=1, scorer=fuzz.WRatio, processor=lambda s: s.lower())
        
        expected_result = next((r for r in results if r[0] == expected), None)
        if expected_result:
            base_score = expected_result[1] / 100.0
            is_query_phrase = " " in query.strip()
            corrected_score = apply_length_correction(query, expected, base_score, is_query_phrase)
            
            print(f"   Final score: {corrected_score:.3f}")
            for threshold in thresholds:
                status = "✅ PASS" if corrected_score >= threshold else "❌ FAIL"
                print(f"   {threshold:.1f}: {status}")
        else:
            print(f"   ❌ '{expected}' not found in results")
        print()

if __name__ == "__main__":
    comprehensive_fuzzy_test()
    test_threshold_sensitivity()