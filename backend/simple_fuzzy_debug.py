#!/usr/bin/env python3
"""
Simple debug script to test fuzzy search algorithms directly.
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

def test_rapidfuzz_algorithms():
    """Test different RapidFuzz algorithms and scorers."""
    print("🧪 Testing RapidFuzz Algorithms")
    print("=" * 60)
    
    test_cases = [
        ("enui", "ennui"),
        ("en coulise", "en coulisse"), 
    ]
    
    # Different scorers to test
    scorers = [
        ("WRatio", fuzz.WRatio),
        ("ratio", fuzz.ratio),
        ("partial_ratio", fuzz.partial_ratio), 
        ("token_sort_ratio", fuzz.token_sort_ratio),
        ("token_set_ratio", fuzz.token_set_ratio),
        ("QRatio", fuzz.QRatio),
    ]
    
    for query, expected in test_cases:
        print(f"\n🎯 Query: '{query}' → Expected: '{expected}'")
        print("-" * 40)
        
        # Test direct scoring between query and expected
        print(f"Direct scoring between '{query}' and '{expected}':")
        for scorer_name, scorer in scorers:
            score = scorer(query.lower(), expected.lower()) / 100.0
            print(f"  {scorer_name:15}: {score:.3f}")
        
        print("\nTop matches using different scorers:")
        for scorer_name, scorer in scorers:
            results = process.extract(
                query.lower(),
                [w.lower() for w in test_vocabulary],
                limit=3,
                scorer=scorer,
            )
            print(f"  {scorer_name:15}: {results}")
        print()

def test_jaro_winkler():
    """Test Jaro-Winkler algorithm."""
    print("🧪 Testing Jaro-Winkler Algorithm") 
    print("=" * 60)
    
    test_cases = [
        ("enui", "ennui"),
        ("en coulise", "en coulisse"),
    ]
    
    for query, expected in test_cases:
        print(f"\n🎯 Query: '{query}' → Expected: '{expected}'")
        print("-" * 40)
        
        # Test direct scoring
        jw_score = jellyfish.jaro_winkler_similarity(query.lower(), expected.lower())
        jaro_score = jellyfish.jaro_similarity(query.lower(), expected.lower())
        
        print("Direct scoring:")
        print(f"  Jaro-Winkler: {jw_score:.3f}")
        print(f"  Jaro:         {jaro_score:.3f}")
        
        # Test against all vocabulary
        print("\nTop Jaro-Winkler matches:")
        jw_results = []
        for word in test_vocabulary:
            score = jellyfish.jaro_winkler_similarity(query.lower(), word.lower())
            jw_results.append((word, score))
        
        jw_results.sort(key=lambda x: x[1], reverse=True)
        for i, (word, score) in enumerate(jw_results[:5]):
            marker = "✅" if word == expected else "  "
            print(f"  {marker} {i+1}. '{word}' ({score:.3f})")
        print()

def analyze_length_correction():
    """Analyze the length correction logic from the codebase."""
    print("📏 Analyzing Length Correction Logic")
    print("=" * 60)
    
    def apply_length_correction(query: str, candidate: str, base_score: float) -> float:
        """Simplified version of the length correction from fuzzy.py"""
        # No correction needed for perfect matches
        if base_score >= 0.99:
            return base_score

        query_len = len(query)
        candidate_len = len(candidate)
        is_candidate_phrase = " " in candidate
        is_query_phrase = " " in query
        
        query_lower = query.lower()
        candidate_lower = candidate.lower()

        # Check if query is a prefix of the candidate
        is_prefix_match = candidate_lower.startswith(query_lower)

        # Check if query matches the first word of a phrase exactly
        first_word_match = False
        if is_candidate_phrase and not is_query_phrase:
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
            phrase_penalty = 0.7
        elif not is_query_phrase and is_candidate_phrase:
            if is_prefix_match or first_word_match:
                phrase_penalty = 1.2
            else:
                phrase_penalty = 0.95
        elif is_query_phrase and is_candidate_phrase:
            phrase_penalty = 1.1 if length_ratio > 0.6 else 1.0

        # Short fragment penalty
        if candidate_len <= 3 and query_len > 6:
            short_penalty = 0.5
        elif candidate_len < query_len * 0.5:
            short_penalty = 0.75
        else:
            short_penalty = 1.0

        # Prefix match bonus
        prefix_bonus = 1.3 if is_prefix_match else 1.0

        # First word match bonus
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

        return max(0.0, min(1.0, corrected_score))
    
    test_cases = [
        ("enui", "ennui", 0.8),
        ("en coulise", "en coulisse", 0.9),
        ("en", "en coulisse", 0.5),
    ]
    
    for query, candidate, base_score in test_cases:
        corrected = apply_length_correction(query, candidate, base_score)
        
        print(f"\nQuery: '{query}' → Candidate: '{candidate}'")
        print(f"  Base score: {base_score:.3f}")
        print(f"  Corrected:  {corrected:.3f}")
        print(f"  Query is phrase: {' ' in query}")
        print(f"  Candidate is phrase: {' ' in candidate}")
        print(f"  Is prefix match: {candidate.lower().startswith(query.lower())}")
        
        # Calculate components
        query_len = len(query)
        candidate_len = len(candidate)
        length_ratio = min(query_len, candidate_len) / max(query_len, candidate_len)
        print(f"  Length ratio: {length_ratio:.3f}")

def simulate_candidate_selection():
    """Simulate the candidate selection logic."""
    print("🎯 Simulating Candidate Selection")
    print("=" * 60)
    
    # Create simplified indices
    vocabulary = test_vocabulary
    length_groups = {}
    prefix_groups = {}
    
    for i, word in enumerate(vocabulary):
        word_len = len(word)
        word_lower = word.lower()
        
        # Length indexing
        if word_len not in length_groups:
            length_groups[word_len] = []
        length_groups[word_len].append(i)
        
        # Prefix indexing (2-3 chars)
        prefix_len = min(3, max(2, word_len // 3))
        prefix = word_lower[:prefix_len]
        if prefix not in prefix_groups:
            prefix_groups[prefix] = []
        prefix_groups[prefix].append(i)
    
    print(f"Length groups: {length_groups}")
    print(f"Prefix groups: {prefix_groups}")
    print()
    
    def get_candidates(query, length_tolerance=2):
        """Get candidates like the corpus does."""
        query_len = len(query)
        prefix = query[:2] if query_len <= 4 else None
        
        candidate_set = set()
        
        # Length-based candidates
        for length in range(max(1, query_len - length_tolerance), query_len + length_tolerance + 1):
            if length in length_groups:
                candidate_set.update(length_groups[length])
        
        # Add prefix-based candidates if provided
        if prefix:
            prefix_lower = prefix.lower()
            for stored_prefix, indices in prefix_groups.items():
                if stored_prefix.startswith(prefix_lower):
                    candidate_set.update(indices)
        
        return [vocabulary[i] for i in candidate_set]
    
    test_queries = ["enui", "en coulise", "en"]
    
    for query in test_queries:
        candidates = get_candidates(query)
        print(f"Query: '{query}' → {len(candidates)} candidates")
        print(f"  Candidates: {candidates}")
        print()

if __name__ == "__main__":
    test_rapidfuzz_algorithms()
    test_jaro_winkler() 
    analyze_length_correction()
    simulate_candidate_selection()