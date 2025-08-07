#!/usr/bin/env python3
"""
Test the actual search system to see if we can reproduce the reported issues.
"""
import asyncio
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_with_minimal_setup():
    """Test fuzzy search with a minimal setup."""
    try:
        from floridify.search.constants import FuzzySearchMethod
        from floridify.search.corpus.core import Corpus
        from floridify.search.fuzzy import FuzzySearch
        
        # Create a comprehensive French test corpus
        french_vocabulary = [
            # The target words
            "ennui", "en coulisse", "coulisse", "enquête",
            
            # Similar/interfering words
            "ennuie", "ennuyé", "ennuyer", "ennuyeux", 
            "enquêter", "enquêteur",
            "coulis", "couloir", "couleurs", "couler",
            "coulisser", "coulissé", "coulissant",
            
            # French phrases with "en"
            "en route", "en effet", "en fait", "en plus", "en cours",
            "en train", "en avant", "en arrière", "en haut", "en bas",
            "en couleur", "en couleurs",
            
            # Other common French words
            "bonjour", "bonsoir", "merci", "oui", "non",
            "maintenant", "aujourd'hui", "hier", "demain",
            "monde", "maison", "famille", "temps", "nuit",
        ]
        
        print("🧪 Testing Real Search System")
        print("=" * 60)
        
        # Create corpus
        corpus = await Corpus.create("test_french", french_vocabulary)
        print(f"Created corpus with {len(corpus.vocabulary)} words")
        
        # Initialize fuzzy search
        fuzzy_search = FuzzySearch(min_score=0.6)  # Default threshold
        
        # Test problematic cases
        test_cases = [
            ("enui", "ennui", "Missing 'n' - should find ennui"),
            ("en coulise", "en coulisse", "Missing 's' - should find en coulisse"),
            ("couli", "coulisse", "Partial match - might prefer coulis incorrectly"),
            ("enquete", "enquête", "Missing accent - should find enquête"),
            ("enu", "ennui", "Very short partial - might fail"),
        ]
        
        for query, expected, description in test_cases:
            print(f"\n🎯 {description}")
            print(f"   Query: '{query}' → Expected: '{expected}'")
            print("-" * 40)
            
            # Test with different methods
            methods = [
                (FuzzySearchMethod.AUTO, "Auto"),
                (FuzzySearchMethod.RAPIDFUZZ, "RapidFuzz"),
                (FuzzySearchMethod.JARO_WINKLER, "Jaro-Winkler"),
            ]
            
            for method, method_name in methods:
                matches = fuzzy_search.search(
                    query=query,
                    corpus=corpus,
                    max_results=5,
                    method=method,
                    min_score=0.1  # Lower threshold to see all results
                )
                
                print(f"   📊 {method_name}:")
                if not matches:
                    print("      ❌ No matches found")
                    continue
                
                # Check if expected word is found
                expected_found = False
                expected_rank = None
                
                for i, match in enumerate(matches):
                    marker = ""
                    if match.word == expected:
                        expected_found = True
                        expected_rank = i + 1
                        marker = "✅"
                    
                    threshold_pass = "✅" if match.score >= 0.6 else "❌"
                    print(f"      {marker} {i+1}. '{match.word}': {match.score:.3f} {threshold_pass}")
                
                if expected_found:
                    print(f"      ✅ Expected word found at rank #{expected_rank}")
                else:
                    print(f"      ❌ Expected word '{expected}' NOT found")
            
            print()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This script needs to be run from the backend directory with proper dependencies")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_minimal_setup())