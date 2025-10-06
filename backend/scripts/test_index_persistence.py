#!/usr/bin/env python3
"""Test that index persistence is now fixed."""

import asyncio
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.search.models import SearchIndex, TrieIndex
from floridify.search.semantic.models import SemanticIndex
from floridify.storage.mongodb import init_db

async def test_persistence():
    await init_db()

    # Get a corpus
    manager = get_tree_corpus_manager()
    corpus = await manager.get_corpus(corpus_name='language_english_full')

    if not corpus:
        print("❌ Corpus not found")
        return

    print(f"✅ Found corpus: {corpus.corpus_name} (ID: {corpus.corpus_id})")

    # Create and save SearchIndex
    search_idx = SearchIndex(
        corpus_id=corpus.corpus_id,
        corpus_name=corpus.corpus_name,
        vocabulary_hash=corpus.vocabulary_hash,
    )
    await search_idx.save()
    print(f"✅ SearchIndex saved with resource_id: {corpus.corpus_id!s}:search")

    # Try to retrieve it
    retrieved = await SearchIndex.get(corpus_name=corpus.corpus_name)
    if retrieved:
        print(f"✅ SearchIndex retrieved successfully")
    else:
        print(f"❌ SearchIndex retrieval failed")

    # Test TrieIndex
    trie_idx = TrieIndex(
        corpus_id=corpus.corpus_id,
        corpus_name=corpus.corpus_name,
        vocabulary_hash=corpus.vocabulary_hash,
        trie_data=[],
    )
    await trie_idx.save()
    print(f"✅ TrieIndex saved with resource_id: {corpus.corpus_id!s}:trie")

    retrieved_trie = await TrieIndex.get(corpus_name=corpus.corpus_name)
    if retrieved_trie:
        print(f"✅ TrieIndex retrieved successfully")
    else:
        print(f"❌ TrieIndex retrieval failed")

    # Test SemanticIndex
    semantic_idx = SemanticIndex(
        corpus_id=corpus.corpus_id,
        corpus_name=corpus.corpus_name,
        model_name="Alibaba-NLP/gte-Qwen2-1.5B-instruct",
        vocabulary_hash=corpus.vocabulary_hash,
        embeddings=[],
        words=[],
    )
    await semantic_idx.save()
    print(f"✅ SemanticIndex saved with resource_id: {corpus.corpus_id!s}:semantic:Alibaba-NLP/gte-Qwen2-1.5B-instruct")

    retrieved_semantic = await SemanticIndex.get(
        corpus_name=corpus.corpus_name,
        model_name="Alibaba-NLP/gte-Qwen2-1.5B-instruct"
    )
    if retrieved_semantic:
        print(f"✅ SemanticIndex retrieved successfully")
    else:
        print(f"❌ SemanticIndex retrieval failed")

    # Check MongoDB directly
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017')
    db = client.floridify

    print("\n📊 MongoDB verification:")
    search_doc = db.versioned_data.find_one({"resource_id": f"{corpus.corpus_id!s}:search"})
    print(f"SearchIndex in DB: {'✅' if search_doc else '❌'}")

    trie_doc = db.versioned_data.find_one({"resource_id": f"{corpus.corpus_id!s}:trie"})
    print(f"TrieIndex in DB: {'✅' if trie_doc else '❌'}")

    semantic_doc = db.versioned_data.find_one({"resource_id": f"{corpus.corpus_id!s}:semantic:Alibaba-NLP/gte-Qwen2-1.5B-instruct"})
    print(f"SemanticIndex in DB: {'✅' if semantic_doc else '❌'}")

if __name__ == "__main__":
    asyncio.run(test_persistence())