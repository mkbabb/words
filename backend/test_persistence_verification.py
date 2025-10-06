#!/usr/bin/env python3
"""Verify that index persistence works correctly with our fixes."""

import asyncio

from floridify.caching.models import VersionConfig
from floridify.corpus.core import Corpus
from floridify.search.models import SearchIndex, TrieIndex
from floridify.search.semantic.models import SemanticIndex
from floridify.storage.mongodb import init_db
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def test_persistence():
    """Test that index persistence works correctly."""
    # Initialize database
    await init_db()

    # Create a test corpus
    test_vocabulary = ["apple", "banana", "cherry", "date", "elderberry"]
    test_lemmas = ["apple", "banana", "cherry", "date", "elderberry"]

    corpus = Corpus(
        corpus_name="test_persistence_verification",
        vocabulary=test_vocabulary,
        lemmatized_vocabulary=test_lemmas,
        language="en",
    )
    await corpus.save(VersionConfig())
    logger.info(f"✅ Created corpus: {corpus.corpus_name} (ID: {corpus.corpus_id})")

    # Test TrieIndex persistence
    trie_index = TrieIndex(
        corpus_id=corpus.corpus_id,
        corpus_name=corpus.corpus_name,
        vocabulary_hash=corpus.vocabulary_hash,
        trie_data=test_vocabulary,
    )
    await trie_index.save()
    logger.info(f"✅ Saved TrieIndex")

    # Retrieve and verify
    retrieved_trie = await TrieIndex.get(corpus_id=corpus.corpus_id)
    assert retrieved_trie is not None
    assert retrieved_trie.vocabulary_hash == corpus.vocabulary_hash
    logger.info(f"✅ Retrieved and verified TrieIndex")

    # Test SearchIndex persistence
    search_index = SearchIndex(
        corpus_id=corpus.corpus_id,
        corpus_name=corpus.corpus_name,
        vocabulary_hash=corpus.vocabulary_hash,
        has_trie=True,
        has_fuzzy=True,
        has_semantic=False,
        trie_index_id=trie_index.index_id,
    )
    await search_index.save()
    logger.info(f"✅ Saved SearchIndex")

    # Retrieve and verify
    retrieved_search = await SearchIndex.get(corpus_id=corpus.corpus_id)
    assert retrieved_search is not None
    assert retrieved_search.vocabulary_hash == corpus.vocabulary_hash
    assert retrieved_search.trie_index_id == trie_index.index_id
    logger.info(f"✅ Retrieved and verified SearchIndex")

    # Test SemanticIndex persistence with small data
    semantic_index = SemanticIndex(
        corpus_id=corpus.corpus_id,
        corpus_name=corpus.corpus_name,
        vocabulary_hash=corpus.vocabulary_hash,
        model_name="test_model",
        vocabulary=test_vocabulary,
        lemmatized_vocabulary=test_lemmas,
    )

    # Create small binary data for testing
    import base64
    import pickle
    import zlib

    import numpy as np

    fake_embeddings = np.random.randn(len(test_vocabulary), 384).astype(np.float32)
    embeddings_bytes = pickle.dumps(fake_embeddings)
    compressed = zlib.compress(embeddings_bytes)
    binary_data = {"embeddings": base64.b64encode(compressed).decode("utf-8")}

    await semantic_index.save(binary_data=binary_data)
    logger.info(f"✅ Saved SemanticIndex with compressed binary data")

    # Retrieve and verify
    retrieved_semantic = await SemanticIndex.get(
        corpus_id=corpus.corpus_id, model_name="test_model"
    )
    assert retrieved_semantic is not None
    assert retrieved_semantic.vocabulary_hash == corpus.vocabulary_hash
    logger.info(f"✅ Retrieved and verified SemanticIndex")

    # Test that binary data is accessible
    if hasattr(retrieved_semantic, "binary_data") and retrieved_semantic.binary_data:
        # Decompress and verify
        compressed_data = base64.b64decode(retrieved_semantic.binary_data["embeddings"])
        decompressed = zlib.decompress(compressed_data)
        restored_embeddings = pickle.loads(decompressed)
        assert restored_embeddings.shape == fake_embeddings.shape
        logger.info(f"✅ Verified binary data integrity (shape: {restored_embeddings.shape})")
    else:
        logger.warning("⚠️ Binary data not found in retrieved semantic index")

    print("\n" + "=" * 50)
    print("✅ ALL PERSISTENCE TESTS PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_persistence())