#!/usr/bin/env python3
"""Test script for cascading image deletion."""

import asyncio
import logging

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.floridify.api.repositories.image_repository import ImageRepository
from src.floridify.models import Definition, ImageMedia, SynthesizedDictionaryEntry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cascade_deletion():
    """Test the cascade deletion functionality."""
    
    # Initialize database connection
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(
        database=client.floridify,
        document_models=[ImageMedia, Definition, SynthesizedDictionaryEntry]
    )
    
    # Create repository
    repo = ImageRepository()
    
    # Find an image that has references (for testing)
    # This is just for demonstration - in real usage, you'd delete specific images
    images_with_refs = await ImageMedia.find().to_list()
    
    if not images_with_refs:
        logger.info("No images found to test")
        return
    
    # Check for entries with image references
    entries_with_images = await SynthesizedDictionaryEntry.find(
        SynthesizedDictionaryEntry.image_ids != []
    ).to_list()
    
    definitions_with_images = await Definition.find(
        Definition.image_ids != []
    ).to_list()
    
    logger.info(f"Found {len(entries_with_images)} entries with images")
    logger.info(f"Found {len(definitions_with_images)} definitions with images")
    
    if entries_with_images:
        entry = entries_with_images[0]
        if entry.image_ids:
            image_id = entry.image_ids[0]
            logger.info(f"Testing deletion of image {image_id} referenced by entry {entry.id}")
            
            # Count references before deletion
            entries_before = await SynthesizedDictionaryEntry.find(
                SynthesizedDictionaryEntry.image_ids.in_([image_id])
            ).count()
            definitions_before = await Definition.find(
                Definition.image_ids.in_([image_id])
            ).count()
            
            logger.info(f"Before deletion: {entries_before} entries, {definitions_before} definitions reference this image")
            
            # Perform cascade deletion
            try:
                await repo.delete(image_id)
                logger.info(f"Successfully deleted image {image_id}")
                
                # Count references after deletion
                entries_after = await SynthesizedDictionaryEntry.find(
                    SynthesizedDictionaryEntry.image_ids.in_([image_id])
                ).count()
                definitions_after = await Definition.find(
                    Definition.image_ids.in_([image_id])
                ).count()
                
                logger.info(f"After deletion: {entries_after} entries, {definitions_after} definitions reference this image")
                
                if entries_after == 0 and definitions_after == 0:
                    logger.info("✅ Cascade deletion successful - all references cleaned up")
                else:
                    logger.error("❌ Cascade deletion failed - references still exist")
                    
            except Exception as e:
                logger.error(f"Error during deletion: {e}")
    
    # Close database connection
    client.close()

if __name__ == "__main__":
    asyncio.run(test_cascade_deletion())