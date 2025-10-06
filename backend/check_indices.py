#!/usr/bin/env python3
"""Check the state of indices in MongoDB."""

from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb://localhost:27017")
db = client.floridify

# Count documents
total_docs = db.versioned_data.count_documents({})
print(f"Total versioned documents: {total_docs}")

# Check resource types
resource_types = db.versioned_data.distinct("resource_type")
print(f"\nResource types found: {resource_types}")

# Check each resource type
for resource_type in resource_types:
    count = db.versioned_data.count_documents({"resource_type": resource_type})
    latest = db.versioned_data.find_one(
        {"resource_type": resource_type, "version_info.is_latest": True},
        {"resource_id": 1, "created_at": 1, "version_info.version": 1}
    )
    print(f"\n{resource_type}:")
    print(f"  Count: {count}")
    if latest:
        print(f"  Latest: {latest.get('resource_id')} v{latest['version_info']['version']}")
        print(f"  Created: {latest.get('created_at')}")

# Check specific indices
print("\n=== Checking Specific Indices ===")

# Check for SearchIndex
search_indices = db.versioned_data.count_documents({"resource_type": "search"})
print(f"SearchIndex count: {search_indices}")

# Check for SemanticIndex
semantic_indices = db.versioned_data.count_documents({"resource_type": "semantic"})
print(f"SemanticIndex count: {semantic_indices}")

# Check for TrieIndex
trie_indices = db.versioned_data.count_documents({"resource_type": "trie"})
print(f"TrieIndex count: {trie_indices}")

# Check for Corpus
corpus_count = db.versioned_data.count_documents({"resource_type": "corpus"})
print(f"Corpus count: {corpus_count}")

# Show latest corpus
latest_corpus = db.versioned_data.find_one(
    {"resource_type": "corpus", "version_info.is_latest": True},
    {"resource_id": 1, "metadata.vocabulary_size": 1, "metadata.child_corpus_ids": 1}
)
if latest_corpus:
    print(f"\nLatest corpus: {latest_corpus.get('resource_id')}")
    if 'metadata' in latest_corpus:
        print(f"  Vocabulary size: {latest_corpus['metadata'].get('vocabulary_size', 'N/A')}")
        child_ids = latest_corpus['metadata'].get('child_corpus_ids', [])
        print(f"  Child corpora: {len(child_ids)}")