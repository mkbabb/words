#!/usr/bin/env python3
"""Test to check if multiple provider data entries are passed to synthesis."""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from src.floridify.models import Definition, ProviderData, Word, SynthesizedDictionaryEntry
from src.floridify.constants import DictionaryProvider
from src.floridify.storage.mongodb import get_storage
from src.floridify.core.lookup_pipeline import _synthesize_with_ai
from src.floridify.ai.factory import get_definition_synthesizer


async def check_synthesis_input():
    """Check what's being passed to the synthesis function."""
    print("Checking synthesis input for 'fork'...")
    
    # Get storage
    storage = await get_storage()
    
    # Find the word
    word = await storage.get_word("fork")
    if not word:
        print("Word 'fork' not found")
        return
        
    print(f"\nFound word: {word.text} (ID: {word.id})")
    
    # Find all provider data
    provider_data_list = await ProviderData.find(
        ProviderData.word_id == str(word.id),
        ProviderData.provider == DictionaryProvider.WIKTIONARY
    ).to_list()
    
    print(f"\nFound {len(provider_data_list)} provider data entries for wiktionary")
    
    # Check what definitions each provider data has
    unique_def_ids = set()
    for i, pd in enumerate(provider_data_list):
        print(f"\nProvider Data {i+1}:")
        print(f"  ID: {pd.id}")
        print(f"  Definition count: {len(pd.definition_ids)}")
        unique_def_ids.update(pd.definition_ids)
        
    print(f"\nTotal unique definition IDs across all provider data: {len(unique_def_ids)}")
    
    # Now let's see what would happen if we passed all provider data to synthesis
    print("\n\nSimulating synthesis with all provider data...")
    all_definitions = []
    
    for pd in provider_data_list:
        for def_id in pd.definition_ids:
            definition = await Definition.get(def_id)
            if definition:
                all_definitions.append(definition)
    
    print(f"Total definitions extracted: {len(all_definitions)}")
    
    # Check for duplicates
    unique_keys = set()
    duplicates = 0
    for defn in all_definitions:
        key = (defn.part_of_speech, defn.text.strip().lower())
        if key in unique_keys:
            duplicates += 1
        else:
            unique_keys.add(key)
    
    print(f"Duplicate definitions: {duplicates}")
    print(f"Unique definitions: {len(unique_keys)}")
    
    # Check existing synthesized entry
    print("\n\nChecking existing synthesized entry...")
    existing = await SynthesizedDictionaryEntry.find_one(
        SynthesizedDictionaryEntry.word_id == str(word.id)
    )
    
    if existing:
        print(f"Found existing entry with {len(existing.definition_ids)} definitions")
        print(f"Source provider data IDs: {len(existing.source_provider_data_ids)}")
        
        # Check if it used multiple provider data
        if len(existing.source_provider_data_ids) > 1:
            print("\n⚠️  ISSUE: Multiple provider data entries were used!")
            print("This could lead to duplicate definitions being synthesized.")
    

if __name__ == "__main__":
    asyncio.run(check_synthesis_input())