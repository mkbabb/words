#!/usr/bin/env python
"""Test script for provider system integration."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.floridify.connectors.api.free_dictionary import FreeDictionaryConnector
from src.floridify.connectors.api.merriam_webster import MerriamWebsterConnector
from src.floridify.connectors.batch.corpus_walker import CorpusWalker
from src.floridify.connectors.batch.bulk_downloader import WiktionaryBulkDownloader
from src.floridify.connectors.scraper.dictionary_com import DictionaryComConnector
from src.floridify.models import Word
from src.floridify.models.definition import Language
from src.floridify.storage.mongodb import init_db
from src.floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def test_free_dictionary():
    """Test Free Dictionary API connector."""
    logger.info("Testing Free Dictionary API...")
    
    connector = FreeDictionaryConnector()
    
    # Test word
    word = Word(
        text="example",
        normalized="example",
        language=Language.ENGLISH,
    )
    await word.save()
    
    # Fetch with versioning
    result = await connector.fetch_with_versioning(word)
    
    if result:
        logger.info(f"✓ Free Dictionary: Found data for 'example'")
        logger.info(f"  Version: {result.version_info.provider_version}")
        logger.info(f"  Is Latest: {result.version_info.is_latest}")
    else:
        logger.error("✗ Free Dictionary: Failed to fetch data")
    
    return result


async def test_dictionary_com():
    """Test Dictionary.com scraper."""
    logger.info("Testing Dictionary.com scraper...")
    
    connector = DictionaryComConnector()
    
    # Test word
    word = Word(
        text="computer",
        normalized="computer",
        language=Language.ENGLISH,
    )
    await word.save()
    
    # Fetch with versioning
    result = await connector.fetch_with_versioning(word)
    
    if result:
        logger.info(f"✓ Dictionary.com: Found data for 'computer'")
        logger.info(f"  Version: {result.version_info.provider_version}")
        logger.info(f"  Data Hash: {result.version_info.data_hash[:8]}...")
    else:
        logger.error("✗ Dictionary.com: Failed to fetch data")
    
    return result


async def test_corpus_walker():
    """Test corpus walker with Free Dictionary."""
    logger.info("Testing Corpus Walker...")
    
    # Create a small test corpus
    test_words = ["hello", "world", "test", "example", "dictionary"]
    
    connector = FreeDictionaryConnector()
    walker = CorpusWalker(
        connector=connector,
        corpus_name="test_corpus",
        batch_size=2,
    )
    
    # Note: This would need a real corpus to be set up
    logger.info("✓ Corpus Walker: Initialized successfully")
    logger.info(f"  Provider: {connector.provider_name.value}")
    logger.info(f"  Batch Size: 2")
    
    # In a real test, you would call:
    # batch_op = await walker.walk_corpus(max_words=5)
    

async def test_provider_repository():
    """Test provider data repository."""
    logger.info("Testing Provider Repository...")
    
    from src.floridify.api.repositories.provider_repository import ProviderDataRepository
    
    repo = ProviderDataRepository()
    
    # Get words with Free Dictionary data
    words = await repo.get_words_with_provider(
        provider="free_dictionary",
        limit=5,
    )
    
    logger.info(f"✓ Provider Repository: Found {len(words)} words with Free Dictionary data")
    if words:
        logger.info(f"  Sample words: {words[:3]}")
    
    return words


async def main():
    """Run all provider tests."""
    logger.info("="*60)
    logger.info("Provider System Integration Tests")
    logger.info("="*60)
    
    # Initialize database
    await init_db()
    
    # Run tests
    tests = [
        test_free_dictionary(),
        test_dictionary_com(),
        test_corpus_walker(),
        test_provider_repository(),
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    # Summary
    logger.info("="*60)
    logger.info("Test Summary")
    logger.info("="*60)
    
    passed = sum(1 for r in results if r and not isinstance(r, Exception))
    failed = sum(1 for r in results if isinstance(r, Exception))
    
    logger.info(f"Passed: {passed}/{len(tests)}")
    logger.info(f"Failed: {failed}/{len(tests)}")
    
    if failed > 0:
        logger.error("Some tests failed:")
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"  Test {i+1}: {result}")
    
    return passed == len(tests)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)