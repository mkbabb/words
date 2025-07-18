#!/usr/bin/env python3
"""Test search API integration with real pipeline."""

import asyncio
import httpx


async def test_search_api(query: str, method: str = "hybrid") -> None:
    """Test regular search API endpoint."""
    url = "http://localhost:8000/api/v1/search"
    params = {
        "q": query,
        "method": method,
        "max_results": 5,
        "min_score": 0.5,
    }
    
    print(f"\n[TEST] Search API: query='{query}', method='{method}'")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"  Results: {data['total_results']} found in {data['search_time_ms']}ms")
        
        for i, result in enumerate(data['results'][:3], 1):
            print(f"  {i}. {result['word']} (score: {result['score']:.3f}, method: {result['method']})")


async def test_search_methods():
    """Test different search methods."""
    test_cases = [
        # (query, method, description)
        ("cognition", "exact", "Exact match test"),
        ("cogn", "fuzzy", "Fuzzy/prefix match test"),
        ("beautiful", "semantic", "Semantic search test"),
        ("make", "hybrid", "Hybrid search test"),
        ("xyz123", "exact", "No results test"),
    ]
    
    print("Testing Search API Integration")
    print("=" * 60)
    
    for query, method, desc in test_cases:
        print(f"\n{desc}:")
        try:
            await test_search_api(query, method)
        except Exception as e:
            print(f"  ERROR: {e}")
        
        await asyncio.sleep(0.5)  # Brief pause between tests


async def test_performance():
    """Test search performance and caching."""
    query = "beautiful"
    
    print("\n\nPerformance Test")
    print("=" * 60)
    
    # First call (cold cache)
    print("\nFirst call (cold cache):")
    await test_search_api(query, "hybrid")
    
    # Second call (warm cache)
    print("\nSecond call (warm cache - should be faster):")
    await test_search_api(query, "hybrid")
    
    # Different method (should not use cache)
    print("\nDifferent method (should not use cache):")
    await test_search_api(query, "exact")


async def main():
    """Run all tests."""
    await test_search_methods()
    await test_performance()
    
    print("\n\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(main())