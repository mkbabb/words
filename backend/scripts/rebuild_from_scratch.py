#!/usr/bin/env python3
"""Complete rebuild from scratch - no assumptions."""

import asyncio
import time

from floridify.corpus.language.core import LanguageCorpus
from floridify.models.base import Language
from floridify.search.core import Search
from floridify.storage.mongodb import init_db
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def rebuild_everything():
    """Rebuild corpus and search from absolute scratch."""

    print("\n" + "="*80)
    print("COMPLETE REBUILD FROM SCRATCH")
    print("="*80 + "\n")

    # Step 1: Initialize database
    print("[1/6] Initializing database...")
    await init_db()
    print("✓ Database initialized\n")

    # Step 2: Build English corpus from sources
    print("[2/6] Building English corpus from sources...")
    print("      This will download and process ~270k words from multiple sources")
    print("      Expected time: 2-5 minutes")

    start = time.time()
    corpus = await LanguageCorpus.create_from_language(
        corpus_name="language_english",
        language=Language.ENGLISH,
        semantic=False,  # We'll add semantic later
    )
    elapsed = time.time() - start

    print(f"✓ Corpus built in {elapsed:.1f}s")
    print(f"  - Corpus name: {corpus.corpus_name}")
    print(f"  - Vocabulary size: {len(corpus.vocabulary):,}")
    print(f"  - Sources: {len(corpus.sources)}")
    print(f"  - Child corpora: {len(corpus.child_corpus_ids)}")

    if len(corpus.vocabulary) == 0:
        print("\n❌ FAILED: Corpus has 0 vocabulary!")
        return None

    print(f"  - First 10 words: {corpus.vocabulary[:10]}")
    print()

    # Step 3: Verify persistence
    print("[3/6] Verifying corpus persistence...")
    from floridify.corpus.core import Corpus
    from floridify.caching.models import VersionConfig

    loaded = await Corpus.get(
        corpus_name="language_english",
        config=VersionConfig(use_cache=False)  # Force DB load
    )

    if not loaded:
        print("❌ FAILED: Could not reload corpus from database!")
        return None

    print(f"✓ Corpus reloaded from database")
    print(f"  - Vocabulary size: {len(loaded.vocabulary):,}")
    print(f"  - Hash: {loaded.vocabulary_hash[:16]}")
    print()

    # Step 4: Build search indices (without semantic for now)
    print("[4/6] Building search indices...")
    print("      Building Trie and Fuzzy search indices")

    start = time.time()
    search = await Search.from_corpus(
        corpus_name="language_english",
        semantic=False,  # Skip semantic for now
    )
    elapsed = time.time() - start

    print(f"✓ Search indices built in {elapsed:.1f}s")
    print(f"  - Trie search: {'✓' if search.trie_search else '✗'}")
    print(f"  - Fuzzy search: {'✓' if search.fuzzy_search else '✗'}")
    print()

    # Step 5: Test basic search
    print("[5/6] Testing basic search...")

    test_words = ["hello", "test", "the", "computer", "algorithm"]
    for word in test_words:
        results = search.search_exact(word)  # Not async
        status = "✓" if results else "✗"
        print(f"  {status} '{word}': {len(results)} results")

    print()

    # Step 6: Build semantic index
    print("[6/6] Building semantic index...")
    print("      This will take 15-20 minutes for ~270k words")
    print("      Model: Alibaba-NLP/gte-Qwen2-1.5B-instruct")
    print("      Please wait... (no timeout)")

    start = time.time()
    search_with_semantic = await Search.from_corpus(
        corpus_name="language_english",
        semantic=True,
    )

    # Wait for semantic to finish
    if search_with_semantic._semantic_init_task:
        print("      Waiting for semantic initialization...")
        await search_with_semantic.await_semantic_ready()

    elapsed = time.time() - start

    if search_with_semantic._semantic_ready:
        print(f"✓ Semantic index built in {elapsed/60:.1f} minutes")
        if search_with_semantic.semantic_search:
            print(f"  - Embeddings: {search_with_semantic.semantic_search.index.num_embeddings:,}")
            print(f"  - Dimensions: {search_with_semantic.semantic_search.index.embedding_dimension}")
    else:
        print(f"✗ Semantic build failed after {elapsed/60:.1f} minutes")
        if hasattr(search_with_semantic, '_semantic_init_error'):
            print(f"  Error: {search_with_semantic._semantic_init_error}")

    print()
    print("="*80)
    print("REBUILD COMPLETE")
    print("="*80)

    return {
        'corpus': corpus,
        'search': search_with_semantic,
    }


if __name__ == "__main__":
    result = asyncio.run(rebuild_everything())

    if result:
        print("\n✅ SUCCESS - System rebuilt and verified")
        print("\nNext steps:")
        print("  1. Test search via API: curl 'http://localhost:8000/api/v1/search/hello'")
        print("  2. Run benchmarks: python scripts/benchmark_performance.py")
    else:
        print("\n❌ FAILED - Check logs above for errors")
