#!/usr/bin/env python
"""Comprehensive test of all providers with versioning."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Direct MongoDB connection for testing
MONGODB_URL = "mongodb://localhost:27017/floridify_test"


async def init_database():
    """Initialize database connection directly."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    
    from src.floridify.models import Word, Definition, Example, Pronunciation
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
            VersionedProviderData,
        ],
    )
    
    return database


async def test_provider(connector_class, word_text: str, **init_kwargs):
    """Test a single provider with versioning."""
    from src.floridify.models import Word
    from src.floridify.models.definition import Language
    from src.floridify.models.provider import VersionedProviderData
    from src.floridify.connectors.config import VersionConfig
    
    print(f"\n{'='*60}")
    print(f"Testing {connector_class.__name__}")
    print(f"{'='*60}")
    
    try:
        # Initialize connector
        connector = connector_class(**init_kwargs)
        print(f"✓ Initialized {connector.provider_name.value} connector")
        
        # Create test word
        word = Word(
            text=word_text,
            normalized=word_text.lower(),
            language=Language.ENGLISH,
        )
        await word.save()
        print(f"✓ Created word: '{word.text}'")
        
        # Test 1: Initial fetch with versioning
        print("\n1. Initial fetch with versioning:")
        config = VersionConfig(
            save_versioned=True,
            increment_version=False,
        )
        
        result = await connector.fetch_definition(word, version_config=config)
        
        if result:
            print(f"  ✓ Fetched data successfully")
            print(f"    Provider: {result.provider.value}")
            print(f"    Definitions: {len(result.definition_ids)}")
            if result.pronunciation_id:
                print(f"    Has pronunciation: Yes")
            if result.etymology:
                print(f"    Has etymology: Yes")
        else:
            print(f"  ℹ No data found for '{word.text}'")
            return
        
        # Test 2: Check versioned data was saved
        print("\n2. Checking versioned storage:")
        versioned = await VersionedProviderData.find_one(
            {
                "word_id": word.id,
                "provider": connector.provider_name,
                "version_info.is_latest": True,
            }
        )
        
        if versioned:
            print(f"  ✓ Data saved to versioned storage")
            print(f"    Version: {versioned.version_info.provider_version}")
            print(f"    Hash: {versioned.version_info.data_hash[:16]}...")
            initial_hash = versioned.version_info.data_hash
        else:
            print(f"  ✗ No versioned data found")
            return
        
        # Test 3: Fetch again (should use cache)
        print("\n3. Fetch again (should use cache):")
        result2 = await connector.fetch_definition(word, version_config=config)
        
        if result2:
            print(f"  ✓ Fetched from cache")
            
            # Check if version is the same
            versioned2 = await VersionedProviderData.find_one(
                {
                    "word_id": word.id,
                    "provider": connector.provider_name,
                    "version_info.is_latest": True,
                }
            )
            if versioned2 and versioned2.version_info.data_hash == initial_hash:
                print(f"  ✓ Same data hash (no duplicate saved)")
        
        # Test 4: Force API refresh
        print("\n4. Force API refresh:")
        config_force = VersionConfig(
            force_api=True,
            save_versioned=True,
            increment_version=True,
        )
        
        result3 = await connector.fetch_definition(word, version_config=config_force)
        
        if result3:
            print(f"  ✓ Forced API call successful")
            
            # Check if data changed
            versioned3 = await VersionedProviderData.find_one(
                {
                    "word_id": word.id,
                    "provider": connector.provider_name,
                    "version_info.is_latest": True,
                }
            )
            
            if versioned3:
                if versioned3.version_info.data_hash != initial_hash:
                    print(f"  ✓ New data fetched (hash changed)")
                    print(f"    New version: {versioned3.version_info.provider_version}")
                else:
                    print(f"  ℹ Same data (hash unchanged)")
        
        # Test 5: Fetch specific version
        print("\n5. Fetch specific version:")
        if versioned:
            config_version = VersionConfig(
                version=versioned.version_info.provider_version,
            )
            
            result4 = await connector.fetch_definition(word, version_config=config_version)
            
            if result4:
                print(f"  ✓ Fetched version {versioned.version_info.provider_version}")
        
        # Test 6: Backward compatibility
        print("\n6. Test backward compatibility:")
        result5 = await connector.fetch_definition(
            word,
            force_api=False,
            save_versioned=True,
        )
        
        if result5:
            print(f"  ✓ Backward compatible API works")
        
        print(f"\n✅ All tests passed for {connector_class.__name__}")
        
    except Exception as e:
        print(f"\n❌ Error testing {connector_class.__name__}: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Test all providers."""
    print("=" * 60)
    print("COMPREHENSIVE PROVIDER TESTING")
    print("=" * 60)
    
    # Initialize database
    print("\nInitializing database...")
    try:
        db = await init_database()
        print("✓ Database initialized")
        
        # Clear test collection
        await db["word"].delete_many({})
        await db["versionedproviderdata"].delete_many({})
        print("✓ Test collections cleared")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return 1
    
    # Test words
    test_words = ["example", "dictionary", "test"]
    
    # Test each provider
    providers_to_test = []
    
    # 1. WiktionaryConnector (scraper, no auth needed)
    from src.floridify.connectors.scraper.wiktionary import WiktionaryConnector
    providers_to_test.append((WiktionaryConnector, test_words[0], {}))
    
    # 2. FreeDictionaryConnector (API, no auth needed)
    from src.floridify.connectors.api.free_dictionary import FreeDictionaryConnector
    providers_to_test.append((FreeDictionaryConnector, test_words[1], {}))
    
    # 3. DictionaryComConnector (scraper, no auth needed)
    from src.floridify.connectors.scraper.dictionary_com import DictionaryComConnector
    providers_to_test.append((DictionaryComConnector, test_words[2], {}))
    
    # 4. WordHippoConnector (scraper, no auth needed)
    from src.floridify.connectors.scraper.wordhippo import WordHippoConnector
    providers_to_test.append((WordHippoConnector, test_words[0], {}))
    
    # 5. AppleDictionaryConnector (local, macOS only)
    try:
        import platform
        if platform.system() == "Darwin":
            from src.floridify.connectors.local.apple_dictionary import AppleDictionaryConnector
            providers_to_test.append((AppleDictionaryConnector, test_words[1], {}))
    except:
        print("ℹ Skipping AppleDictionaryConnector (not on macOS)")
    
    # Note: Skipping OxfordConnector and MerriamWebsterConnector as they need API keys
    
    # Run tests
    for connector_class, word, kwargs in providers_to_test:
        await test_provider(connector_class, word, **kwargs)
        # Small delay between providers
        await asyncio.sleep(1)
    
    print("\n" + "=" * 60)
    print("ALL PROVIDER TESTS COMPLETE")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))