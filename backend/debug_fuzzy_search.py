#!/usr/bin/env python3
"""
Debug script to investigate fuzzy search failures.

Tests the specific cases:
1. "enui" doesn't return "ennui" 
2. "en coulise" doesn't return "en coulisse"
"""

import asyncio

from rapidfuzz import fuzz, process

from src.floridify.search.constants import DEFAULT_MIN_SCORE, FuzzySearchMethod
from src.floridify.search.corpus.core import Corpus
from src.floridify.search.fuzzy import FuzzySearch

# Test data - create a minimal corpus with our problem words
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
    # Add some other similar words for context
    "en route",
    "en effet",
    "en fait",
    "bonjour",
    "hello",
    "monde"
]

async def debug_fuzzy_search():
    """Debug the fuzzy search implementation."""
    print("🔍 Debugging Fuzzy Search Implementation")
    print("=" * 60)
    
    # Create test corpus
    print("Creating test corpus...")
    corpus = await Corpus.create("test", test_vocabulary)
    print(f"Corpus created with {len(corpus.vocabulary)} words")
    print(f"Vocabulary: {corpus.vocabulary}")
    print()
    
    # Initialize fuzzy search
    fuzzy_search = FuzzySearch(min_score=DEFAULT_MIN_SCORE)
    
    # Test cases
    test_cases = [
        ("enui", "ennui", "Should find 'ennui' for 'enui'"),
        ("en coulise", "en coulisse", "Should find 'en coulisse' for 'en coulise'"),
        ("ennui", "ennui", "Exact match test"),
        ("en coulisse", "en coulisse", "Exact phrase match test"),
    ]
    
    for query, expected, description in test_cases:
        print(f"🧪 Test Case: {description}")
        print(f"Query: '{query}' → Expected: '{expected}'")
        print("-" * 40)
        
        # Test with different methods
        for method in [FuzzySearchMethod.AUTO, FuzzySearchMethod.RAPIDFUZZ, FuzzySearchMethod.JARO_WINKLER]:
            print(f"\n📊 Method: {method.value}")
            
            # Get fuzzy matches
            matches = fuzzy_search.search(
                query=query,
                corpus=corpus,
                max_results=10,
                method=method,
                min_score=0.1  # Lower threshold to see more results
            )
            
            print(f"Found {len(matches)} matches:")
            for i, match in enumerate(matches[:5]):  # Show top 5
                found_expected = "✅" if match.word == expected else "❌"
                print(f"  {i+1}. {found_expected} '{match.word}' (score: {match.score:.3f})")
            
            # Check if expected word was found
            expected_found = any(match.word == expected for match in matches)
            if expected_found:
                expected_match = next(match for match in matches if match.word == expected)
                print(f"✅ Expected word found with score: {expected_match.score:.3f}")
            else:
                print(f"❌ Expected word '{expected}' NOT found")
                
            print()
        
        # Test raw RapidFuzz scoring
        print("🔬 Raw RapidFuzz Analysis:")
        candidates = [word for word in corpus.vocabulary]
        
        # Test different scorers
        scorers = [
            ("WRatio", fuzz.WRatio),
            ("ratio", fuzz.ratio), 
            ("partial_ratio", fuzz.partial_ratio),
            ("token_sort_ratio", fuzz.token_sort_ratio),
        ]
        
        for scorer_name, scorer in scorers:
            results = process.extract(
                query.lower(),
                [w.lower() for w in candidates],
                limit=3,
                scorer=scorer,
            )
            print(f"  {scorer_name}: {results}")
        
        print("=" * 60)
        print()

def analyze_length_correction():
    """Analyze the length correction logic."""
    print("📏 Analyzing Length Correction Logic")
    print("-" * 40)
    
    # Test the length correction function directly
    fuzzy_search = FuzzySearch()
    
    test_cases = [
        ("enui", "ennui", 0.8),  # Missing one character
        ("en coulise", "en coulisse", 0.9),  # Missing one character in phrase
        ("en", "en coulisse", 0.5),  # Very short query vs long phrase
    ]
    
    for query, candidate, base_score in test_cases:
        is_query_phrase = " " in query.strip()
        corrected_score = fuzzy_search._apply_length_correction(
            query, candidate, base_score, is_query_phrase
        )
        
        print(f"Query: '{query}' → Candidate: '{candidate}'")
        print(f"  Base score: {base_score:.3f}")
        print(f"  Corrected score: {corrected_score:.3f}")
        print(f"  Is query phrase: {is_query_phrase}")
        print(f"  Is candidate phrase: {' ' in candidate}")
        print(f"  Length ratio: {min(len(query), len(candidate)) / max(len(query), len(candidate)):.3f}")
        print()

def analyze_candidate_selection():
    """Analyze how candidates are selected."""
    print("🎯 Analyzing Candidate Selection")
    print("-" * 40)
    
    async def test_candidates():
        corpus = await Corpus.create("test", test_vocabulary)
        
        test_queries = ["enui", "en coulise"]
        
        for query in test_queries:
            print(f"Query: '{query}' (length: {len(query)})")
            
            # Get candidates using the same logic as fuzzy search
            candidates = corpus.get_candidates_optimized(
                query_len=len(query),
                prefix=query[:2] if len(query) <= 4 else None,
                length_tolerance=2,
                max_candidates=1000
            )
            
            print(f"Selected {len(candidates)} candidates:")
            candidate_words = corpus.get_words_by_indices(candidates)
            for i, word in enumerate(candidate_words):
                print(f"  {i+1}. '{word}' (length: {len(word)})")
            print()
    
    asyncio.run(test_candidates())

if __name__ == "__main__":
    # Run all analyses
    asyncio.run(debug_fuzzy_search())
    analyze_length_correction() 
    analyze_candidate_selection()