#!/usr/bin/env python3
"""Cleanup broken image references from all synthesized entries."""

import asyncio
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from floridify.models import ImageMedia, SynthesizedDictionaryEntry, Definition

async def cleanup_broken_image_refs():
    """Remove broken image references from all entries and definitions."""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    database = client.floridify
    
    # Initialize Beanie
    await init_beanie(
        database=database,
        document_models=[ImageMedia, SynthesizedDictionaryEntry, Definition]
    )
    
    print("🔄 Starting cleanup of broken image references...")
    
    # Get all existing image IDs
    existing_images = await ImageMedia.find().to_list()
    existing_image_ids = {str(img.id) for img in existing_images}
    print(f"📊 Found {len(existing_image_ids)} existing images in database")
    
    # Process SynthesizedDictionaryEntry documents
    print("\n🔍 Checking synthesized entries...")
    entries = await SynthesizedDictionaryEntry.find(
        SynthesizedDictionaryEntry.image_ids != []
    ).to_list()
    
    updated_entries = 0
    removed_refs = 0
    
    for entry in entries:
        original_count = len(entry.image_ids)
        # Keep only image IDs that actually exist
        valid_image_ids = [
            img_id for img_id in entry.image_ids 
            if str(img_id) in existing_image_ids
        ]
        
        if len(valid_image_ids) != original_count:
            broken_count = original_count - len(valid_image_ids)
            print(f"  📝 Entry {entry.id}: removing {broken_count} broken references")
            entry.image_ids = valid_image_ids
            await entry.save()
            updated_entries += 1
            removed_refs += broken_count
    
    print(f"✅ Updated {updated_entries} synthesized entries, removed {removed_refs} broken references")
    
    # Process Definition documents
    print("\n🔍 Checking definitions...")
    definitions = await Definition.find(
        Definition.image_ids != []
    ).to_list()
    
    updated_definitions = 0
    removed_def_refs = 0
    
    for definition in definitions:
        original_count = len(definition.image_ids)
        # Keep only image IDs that actually exist
        valid_image_ids = [
            img_id for img_id in definition.image_ids 
            if str(img_id) in existing_image_ids
        ]
        
        if len(valid_image_ids) != original_count:
            broken_count = original_count - len(valid_image_ids)
            print(f"  📝 Definition {definition.id}: removing {broken_count} broken references")
            definition.image_ids = valid_image_ids
            await definition.save()
            updated_definitions += 1
            removed_def_refs += broken_count
    
    print(f"✅ Updated {updated_definitions} definitions, removed {removed_def_refs} broken references")
    
    # Summary
    total_updated = updated_entries + updated_definitions
    total_removed = removed_refs + removed_def_refs
    
    print(f"\n🎉 Cleanup complete!")
    print(f"   📊 Total documents updated: {total_updated}")
    print(f"   🗑️  Total broken references removed: {total_removed}")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(cleanup_broken_image_refs())