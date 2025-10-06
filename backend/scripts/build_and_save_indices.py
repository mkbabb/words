#!/usr/bin/env python3
"""Build and properly save all search indices for language_english_full corpus."""

import asyncio
import time
from floridify.search.core import Search
from floridify.search.models import SearchIndex, TrieIndex
from floridify.search.semantic.models import SemanticIndex
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.storage.mongodb import init_db
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def build_and_save_indices():
    """Build all indices and ensure they're properly saved."""

    # Initialize database
    await init_db()

    # Get the corpus
    manager = get_tree_corpus_manager()
    corpus = await manager.get_corpus(corpus_name='language_english_full')

    if not corpus:
        print("❌ Corpus 'language_english_full' not found!")
        return

    print(f"✅ Found corpus with {len(corpus.vocabulary):,} words")

    # Build Search with semantic enabled - this should create all indices
    print("\n🔨 Building search engine (this will create all indices)...")
    start = time.time()

    search = await Search.from_corpus(
        corpus_name='language_english_full',
        semantic_model="Alibaba-NLP/gte-Qwen2-1.5B-instruct"
    )

    elapsed = time.time() - start
    print(f"✅ Search engine built in {elapsed:.2f}s")

    # Now verify the indices were saved
    print("\n📦 Verifying saved indices...")

    # Check SearchIndex
    search_idx = await SearchIndex.get(corpus_name='language_english_full')
    if search_idx:
        print(f"✅ SearchIndex saved: {search_idx.resource_id}")
    else:
        print("❌ SearchIndex NOT saved")

    # Check TrieIndex
    trie_idx = await TrieIndex.get(corpus_name='language_english_full')
    if trie_idx:
        print(f"✅ TrieIndex saved: {trie_idx.resource_id}")
    else:
        print("❌ TrieIndex NOT saved")

    # Check SemanticIndex
    semantic_idx = await SemanticIndex.get(
        corpus_name='language_english_full',
        model_name="Alibaba-NLP/gte-Qwen2-1.5B-instruct"
    )
    if semantic_idx:
        print(f"✅ SemanticIndex saved: {semantic_idx.resource_id}")
        print(f"   Embeddings: {semantic_idx.num_embeddings:,}")
        print(f"   Memory: {semantic_idx.memory_usage_mb:.2f}MB")
    else:
        print("❌ SemanticIndex NOT saved")

    # Test that search is now fast
    print("\n⚡ Testing search performance...")
    start = time.time()
    results = await search.search("hello", max_results=3)
    elapsed = (time.time() - start) * 1000
    print(f"Search completed in {elapsed:.2f}ms")
    if results:
        print(f"Found: {results[0].word}")

    # Now test loading from cache
    print("\n🔄 Testing load from cache (should be instant)...")
    start = time.time()
    search2 = await Search.from_corpus(corpus_name='language_english_full')
    elapsed = time.time() - start
    print(f"Search engine loaded in {elapsed:.2f}s")

    # Test search again
    start = time.time()
    results = await search2.search("hello", max_results=3)
    elapsed = (time.time() - start) * 1000
    print(f"Search completed in {elapsed:.2f}ms")

    print("\n✅ All done!")


if __name__ == "__main__":
    asyncio.run(build_and_save_indices())