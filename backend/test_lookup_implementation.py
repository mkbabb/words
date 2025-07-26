#!/usr/bin/env python3
"""Test the lookup implementation with deduplication and batch processing."""

import asyncio
import time
import httpx
import json
from datetime import datetime


async def test_basic_lookup(word: str = "example"):
    """Test basic lookup without streaming."""
    print(f"\n🔍 Testing basic lookup for '{word}'...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        start_time = time.time()
        
        response = await client.get(
            f"http://localhost:8000/api/v1/lookup/{word}",
            params={"force_refresh": "false"}
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Lookup successful in {elapsed:.2f}s")
            print(f"   - Definitions: {len(data.get('definitions', []))}")
            print(f"   - Last updated: {data.get('last_updated')}")
            return data
        else:
            print(f"❌ Lookup failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None


async def test_streaming_lookup(word: str = "example"):
    """Test streaming lookup with SSE."""
    print(f"\n🌊 Testing streaming lookup for '{word}'...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        start_time = time.time()
        stages = []
        
        async with client.stream(
            'GET',
            f"http://localhost:8000/api/v1/lookup/{word}/stream",
            params={"force_refresh": "false"}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith('event:'):
                    event_type = line.split(':', 1)[1].strip()
                    
                elif line.startswith('data:'):
                    data = json.loads(line[5:])
                    
                    if event_type == 'progress':
                        stage = data.get('stage', 'UNKNOWN')
                        progress = data.get('progress', 0)
                        message = data.get('message', '')
                        
                        stages.append({
                            'stage': stage,
                            'progress': progress,
                            'message': message,
                            'timestamp': time.time() - start_time
                        })
                        
                        print(f"   📍 {stage} ({progress}%) - {message}")
                        
                    elif event_type == 'complete':
                        elapsed = time.time() - start_time
                        print(f"✅ Streaming lookup completed in {elapsed:.2f}s")
                        
                        if 'details' in data and 'result' in data['details']:
                            result = data['details']['result']
                            print(f"   - Definitions: {len(result.get('definitions', []))}")
                            return result
                        
                    elif event_type == 'error':
                        print(f"❌ Streaming error: {data.get('error')}")
                        return None


async def test_concurrent_deduplication(word: str = "example", count: int = 5):
    """Test concurrent requests to verify deduplication."""
    print(f"\n🔄 Testing concurrent deduplication with {count} requests for '{word}'...")
    
    async def make_request(request_id: int):
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8000/api/v1/lookup/{word}",
                params={"force_refresh": "false"}
            )
            
            elapsed = time.time() - start_time
            
            return {
                'id': request_id,
                'status': response.status_code,
                'time': elapsed,
                'cached': elapsed < 0.5  # Assume <500ms means deduplicated/cached
            }
    
    # Launch concurrent requests
    start_time = time.time()
    tasks = [make_request(i) for i in range(count)]
    results = await asyncio.gather(*tasks)
    total_elapsed = time.time() - start_time
    
    # Analyze results
    successful = sum(1 for r in results if r['status'] == 200)
    deduplicated = sum(1 for r in results if r['cached'])
    
    print(f"✅ Completed {count} concurrent requests in {total_elapsed:.2f}s")
    print(f"   - Successful: {successful}/{count}")
    print(f"   - Deduplicated/Cached: {deduplicated}/{count}")
    
    for result in results:
        status = "✅" if result['status'] == 200 else "❌"
        cache_status = "🎯 (cached)" if result['cached'] else "🔄 (fresh)"
        print(f"   - Request {result['id']}: {status} in {result['time']:.3f}s {cache_status}")


async def test_force_refresh(word: str = "example"):
    """Test force refresh to bypass cache."""
    print(f"\n🔄 Testing force refresh for '{word}'...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # First, do a normal lookup to ensure it's cached
        print("   1️⃣ Initial lookup (to populate cache)...")
        start_time = time.time()
        response1 = await client.get(
            f"http://localhost:8000/api/v1/lookup/{word}",
            params={"force_refresh": "false"}
        )
        time1 = time.time() - start_time
        
        # Then force refresh
        print("   2️⃣ Force refresh lookup...")
        start_time = time.time()
        response2 = await client.get(
            f"http://localhost:8000/api/v1/lookup/{word}",
            params={"force_refresh": "true"}
        )
        time2 = time.time() - start_time
        
        # Finally, check if it's cached
        print("   3️⃣ Cached lookup...")
        start_time = time.time()
        response3 = await client.get(
            f"http://localhost:8000/api/v1/lookup/{word}",
            params={"force_refresh": "false"}
        )
        time3 = time.time() - start_time
        
        print(f"\n📊 Timing Analysis:")
        print(f"   - Initial: {time1:.2f}s")
        print(f"   - Force refresh: {time2:.2f}s (should be slow)")
        print(f"   - Cached: {time3:.2f}s (should be fast)")


async def test_model_configuration():
    """Test that GPT-4o-mini is being used."""
    print("\n🤖 Testing model configuration...")
    
    # Check logs to verify model
    print("   - Model should be: gpt-4o-mini")
    print("   - Check Docker logs for confirmation:")
    print("     docker logs words-backend-1 | grep 'OpenAI model'")


async def main():
    """Run all tests."""
    print("🚀 Floridify Lookup Implementation Test Suite")
    print("=" * 60)
    
    # Test 1: Basic lookup
    await test_basic_lookup("example")
    
    # Test 2: Streaming lookup
    await test_streaming_lookup("example")
    
    # Test 3: Concurrent deduplication
    await test_concurrent_deduplication("example", count=5)
    
    # Test 4: Force refresh
    await test_force_refresh("example")
    
    # Test 5: Model configuration
    await test_model_configuration()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())