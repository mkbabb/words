#!/usr/bin/env python3
"""Test script for SSE endpoints."""

import asyncio
import aiohttp
import json


async def test_lookup_stream():
    """Test the lookup SSE endpoint."""
    print("\n=== Testing Lookup SSE Endpoint ===")
    
    url = "http://localhost:8000/api/v1/lookup/serendipity/stream"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('event:'):
                    event_type = line.split(':', 1)[1].strip()
                    print(f"\nEvent: {event_type}")
                elif line.startswith('data:'):
                    data = json.loads(line.split(':', 1)[1].strip())
                    if event_type == 'progress':
                        print(f"  Stage: {data['stage']}")
                        print(f"  Progress: {data['progress']:.0%}")
                        print(f"  Message: {data['message']}")
                    elif event_type == 'complete':
                        print(f"  Word: {data['word']}")
                        print(f"  Definitions: {len(data['definitions'])} found")
                    elif event_type == 'error':
                        print(f"  Error: {data['error']}")


async def test_search_stream():
    """Test the search SSE endpoint."""
    print("\n=== Testing Search SSE Endpoint ===")
    
    url = "http://localhost:8000/api/v1/search/stream?q=cognition"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('event:'):
                    event_type = line.split(':', 1)[1].strip()
                    print(f"\nEvent: {event_type}")
                elif line.startswith('data:'):
                    data = json.loads(line.split(':', 1)[1].strip())
                    if event_type == 'progress':
                        print(f"  Stage: {data['stage']}")
                        print(f"  Progress: {data['progress']:.0%}")
                        print(f"  Message: {data['message']}")
                    elif event_type == 'complete':
                        print(f"  Query: {data['query']}")
                        print(f"  Results: {data['total_results']} found")
                        print(f"  Time: {data['search_time_ms']}ms")
                        if data['results']:
                            print(f"  Top result: {data['results'][0]['word']} (score: {data['results'][0]['score']:.3f})")
                    elif event_type == 'error':
                        print(f"  Error: {data['error']}")


async def main():
    """Run all tests."""
    try:
        await test_lookup_stream()
        await test_search_stream()
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure the backend server is running on http://localhost:8000")


if __name__ == "__main__":
    asyncio.run(main())