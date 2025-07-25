#!/usr/bin/env python3
"""Test script to check API response shape"""
import httpx
import json

# Test if there's any data in the database
def test_api():
    # Check health
    response = httpx.get("http://localhost:8000/health")
    print("Health check:", json.dumps(response.json(), indent=2))
    
    # Try to get words
    try:
        response = httpx.get("http://localhost:8000/words")
        print("\nWords endpoint:", response.status_code)
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Words endpoint error: {e}")
    
    # Try lookup
    try:
        response = httpx.get("http://localhost:8000/lookup/example")
        print("\nLookup endpoint:", response.status_code)
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Lookup endpoint error: {e}")

if __name__ == "__main__":
    test_api()