#!/usr/bin/env python3
"""Test SSE search streaming with real pipeline integration."""

import asyncio
import json
from typing import Any

import httpx


async def test_sse_search(query: str, method: str = "hybrid") -> None:
    """Test SSE search streaming endpoint."""
    url = f"http://localhost:8000/api/v1/search/stream"
    params = {
        "q": query,
        "method": method,
        "max_results": 10,
        "min_score": 0.5,
    }
    
    print(f"\n{'='*60}")
    print(f"Testing SSE search: query='{query}', method='{method}'")
    print(f"{'='*60}\n")
    
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url, params=params, timeout=30.0) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if not line:
                    continue
                
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    continue
                
                if line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        print_event(event_type, data)
                    except json.JSONDecodeError:
                        print(f"Failed to parse data: {data_str}")


def print_event(event_type: str, data: dict[str, Any]) -> None:
    """Pretty print SSE event."""
    if event_type == "progress":
        print(f"[PROGRESS] Stage: {data.get('stage')}, Progress: {data.get('progress')*100:.0f}%")
        print(f"           Message: {data.get('message')}")
        
        # Print partial results if available
        if "partial_results" in data:
            results = data["partial_results"]
            print(f"           Partial results ({len(results)} items):")
            for r in results[:3]:  # Show top 3
                print(f"             - {r['word']} (score: {r['score']:.3f}, method: {r['method']})")
        
        # Print metadata if available
        if "metadata" in data:
            meta = data["metadata"]
            if meta:
                print(f"           Metadata: {meta}")
        print()
        
    elif event_type == "complete":
        print(f"[COMPLETE] Query: '{data['query']}'")
        print(f"           Total results: {data['total_results']}")
        print(f"           Search time: {data['search_time_ms']}ms")
        print(f"           Results:")
        for i, r in enumerate(data["results"][:5], 1):  # Show top 5
            print(f"           {i}. {r['word']} (score: {r['score']:.3f}, method: {r['method']}, phrase: {r['is_phrase']})")
        print()
        
    elif event_type == "error":
        print(f"[ERROR] {data.get('error')}")
        print()


async def main():
    """Run SSE search tests."""
    # Test cases
    test_cases = [
        ("cogn", "hybrid"),      # Prefix/fuzzy search
        ("florid", "exact"),     # Exact search
        ("beautiful", "fuzzy"),  # Fuzzy search
        ("ornate", "semantic"),  # Semantic search (if enabled)
        ("make up", "hybrid"),   # Phrase search
        ("xyz123", "hybrid"),    # No results expected
    ]
    
    for query, method in test_cases:
        try:
            await test_sse_search(query, method)
            await asyncio.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"Test failed for '{query}': {e}")


if __name__ == "__main__":
    asyncio.run(main())