#!/usr/bin/env python3
"""Script to rebuild language corpus with all sources."""

import asyncio
import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.floridify.corpus.language.core import LanguageCorpus
from src.floridify.corpus.manager import get_tree_corpus_manager
from src.floridify.models.base import Language
from src.floridify.storage.mongodb import get_storage
from src.floridify.utils.logging import get_logger, setup_logging

setup_logging("INFO")
logger = get_logger(__name__)


async def rebuild_language_corpus():
    """Rebuild the language corpus with all sources."""
    try:
        # Initialize storage
        logger.info("Initializing MongoDB storage...")
        await get_storage()

        # Get corpus manager
        manager = get_tree_corpus_manager()

        # Delete existing corpus if it exists
        logger.info("Checking for existing language_english corpus...")
        existing = await manager.get_corpus(corpus_name="language_english")
        if existing:
            logger.info(f"Found existing corpus with {len(existing.vocabulary)} words")
            logger.info("Deleting existing corpus...")
            await manager.delete_corpus(existing.corpus_id)
            logger.info("Existing corpus deleted")

        # Create new corpus with all sources
        logger.info("Creating new language corpus with sources...")
        corpus = await LanguageCorpus.create_from_language(
            corpus_name="language_english",
            language=Language.ENGLISH,
            semantic=True,
            model_name="all-MiniLM-L6-v2",
        )

        logger.info(f"✅ Language corpus created with {len(corpus.vocabulary)} words")
        logger.info(f"   Corpus ID: {corpus.corpus_id}")
        logger.info(f"   Child corpora: {len(corpus.child_corpus_ids)}")

        # Verify some expected words
        test_words = ["hello", "world", "en", "coulisse"]
        found_words = [w for w in test_words if w in corpus.vocabulary]
        logger.info(f"   Found test words: {found_words}")

        # Look for French expressions
        french_in_english = [
            w for w in corpus.vocabulary
            if any(phrase in w for phrase in ["en", "à", "de", "la", "le"])
        ][:10]
        logger.info(f"   Sample French-origin words: {french_in_english}")

        return corpus

    except Exception as e:
        logger.error(f"Failed to rebuild corpus: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    corpus = asyncio.run(rebuild_language_corpus())
    if corpus:
        print(f"\n✅ Successfully rebuilt language corpus with {len(corpus.vocabulary)} words")
    else:
        print("\n❌ Failed to rebuild corpus")
        sys.exit(1)