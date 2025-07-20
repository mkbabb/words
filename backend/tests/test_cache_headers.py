"""Test HTTP cache headers implementation."""

import asyncio
import httpx


async def test_cache_headers():
    """Test that cache headers are properly implemented."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing HTTP Cache Headers Implementation\n")
    
    # Test endpoints with expected cache behaviors
    test_cases = [
        ("/api/v1/health", "no-cache", "Health check should not be cached"),
        ("/api/v1/search?q=test", "max-age=3600", "Search results should cache for 1 hour"),
        ("/api/v1/lookup/computer", "max-age=1800", "Lookup should cache for 30 minutes"),
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for endpoint, expected_cache, description in test_cases:
            print(f"Testing: {endpoint}")
            print(f"Expected: {description}")
            
            try:
                # First request
                response = await client.get(f"{base_url}{endpoint}")
                
                # Check response
                if response.status_code == 200:
                    print(f"✅ Status: {response.status_code}")
                    
                    # Check cache headers
                    cache_control = response.headers.get("Cache-Control", "")
                    etag = response.headers.get("ETag", "")
                    
                    print(f"   Cache-Control: {cache_control}")
                    print(f"   ETag: {etag}")
                    
                    if expected_cache in cache_control:
                        print(f"✅ Cache behavior correct")
                    else:
                        print(f"❌ Expected '{expected_cache}' in Cache-Control")
                    
                    # Test ETag functionality if present
                    if etag and not endpoint.startswith("/api/v1/health"):
                        print("   Testing ETag conditional request...")
                        etag_response = await client.get(
                            f"{base_url}{endpoint}",
                            headers={"If-None-Match": etag}
                        )
                        if etag_response.status_code == 304:
                            print("✅ ETag working - got 304 Not Modified")
                        else:
                            print(f"❌ ETag not working - got {etag_response.status_code}")
                    
                else:
                    print(f"❌ Request failed: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error testing {endpoint}: {e}")
            
            print()  # Empty line for readability
    
    print("🎯 Cache Headers Test Complete")


if __name__ == "__main__":
    asyncio.run(test_cache_headers())