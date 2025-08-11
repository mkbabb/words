#!/usr/bin/env python
"""Test versioned provider system integration."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.floridify.connectors.wholesale.wiktionary_wholesale import (
    WiktionaryTitleListDownloader,
    WiktionaryWholesaleConnector,
)
from src.floridify.models import Word
from src.floridify.models.definition import DictionaryProvider, Language
from src.floridify.storage.mongodb import init_db
from src.floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def test_wiktionary_titles():
    """Test Wiktionary title list download."""
    logger.info("Testing Wiktionary title list download...")
    
    downloader = WiktionaryTitleListDownloader(language="en")
    
    # Download and extract vocabulary
    vocabulary = await downloader.extract_vocabulary(min_length=5)
    
    logger.info(f"✓ Downloaded {len(vocabulary)} words")
    logger.info(f"  Sample words: {vocabulary[:10]}")
    
    return vocabulary


async def test_wiktionary_wholesale():
    """Test Wiktionary wholesale connector."""
    logger.info("Testing Wiktionary wholesale connector...")
    
    connector = WiktionaryWholesaleConnector(language="en")
    
    # Test with a single word
    word = Word(
        text="dictionary",
        normalized="dictionary",
        language=Language.ENGLISH,
    )
    await word.save()
    
    # Fetch definition (will use regular scraper if no wholesale data)
    result = await connector.fetch_definition(word)
    
    if result:
        logger.info(f"✓ Wiktionary wholesale: Found data for 'dictionary'")
    else:
        logger.warning("✗ Wiktionary wholesale: No data found")
    
    return result


async def test_backward_compatibility():
    """Test that old import paths still work."""
    logger.info("Testing backward compatibility...")
    
    try:
        # These imports should work for backward compatibility
        from src.floridify.connectors import (
            DictionaryConnector,
            OxfordConnector,
            WiktionaryConnector,
        )
        
        logger.info("✓ Backward compatible imports work")
        
        # Test that connectors can be instantiated
        wiktionary = WiktionaryConnector()
        logger.info(f"✓ WiktionaryConnector instantiated: {wiktionary.provider_name}")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Import error: {e}")
        return False


async def test_versioned_storage():
    """Test versioned provider data storage."""
    logger.info("Testing versioned data storage...")
    
    from src.floridify.api.repositories.provider_repository import (
        ProviderDataRepository,
    )
    
    repo = ProviderDataRepository()
    
    # Create a test word
    word = Word(
        text="test_word",
        normalized="test_word",
        language=Language.ENGLISH,
    )
    await word.save()
    
    # Check if we can query versioned data
    latest = await repo.get_latest(
        word_id=word.id,
        provider=DictionaryProvider.WIKTIONARY,
    )
    
    if latest:
        logger.info(f"✓ Found versioned data for test word")
        logger.info(f"  Version: {latest.version_info.provider_version}")
    else:
        logger.info("✓ No versioned data yet (expected for new word)")
    
    return True


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Versioned Provider System Tests")
    logger.info("=" * 60)
    
    # Initialize database
    await init_db()
    
    # Run tests
    tests = [
        test_backward_compatibility(),
        test_versioned_storage(),
        test_wiktionary_wholesale(),
        # test_wiktionary_titles(),  # Commented out as it downloads large files
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    # Summary
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
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