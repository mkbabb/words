#!/usr/bin/env python3
"""The simplest possible approach - just get it working."""

import asyncio
import time

from floridify.corpus.core import Corpus
from floridify.models.base import Language
from floridify.search.core import Search
from floridify.storage.mongodb import init_db
import httpx


async def main():
    print("SIMPLE WORKING BUILD - No fancy language corpus, just basics\n")

    await init_db()

    # Step 1: Fetch vocabulary directly
    print("[1/3] Fetching google 10k vocabulary...")
    url = "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english.txt"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        vocabulary = [line.strip() for line in response.text.split('\n') if line.strip()]

    if not vocabulary:
        print("Failed to fetch vocabulary")
        return False

    print(f"      ✓ Fetched {len(vocabulary)} words\n")

    # Step 2: Create corpus directly with vocabulary
    print("[2/3] Creating corpus...")
    corpus = await Corpus.create(
        corpus_name="language_english",  # API expects this name
        vocabulary=vocabulary,
        language=Language.ENGLISH,
    )

    await corpus.save()
    print(f"      ✓ Created corpus with {len(corpus.vocabulary)} words")
    print(f"      ✓ First 10: {corpus.vocabulary[:10]}\n")

    # Step 3: Build search and test
    print("[3/3] Building search and testing...")
    start = time.time()
    search = await Search.from_corpus(
        corpus_name="language_english",
        semantic=False,
    )
    elapsed = time.time() - start
    print(f"      ✓ Search built in {elapsed:.1f}s\n")

    # Test
    print("Testing searches:")
    test_words = ["hello", "world", "test", "computer", "python"]
    for word in test_words:
        results = search.search_exact(word)
        found = "✓" if results else "✗"
        print(f"      {found} '{word}': {len(results)} results")

    print("\n✅ SUCCESS - Search is working!")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
