#!/usr/bin/env python
"""Test versioning directly with local MongoDB."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_versioning():
    """Test versioning with direct MongoDB connection."""
    # Import only what we need
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    
    # Connect directly to local MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    database = client["floridify_test"]
    
    # Initialize Beanie with minimal models
    from src.floridify.models import Word
    from src.floridify.models.provider import VersionedProviderData, ProviderVersion
    from src.floridify.models.definition import Language, DictionaryProvider
    from src.floridify.utils.logging import get_logger
    
    logger = get_logger(__name__)
    
    # Initialize Beanie
    await init_beanie(
        database=database,
        document_models=[Word, VersionedProviderData],
    )
    
    logger.info("=" * 60)
    logger.info("Testing Versioned Provider System (Direct MongoDB)")
    logger.info("=" * 60)
    
    # Test basic versioned data operations
    logger.info("\n1. Creating test word...")
    word = Word(
        text="test_versioning",
        normalized="test_versioning",
        language=Language.ENGLISH,
    )
    await word.save()
    logger.info(f"✓ Created word: {word.text}")
    
    # Test creating versioned data
    logger.info("\n2. Creating versioned provider data...")
    
    versioned_data = VersionedProviderData(
        word_id=word.id,
        word_text=word.text,
        language=word.language,
        provider=DictionaryProvider.WIKTIONARY,
        version_info=ProviderVersion(
            provider_version="1.0.0",
            schema_version="1.0",
            data_hash="test_hash_123",
            is_latest=True,
        ),
        raw_data={"test": "data", "definitions": ["example definition"]},
    )
    await versioned_data.save()
    logger.info(f"✓ Created versioned data v{versioned_data.version_info.provider_version}")
    
    # Test querying versioned data
    logger.info("\n3. Querying versioned data...")
    found = await VersionedProviderData.find_one(
        {
            "word_id": word.id,
            "provider": DictionaryProvider.WIKTIONARY,
            "version_info.is_latest": True,
        }
    )
    if found:
        logger.info(f"✓ Found latest version: {found.version_info.provider_version}")
        logger.info(f"  Hash: {found.version_info.data_hash}")
    else:
        logger.warning("✗ Could not find versioned data")
    
    # Test the unified fetch_definition method directly
    logger.info("\n4. Testing unified fetch_definition...")
    try:
        # Import connector without triggering transformer imports
        from src.floridify.connectors.base import DictionaryConnector
        from src.floridify.models import ProviderData
        
        # Create a mock connector to test base functionality
        class MockConnector(DictionaryConnector):
            @property
            def provider_name(self):
                return DictionaryProvider.WIKTIONARY
            
            async def _fetch_from_provider(self, word_obj, state_tracker=None):
                # Mock implementation
                return ProviderData(
                    word_id=word_obj.id,
                    provider=self.provider_name,
                    definition_ids=[],
                    raw_data={"mock": "data"},
                )
        
        connector = MockConnector()
        
        # Test fetch with versioning
        result = await connector.fetch_definition(
            word,
            save_versioned=True,
        )
        if result:
            logger.info(f"✓ Unified fetch_definition works")
            logger.info(f"  Provider: {result.provider}")
        
        # Test fetching specific version
        result2 = await connector.fetch_definition(
            word,
            version="1.0.0",
        )
        if result2:
            logger.info(f"✓ Fetching specific version works")
        
        # Test force API call
        result3 = await connector.fetch_definition(
            word,
            force_api=True,
            save_versioned=True,
            increment_version=True,
        )
        if result3:
            logger.info(f"✓ Force API call works")
        
    except Exception as e:
        logger.error(f"✗ Error testing unified fetch: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("\n" + "=" * 60)
    logger.info("Test Complete")
    logger.info("=" * 60)
    
    return True


async def main():
    """Run the test."""
    try:
        success = await test_versioning()
        return 0 if success else 1
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))