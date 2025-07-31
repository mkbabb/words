#!/usr/bin/env python3
"""Fix broken image references in the 'queen' synthesized entry."""

import asyncio
import logging
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.floridify.models import ImageMedia, SynthesizedDictionaryEntry, Word
from src.floridify.api.repositories.synthesis_repository import SynthesisRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_queen_entry():
    """Find and fix the queen entry."""
    
    # Initialize database connection
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(
        database=client.floridify,
        document_models=[ImageMedia, SynthesizedDictionaryEntry, Word]
    )
    
    logger.info("Connected to database")
    
    try:
        # Find the word "queen"
        queen_word = await Word.find_one(Word.text == "queen")
        if not queen_word:
            logger.error("Could not find word 'queen'")
            return
        
        logger.info(f"Found word 'queen' with ID: {queen_word.id}")
        
        # Find synthesized entries for "queen"
        queen_entries = await SynthesizedDictionaryEntry.find(
            SynthesizedDictionaryEntry.word_id == queen_word.id
        ).to_list()
        
        if not queen_entries:
            logger.error("No synthesized entries found for 'queen'")
            return
        
        logger.info(f"Found {len(queen_entries)} synthesized entries for 'queen'")
        
        # Process each entry
        for entry in queen_entries:
            logger.info(f"Processing entry {entry.id}")
            logger.info(f"Entry has {len(entry.image_ids)} image IDs: {entry.image_ids}")
            
            if not entry.image_ids:
                logger.info("No image IDs to check")
                continue
            
            # Check which images actually exist
            valid_image_ids = []
            broken_image_ids = []
            
            for image_id in entry.image_ids:
                try:
                    image = await ImageMedia.get(image_id)
                    if image:
                        valid_image_ids.append(image_id)
                        logger.info(f"✅ Image {image_id} exists")
                    else:
                        broken_image_ids.append(image_id)
                        logger.warning(f"❌ Image {image_id} not found")
                except Exception as e:
                    broken_image_ids.append(image_id)
                    logger.warning(f"❌ Error checking image {image_id}: {e}")
            
            # Update entry if there are broken references
            if broken_image_ids:
                logger.info(f"Removing {len(broken_image_ids)} broken image references: {broken_image_ids}")
                
                # Update the entry with only valid image IDs
                entry.image_ids = valid_image_ids
                await entry.save()
                
                logger.info(f"✅ Updated entry {entry.id} - removed broken image references")
                logger.info(f"Entry now has {len(entry.image_ids)} valid image IDs: {entry.image_ids}")
            else:
                logger.info("No broken image references found")
        
        logger.info("✅ Successfully processed all 'queen' entries")
        
    except Exception as e:
        logger.error(f"Error processing queen entry: {e}")
        raise
    finally:
        # Close database connection
        client.close()

async def cleanup_all_broken_refs():
    """Clean up all broken image references across all entries."""
    
    # Initialize database connection
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(
        database=client.floridify,
        document_models=[ImageMedia, SynthesizedDictionaryEntry]
    )
    
    logger.info("Starting cleanup of all broken image references")
    
    try:
        # Get all entries with image IDs
        entries_with_images = await SynthesizedDictionaryEntry.find(
            SynthesizedDictionaryEntry.image_ids != []
        ).to_list()
        
        logger.info(f"Found {len(entries_with_images)} entries with image references")
        
        total_cleaned = 0
        total_broken = 0
        
        for entry in entries_with_images:
            valid_image_ids = []
            broken_count = 0
            
            for image_id in entry.image_ids:
                try:
                    image = await ImageMedia.get(image_id)
                    if image:
                        valid_image_ids.append(image_id)
                    else:
                        broken_count += 1
                        total_broken += 1
                except Exception:
                    broken_count += 1
                    total_broken += 1
            
            if broken_count > 0:
                logger.info(f"Entry {entry.id}: removing {broken_count} broken image references")
                entry.image_ids = valid_image_ids
                await entry.save()
                total_cleaned += 1
        
        logger.info(f"✅ Cleanup complete: {total_cleaned} entries updated, {total_broken} broken references removed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        print("Cleaning up all broken image references...")
        asyncio.run(cleanup_all_broken_refs())
    else:
        print("Fixing 'queen' entry...")
        asyncio.run(fix_queen_entry())
        print("\nTo clean up all broken references, run: python fix_queen_entry.py --all")