#!/usr/bin/env python3
"""Complete script to setup chef with custom definition and image."""

import asyncio
import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from floridify.constants import DictionaryProvider, Language
from floridify.core.lookup_pipeline import lookup_word_pipeline
from floridify.models import Definition, Example, ImageMedia, Word
from floridify.models.relationships import MeaningCluster
from floridify.storage.mongodb import get_storage


async def main():
    # Initialize storage
    await get_storage()
    print("✅ Storage initialized")
    
    # Step 1: Perform lookup for "chef"
    print("\n🔍 Looking up 'chef'...")
    entry = await lookup_word_pipeline(
        word="chef",
        providers=[DictionaryProvider.WIKTIONARY],
        languages=[Language.ENGLISH],
        force_refresh=False,  # Don't force refresh on first lookup
        no_ai=False,
    )
    
    if not entry:
        print("❌ No entry found for 'chef'")
        return
    
    print(f"✅ Found entry for 'chef' - Synth Entry ID: {entry.id}")
    
    # Step 2: Add custom definition
    print("\n📝 Adding custom definition...")
    
    # Get the word
    word = await Word.get(entry.word_id)
    if not word:
        print("❌ Word not found")
        return
    
    # Create example in Virginia Woolf style
    example_text = "That chef, that most exquisite of felines, hath departed this temporal realm, leaving behind only the ethereal scent of a morning dew and the memory of whiskers trembling in afternoon light."
    
    # Create custom definition
    custom_definition = Definition(
        word_id=str(word.id),
        part_of_speech="noun",
        text="The best kitty cat the world has ever known. RIP.",
        meaning_cluster=MeaningCluster(
            id="chef_cat",
            name="Chef Cat",
            description="A beloved feline companion",
            order=0,
            relevance=1.0
        ),
        synonyms=["cat", "small cat", "spirit cat", "spirit animal", "ghost", "siamese cat"],
        antonyms=[],
        word_forms=[],
        example_ids=[],
        image_ids=[],
    )
    await custom_definition.save()
    print(f"✅ Created custom definition with ID: {custom_definition.id}")
    
    # Create and save example
    example = Example(
        definition_id=str(custom_definition.id),
        text=example_text,
        type="generated",
        context="In memory of Chef the cat"
    )
    await example.save()
    
    # Add example to definition
    custom_definition.example_ids = [str(example.id)]
    await custom_definition.save()
    
    # Add to entry's definitions (prepend to make it first)
    entry.definition_ids.insert(0, str(custom_definition.id))
    await entry.save()
    print("✅ Added custom definition to entry")
    
    # Step 3: Add image with binary data
    print("\n🖼️  Loading and binding image to synth entry...")
    
    image_path = Path("/Users/mkbabb/Programming/words/data/images/chef-1.png")
    if not image_path.exists():
        print(f"❌ Image not found at {image_path}")
        return
    
    # Read image data
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    print(f"✅ Loaded image: {len(image_data)} bytes")
    
    # Get image metadata
    try:
        from PIL import Image as PILImage
        with PILImage.open(image_path) as img:
            width, height = img.size
            format = img.format.lower() if img.format else image_path.suffix[1:].lower()
    except ImportError:
        # Fallback if PIL not available
        print("⚠️  PIL not available, using default dimensions")
        width, height = 1024, 1024
        format = image_path.suffix[1:].lower()
    
    # Create ImageMedia document with binary data
    image_media = ImageMedia(
        data=image_data,  # Store binary data
        format=format,
        size_bytes=len(image_data),
        width=width,
        height=height,
        alt_text="Chef the cat",
        description="kitty cat",
    )
    await image_media.save()
    print(f"✅ Created image media with ID: {image_media.id}")
    
    # Add to synth entry
    entry.image_ids.append(str(image_media.id))
    entry.version += 1
    await entry.save()
    print("✅ Bound image to synth entry")
    
    print("\n🎉 Complete!")
    print(f"   Synth Entry ID: {entry.id}")
    print(f"   Custom Definition ID: {custom_definition.id}")
    print(f"   Image ID: {image_media.id}")
    print(f"   Image has data: {image_media.data is not None}")


if __name__ == "__main__":
    asyncio.run(main())