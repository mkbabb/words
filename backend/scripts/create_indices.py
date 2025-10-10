#!/usr/bin/env python3
"""Create and verify MongoDB indices for all Document classes.

This script connects to MongoDB, initializes all Beanie Document classes,
and creates/verifies indices to ensure optimal query performance at scale.

Usage:
    python scripts/create_indices.py

    Options:
        --drop-existing    Drop existing indices before creating new ones
        --verify-only      Only verify indices, don't create any
        --show-queries     Show example queries that use each index
"""

import argparse
import asyncio
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

# Add backend src to path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path / "src"))

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel

from floridify.caching.models import BaseVersionedData
from floridify.models.dictionary import (
    Definition,
    DictionaryEntry,
    Example,
    Fact,
    Pronunciation,
    Word,
)
from floridify.providers.literature.models import LiteratureEntry
from floridify.wordlist.models import WordList
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


# Index documentation for each model
INDEX_DOCS = {
    "BaseVersionedData": {
        "description": "Base class for all versioned data (Corpus, SearchIndex, TrieIndex, SemanticIndex, etc.)",
        "indices": [
            {
                "keys": [("resource_id", 1), ("version_info.is_latest", 1), ("_id", -1)],
                "description": "PRIMARY: Latest version lookup (most frequent query)",
                "queries": [
                    "get_latest(resource_id='corpus_123:search', is_latest=True)",
                    "Find latest version of any resource type",
                ],
            },
            {
                "keys": [("resource_id", 1), ("version_info.version", 1)],
                "description": "Specific version lookup",
                "queries": ["get_by_version(resource_id='corpus_123:search', version='1.2.0')"],
            },
            {
                "keys": [("resource_id", 1), ("version_info.data_hash", 1)],
                "description": "Content hash deduplication during save",
                "queries": ["Check if content already exists before saving new version"],
            },
            {
                "keys": [("corpus_name", 1)],
                "sparse": True,
                "description": "Corpus.Metadata sparse index (only for Corpus documents)",
                "queries": ["Corpus.get(corpus_name='english_lexicon')"],
            },
            {
                "keys": [("vocabulary_hash", 1)],
                "sparse": True,
                "description": "Vocabulary hash lookup for corpus/index validation",
                "queries": ["Verify corpus vocabulary hasn't changed"],
            },
            {
                "keys": [("parent_corpus_id", 1)],
                "sparse": True,
                "description": "Parent corpus lookup for tree operations",
                "queries": ["Find all corpora with specific parent"],
            },
            {
                "keys": [("corpus_id", 1)],
                "sparse": True,
                "description": "Corpus ID lookup for indices (TrieIndex, SearchIndex, SemanticIndex)",
                "queries": [
                    "SearchIndex.get(corpus_id=ObjectId('...'))",
                    "TrieIndex.get(corpus_id=ObjectId('...'))",
                ],
            },
        ],
    },
    "Word": {
        "description": "Core word entity with normalization and lemmatization",
        "indices": [
            {
                "keys": [("text", 1), ("language", 1)],
                "description": "Word text lookup by language",
                "queries": ["Word.find_one({'text': 'hello', 'language': 'en'})"],
            },
            {
                "keys": [("normalized", 1)],
                "description": "Normalized word lookup for search",
                "queries": ["Find all words with normalized form 'helló' -> 'hello'"],
            },
            {
                "keys": [("lemma", 1)],
                "description": "Lemma lookup for word forms",
                "queries": ["Find all words with lemma 'run' (run, runs, running, ran)"],
            },
            {
                "keys": [("text", 1), ("homograph_number", 1)],
                "description": "Homograph disambiguation (bank¹, bank²)",
                "queries": ["Find specific homograph of a word"],
            },
        ],
    },
    "Pronunciation": {
        "description": "Pronunciation data with audio references",
        "indices": [
            {
                "keys": [("word_id", 1)],
                "description": "Foreign key to Word for pronunciation lookup",
                "queries": ["Find all pronunciations for a word"],
            },
        ],
    },
    "Example": {
        "description": "Usage examples (generated or from literature)",
        "indices": [
            {
                "keys": [("definition_id", 1)],
                "description": "Foreign key to Definition",
                "queries": ["Find all examples for a definition"],
            },
            {
                "keys": [("type", 1)],
                "description": "Filter by example type (generated/literature)",
                "queries": ["Find all literature examples"],
            },
        ],
    },
    "Fact": {
        "description": "Interesting facts about words",
        "indices": [
            {
                "keys": [("word_id", 1)],
                "description": "Foreign key to Word",
                "queries": ["Find all facts for a word"],
            },
            {
                "keys": [("category", 1)],
                "description": "Filter by fact category",
                "queries": ["Find all etymology facts"],
            },
        ],
    },
    "WordList": {
        "description": "User word lists with learning metadata",
        "indices": [
            {
                "keys": [("name", 1)],
                "description": "Word list name lookup",
                "queries": ["Find word list by name"],
            },
            {
                "keys": [("hash_id", 1)],
                "description": "Content-based hash identifier",
                "queries": ["Deduplicate word lists"],
            },
            {
                "keys": [("name", "text")],
                "description": "Full-text search on word list names",
                "queries": ["Search for word lists containing 'medical'"],
            },
            {
                "keys": [("created_at", 1)],
                "description": "Sort by creation date",
                "queries": ["Get newest word lists"],
            },
            {
                "keys": [("updated_at", 1)],
                "description": "Sort by update date",
                "queries": ["Get recently modified word lists"],
            },
            {
                "keys": [("last_accessed", 1)],
                "description": "Sort by last access",
                "queries": ["Get recently viewed word lists"],
            },
            {
                "keys": [("owner_id", 1)],
                "description": "Find lists by owner",
                "queries": ["WordList.find({'owner_id': 'user_123'})"],
            },
        ],
    },
    "LiteratureEntry.Metadata": {
        "description": "Literature metadata for versioned persistence",
        "indices": [
            {
                "keys": [("provider", 1)],
                "description": "Filter by literature provider",
                "queries": ["Find all Gutenberg works"],
            },
            {
                "keys": [("work_id", 1)],
                "description": "Lookup by provider-specific work ID",
                "queries": ["Find work by Gutenberg ID"],
            },
        ],
    },
}


