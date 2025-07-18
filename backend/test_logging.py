#!/usr/bin/env python3
"""Test script to verify comprehensive logging in pipelines."""

import asyncio
import logging
from rich.console import Console
from rich.logging import RichHandler

# Configure logging with Rich handler for beautiful output
logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=Console(stderr=True), rich_tracebacks=True)]
)

# Import after logging is configured
from floridify.core.lookup_pipeline import lookup_word_pipeline
from floridify.core.search_pipeline import search_word_pipeline
from floridify.constants import DictionaryProvider, Language


async def test_search_pipeline():
    """Test search pipeline with debug logging."""
    print("\n" + "="*60)
    print("TESTING SEARCH PIPELINE")
    print("="*60 + "\n")
    
    # Test various search scenarios
    test_words = [
        "efflorescence",  # Should find exact match
        "eflorescence",   # Should use fuzzy search
        "bloom",          # Common word, should be fast
        "xyzabc123"       # Should fail gracefully
    ]
    
    for word in test_words:
        print(f"\n🔍 Searching for: '{word}'")
        print("-" * 40)
        
        results = await search_word_pipeline(
            word=word,
            languages=[Language.ENGLISH],
            semantic=False,
            max_results=5
        )
        
        print(f"\n📊 Results: {len(results)} found")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result.word} (score: {result.score:.3f}, method: {result.method})")


async def test_lookup_pipeline():
    """Test lookup pipeline with debug logging."""
    print("\n" + "="*60)
    print("TESTING LOOKUP PIPELINE")
    print("="*60 + "\n")
    
    # Test lookup with AI synthesis
    test_cases = [
        ("flourish", [DictionaryProvider.WIKTIONARY], False),  # Normal lookup
        ("efflorescence", [DictionaryProvider.WIKTIONARY], False),  # Complex word
        ("asdfghjkl", [DictionaryProvider.WIKTIONARY], False),  # Should trigger AI fallback
    ]
    
    for word, providers, no_ai in test_cases:
        print(f"\n📚 Looking up: '{word}'")
        print(f"   Providers: {[p.value for p in providers]}")
        print(f"   AI enabled: {not no_ai}")
        print("-" * 40)
        
        result = await lookup_word_pipeline(
            word=word,
            providers=providers,
            languages=[Language.ENGLISH],
            semantic=False,
            no_ai=no_ai,
            force_refresh=True  # Force fresh lookup to see all logging
        )
        
        if result:
            print(f"\n✅ Success! Found {len(result.definitions)} definitions")
            if result.definitions:
                print(f"   First definition: {result.definitions[0].definition[:100]}...")
        else:
            print(f"\n❌ No result found")


async def test_ai_synthesis():
    """Test AI synthesis with detailed logging."""
    print("\n" + "="*60)
    print("TESTING AI SYNTHESIS")
    print("="*60 + "\n")
    
    # This will test the full pipeline including clustering
    word = "bloom"
    print(f"🤖 Testing AI synthesis for: '{word}'")
    print("-" * 40)
    
    result = await lookup_word_pipeline(
        word=word,
        providers=[DictionaryProvider.WIKTIONARY],
        languages=[Language.ENGLISH],
        semantic=False,
        no_ai=False,
        force_refresh=True
    )
    
    if result and result.definitions:
        print(f"\n✅ Synthesis complete!")
        print(f"   Total definitions: {len(result.definitions)}")
        
        # Show cluster information
        clusters = {}
        for defn in result.definitions:
            cluster = defn.meaning_cluster or "unclustered"
            if cluster not in clusters:
                clusters[cluster] = []
            clusters[cluster].append(defn)
        
        print(f"   Clusters found: {len(clusters)}")
        for cluster_id, defs in clusters.items():
            print(f"     • {cluster_id}: {len(defs)} definitions")


async def main():
    """Run all tests."""
    console = Console()
    
    console.print("\n[bold blue]🧪 COMPREHENSIVE PIPELINE LOGGING TEST[/bold blue]\n")
    
    try:
        # Test search pipeline
        await test_search_pipeline()
        
        # Test lookup pipeline
        await test_lookup_pipeline()
        
        # Test AI synthesis
        await test_ai_synthesis()
        
        console.print("\n[bold green]✅ All tests completed![/bold green]\n")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())