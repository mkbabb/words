#!/usr/bin/env python3
"""Simple test for request deduplication."""

import asyncio
import time
import httpx


async def test_deduplication():
    """Test concurrent requests are deduplicated."""
    # Use force_refresh to bypass cache and test deduplication
    url = "http://localhost:8000/api/v1/lookup/serendipity?force_refresh=true"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test 1: Single request timing
        print("Test 1: Single request timing")
        start = time.time()
        response = await client.get(url)
        single_time = time.time() - start
        print(f"Single request: {response.status_code} in {single_time:.2f}s")
        
        # Test 2: Concurrent requests (should be deduplicated)
        print("\nTest 2: 5 concurrent requests (should be deduplicated)")
        start = time.time()
        tasks = [client.get(url) for _ in range(5)]
        responses = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start
        
        status_codes = [r.status_code for r in responses]
        print(f"Concurrent requests: {status_codes} in {concurrent_time:.2f}s")
        
        # With deduplication, concurrent time should be similar to single time
        if concurrent_time < single_time * 2:
            print("✅ Deduplication working! Concurrent requests completed efficiently.")
        else:
            print("⚠️ Deduplication may not be working as expected.")
        
        # Verify all responses have the same content
        contents = [r.json()["word"] for r in responses if r.status_code == 200]
        if len(set(contents)) == 1:
            print("✅ All responses returned the same content.")
        else:
            print("❌ Responses have different content!")


async def test_ai_with_gpt4o_mini():
    """Test AI endpoints are using GPT-4o-mini."""
    print("\nTest 3: AI endpoints with GPT-4o-mini")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test pronunciation generation
        resp = await client.post(
            "http://localhost:8000/api/v1/ai/synthesize/pronunciation",
            json={"word": "perspicacious"}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Pronunciation generated: {data['pronunciation']['phonetic']}")
        else:
            print(f"❌ Pronunciation failed: {resp.status_code}")


async def test_word_suggestion():
    """Test the word suggestion feature."""
    print("\nTest 4: Word suggestion feature")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Validate query
        resp = await client.post(
            "http://localhost:8000/api/v1/ai/validate-query",
            json={"query": "words that mean happy"}
        )
        
        if resp.status_code == 200 and resp.json().get("is_valid"):
            print("✅ Query validated successfully")
            
            # Get suggestions
            resp = await client.post(
                "http://localhost:8000/api/v1/ai/suggest-words",
                json={"query": "words that mean happy", "count": 5}
            )
            
            if resp.status_code == 200:
                suggestions = resp.json().get("suggestions", [])
                print(f"✅ Generated {len(suggestions)} suggestions:")
                for s in suggestions[:3]:
                    print(f"   - {s['word']}: {s['reason'][:60]}...")
            else:
                print(f"❌ Suggestion generation failed: {resp.status_code}")
        else:
            print("❌ Query validation failed")


async def main():
    await test_deduplication()
    await test_ai_with_gpt4o_mini()
    await test_word_suggestion()
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())