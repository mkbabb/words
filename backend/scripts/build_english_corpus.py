#!/usr/bin/env python3
"""Build comprehensive English language corpus with tree structure.

This script creates a LANGUAGE-level master corpus with multiple child corpora
from all available English language sources, then tests all search functionality.
"""

import asyncio
import time
from datetime import datetime

from floridify.corpus.language.core import LanguageCorpus
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.models.base import Language
from floridify.search.constants import SearchMethod
from floridify.search.core import Search
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def build_english_corpus():
    """Build comprehensive English language corpus."""
    print("=" * 80)
    print("🏗️  BUILDING COMPREHENSIVE ENGLISH LANGUAGE CORPUS")
    print("=" * 80)
    print()

    start_time = time.time()

    # Create language corpus with all English sources
    # Use standard naming pattern: language_{language}
    print("📚 Step 1: Creating master language corpus...")
    corpus = await LanguageCorpus.create_from_language(
        corpus_name="language_english",  # Standard pattern: language_{language}
        language=Language.ENGLISH,
        semantic=True,  # Enable semantic search with GTE-Qwen2 (default model)
        # model_name defaults to DEFAULT_SENTENCE_MODEL (GTE-Qwen2-1.5B-instruct)
    )

    elapsed = time.time() - start_time
    print(f"✅ Master corpus created in {elapsed:.1f}s")
    print(f"   Corpus ID: {corpus.corpus_id}")
    print(f"   Total vocabulary: {len(corpus.vocabulary):,} unique words")
    print(f"   Children: {len(corpus.child_corpus_ids)}")
    print()

    # Display tree structure
    print("🌳 Step 2: Displaying corpus tree structure...")
    manager = get_tree_corpus_manager()

    if corpus.child_corpus_ids:
        print(f"\nMaster: {corpus.corpus_name}")
        print(f"  ├─ ID: {corpus.corpus_id}")
        print(f"  ├─ Vocabulary: {len(corpus.vocabulary):,} words")
        print(f"  └─ Children: {len(corpus.child_corpus_ids)}")

        for i, child_id in enumerate(corpus.child_corpus_ids):
            child = await manager.get_corpus(corpus_id=child_id)
            if child:
                is_last = i == len(corpus.child_corpus_ids) - 1
                prefix = "└──" if is_last else "├──"
                print(f"\n     {prefix} Child {i+1}: {child.corpus_name}")
                print(f"         ├─ ID: {child.corpus_id}")
                print(f"         ├─ Vocabulary: {len(child.vocabulary):,} words")
                print(f"         └─ Source: {child.corpus_type.value}")
    print()

    # Test vocabulary aggregation
    print("🔄 Step 3: Testing vocabulary aggregation...")
    if corpus.corpus_id:
        agg_start = time.time()
        aggregated_vocab = await manager.aggregate_vocabularies(corpus.corpus_id)
        agg_elapsed = time.time() - agg_start

        print(f"   ✅ Aggregated {len(aggregated_vocab):,} words in {agg_elapsed:.2f}s")
        print(f"   Match with master: {len(aggregated_vocab) == len(corpus.vocabulary)}")
    print()

    # Create search index
    print("🔎 Step 4: Building search indices...")
    search_start = time.time()

    search = await Search.from_corpus(
        corpus_name=corpus.corpus_name,
        semantic=True,
    )

    search_elapsed = time.time() - search_start
    print(f"   ✅ Search indices built in {search_elapsed:.1f}s")
    print(f"   Trie index: {'✓' if search.trie_search else '✗'}")
    print(f"   Fuzzy search: {'✓' if search.fuzzy_search else '✗'}")
    print(f"   Semantic search: {'✓' if search.semantic_search else '✗'}")
    print()

    return corpus, search


