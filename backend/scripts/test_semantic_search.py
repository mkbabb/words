#!/usr/bin/env python3
"""Test semantic search directly."""

import asyncio
import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.floridify.search.semantic.core import SemanticSearch
from src.floridify.corpus.manager import get_tree_corpus_manager
from src.floridify.storage.mongodb import get_storage
from src.floridify.utils.logging import get_logger, setup_logging

setup_logging("INFO")
logger = get_logger(__name__)


async def test_semantic_search():
    """Test semantic search functionality."""
    try:
        # Initialize storage
        logger.info("Initializing MongoDB storage...")
        await get_storage()

        # Get corpus manager
        manager = get_tree_corpus_manager()

        # Get the language corpus
        logger.info("Loading language_english corpus...")
        corpus = await manager.get_corpus(corpus_name="language_english")

        if not corpus:
            logger.error("Could not find language_english corpus")
            return False

        logger.info(f"Loaded corpus with {len(corpus.vocabulary)} words")
        logger.info(f"Lemmatized vocabulary: {len(corpus.lemmatized_vocabulary)} lemmas")

        # Test building semantic search with smaller batch
        logger.info("Building semantic search with batch processing...")

        # Use a simpler, faster model for testing
        search = await SemanticSearch.from_corpus(
            corpus=corpus,
            model_name="all-MiniLM-L6-v2",  # Smaller, faster model
        )

        logger.info("✅ Semantic search initialized")

        # Test a search
        test_queries = ["hello", "bonjour", "en coulisse", "test"]
        for query in test_queries:
            logger.info(f"Searching for: {query}")
            results = await search.search(query, k=5)
            if results:
                logger.info(f"  Found {len(results)} results")
                for r in results[:3]:
                    logger.info(f"    - {r.word} (score: {r.score:.2f})")
            else:
                logger.info(f"  No results found")

        return True

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_semantic_search())
    if success:
        print("\n✅ Semantic search test passed")
    else:
        print("\n❌ Semantic search test failed")
        sys.exit(1)