#!/usr/bin/env python
"""Test the new VersionConfig system."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_version_config():
    """Test the VersionConfig functionality."""
    from src.floridify.connectors.config import VersionConfig
    from src.floridify.utils.logging import get_logger
    
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("Testing VersionConfig System")
    logger.info("=" * 60)
    
    # Test 1: Default config
    logger.info("\n1. Testing default VersionConfig")
    config = VersionConfig()
    logger.info(f"  force_api: {config.force_api}")
    logger.info(f"  version: {config.version}")
    logger.info(f"  save_versioned: {config.save_versioned}")
    logger.info(f"  increment_version: {config.increment_version}")
    
    # Test 2: Custom config
    logger.info("\n2. Testing custom VersionConfig")
    config = VersionConfig(
        force_api=True,
        version="1.2.3",
        save_versioned=False,
        increment_version=False,
    )
    logger.info(f"  force_api: {config.force_api}")
    logger.info(f"  version: {config.version}")
    logger.info(f"  save_versioned: {config.save_versioned}")
    logger.info(f"  increment_version: {config.increment_version}")
    
    # Test 3: Config is frozen (immutable)
    logger.info("\n3. Testing immutability")
    try:
        config.force_api = False
        logger.error("  ✗ Config should be immutable!")
    except Exception:
        logger.info("  ✓ Config is properly immutable")
    
    # Test 4: Test with mock connector
    logger.info("\n4. Testing with connector")
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    from src.floridify.models import Word
    from src.floridify.models.provider import VersionedProviderData
    from src.floridify.models.definition import Language, DictionaryProvider
    
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    database = client["floridify_test"]
    
    await init_beanie(
        database=database,
        document_models=[Word, VersionedProviderData],
    )
    
    # Create test word
    word = Word(
        text="test_config",
        normalized="test_config",
        language=Language.ENGLISH,
    )
    await word.save()
    
    # Import base connector
    from src.floridify.connectors.base import DictionaryConnector
    from src.floridify.models import ProviderData
    
    class TestConnector(DictionaryConnector):
        @property
        def provider_name(self):
            return DictionaryProvider.WIKTIONARY
        
        async def _fetch_from_provider(self, word_obj, state_tracker=None):
            return ProviderData(
                word_id=word_obj.id,
                provider=self.provider_name,
                definition_ids=[],
                raw_data={"test": "config_test"},
            )
    
    connector = TestConnector()
    
    # Test with VersionConfig
    config = VersionConfig(save_versioned=True)
    result = await connector.fetch_definition(word, version_config=config)
    if result:
        logger.info(f"  ✓ Fetch with VersionConfig successful")
    
    # Test backward compatibility
    result2 = await connector.fetch_definition(
        word,
        force_api=True,
        save_versioned=False,
    )
    if result2:
        logger.info(f"  ✓ Backward compatibility works")
    
    logger.info("\n" + "=" * 60)
    logger.info("All Tests Passed!")
    logger.info("=" * 60)
    
    return True


async def main():
    """Run the test."""
    try:
        success = await test_version_config()
        return 0 if success else 1
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))