async def get_all_indices(collection_name: str, db) -> list[dict]:
    """Get all indices for a collection."""
    try:
        collection = db[collection_name]
        indices = await collection.index_information()
        return [
            {
                "name": name,
                "keys": list(info.get("key", [])),
                "unique": info.get("unique", False),
                "sparse": info.get("sparse", False),
                "text": "text" in dict(info.get("key", [])).values(),
            }
            for name, info in indices.items()
            if name != "_id_"  # Skip default _id index
        ]
    except Exception as e:
        logger.warning(f"Failed to get indices for {collection_name}: {e}")
        return []


async def verify_indices(client: AsyncIOMotorClient, show_queries: bool = False) -> dict[str, dict]:
    """Verify all indices exist and document them."""
    db = client.floridify
    results = {}

    logger.info("=" * 80)
    logger.info("MongoDB Index Verification Report")
    logger.info("=" * 80)

    # Get all document models
    models = [
        ("BaseVersionedData", BaseVersionedData),
        ("Word", Word),
        ("Pronunciation", Pronunciation),
        ("Example", Example),
        ("Fact", Fact),
        ("WordList", WordList),
    ]

    # Check if LiteratureEntry.Metadata has Settings class
    if hasattr(LiteratureEntry, "Metadata"):
        models.append(("LiteratureEntry.Metadata", LiteratureEntry.Metadata))

    for model_name, model_class in models:
        # Get collection name
        collection_name = getattr(model_class.Settings, "name", model_class.__name__.lower())

        logger.info(f"\n{'=' * 80}")
        logger.info(f"Model: {model_name}")
        logger.info(f"Collection: {collection_name}")

        if model_name in INDEX_DOCS:
            logger.info(f"Description: {INDEX_DOCS[model_name]['description']}")

        # Get expected indices from Settings
        expected_indices = []
        if hasattr(model_class, "Settings") and hasattr(model_class.Settings, "indexes"):
            for idx in model_class.Settings.indexes:
                if isinstance(idx, str):
                    expected_indices.append([(idx, 1)])
                elif isinstance(idx, list):
                    expected_indices.append(idx)
                elif isinstance(idx, IndexModel):
                    expected_indices.append(list(idx.document["key"]))

        # Get actual indices from database
        actual_indices = await get_all_indices(collection_name, db)

        results[model_name] = {
            "collection": collection_name,
            "expected_count": len(expected_indices),
            "actual_count": len(actual_indices),
            "indices": actual_indices,
        }

        logger.info(f"\nExpected indices: {len(expected_indices)}")
        logger.info(f"Actual indices: {len(actual_indices)}")

        if actual_indices:
            logger.info("\nActual Indices:")
            for idx in actual_indices:
                flags = []
                if idx["unique"]:
                    flags.append("UNIQUE")
                if idx["sparse"]:
                    flags.append("SPARSE")
                if idx["text"]:
                    flags.append("TEXT")

                flag_str = f" [{', '.join(flags)}]" if flags else ""
                logger.info(f"  • {idx['name']}: {idx['keys']}{flag_str}")

                # Show documentation if available
                if show_queries and model_name in INDEX_DOCS:
                    for idx_doc in INDEX_DOCS[model_name]["indices"]:
                        if idx_doc["keys"] == idx["keys"]:
                            logger.info(f"    → {idx_doc['description']}")
                            if "queries" in idx_doc:
                                for query in idx_doc["queries"]:
                                    logger.info(f"      Example: {query}")
                            break

        if not actual_indices:
            logger.warning(f"  ⚠️  No indices found for {collection_name}")

    return results


