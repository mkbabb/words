#!/usr/bin/env python3
"""Test MongoDB connection through SSH tunnel."""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from motor.motor_asyncio import AsyncIOMotorClient
from floridify.utils.config import Config
from floridify.utils.paths import get_project_root


async def test_connection():
    """Test MongoDB connection through SSH tunnel."""
    print("Testing MongoDB connection through SSH tunnel...")
    
    try:
        # Get settings
        config = Config.from_file()
        print(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
        mongodb_url = config.database.get_url()
        cert_path = config.database.cert_path
        print(f"MongoDB URL: {mongodb_url[:50]}...{mongodb_url[-30:]}")
        print(f"Certificate path: {cert_path}")
        
        # Create client
        print("\nCreating MongoDB client...")
        client = AsyncIOMotorClient(
            mongodb_url,
            tlsCAFile=str(cert_path),
            serverSelectionTimeoutMS=5000,  # 5 second timeout
        )
        
        # Test connection
        print("Testing connection...")
        result = await client.admin.command('ping')
        print(f"✓ Connection successful! Ping result: {result}")
        
        # List databases
        print("\nListing databases...")
        dbs = await client.list_database_names()
        print(f"Available databases: {dbs}")
        
        # Test floridify database
        if config.database.name in dbs:
            print(f"\n✓ Found '{config.database.name}' database")
            db = client[config.database.name]
            
            # List collections
            collections = await db.list_collection_names()
            print(f"Collections: {collections}")
            
            # Count documents in words collection
            if "words" in collections:
                count = await db.words.count_documents({})
                print(f"Words collection has {count} documents")
        else:
            print(f"\n✗ Database '{config.database.name}' not found")
        
        # Close connection
        client.close()
        print("\n✓ Connection test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Connection failed: {type(e).__name__}: {e}")
        return False
    
    return True


if __name__ == "__main__":
    # Ensure we're in development mode
    os.environ["ENVIRONMENT"] = "development"
    
    # Run the test
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)