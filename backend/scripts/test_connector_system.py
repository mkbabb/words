#!/usr/bin/env python
"""Test the complete connector system with VersionConfig."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_connector_system():
    """Test the connector system comprehensively."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    
    from src.floridify.models import Word
    from src.floridify.models.definition import Language, DictionaryProvider
    from src.floridify.models.provider import VersionedProviderData
    from src.floridify.connectors.config import VersionConfig
    from src.floridify.utils.logging import get_logger
    
    logger = get_logger(__name__)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    database = client["floridify_test"]
    
    # Initialize Beanie
    await init_beanie(
        database=database,
        document_models=[Word, VersionedProviderData],
    )
    
    logger.info("=" * 60)
    logger.info("Testing Connector System with VersionConfig")
    logger.info("=" * 60)
    
    # Create test word
    word = Word(
        text="example",
        normalized="example",
        language=Language.ENGLISH,  # Using enum properly
    )
    await word.save()
    logger.info(f"\n✓ Created word: {word.text} with language: {word.language}")
    
    # Test 1: VersionConfig creation
    logger.info("\n1. Testing VersionConfig:")
    config = VersionConfig(
        force_api=False,
        save_versioned=True,
        increment_version=True,
    )
    logger.info(f"  ✓ VersionConfig created with save_versioned={config.save_versioned}")
    
    # Test 2: Test with WiktionaryConnector
    logger.info("\n2. Testing WiktionaryConnector:")
    try:
        from src.floridify.connectors.scraper.wiktionary import WiktionaryConnector
        
        connector = WiktionaryConnector()
        logger.info(f"  Provider: {connector.provider_name.value}")
        
        # Fetch with VersionConfig
        result = await connector.fetch_definition(
            word,
            version_config=config,
        )
        
        if result:
            logger.info(f"  ✓ Fetched data for '{word.text}'")
            logger.info(f"    Definitions: {len(result.definition_ids)}")
        else:
            logger.info(f"  ℹ No data found for '{word.text}'")
        
    except Exception as e:
        logger.error(f"  ✗ WiktionaryConnector test failed: {e}")
    
    # Test 3: Check versioned data was saved
    logger.info("\n3. Checking versioned data:")
    versioned = await VersionedProviderData.find_one(
        {
            "word_id": word.id,
            "provider": DictionaryProvider.WIKTIONARY,
            "version_info.is_latest": True,
        }
    )
    
    if versioned:
        logger.info(f"  ✓ Versioned data saved")
        logger.info(f"    Version: {versioned.version_info.provider_version}")
        logger.info(f"    Language: {versioned.language}")  # Already a string
    else:
        logger.info("  ℹ No versioned data found")
    
    # Test 4: Test backward compatibility
    logger.info("\n4. Testing backward compatibility:")
    result2 = await connector.fetch_definition(
        word,
        force_api=True,
        save_versioned=False,
    )
    
    if result2:
        logger.info(f"  ✓ Backward compatibility works")
    else:
        logger.info(f"  ℹ No data fetched")
    
    # Test 5: Test specific version fetch
    logger.info("\n5. Testing specific version fetch:")
    if versioned:
        config_with_version = VersionConfig(
            version=versioned.version_info.provider_version,
        )
        
        result3 = await connector.fetch_definition(
            word,
            version_config=config_with_version,
        )
        
        if result3:
            logger.info(f"  ✓ Fetched specific version: {versioned.version_info.provider_version}")
        else:
            logger.info("  ✗ Could not fetch specific version")
    
    logger.info("\n" + "=" * 60)
    logger.info("Connector System Test Complete!")
    logger.info("=" * 60)
    
    return True


async def main():
    """Run the test."""
    try:
        success = await test_connector_system()
        return 0 if success else 1
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))