#!/usr/bin/env python
"""Verification script for cascade deletion implementation.

This script demonstrates that cascade deletion properly removes all
dependent indices when a Corpus is deleted, preventing orphaned documents.

Usage:
    python scripts/verify_cascade_deletion.py
"""

from __future__ import annotations

import asyncio

from floridify.caching.manager import get_version_manager
from floridify.caching.models import ResourceType
from floridify.corpus.core import Corpus
from floridify.models.base import Language
from floridify.search.models import SearchIndex, TrieIndex
from floridify.search.semantic.models import SemanticIndex
from floridify.storage.mongodb import init_db
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def verify_cascade_deletion():
    """Verify cascade deletion implementation."""
    # Initialize database
    await init_db()

    logger.info("=" * 80)
    logger.info("CASCADE DELETION VERIFICATION")
    logger.info("=" * 80)

    # Step 1: Create a corpus
    logger.info("\n[1] Creating test corpus...")
    vocabulary = ["apple", "banana", "cherry", "date", "elderberry"]
    corpus = await Corpus.create(
        corpus_name="cascade_verification_corpus",
        vocabulary=vocabulary,
        language=Language.ENGLISH,
        semantic=False,
    )
    await corpus.save()
    corpus_id = corpus.corpus_id
    corpus_name = corpus.corpus_name

    logger.info(f"✓ Created corpus: {corpus_name} (ID: {corpus_id})")

    # Step 2: Create TrieIndex
    logger.info("\n[2] Creating TrieIndex...")
    trie_index = await TrieIndex.create(corpus=corpus)
    await trie_index.save()
    logger.info(f"✓ Created TrieIndex with {trie_index.word_count} words")

    # Step 3: Create SemanticIndex
    logger.info("\n[3] Creating SemanticIndex...")
    semantic_index = await SemanticIndex.create(
        corpus=corpus,
        model_name="all-MiniLM-L6-v2",
    )
    await semantic_index.save()
    logger.info(f"✓ Created SemanticIndex with model {semantic_index.model_name}")

    # Step 4: Create SearchIndex
    logger.info("\n[4] Creating SearchIndex...")
    search_index = await SearchIndex.create(
        corpus=corpus,
        semantic=True,
        semantic_model="all-MiniLM-L6-v2",
    )
    search_index.trie_index_id = trie_index.index_id
    search_index.has_trie = True
    search_index.semantic_index_id = semantic_index.index_id
    search_index.has_semantic = True
    await search_index.save()
    logger.info(f"✓ Created SearchIndex with TrieIndex and SemanticIndex")

    # Step 5: Verify all exist
    logger.info("\n[5] Verifying all indices exist...")
    vm = get_version_manager()

    corpus_meta = await vm.get_latest(
        resource_id=corpus_name,
        resource_type=ResourceType.CORPUS,
    )
    assert corpus_meta is not None, "Corpus metadata not found"
    logger.info(f"✓ Corpus metadata exists: {corpus_name}")

    search_meta = await vm.get_latest(
        resource_id=f"{corpus_id!s}:search",
        resource_type=ResourceType.SEARCH,
    )
    assert search_meta is not None, "SearchIndex metadata not found"
    logger.info(f"✓ SearchIndex metadata exists")

    trie_meta = await vm.get_latest(
        resource_id=f"{corpus_id!s}:trie",
        resource_type=ResourceType.TRIE,
    )
    assert trie_meta is not None, "TrieIndex metadata not found"
    logger.info(f"✓ TrieIndex metadata exists")

    semantic_meta = await vm.get_latest(
        resource_id=f"{corpus_id!s}:semantic:all-MiniLM-L6-v2",
        resource_type=ResourceType.SEMANTIC,
    )
    assert semantic_meta is not None, "SemanticIndex metadata not found"
    logger.info(f"✓ SemanticIndex metadata exists")

    # Step 6: Delete the corpus
    logger.info("\n[6] Deleting corpus (should cascade to all indices)...")
    await corpus.delete()
    logger.info(f"✓ Corpus deleted: {corpus_name}")

    # Step 7: Verify all are deleted
    logger.info("\n[7] Verifying all indices are deleted...")

    corpus_meta = await vm.get_latest(
        resource_id=corpus_name,
        resource_type=ResourceType.CORPUS,
    )
    assert corpus_meta is None, "Corpus metadata still exists (orphan!)"
    logger.info(f"✓ Corpus metadata deleted")

    search_meta = await vm.get_latest(
        resource_id=f"{corpus_id!s}:search",
        resource_type=ResourceType.SEARCH,
    )
    assert search_meta is None, "SearchIndex metadata still exists (orphan!)"
    logger.info(f"✓ SearchIndex metadata deleted")

    trie_meta = await vm.get_latest(
        resource_id=f"{corpus_id!s}:trie",
        resource_type=ResourceType.TRIE,
    )
    assert trie_meta is None, "TrieIndex metadata still exists (orphan!)"
    logger.info(f"✓ TrieIndex metadata deleted")

    semantic_meta = await vm.get_latest(
        resource_id=f"{corpus_id!s}:semantic:all-MiniLM-L6-v2",
        resource_type=ResourceType.SEMANTIC,
    )
    assert semantic_meta is None, "SemanticIndex metadata still exists (orphan!)"
    logger.info(f"✓ SemanticIndex metadata deleted")

    logger.info("\n" + "=" * 80)
    logger.info("✅ CASCADE DELETION VERIFICATION PASSED")
    logger.info("=" * 80)
    logger.info("\nResult: No orphaned documents found - cascade deletion working correctly!")


if __name__ == "__main__":
    asyncio.run(verify_cascade_deletion())
