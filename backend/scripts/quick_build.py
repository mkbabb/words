#!/usr/bin/env python3
"""Quick build - English corpus + search indices only."""

import asyncio
import time

from floridify.corpus.language.core import LanguageCorpus
from floridify.models.base import Language
from floridify.search.core import Search
from floridify.storage.mongodb import init_db
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def main():
    print("="*80)
    print("QUICK BUILD - English Corpus + Search Indices")
    print("="*80 + "\n")

    await init_db()

    # Build corpus
    print("[1/3] Building English corpus from all sources...")
    start = time.time()
    corpus = await LanguageCorpus.create_from_language(
        corpus_name="language_english",
        language=Language.ENGLISH,
        semantic=False,
    )
    elapsed = time.time() - start
    print(f"      ✓ Built in {elapsed:.1f}s")
    print(f"      ✓ Vocabulary: {len(corpus.vocabulary):,} words")

    if len(corpus.vocabulary) == 0:
        print("      ✗ FAILED - Corpus has 0 words!")
        return False

    print(f"      ✓ First 10: {corpus.vocabulary[:10]}\n")

    # Build search indices
    print("[2/3] Building search indices...")
    start = time.time()
    search = await Search.from_corpus(
        corpus_name="language_english",
        semantic=False,
    )
    elapsed = time.time() - start
    print(f"      ✓ Built in {elapsed:.1f}s")
    print(f"      ✓ Trie: {search.trie_search is not None}")
    print(f"      ✓ Fuzzy: {search.fuzzy_search is not None}\n")

    # Test search
    print("[3/3] Testing search...")
    test_words = ["hello", "world", "test", "computer", "python"]
    for word in test_words:
        results = search.search_exact(word)
        found = "✓" if results else "✗"
        print(f"      {found} '{word}': {len(results)} results")

    print("\n" + "="*80)
    print("BUILD COMPLETE")
    print("="*80)
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
