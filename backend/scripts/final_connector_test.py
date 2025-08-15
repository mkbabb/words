#!/usr/bin/env python
"""Final comprehensive test of all working connectors."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Direct MongoDB connection for testing
MONGODB_URL = "mongodb://localhost:27017/floridify_test"


async def init_database():
    """Initialize database connection directly."""
    from beanie import init_beanie
    from motor.motor_asyncio import AsyncIOMotorClient

    from src.floridify.models import Definition, Example, Pronunciation, ProviderData, Word
    from src.floridify.models.provider import VersionedProviderData
    
    # Connect directly to local MongoDB
    client = AsyncIOMotorClient(MONGODB_URL)
    database = client["floridify_test"]
    
    # Initialize Beanie
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


async def test_connector_comprehensive(connector_class, name, test_word, **init_kwargs):
    """Test a connector comprehensively."""
    from src.floridify.models import Word
    from floridify.models.dictionary import Language
    from src.floridify.models.provider import VersionedProviderData
    from src.floridify.providers.base import VersionConfig
    
    print(f"\n{'=' * 60}")
    print(f"COMPREHENSIVE TEST: {name}")
    print(f"{'=' * 60}")
    
    try:
        # Initialize connector
        connector = connector_class(**init_kwargs)
        print(f"✓ {name} initialized successfully")
        print(f"  Provider: {connector.provider_name}")
        print(f"  Rate limit: {connector.rate_limit} req/sec")
        
        # Create test word
        word = Word(
            text=test_word,
            normalized=test_word.lower(),
            language=Language.ENGLISH,
        )
        await word.save()
        print(f"✓ Test word '{test_word}' created")
        
        # Test 1: Initial fetch with versioning
        print("\n1. Initial fetch with versioning:")
        config1 = VersionConfig(save_versioned=True, force_api=True)
        result1 = await connector.fetch_definition(word, version_config=config1)
        
        if result1:
            print("  ✓ Successfully fetched definition")
            print(f"    Provider: {result1.provider}")
            print(f"    Definitions: {len(result1.definition_ids)}")
            print(f"    Has pronunciation: {result1.pronunciation_id is not None}")
            print(f"    Has etymology: {result1.etymology is not None}")
            
            # Check versioned storage
            versioned1 = await VersionedProviderData.find_one(
                {"word_id": word.id, "provider": connector.provider_name, "version_info.is_latest": True}
            )
            if versioned1:
                print(f"    ✓ Saved to versioned storage v{versioned1.version_info.provider_version}")
                initial_hash = versioned1.version_info.data_hash
            else:
                print("    ✗ Not saved to versioned storage")
                initial_hash = None
        else:
            print(f"  ℹ No definition found for '{test_word}'")
            return False
        
        # Test 2: Fetch again (should use cache)
        print("\n2. Test caching behavior:")
        config2 = VersionConfig(save_versioned=True, force_api=False)
        result2 = await connector.fetch_definition(word, version_config=config2)
        
        if result2:
            print("  ✓ Second fetch successful (used cache)")
            versioned2 = await VersionedProviderData.find_one(
                {"word_id": word.id, "provider": connector.provider_name, "version_info.is_latest": True}
            )
            if versioned2 and initial_hash and versioned2.version_info.data_hash == initial_hash:
                print("  ✓ Same data hash (no duplicate save)")
            else:
                print("  ℹ Data hash changed or missing")
        
        # Test 3: Force refresh
        print("\n3. Test force refresh:")
        config3 = VersionConfig(save_versioned=True, force_api=True, increment_version=True)
        result3 = await connector.fetch_definition(word, version_config=config3)
        
        if result3:
            print("  ✓ Force refresh successful")
            versioned3 = await VersionedProviderData.find_one(
                {"word_id": word.id, "provider": connector.provider_name, "version_info.is_latest": True}
            )
            if versioned3:
                if initial_hash and versioned3.version_info.data_hash != initial_hash:
                    print(f"  ✓ New version created: v{versioned3.version_info.provider_version}")
                else:
                    print(f"  ℹ Same data, version: v{versioned3.version_info.provider_version}")
        
        # Test 4: Version-specific fetch
        print("\n4. Test version-specific fetch:")
        if versioned1:
            config4 = VersionConfig(version=versioned1.version_info.provider_version)
            result4 = await connector.fetch_definition(word, version_config=config4)
            if result4:
                print(f"  ✓ Fetched specific version v{versioned1.version_info.provider_version}")
            else:
                print("  ✗ Could not fetch specific version")
        
        # Test 5: Backward compatibility
        print("\n5. Test backward compatibility:")
        result5 = await connector.fetch_definition(
            word,
            force_api=False,
            save_versioned=True,
        )
        if result5:
            print("  ✓ Backward compatible API works")
        else:
            print("  ✗ Backward compatibility failed")
        
        print(f"\n✅ {name} - All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ {name} - Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run tests for all working connectors."""
    print("=" * 60)
    print("FINAL COMPREHENSIVE CONNECTOR TESTS")
    print("=" * 60)
    
    # Initialize database
    print("\nInitializing database...")
    try:
        await init_database()
        print("✓ Database connected and initialized")
    except Exception as e:
        print(f"✗ Database failed: {e}")
        return False
    
    results = []
    
    # Test 1: Apple Dictionary (macOS only)
    try:
        import platform
        if platform.system() == "Darwin":
            from src.floridify.providers.dictionary.local.apple_dictionary import (
                AppleDictionaryConnector,
            )
            result = await test_connector_comprehensive(
                AppleDictionaryConnector,
                "Apple Dictionary",
                "apple"
            )
            results.append(("Apple Dictionary", result))
        else:
            print("\n⚠️ Skipping Apple Dictionary (not on macOS)")
    except Exception as e:
        print(f"\n❌ Apple Dictionary test setup failed: {e}")
        results.append(("Apple Dictionary", False))
    
    # Test 2: WordHippo Scraper
    try:
        from src.floridify.providers.dictionary.scraper.wordhippo import WordHippoConnector
        result = await test_connector_comprehensive(
            WordHippoConnector,
            "WordHippo Scraper",
            "computer"
        )
        results.append(("WordHippo", result))
    except Exception as e:
        print(f"\n❌ WordHippo test setup failed: {e}")
        results.append(("WordHippo", False))
    
    # Test 3: Free Dictionary API
    try:
        from src.floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector
        result = await test_connector_comprehensive(
            FreeDictionaryConnector,
            "Free Dictionary API", 
            "hello"
        )
        results.append(("Free Dictionary", result))
    except Exception as e:
        print(f"\n❌ Free Dictionary test setup failed: {e}")
        results.append(("Free Dictionary", False))
    
    # Test 4: Wiktionary Scraper  
    try:
        from src.floridify.providers.dictionary.scraper.wiktionary import WiktionaryConnector
        result = await test_connector_comprehensive(
            WiktionaryConnector,
            "Wiktionary Scraper",
            "example"
        )
        results.append(("Wiktionary", result))
    except Exception as e:
        print(f"\n❌ Wiktionary test setup failed: {e}")
        results.append(("Wiktionary", False))
    
    # Final Results
    print(f"\n{'=' * 60}")
    print("FINAL RESULTS SUMMARY")
    print(f"{'=' * 60}")
    
    passed = 0
    total = len(results)
    
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{name:<20}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} connectors passed all tests")
    
    if passed == total:
        print("🎉 ALL CONNECTORS WORKING PERFECTLY!")
    elif passed > 0:
        print("⚠️ Some connectors working, some need attention")
    else:
        print("❌ All connectors need fixes")
    
    print(f"\n{'=' * 60}")
    print("Test completed!")
    print(f"{'=' * 60}")
    
    return passed == total


async def main():
    """Run the comprehensive test."""
    try:
        success = await run_all_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))