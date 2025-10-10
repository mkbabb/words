#!/usr/bin/env python3
"""Fix _class_id in MongoDB documents for Beanie compatibility."""

import asyncio

from floridify.storage.mongodb import get_storage, init_db


async def main():
    await init_db()
    storage = await get_storage()
    db = storage.client[storage.database_name]

    # Update all documents to BaseVersionedData
    result = await db.versioned_data.update_many({}, {"$set": {"_class_id": "BaseVersionedData"}})

    print(f"Updated {result.modified_count} documents")

    # Verify
    sample = await db.versioned_data.find_one({})
    print(f"Sample _class_id: {sample.get('_class_id')}")

    # Test Beanie query
    from floridify.caching.models import BaseVersionedData

    count = await BaseVersionedData.count()
    print(f"Beanie can now see {count} documents")


if __name__ == "__main__":
    asyncio.run(main())
