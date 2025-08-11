#!/usr/bin/env python
"""Test scraper connectors (WordHippo and Dictionary.com)."""

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


async def test_scraper_connector(connector_class, connector_name, test_words):
    """Test a scraper connector."""
    from src.floridify.models import Word
    from src.floridify.models.definition import Language
    from src.floridify.connectors.config import VersionConfig
    
    print(f"\n{'=' * 60}")
    print(f"Testing {connector_name}")
    print(f"{'=' * 60}")
    
    # Initialize connector
    try:
        connector = connector_class()
        print(f"✓ {connector_name} connector initialized")
        print(f"  Provider: {connector.provider_name}")
        print(f"  Rate limit: {connector.rate_limit} req/sec")
    except Exception as e:
        print(f"✗ {connector_name} initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    success_count = 0
    
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
            config = VersionConfig(save_versioned=True, force_api=True)
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
                
                # Load and show definitions
                if result.definition_ids:
                    from src.floridify.models import Definition
                    definitions = await Definition.find(
                        {"_id": {"$in": result.definition_ids}}
                    ).to_list()
                    
                    print(f"  Definitions found: {len(definitions)}")
                    for i, definition in enumerate(definitions[:3]):  # Show first 3
                        print(f"    {i+1}. [{definition.part_of_speech}] {definition.text[:150]}...")
                        
                        # Show examples
                        if definition.example_ids:
                            from src.floridify.models import Example
                            examples = await Example.find(
                                {"_id": {"$in": definition.example_ids}}
                            ).to_list()
                            print(f"       Examples: {len(examples)}")
                            for j, example in enumerate(examples[:2]):
                                print(f"         {j+1}. {example.text}")
                
                success_count += 1
                
            else:
                print(f"ℹ No definition found for '{word_text}'")
                
            # Small delay between requests for scraper politeness
            await asyncio.sleep(2)
                
        except Exception as e:
            print(f"✗ Error testing '{word_text}': {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{connector_name} Results: {success_count}/{len(test_words)} words successful")
    return success_count > 0


async def test_all_scrapers():
    """Test all scraper connectors."""
    print("=" * 60)
    print("TESTING SCRAPER CONNECTORS")
    print("=" * 60)
    
    # Initialize database
    print("\nInitializing database...")
    try:
        await init_database()
        print("✓ Database connected and initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False
    
    # Test words - using common words that should exist in most dictionaries
    test_words = ["hello", "world", "computer", "love"]
    
    all_success = True
    
    # Test Dictionary.com scraper
    try:
        from src.floridify.connectors.scraper.dictionary_com import DictionaryComConnector
        success = await test_scraper_connector(
            DictionaryComConnector,
            "Dictionary.com Connector",
            test_words
        )
        if not success:
            all_success = False
    except Exception as e:
        print(f"✗ Dictionary.com connector test failed: {e}")
        all_success = False
    
    # Test WordHippo scraper  
    try:
        from src.floridify.connectors.scraper.wordhippo import WordHippoConnector
        success = await test_scraper_connector(
            WordHippoConnector,
            "WordHippo Connector", 
            test_words
        )
        if not success:
            all_success = False
    except Exception as e:
        print(f"✗ WordHippo connector test failed: {e}")
        all_success = False
    
    # Test force refresh functionality
    print(f"\n{'=' * 60}")
    print("Testing Force Refresh Functionality")
    print(f"{'=' * 60}")
    
    try:
        from src.floridify.connectors.scraper.dictionary_com import DictionaryComConnector
        from src.floridify.models import Word
        from src.floridify.models.definition import Language
        from src.floridify.connectors.config import VersionConfig
        
        connector = DictionaryComConnector()
        
        word = Word(
            text="refresh_test",
            normalized="refresh_test",
            language=Language.ENGLISH,
        )
        await word.save()
        
        # First fetch
        config1 = VersionConfig(save_versioned=True, force_api=False)
        result1 = await connector.fetch_definition(word, version_config=config1)
        
        # Second fetch (should use cache)
        result2 = await connector.fetch_definition(word, version_config=config1)
        
        # Force refresh
        config2 = VersionConfig(save_versioned=True, force_api=True, increment_version=True)
        result3 = await connector.fetch_definition(word, version_config=config2)
        
        print("✓ Force refresh functionality tested")
        
    except Exception as e:
        print(f"✗ Force refresh test failed: {e}")
        all_success = False
    
    print(f"\n{'=' * 60}")
    if all_success:
        print("ALL SCRAPER TESTS COMPLETED SUCCESSFULLY")
    else:
        print("SOME SCRAPER TESTS FAILED")
    print(f"{'=' * 60}")
    
    return all_success


async def main():
    """Run the test."""
    try:
        success = await test_all_scrapers()
        return 0 if success else 1
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))