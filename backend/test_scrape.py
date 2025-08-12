#!/usr/bin/env python
"""Test scraping with 10 words across all dictionary providers."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from floridify.providers.dictionary.base import DictionaryConnector
from floridify.providers.connector import ConnectorConfig
from floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector
from floridify.providers.dictionary.api.oxford import OxfordConnector
from floridify.providers.dictionary.local.apple_dictionary import AppleDictionaryConnector
from floridify.providers.dictionary.scraper.wiktionary import WiktionaryConnector
from floridify.providers.dictionary.scraper.wordhippo import WordHippoConnector
from floridify.models.definition import Language

# Test words
TEST_WORDS = [
    "hello",
    "world",
    "python",
    "computer",
    "beautiful",
    "language",
    "dictionary",
    "example",
    "test",
    "work",
]


async def test_provider(connector: DictionaryConnector, name: str) -> dict:
    """Test a dictionary provider with sample words."""
    results = {"provider": name, "success": 0, "failed": 0, "words": []}
    
    for word in TEST_WORDS:
        try:
            print(f"  Testing '{word}'...", end=" ")
            result = await connector.fetch_definition(
                word,
                Language.ENGLISH,
            )
            
            if result and result.definitions:
                print(f"✓ ({len(result.definitions)} definitions)")
                results["success"] += 1
                results["words"].append(word)
            else:
                print("✗ (no definitions)")
                results["failed"] += 1
        except Exception as e:
            print(f"✗ ({e.__class__.__name__}: {e})")
            results["failed"] += 1
    
    return results


async def main():
    """Run tests across all providers."""
    print("Testing Dictionary Providers with 10 Words\n")
    print("=" * 50)
    
    # Initialize providers
    providers = [
        (FreeDictionaryConnector(), "FreeDictionary"),
        (WiktionaryConnector(), "Wiktionary"),
    ]
    
    # Add platform-specific providers
    import platform
    if platform.system() == "Darwin":
        providers.append((AppleDictionaryConnector(), "Apple Dictionary"))
    
    # Add providers that require API keys (skip if not configured)
    try:
        providers.append((OxfordConnector(), "Oxford"))
    except Exception:
        print("Oxford connector not configured (API key required)")
    
    try:
        providers.append((WordHippoConnector(), "WordHippo"))
    except Exception:
        print("WordHippo connector initialization failed")
    
    # Test each provider
    all_results = []
    for connector, name in providers:
        print(f"\nTesting {name}:")
        print("-" * 30)
        
        try:
            results = await test_provider(connector, name)
            all_results.append(results)
            print(f"Summary: {results['success']}/{len(TEST_WORDS)} successful")
        except Exception as e:
            print(f"Provider failed: {e}")
    
    # Print overall summary
    print("\n" + "=" * 50)
    print("Overall Summary:")
    print("-" * 30)
    
    for result in all_results:
        success_rate = (result["success"] / len(TEST_WORDS)) * 100
        print(f"{result['provider']:20} {result['success']:2}/{len(TEST_WORDS):2} ({success_rate:.0f}%)")
    
    # Check for regressions
    total_success = sum(r["success"] for r in all_results)
    total_tests = len(all_results) * len(TEST_WORDS)
    overall_rate = (total_success / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\nOverall Success Rate: {overall_rate:.1f}%")
    
    if overall_rate < 50:
        print("\n⚠️ WARNING: Low success rate detected - possible regression")
        return 1
    else:
        print("\n✅ No major regressions detected")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)