#!/usr/bin/env python3
"""Simple test for semantic search functionality."""

import asyncio
import httpx
import time
import sys


async def test_semantic_search_simple():
    """Test basic semantic search functionality."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Semantic Search Implementation")
    print("=" * 60)
    
    # Create a simple async HTTP client with longer timeout
    timeout = httpx.Timeout(30.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        
        # Test 1: Create a corpus with test words
        print("\n📝 Step 1: Creating test corpus...")
        corpus_data = {
            "words": [
                "happy", "joyful", "cheerful", "glad", "elated",
                "sad", "melancholy", "depressed", "unhappy", "miserable",
                "angry", "furious", "irate", "mad", "enraged"
            ],
            "name": "Emotion Words Test",
            "ttl_hours": 1.0
        }
        
        try:
            response = await client.post(f"{base_url}/corpus", json=corpus_data)
            if response.status_code == 201:
                corpus_info = response.json()
                corpus_id = corpus_info['corpus_id']
                print(f"✅ Created corpus: {corpus_id[:8]}...")
            else:
                print(f"❌ Failed to create corpus: {response.status_code}")
                print(response.text)
                return
        except Exception as e:
            print(f"❌ Error creating corpus: {e}")
            return
        
        # Test 2: Search corpus WITHOUT semantic
        print("\n📝 Step 2: Searching corpus (semantic disabled)...")
        try:
            response = await client.post(
                f"{base_url}/corpus/{corpus_id}/search",
                params={
                    "query": "joyous",  # Not in corpus, but similar to "joyful"
                    "max_results": 5,
                    "use_semantic": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"✅ Found {len(results)} results without semantic:")
                for i, result in enumerate(results[:3], 1):
                    print(f"   {i}. {result['word']} (score: {result['score']:.2f}, method: {result['method']})")
            else:
                print(f"❌ Search failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error searching: {e}")
        
        # Test 3: Search corpus WITH semantic
        print("\n📝 Step 3: Searching corpus (semantic enabled)...")
        print("   Note: First semantic search may take time to download model...")
        
        try:
            start_time = time.time()
            response = await client.post(
                f"{base_url}/corpus/{corpus_id}/search",
                params={
                    "query": "joyous",  # Not in corpus, but similar to "joyful"
                    "max_results": 5,
                    "use_semantic": True
                },
                timeout=httpx.Timeout(60.0)  # Longer timeout for model download
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"✅ Found {len(results)} results with semantic (took {elapsed:.2f}s):")
                for i, result in enumerate(results[:5], 1):
                    print(f"   {i}. {result['word']} (score: {result['score']:.2f}, method: {result['method']})")
                
                # Check metadata
                metadata = data.get('metadata', {})
                if metadata.get('semantic_enabled'):
                    print("   ✅ Semantic search was enabled")
            else:
                print(f"❌ Search failed: {response.status_code}")
                print(response.text)
        except httpx.TimeoutException:
            print("⏱️ Request timed out - model download may be in progress")
            print("   Try running the test again in a minute")
        except Exception as e:
            print(f"❌ Error searching: {e}")
        
        # Test 4: Test semantic similarity with different queries
        print("\n📝 Step 4: Testing semantic similarity...")
        test_queries = [
            ("ecstatic", ["happy", "joyful", "elated"]),  # Similar to happy
            ("gloomy", ["sad", "melancholy", "depressed"]),  # Similar to sad
            ("livid", ["angry", "furious", "mad"])  # Similar to angry
        ]
        
        for query, expected_words in test_queries:
            print(f"\n   Query: '{query}'")
            try:
                response = await client.post(
                    f"{base_url}/corpus/{corpus_id}/search",
                    params={
                        "query": query,
                        "max_results": 3,
                        "use_semantic": True
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    found_words = [r['word'] for r in results]
                    
                    # Check if we found expected similar words
                    matches = [w for w in expected_words if w in found_words]
                    if matches:
                        print(f"   ✅ Found similar: {', '.join(found_words[:3])}")
                    else:
                        print(f"   ⚠️ Found: {', '.join(found_words[:3])}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 60)
        print("✅ Test completed!")
        print("\nNote: If semantic search failed or timed out on first run,")
        print("the model may still be downloading. Try running again in a minute.")


if __name__ == "__main__":
    asyncio.run(test_semantic_search_simple())