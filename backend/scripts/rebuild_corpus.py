#!/usr/bin/env python3
"""Rebuild language corpus from sources."""

import asyncio

from floridify.corpus.language.core import LanguageCorpus
from floridify.models.base import Language
from floridify.storage.mongodb import init_db
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def rebuild_english_corpus():
    """Rebuild the English language corpus from all sources."""
    logger.info("Initializing database...")
    await init_db()

    logger.info("Building English corpus from sources...")
    corpus = await LanguageCorpus.create_from_language(
        corpus_name="language_english",
        language=Language.ENGLISH,
        semantic=False,  # Don't build semantic yet - just get vocabulary
    )

    logger.info(f"Corpus built: {corpus.corpus_name}")
    logger.info(f"Vocabulary size: {len(corpus.vocabulary)}")
    logger.info(f"Sources: {len(corpus.sources)}")
    logger.info(f"Child corpora: {len(corpus.child_corpus_ids)}")

    if len(corpus.vocabulary) > 0:
        logger.info(f"First 10 words: {corpus.vocabulary[:10]}")
        logger.info("✅ SUCCESS - Corpus has vocabulary!")
    else:
        logger.error("❌ FAILED - Corpus still has 0 vocabulary!")

    return corpus


if __name__ == "__main__":
    asyncio.run(rebuild_english_corpus())
