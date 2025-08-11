#!/usr/bin/env python
"""Test unified fetch_definition with versioning parameters."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.floridify.connectors.scraper.wiktionary import WiktionaryConnector
from src.floridify.models import Word
from src.floridify.models.definition import Language
from src.floridify.models.provider import VersionedProviderData
from src.floridify.storage.mongodb import init_db
from src.floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def test_unified_fetch():
    """Test the unified fetch_definition method with versioning."""
    logger.info("=" * 60)
    logger.info("Testing Unified fetch_definition")
    logger.info("=" * 60)
    
    # Initialize database
    await init_db()
    
    # Create a test word
    word = Word(
        text="example",
        normalized="example",
        language=Language.ENGLISH,
    )
    await word.save()
    
    # Initialize connector
    connector = WiktionaryConnector()
    
    # Test 1: Basic fetch with versioning
    logger.info("\nTest 1: Basic fetch with versioning")
    result = await connector.fetch_definition(
        word,
        save_versioned=True,
    )
    if result:
        logger.info(f"✓ Fetched data for 'example'")
        logger.info(f"  Provider: {result.provider}")
        logger.info(f"  Definitions: {len(result.definition_ids)} found")
    else:
        logger.warning("✗ No data fetched")
    
    # Test 2: Check versioned data was saved
    logger.info("\nTest 2: Check versioned data was saved")
    versioned = await VersionedProviderData.find_one(
        {
            "word_id": word.id,
            "provider": connector.provider_name,
            "version_info.is_latest": True,
        }
    )
    if versioned:
        logger.info(f"✓ Versioned data saved")
        logger.info(f"  Version: {versioned.version_info.provider_version}")
        logger.info(f"  Hash: {versioned.version_info.data_hash[:16]}...")
    else:
        logger.warning("✗ No versioned data found")
    
    # Test 3: Force API call (should create new version)
    logger.info("\nTest 3: Force API call (should not increment version without changes)")
    result2 = await connector.fetch_definition(
        word,
        force_api=True,
        save_versioned=True,
        increment_version=True,
    )
    if result2:
        logger.info(f"✓ Force API call successful")
        
        # Check if version was incremented (shouldn't be if data is same)
        versioned2 = await VersionedProviderData.find_one(
            {
                "word_id": word.id,
                "provider": connector.provider_name,
                "version_info.is_latest": True,
            }
        )
        if versioned2:
            if versioned and versioned2.version_info.data_hash == versioned.version_info.data_hash:
                logger.info(f"  ✓ Duplicate data detected, version not incremented")
            else:
                logger.info(f"  New version: {versioned2.version_info.provider_version}")
    
    # Test 4: Fetch specific version
    logger.info("\nTest 4: Fetch specific version")
    if versioned:
        result3 = await connector.fetch_definition(
            word,
            version=versioned.version_info.provider_version,
        )
        if result3:
            logger.info(f"✓ Fetched specific version {versioned.version_info.provider_version}")
        else:
            logger.warning("✗ Could not fetch specific version")
    
    # Test 5: Backward compatibility - fetch_with_versioning
    logger.info("\nTest 5: Backward compatibility test")
    versioned_result = await connector.fetch_with_versioning(word)
    if versioned_result:
        logger.info(f"✓ fetch_with_versioning still works")
        logger.info(f"  Version: {versioned_result.version_info.provider_version}")
    else:
        logger.warning("✗ fetch_with_versioning failed")
    
    logger.info("\n" + "=" * 60)
    logger.info("Tests Complete")
    logger.info("=" * 60)
    
    return True


async def main():
    """Run the test."""
    try:
        success = await test_unified_fetch()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))