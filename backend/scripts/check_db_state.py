#!/usr/bin/env python3
"""Check actual database state."""

import asyncio

from floridify.caching.models import BaseVersionedData
from floridify.storage.mongodb import get_storage, init_db


async def main():
    await init_db()

    # Count with Beanie
    beanie_count = await BaseVersionedData.count()
    print(f"Beanie count: {beanie_count}")

    # Count with raw pymongo
    storage = await get_storage()
    db = storage.client[storage.database_name]
    raw_count = await db.versioned_data.count_documents({})
    print(f"Raw pymongo count: {raw_count}")

    if raw_count > 0:
        doc = await db.versioned_data.find_one({})
        print(f"Sample doc _class_id: {doc.get('_class_id')}")
        print(f"Sample doc resource_id: {doc.get('resource_id')}")
        print(f"Sample doc resource_type: {doc.get('resource_type')}")


if __name__ == "__main__":
    asyncio.run(main())
