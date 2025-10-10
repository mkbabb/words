#!/usr/bin/env python3
"""Test if parent corpus aggregates child vocabularies."""

import asyncio

from floridify.corpus.core import Corpus
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.caching.models import VersionConfig
from floridify.models.base import Language
from floridify.storage.mongodb import init_db

async def test():
    await init_db()
    manager = get_tree_corpus_manager()

    print("1. Creating parent corpus (master)...")
    parent = await Corpus.create(
        corpus_name="test_parent",
        vocabulary=[],  # Empty vocabulary
        language=Language.ENGLISH,
    )
    parent.is_master = True
    await parent.save()
    print(f"   Parent created with {len(parent.vocabulary)} words, is_master={parent.is_master}")

    print("\n2. Creating child corpus 1...")
    child1 = await Corpus.create(
        corpus_name="test_child1",
        vocabulary=["hello", "world"],
        language=Language.ENGLISH,
    )
    await child1.save()
    print(f"   Child 1 created with {len(child1.vocabulary)} words")

    print("\n3. Adding child to parent...")
    await manager.update_parent(parent.corpus_id, child1.corpus_id)
    print(f"   Child added")

    print("\n4. Aggregating vocabularies...")
    aggregated = await manager.aggregate_vocabularies(
        parent.corpus_id,
        update_parent=True
    )
    print(f"   Aggregated {len(aggregated)} words: {aggregated}")

    print("\n5. Reloading parent from DB...")
    reloaded = await manager.get_corpus(
        corpus_id=parent.corpus_id,
        config=VersionConfig(use_cache=False)
    )

    if reloaded:
        print(f"   ✓ Reloaded parent")
        print(f"   ✓ Vocabulary: {len(reloaded.vocabulary)} words")
        print(f"   ✓ Words: {reloaded.vocabulary}")
        print(f"   ✓ Children: {len(reloaded.child_corpus_ids)}")

        if len(reloaded.vocabulary) == 2:
            print("\n✅ SUCCESS - Aggregation works!")
            return True
        else:
            print(f"\n❌ FAILED - Expected 2 words, got {len(reloaded.vocabulary)}")
            return False
    else:
        print("\n❌ FAILED - Could not reload parent")
        return False

if __name__ == "__main__":
    result = asyncio.run(test())
    if result:
        exit(0)
    else:
        exit(1)
