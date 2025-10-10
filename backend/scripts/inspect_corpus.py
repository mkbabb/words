#!/usr/bin/env python3
"""Inspect corpus state in MongoDB."""

import asyncio
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.storage.mongodb import get_storage
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Inspect corpus state."""
    # Initialize MongoDB
    await get_storage()

    # Get corpus manager
    manager = get_tree_corpus_manager()

    # Import Corpus model
    from floridify.corpus.core import Corpus

    # List all corpus metadata from MongoDB
    logger.info("Fetching all corpus metadata from MongoDB...")
    metadata_list = await Corpus.Metadata.find_all().to_list()

    # Filter for latest versions only
    latest_metadata = [m for m in metadata_list if m.version_info.is_latest]

    logger.info(f"\n{'='*80}")
    logger.info(f"TOTAL CORPORA (latest versions): {len(latest_metadata)}")
    logger.info(f"{'='*80}\n")

    for metadata in latest_metadata:
        logger.info(f"Corpus: {metadata.resource_id}")
        logger.info(f"  Type: {metadata.resource_type}")
        logger.info(f"  Namespace: {metadata.namespace}")
        logger.info(f"  Version: {metadata.version_info.version}")
        logger.info(f"  Data Hash: {metadata.version_info.data_hash[:8] if metadata.version_info.data_hash else None}")
        logger.info("")

    # Check language_english specifically
    logger.info(f"\n{'='*80}")
    logger.info("CHECKING language_english CORPUS")
    logger.info(f"{'='*80}\n")

    try:
        corpus = await manager.get_corpus(corpus_name="language_english")
        logger.info(f"Found corpus: {corpus.corpus_name}")
        logger.info(f"  Vocabulary: {len(corpus.vocabulary)} words")
        logger.info(f"  First 20 words: {corpus.vocabulary[:20]}")
        logger.info(f"  Child corpora: {len(corpus.child_corpus_ids)}")

        if corpus.child_corpus_ids:
            logger.info("\n  Child Corpora:")
            for child_id in corpus.child_corpus_ids:
                child = await manager.get_corpus(corpus_id=child_id)
                logger.info(f"    - {child.corpus_name} ({len(child.vocabulary)} words)")
        else:
            logger.info("\n  ⚠️  WARNING: No child corpora found!")

    except Exception as e:
        logger.error(f"Error fetching language_english: {e}")


if __name__ == "__main__":
    asyncio.run(main())
