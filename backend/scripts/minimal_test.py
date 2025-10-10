#!/usr/bin/env python3
"""Minimal test - can we save and load a corpus?"""

import asyncio

from floridify.corpus.core import Corpus
from floridify.caching.models import VersionConfig
from floridify.models.base import Language
from floridify.storage.mongodb import init_db

async def test():
    await init_db()

    # Create tiny corpus
    print("1. Creating tiny corpus...")
    corpus = await Corpus.create(
        corpus_name="test_minimal",
        vocabulary=["hello", "world", "test"],
        language=Language.ENGLISH,
    )

    print(f"   Created with {len(corpus.vocabulary)} words")

    # Save it
    print("2. Saving...")
    await corpus.save()
    print(f"   Saved with ID: {corpus.corpus_id}")

    # Try to load it back
    print("3. Loading from DB...")
    loaded = await Corpus.get(
        corpus_name="test_minimal",
        config=VersionConfig(use_cache=False)
    )

    if loaded:
        print(f"   ✓ Loaded: {loaded.corpus_name}")
        print(f"   ✓ Vocabulary: {len(loaded.vocabulary)} words")
        print(f"   ✓ Words: {loaded.vocabulary}")

        if len(loaded.vocabulary) == 3:
            print("\n✅ SUCCESS - Corpus persists correctly!")
            return True
        else:
            print(f"\n❌ FAILED - Expected 3 words, got {len(loaded.vocabulary)}")
            return False
    else:
        print("\n❌ FAILED - Could not load corpus from DB")
        return False

if __name__ == "__main__":
    result = asyncio.run(test())
    if result:
        exit(0)
    else:
        exit(1)
