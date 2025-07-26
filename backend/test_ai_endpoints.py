#!/usr/bin/env python3
"""Test script for AI word suggestion endpoints."""

import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

async def test_query_validation():
    """Test the query validation endpoint."""
    print("\n=== Testing Query Validation ===")
    
    test_cases = [
        ("words that mean stubborn", True),
        ("what are some words for being really dedicated", True), 
        ("words like persistent, determined", True),
        ("hello world", False),
        ("xyz123", False),
        ("what is the weather", False),
    ]
    
    async with httpx.AsyncClient() as client:
        for query, expected_valid in test_cases:
            response = await client.post(
                f"{BASE_URL}/ai/validate-query",
                json={"query": query}
            )
            if response.status_code != 200:
                print(f"✗ Error {response.status_code}: {response.text}")
                continue
                
            result = response.json()
            is_valid = result.get("is_valid", False)
            status = "✓" if is_valid == expected_valid else "✗"
            print(f"{status} Query: '{query[:30]}...' - Valid: {is_valid}")
            if is_valid != expected_valid:
                print(f"   Reason: {result.get('reason', 'No reason provided')}")

async def test_word_suggestions():
    """Test the word suggestions endpoint."""
    print("\n=== Testing Word Suggestions ===")
    
    test_queries = [
        "words that mean I'm really dedicated to something",
        "words that mean detailed oriented",
        "words that mean stubborn, but like mean too",
        "I need a word for someone who never gives up even when ___ seems impossible",
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            
            response = await client.post(
                f"{BASE_URL}/ai/suggest-words",
                json={"query": query, "count": 5}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"Query Type: {result['query_type']}")
                print("Suggestions:")
                for i, suggestion in enumerate(result['suggestions'][:3], 1):
                    print(f"  {i}. {suggestion['word']} (confidence: {suggestion['confidence']:.2f}, beauty: {suggestion['efflorescence']:.2f})")
                    print(f"     → {suggestion['reasoning']}")
                    if suggestion.get('example_usage'):
                        print(f"     Example: {suggestion['example_usage']}")
            else:
                print(f"Error {response.status_code}: {response.text}")

async def test_invalid_query():
    """Test error handling for invalid queries."""
    print("\n=== Testing Invalid Query Handling ===")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/ai/suggest-words",
            json={"query": "hello", "count": 5}
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 400:
            error = response.json()
            print(f"Error: {error.get('detail', 'Unknown error')}")

async def main():
    """Run all tests."""
    print("Testing AI Word Suggestion Endpoints")
    print("=" * 50)
    
    try:
        await test_query_validation()
    except Exception as e:
        print(f"Query validation test failed: {e}")
        
    try:
        await test_word_suggestions()
    except Exception as e:
        print(f"Word suggestions test failed: {e}")
        
    try:
        await test_invalid_query()
    except Exception as e:
        print(f"Invalid query test failed: {e}")
    
    print("\n" + "=" * 50)
    print("Tests completed!")

if __name__ == "__main__":
    asyncio.run(main())