async def create_indices(client: AsyncIOMotorClient, drop_existing: bool = False) -> None:
    """Create indices for all models."""
    logger.info("\n" + "=" * 80)
    logger.info("Creating MongoDB Indices")
    logger.info("=" * 80)

    # Initialize Beanie with all document models
    db = client.floridify

    # Get all document models - BaseVersionedData is the root for polymorphic versioned data
    document_models = [
        BaseVersionedData,  # This covers Corpus.Metadata, SearchIndex.Metadata, etc.
        Word,
        Pronunciation,
        Example,
        Fact,
        WordList,
    ]

    # Check if LiteratureEntry.Metadata has Settings
    if (
        hasattr(LiteratureEntry, "Metadata")
        and hasattr(LiteratureEntry.Metadata, "Settings")
        and hasattr(LiteratureEntry.Metadata.Settings, "name")
    ):
        document_models.append(LiteratureEntry.Metadata)

    logger.info(f"\nInitializing Beanie with {len(document_models)} document models...")
    await init_beanie(database=db, document_models=document_models)

    # Create indices for each model
    for model in document_models:
        collection_name = getattr(model.Settings, "name", model.__name__.lower())
        logger.info(f"\nProcessing {model.__name__} (collection: {collection_name})")

        try:
            if drop_existing:
                logger.info(f"  Dropping existing indices for {collection_name}...")
                collection = db[collection_name]
                # Drop all indices except _id
                indices = await collection.index_information()
                for index_name in indices:
                    if index_name != "_id_":
                        try:
                            await collection.drop_index(index_name)
                            logger.info(f"    Dropped: {index_name}")
                        except Exception as e:
                            logger.warning(f"    Failed to drop {index_name}: {e}")

            # Create indices via Beanie
            logger.info(f"  Creating indices for {model.__name__}...")

            # Get the motor collection
            collection = model.get_motor_collection()

            # Process indices from Settings.indexes
            if hasattr(model.Settings, "indexes"):
                for idx in model.Settings.indexes:
                    try:
                        if isinstance(idx, IndexModel):
                            # Already an IndexModel, create it directly
                            await collection.create_indexes([idx])
                            logger.info(f"    ✓ Created index: {idx.document['key']}")
                        elif isinstance(idx, str):
                            # Simple field name
                            await collection.create_index([(idx, 1)])
                            logger.info(f"    ✓ Created index: {idx}")
                        elif isinstance(idx, list):
                            # List of (field, direction) tuples
                            await collection.create_index(idx)
                            logger.info(f"    ✓ Created index: {idx}")
                    except Exception as e:
                        logger.warning(f"    ⚠️  Failed to create index {idx}: {e}")

            logger.info(f"  ✓ Completed {model.__name__}")

        except Exception as e:
            logger.error(f"  ✗ Failed to process {model.__name__}: {e}")


async def show_statistics(client: AsyncIOMotorClient) -> None:
    """Show collection statistics."""
    db = client.floridify
    logger.info("\n" + "=" * 80)
    logger.info("Collection Statistics")
    logger.info("=" * 80)

    collections = await db.list_collection_names()

    total_docs = 0
    total_size = 0

    for collection_name in sorted(collections):
        try:
            stats = await db.command("collStats", collection_name)
            doc_count = stats.get("count", 0)
            size = stats.get("size", 0)
            index_size = stats.get("totalIndexSize", 0)

            total_docs += doc_count
            total_size += size

            size_mb = size / (1024 * 1024)
            index_size_mb = index_size / (1024 * 1024)

            logger.info(
                f"\n{collection_name}:"
                f"\n  Documents: {doc_count:,}"
                f"\n  Data size: {size_mb:.2f} MB"
                f"\n  Index size: {index_size_mb:.2f} MB"
            )
        except Exception as e:
            logger.warning(f"Failed to get stats for {collection_name}: {e}")

    logger.info(f"\n{'=' * 80}")
    logger.info(f"Total documents: {total_docs:,}")
    logger.info(f"Total data size: {total_size / (1024 * 1024):.2f} MB")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create and verify MongoDB indices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop existing indices before creating new ones",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify indices, don't create any",
    )
    parser.add_argument(
        "--show-queries",
        action="store_true",
        help="Show example queries that use each index",
    )
    parser.add_argument(
        "--show-stats",
        action="store_true",
        help="Show collection statistics",
    )
    parser.add_argument(
        "--mongodb-url",
        default="mongodb://localhost:27017",
        help="MongoDB connection URL",
    )

    args = parser.parse_args()

    # Connect to MongoDB
    logger.info(f"Connecting to MongoDB at {args.mongodb_url}...")
    client = AsyncIOMotorClient(args.mongodb_url)

    try:
        # Test connection
        await client.admin.command("ping")
        logger.info("✓ Connected to MongoDB")

        if args.show_stats:
            await show_statistics(client)

        if args.verify_only:
            # Only verify
            await verify_indices(client, show_queries=args.show_queries)
        else:
            # Create indices
            await create_indices(client, drop_existing=args.drop_existing)

            # Verify after creation
            logger.info("\n" + "=" * 80)
            logger.info("Verifying indices after creation...")
            logger.info("=" * 80)
            await verify_indices(client, show_queries=args.show_queries)

        logger.info("\n" + "=" * 80)
        logger.info("Index Management Complete")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Failed to manage indices: {e}", exc_info=True)
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