async def test_search_functionality(corpus, search):
    """Test all search methods on the corpus."""
    print("=" * 80)
    print("🧪 TESTING SEARCH FUNCTIONALITY")
    print("=" * 80)
    print()

    test_queries = [
        ("hello", "Common word - should find exact match"),
        ("wrld", "Typo - should find 'world' via fuzzy"),
        ("happiness", "Abstract concept - semantic similarity test"),
        ("xylophone", "Less common word - test coverage"),
        ("asdf", "Nonsense - should return no results or similar"),
    ]

    for query, description in test_queries:
        print(f"Query: '{query}'")
        print(f"Test: {description}")

        # Exact search
        exact_start = time.time()
        exact_results = await search.search(query, max_results=3, method=SearchMethod.EXACT)
        exact_time = (time.time() - exact_start) * 1000

        if exact_results:
            print(f"  ✓ Exact ({exact_time:.1f}ms): {exact_results[0].word} (score: {exact_results[0].score})")
        else:
            print(f"  ✗ Exact ({exact_time:.1f}ms): No results")

        # Fuzzy search
        fuzzy_start = time.time()
        fuzzy_results = await search.search(query, max_results=3, method=SearchMethod.FUZZY, min_score=0.6)
        fuzzy_time = (time.time() - fuzzy_start) * 1000

        if fuzzy_results:
            top_fuzzy = fuzzy_results[0]
            print(f"  ✓ Fuzzy ({fuzzy_time:.1f}ms): {top_fuzzy.word} (score: {top_fuzzy.score:.2f})")
            if len(fuzzy_results) > 1:
                print(f"     + {fuzzy_results[1].word} (score: {fuzzy_results[1].score:.2f})")
        else:
            print(f"  ✗ Fuzzy ({fuzzy_time:.1f}ms): No results")

        # Semantic search (if available)
        if search.semantic_search:
            semantic_start = time.time()
            semantic_results = await search.search(query, max_results=3, method=SearchMethod.SEMANTIC, min_score=0.5)
            semantic_time = (time.time() - semantic_start) * 1000

            if semantic_results:
                top_semantic = semantic_results[0]
                print(f"  ✓ Semantic ({semantic_time:.1f}ms): {top_semantic.word} (score: {top_semantic.score:.2f})")
                if len(semantic_results) > 1:
                    print(f"     + {semantic_results[1].word} (score: {semantic_results[1].score:.2f})")
            else:
                print(f"  ✗ Semantic ({semantic_time:.1f}ms): No results")

        # Cascade search (uses all methods - SMART mode)
        cascade_start = time.time()
        cascade_results = await search.search(query, max_results=5)
        cascade_time = (time.time() - cascade_start) * 1000

        if cascade_results:
            print(f"  ✓ Cascade ({cascade_time:.1f}ms): {len(cascade_results)} results")
            for result in cascade_results[:3]:
                print(f"     - {result.word} (score: {result.score:.2f}, method: {result.method.value})")
        else:
            print(f"  ✗ Cascade ({cascade_time:.1f}ms): No results")

        print()


async def generate_corpus_statistics(corpus, search):
    """Generate detailed statistics about the corpus."""
    print("=" * 80)
    print("📊 CORPUS STATISTICS")
    print("=" * 80)
    print()

    print(f"Master Corpus: {corpus.corpus_name}")
    print(f"  Language: {corpus.language.value}")
    print(f"  Type: {corpus.corpus_type.value}")
    print(f"  Is Master: {corpus.is_master}")
    print()

    print(f"Vocabulary:")
    print(f"  Total words: {len(corpus.vocabulary):,}")
    print(f"  Unique words: {corpus.unique_word_count:,}")
    print(f"  Vocabulary hash: {corpus.vocabulary_hash[:16]}...")
    print()

    print(f"Tree Structure:")
    print(f"  Children: {len(corpus.child_corpus_ids)}")
    print(f"  Parent: {corpus.parent_corpus_id or 'None (root)'}")
    print()

    print(f"Search Capabilities:")
    print(f"  Trie index: {search.trie_search is not None}")
    print(f"  Fuzzy search: {search.fuzzy_search is not None}")
    print(f"  Semantic search: {search.semantic_search is not None}")
    if search.semantic_search:
        print(f"  Embedding model: {corpus.metadata.get('model_name', 'N/A')}")
    print()

    print(f"Sample vocabulary (first 20):")
    for i, word in enumerate(corpus.vocabulary[:20]):
        print(f"  {i+1:2d}. {word}")
    print()


async def main():
    """Main execution."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "ENGLISH LANGUAGE CORPUS BUILDER" + " " * 26 + "║")
    print("║" + " " * 25 + "Comprehensive Test Suite" + " " * 29 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize database connection
    print("🔌 Initializing database connection...")
    from floridify.storage.mongodb import get_storage

    await get_storage()
    print("   ✅ Database connected")
    print()

    overall_start = time.time()

    # Build corpus
    corpus, search = await build_english_corpus()

    # Test search functionality
    await test_search_functionality(corpus, search)

    # Generate statistics
    await generate_corpus_statistics(corpus, search)

    overall_elapsed = time.time() - overall_start

    print("=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)
    print(f"Total time: {overall_elapsed:.1f}s ({overall_elapsed/60:.1f}m)")
    print(f"Corpus ID: {corpus.corpus_id}")
    print(f"Total vocabulary: {len(corpus.vocabulary):,} unique words")
    print()


if __name__ == "__main__":
    asyncio.run(main())
