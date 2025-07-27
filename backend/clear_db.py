#!/usr/bin/env python3
"""Clear MongoDB database collections."""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from src.floridify.models.models import (
    Word, Definition, Pronunciation, Example, 
    SynthesizedDictionaryEntry, ProviderData, Fact
)

async def clear_database():
    """Clear all collections in the database."""
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.floridify
    
    # Initialize Beanie with document models
    await init_beanie(
        database=db,
        document_models=[
            Word,
            Definition,
            Pronunciation,
            Example,
            SynthesizedDictionaryEntry,
            ProviderData,
            AudioMedia,
            Fact
        ]
    )
    
    # Clear all collections
    collections = [
        Word,
        Definition,
        Pronunciation,
        Example,
        SynthesizedDictionaryEntry,
        ProviderData,
        AudioMedia,
        Fact
    ]
    
    for collection in collections:
        count = await collection.find().count()
        if count > 0:
            await collection.delete_all()
            print(f"✅ Cleared {collection.__name__} collection ({count} documents)")
        else:
            print(f"ℹ️  {collection.__name__} collection is already empty")
    
    print("\n🎉 Database cleared successfully!")

if __name__ == "__main__":
    asyncio.run(clear_database())