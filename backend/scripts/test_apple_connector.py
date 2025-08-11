#!/usr/bin/env python
"""Test Apple Dictionary connector directly on macOS."""

import asyncio
import sys
from pathlib import Path

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
    
    return database


async def test_apple_dictionary():
    """Test Apple Dictionary connector."""
    from src.floridify.models import Word
    from src.floridify.models.definition import Language
    from src.floridify.connectors.config import VersionConfig
    from src.floridify.connectors.local.apple_dictionary import AppleDictionaryConnector
    
    print("=" * 60)
    print("Testing Apple Dictionary Connector on macOS")
    print("=" * 60)
    
    # Initialize database
    print("\nInitializing database...")
    try:
        await init_database()
        print("✓ Database connected")
    except Exception as e:
        print(f"✗ Database failed: {e}")
        return False
    
    # Test connector initialization
    print("\nInitializing Apple Dictionary connector...")
    try:
        connector = AppleDictionaryConnector()
        print(f"✓ Apple Dictionary connector initialized")
        print(f"  Platform compatible: {connector._platform_compatible}")
        print(f"  Service available: {connector._is_available()}")
        
        # Get service info
        info = connector.get_service_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"✗ Apple Dictionary initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if not connector._is_available():
        print("\n⚠️ Apple Dictionary Services not available")
        return False
    
    # Test words
    test_words = ["apple", "dictionary", "computer", "example"]
    
    for word_text in test_words:
        print(f"\n{'-' * 40}")
        print(f"Testing word: '{word_text}'")
        print(f"{'-' * 40}")
        
        try:
            # Create word
            word = Word(
                text=word_text,
                normalized=word_text.lower(),
                language=Language.ENGLISH,
            )
            await word.save()
            print(f"✓ Created word object")
            
            # Test fetch with versioning
            config = VersionConfig(save_versioned=True)
            result = await connector.fetch_definition(word, version_config=config)
            
            if result:
                print(f"✓ Fetched definition successfully")
                print(f"  Provider: {result.provider}")
                print(f"  Definitions: {len(result.definition_ids)}")
                
                if result.pronunciation_id:
                    print(f"  Has pronunciation: Yes")
                    # Load pronunciation
                    from src.floridify.models import Pronunciation
                    pron = await Pronunciation.get(result.pronunciation_id)
                    if pron:
                        print(f"    IPA: {pron.ipa}")
                        print(f"    Phonetic: {pron.phonetic}")
                
                if result.etymology:
                    print(f"  Has etymology: Yes")
                    print(f"    Text: {result.etymology.text[:100]}...")
                
                # Load and show first definition
                if result.definition_ids:
                    from src.floridify.models import Definition
                    definition = await Definition.get(result.definition_ids[0])
                    if definition:
                        print(f"  First definition:")
                        print(f"    Part of speech: {definition.part_of_speech}")
                        print(f"    Text: {definition.text[:200]}...")
                        
                        # Show examples
                        if definition.example_ids:
                            from src.floridify.models import Example
                            examples = await Example.find(
                                {"_id": {"$in": definition.example_ids}}
                            ).to_list()
                            print(f"    Examples: {len(examples)}")
                            for i, example in enumerate(examples[:2]):
                                print(f"      {i+1}. {example.text}")
            else:
                print(f"ℹ No definition found for '{word_text}'")
                
        except Exception as e:
            print(f"✗ Error testing '{word_text}': {e}")
            import traceback
            traceback.print_exc()
    
    # Test force refresh
    print(f"\n{'-' * 40}")
    print("Testing force refresh")
    print(f"{'-' * 40}")
    
    try:
        word = Word(
            text="test",
            normalized="test",
            language=Language.ENGLISH,
        )
        await word.save()
        
        config_force = VersionConfig(
            force_api=True,
            save_versioned=True,
            increment_version=True,
        )
        
        result = await connector.fetch_definition(word, version_config=config_force)
        if result:
            print("✓ Force refresh worked")
        else:
            print("ℹ No data for force refresh test")
            
    except Exception as e:
        print(f"✗ Force refresh test failed: {e}")
    
    print("\n" + "=" * 60)
    print("Apple Dictionary Test Complete")
    print("=" * 60)
    
    return True


async def main():
    """Run the test."""
    try:
        success = await test_apple_dictionary()
        return 0 if success else 1
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))