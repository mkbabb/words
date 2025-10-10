#!/usr/bin/env python3
"""Test if BaseVersionedData is properly initialized with Beanie."""

import asyncio
from floridify.storage.mongodb import get_storage
from floridify.caching.models import BaseVersionedData


async def main():
    # Initialize storage
    storage = await get_storage()
    print(f"✅ Storage initialized: {storage}")

    # Check if BaseVersionedData collection is initialized
    try:
        collection = BaseVersionedData.get_pymongo_collection()
        if collection is None:
            print("❌ BaseVersionedData collection is None!")
        else:
            print(f"✅ BaseVersionedData collection: {collection.name}")

            # Try a simple query
            count = await BaseVersionedData.count()
            print(f"✅ Document count: {count}")

            # Test find
            results = await BaseVersionedData.find().limit(1).to_list()
            print(f"✅ Sample query works, found {len(results)} documents")

    except Exception as e:
        print(f"❌ Error accessing BaseVersionedData collection: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
