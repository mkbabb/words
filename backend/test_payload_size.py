#!/usr/bin/env python3
"""Test script to check the size of the completion payload."""

import asyncio
import json
import sys

sys.path.insert(0, 'src')

from floridify.api.routers.lookup import LookupParams, _cached_lookup
from floridify.constants import DictionaryProvider, Language


async def test_payload_size():
    """Test the size of the bug definition payload."""
    # Create lookup params
    params = LookupParams(
        force_refresh=True,
        providers=[DictionaryProvider.WIKTIONARY],
        languages=[Language.ENGLISH],
        no_ai=False,
    )
    
    # Get the result
    result = await _cached_lookup("bug", params)
    
    if result:
        # Serialize the result
        result_data = result.model_dump(mode='json')
        result_json = json.dumps(result_data)
        
        print(f"Definition payload size: {len(result_json):,} characters")
        print(f"Definition payload size: {len(result_json.encode('utf-8')):,} bytes")
        print(f"Number of definitions: {len(result_data.get('definitions', []))}")
        
        # Check each definition size
        for i, definition in enumerate(result_data.get('definitions', [])):
            def_json = json.dumps(definition)
            print(f"Definition {i+1} size: {len(def_json):,} characters")
            if 'examples' in definition:
                print(f"  - Examples: {len(definition['examples'])}")
        
        # Test if it would trigger chunking
        if len(result_json) > 32768:
            print(f"\n🚨 LARGE PAYLOAD DETECTED! Size {len(result_json):,} > 32KB threshold")
            print("This will trigger chunked completion.")
        else:
            print(f"\n✅ Payload size {len(result_json):,} is under 32KB threshold")
    else:
        print("No result found")

if __name__ == "__main__":
    asyncio.run(test_payload_size())