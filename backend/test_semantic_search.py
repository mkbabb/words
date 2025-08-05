#!/usr/bin/env python3
"""Test script for semantic search functionality."""

import asyncio
import httpx
import json
from typing import Any


async def test_semantic_search():
    """Test semantic search via REST API."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing Semantic Search Implementation\n")
        print("=" * 60)
        
        # Test 1: Basic search without semantic
        print("\n📝 Test 1: Basic search (semantic disabled)")
        response = await client.get(
            f"{base_url}/search",
            params={
                "q": "happy",
                "max_results": 5,
                "semantic": False
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data['results'])} results")
            for i, result in enumerate(data['results'][:3], 1):
                print(f"  {i}. {result['word']} (score: {result['score']:.2f}, method: {result['method']})")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
        
        # Test 2: Search with semantic enabled
        print("\n📝 Test 2: Semantic search (semantic enabled)")
        response = await client.get(
            f"{base_url}/search",
            params={
                "q": "happy",
                "max_results": 5,
                "semantic": True,
                "semantic_weight": 0.8
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data['results'])} results")
            for i, result in enumerate(data['results'][:3], 1):
                print(f"  {i}. {result['word']} (score: {result['score']:.2f}, method: {result['method']})")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
        
        # Test 3: Create corpus and search with semantic
        print("\n📝 Test 3: Corpus search with semantic")
        
        # Create corpus
        corpus_data = {
            "words": ["happy", "joyful", "cheerful", "sad", "melancholy", "depressed", "excited", "thrilled"],
            "name": "Emotion Words Test",
            "ttl_hours": 1.0
        }
        
        response = await client.post(
            f"{base_url}/corpus",
            json=corpus_data
        )
        
        if response.status_code == 201:
            corpus_info = response.json()
            corpus_id = corpus_info['corpus_id']
            print(f"✅ Created corpus: {corpus_id}")
            
            # Search corpus without semantic
            print("\n  Searching corpus (semantic disabled):")
            response = await client.post(
                f"{base_url}/corpus/{corpus_id}/search",
                params={
                    "query": "joyous",
                    "max_results": 5,
                    "use_semantic": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Found {len(data['results'])} results")
                for result in data['results'][:3]:
                    print(f"    - {result['word']} (score: {result['score']:.2f}, method: {result['method']})")
            else:
                print(f"  ❌ Error: {response.status_code}")
            
            # Search corpus with semantic
            print("\n  Searching corpus (semantic enabled):")
            response = await client.post(
                f"{base_url}/corpus/{corpus_id}/search",
                params={
                    "query": "joyous",
                    "max_results": 5,
                    "use_semantic": True
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Found {len(data['results'])} results")
                for result in data['results'][:3]:
                    print(f"    - {result['word']} (score: {result['score']:.2f}, method: {result['method']})")
                
                # Check if semantic was used
                if data.get('metadata', {}).get('semantic_enabled'):
                    print("  ✅ Semantic search was enabled")
            else:
                print(f"  ❌ Error: {response.status_code}")
        else:
            print(f"❌ Failed to create corpus: {response.status_code}")
        
        # Test 4: Rebuild index with semantic
        print("\n📝 Test 4: Rebuild search index with semantic")
        rebuild_data = {
            "languages": ["en"],
            "force_download": False,
            "rebuild_semantic": True
        }
        
        response = await client.post(
            f"{base_url}/search/rebuild-index",
            json=rebuild_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Index rebuilt: {data['message']}")
            if 'semantic_enabled' in data.get('statistics', {}):
                print(f"  Semantic: {data['statistics']['semantic_enabled']}")
        else:
            print(f"❌ Error: {response.status_code}")
        
        # Test 5: Invalidate semantic cache
        print("\n📝 Test 5: Invalidate semantic cache")
        invalidate_data = {
            "cleanup_expired": True
        }
        
        response = await client.post(
            f"{base_url}/search/invalidate-semantic-cache",
            json=invalidate_data
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cache invalidated: {data['message']}")
        else:
            print(f"❌ Error: {response.status_code}")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_semantic_search())