#!/usr/bin/env python3
"""Test production MongoDB connection and basic app functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from floridify.utils.config import get_database_config, load_config
from floridify.storage.mongodb import get_storage
from floridify.models.models import DictionaryEntry


async def test_database_connection():
    """Test database connection with current configuration."""
    print("🔍 Testing MongoDB Connection")
    print("=" * 50)
    
    # Test config loading
    try:
        mongodb_url, database_name = get_database_config()
        print(f"✅ Config loaded successfully")
        print(f"   Database: {database_name}")
        print(f"   URL: {mongodb_url[:30]}..." if len(mongodb_url) > 30 else f"   URL: {mongodb_url}")
        
        # Mask sensitive parts of production URL
        if "docdb" in mongodb_url:
            print("   🔒 Production DocumentDB detected")
        else:
            print("   🏠 Local MongoDB detected")
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False
    
    # Test MongoDB connection
    try:
        print(f"\n📡 Connecting to MongoDB...")
        storage = await get_storage()
        print("✅ MongoDB connection successful")
        
        # Test basic operations
        print(f"\n🧪 Testing basic database operations...")
        
        # Try to check if a word exists (should be safe, read-only)
        exists = await storage.entry_exists("test")
        print("✅ Database query successful")
        print(f"   Word 'test' exists: {exists}")
        
        # Test connection info
        client = storage.client
        if client:
            server_info = await client.admin.command("hello")
            print(f"✅ Server info retrieved:")
            print(f"   Server: {server_info.get('hosts', ['unknown'])[0] if server_info.get('hosts') else 'unknown'}")
            print(f"   Version: {server_info.get('version', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def test_config_structure():
    """Test that Config object loads correctly."""
    print(f"\n⚙️  Testing Configuration Structure")
    print("=" * 50)
    
    try:
        config = load_config()
        print("✅ Structured config loaded successfully")
        print(f"   OpenAI model: {config.openai.model}")
        print(f"   Database name: {config.database.name}")
        print(f"   Database URL: {config.database.url[:30]}...")
        
        # Test that all required sections exist
        sections = ["openai", "oxford", "dictionary_com", "database"]
        for section in sections:
            if hasattr(config, section):
                print(f"   ✅ {section} section present")
            else:
                print(f"   ❌ {section} section missing")
                
        return True
        
    except Exception as e:
        print(f"❌ Structured config loading failed: {e}")
        return False


def test_environment_variables():
    """Test environment variable detection."""
    print(f"\n🌍 Testing Environment Variables")
    print("=" * 50)
    
    env_vars = ["MONGODB_URL", "MONGODB_DATABASE", "FLORIDIFY_CONFIG_PATH"]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive data
            if "mongodb://" in value and len(value) > 30:
                masked_value = f"{value[:20]}...{value[-10:]}"
            else:
                masked_value = value
            print(f"   ✅ {var}: {masked_value}")
        else:
            print(f"   ⚪ {var}: not set")
    
    return True


async def main():
    """Run all tests."""
    print("🚀 Floridify Production Connection Test")
    print("=" * 60)
    
    # Run tests
    tests = [
        test_environment_variables,
        test_config_structure,
        test_database_connection,
    ]
    
    results = []
    for i, test in enumerate(tests, 1):
        print(f"\nTest {i}/{len(tests)}: {test.__name__}")
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! MongoDB connection is working.")
        return 0
    else:
        print("⚠️  Some tests failed. Check configuration.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with unexpected error: {e}")
        sys.exit(1)