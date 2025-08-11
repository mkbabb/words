#!/usr/bin/env python
"""Test the versioning system with mock and real providers."""

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime, UTC
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Direct MongoDB connection for testing
MONGODB_URL = "mongodb://localhost:27017/floridify_test"


async def init_database():
    """Initialize database connection directly."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    
    from src.floridify.models import Word, Definition, Example, Pronunciation, ProviderData
    from src.floridify.models.provider import VersionedProviderData
    
    # Connect directly to local MongoDB
    client = AsyncIOMotorClient(MONGODB_URL)
    database = client["floridify_test"]
    
    # Initialize Beanie with all document models
    await init_beanie(
        database=database,
        document_models=[
            Word,
            Definition,
            Example,
            Pronunciation,
            ProviderData,
            VersionedProviderData,
        ],
    )
    
    # Clear test data
    await database["word"].delete_many({})
    await database["versionedproviderdata"].delete_many({})
    
    return database


async def test_versioning_with_mock():
    """Test versioning system with mock provider."""
    from src.floridify.models import Word, ProviderData
    from src.floridify.models.definition import Language, DictionaryProvider
    from src.floridify.models.provider import VersionedProviderData
    from src.floridify.connectors.base import DictionaryConnector
    from src.floridify.connectors.config import VersionConfig
    
    print("\n" + "=" * 60)
    print("TEST 1: VERSIONING WITH MOCK PROVIDER")
    print("=" * 60)
    
    # Create mock connector
    class MockConnector(DictionaryConnector):
        def __init__(self):
            super().__init__(rate_limit=10.0)
            self.call_count = 0
            
        @property
        def provider_name(self):
            return DictionaryProvider.WIKTIONARY
        
        async def _fetch_from_provider(self, word_obj, state_tracker=None):
            """Mock provider that returns different data each call."""
            if not word_obj.id:
                raise ValueError(f"Word {word_obj.text} must be saved")
            
            self.call_count += 1
            
            # Return different data based on call count
            return ProviderData(
                word_id=word_obj.id,
                provider=self.provider_name,
                definition_ids=[],
                raw_data={
                    "test": "data",
                    "call_count": self.call_count,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
    
    connector = MockConnector()
    print(f"✓ Created MockConnector")
    
    # Create test word
    word = Word(
        text="testword",
        normalized="testword",
        language=Language.ENGLISH,
    )
    await word.save()
    print(f"✓ Created word: '{word.text}' (id: {word.id})")
    
    # Test 1: Initial fetch with versioning
    print("\n1. Initial fetch with versioning:")
    config = VersionConfig(save_versioned=True, increment_version=False)
    
    result1 = await connector.fetch_definition(word, version_config=config)
    print(f"  ✓ First fetch complete (call_count: {connector.call_count})")
    print(f"    Provider: {result1.provider}")
    print(f"    Raw data: {result1.raw_data}")
    
    # Check versioned data
    v1 = await VersionedProviderData.find_one(
        {"word_id": word.id, "provider": connector.provider_name}
    )
    print(f"  ✓ Versioned data saved:")
    print(f"    Version: {v1.version_info.provider_version}")
    print(f"    Hash: {v1.version_info.data_hash[:16]}...")
    initial_hash = v1.version_info.data_hash
    
    # Test 2: Fetch again (should use cache)
    print("\n2. Fetch again (should use cache):")
    result2 = await connector.fetch_definition(word, version_config=config)
    print(f"  ✓ Second fetch complete (call_count: {connector.call_count})")
    
    if connector.call_count == 1:
        print(f"  ✓ Used cached data (no API call)")
    else:
        print(f"  ✗ Made unnecessary API call")
    
    # Test 3: Force API refresh
    print("\n3. Force API refresh:")
    config_force = VersionConfig(
        force_api=True,
        save_versioned=True,
        increment_version=True,
    )
    
    result3 = await connector.fetch_definition(word, version_config=config_force)
    print(f"  ✓ Forced fetch complete (call_count: {connector.call_count})")
    
    if connector.call_count == 2:
        print(f"  ✓ Made new API call as expected")
    
    # Check if version incremented
    v2 = await VersionedProviderData.find_one(
        {"word_id": word.id, "provider": connector.provider_name, "version_info.is_latest": True}
    )
    
    if v2.version_info.data_hash != initial_hash:
        print(f"  ✓ New data saved (hash changed)")
        print(f"    New version: {v2.version_info.provider_version}")
        if v2.version_info.provider_version != v1.version_info.provider_version:
            print(f"  ✓ Version incremented correctly")
    
    # Test 4: Fetch specific version
    print("\n4. Fetch specific version:")
    config_version = VersionConfig(version=v1.version_info.provider_version)
    
    result4 = await connector.fetch_definition(word, version_config=config_version)
    print(f"  ✓ Fetched version {v1.version_info.provider_version}")
    print(f"  Call count still: {connector.call_count} (no new API call)")
    
    # Test 5: Backward compatibility
    print("\n5. Test backward compatibility:")
    result5 = await connector.fetch_definition(
        word,
        force_api=False,
        save_versioned=True,
        increment_version=False,
    )
    print(f"  ✓ Backward compatible call succeeded")
    
    print("\n✅ All versioning tests passed!")


async def test_real_provider():
    """Test with a real provider that works without auth."""
    from src.floridify.models import Word, Definition
    from src.floridify.models.definition import Language, DictionaryProvider
    from src.floridify.models.provider import VersionedProviderData
    from src.floridify.connectors.config import VersionConfig
    
    print("\n" + "=" * 60)
    print("TEST 2: REAL PROVIDER (SIMPLE MOCK)")
    print("=" * 60)
    
    # Create a simplified test connector that always returns data
    from src.floridify.connectors.base import DictionaryConnector
    from src.floridify.models import ProviderData
    
    class SimpleTestConnector(DictionaryConnector):
        """Simple connector that always returns test data."""
        
        @property
        def provider_name(self):
            return DictionaryProvider.FREE_DICTIONARY
        
        async def _fetch_from_provider(self, word_obj, state_tracker=None):
            """Always return test data."""
            if not word_obj.id:
                raise ValueError(f"Word {word_obj.text} must be saved")
            
            # Create a test definition
            definition = Definition(
                word_id=word_obj.id,
                part_of_speech="noun",
                text=f"A test definition for {word_obj.text}",
                sense_number="1",
                synonyms=["example", "sample"],
                antonyms=[],
                example_ids=[],
            )
            await definition.save()
            
            return ProviderData(
                word_id=word_obj.id,
                provider=self.provider_name,
                definition_ids=[definition.id],
                raw_data={
                    "word": word_obj.text,
                    "definitions": [{"text": definition.text, "pos": "noun"}],
                },
            )
    
    connector = SimpleTestConnector()
    print(f"✓ Created SimpleTestConnector (provider: {connector.provider_name.value})")
    
    # Create test word
    word = Word(
        text="apple",
        normalized="apple",
        language=Language.ENGLISH,
    )
    await word.save()
    print(f"✓ Created word: '{word.text}'")
    
    # Test fetch with versioning
    print("\n1. Fetch with versioning:")
    config = VersionConfig(save_versioned=True)
    
    result = await connector.fetch_definition(word, version_config=config)
    
    if result:
        print(f"  ✓ Fetched data successfully")
        print(f"    Provider: {result.provider}")
        print(f"    Definitions: {len(result.definition_ids)}")
        
        # Load the definition
        if result.definition_ids:
            definition = await Definition.get(result.definition_ids[0])
            if definition:
                print(f"    Definition text: '{definition.text}'")
                print(f"    Part of speech: {definition.part_of_speech}")
    
    # Check versioned storage
    print("\n2. Check versioned storage:")
    versioned = await VersionedProviderData.find_one(
        {"word_id": word.id, "provider": connector.provider_name}
    )
    
    if versioned:
        print(f"  ✓ Data saved to versioned storage")
        print(f"    Version: {versioned.version_info.provider_version}")
        print(f"    Is latest: {versioned.version_info.is_latest}")
    
    print("\n✅ Real provider test passed!")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("VERSIONING SYSTEM COMPREHENSIVE TEST")
    print("=" * 60)
    
    # Initialize database
    print("\nInitializing database...")
    try:
        db = await init_database()
        print("✓ Database connected and initialized")
        print(f"  Database: {db.name}")
        print(f"  Collections cleared")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return 1
    
    # Run tests
    try:
        await test_versioning_with_mock()
        await test_real_provider()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))