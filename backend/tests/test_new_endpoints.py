"""Test new API endpoints."""

import asyncio
import httpx
import json


async def test_endpoints():
    """Test the new definition and batch endpoints."""
    base_url = "http://localhost:8000/api"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test definition update
        print("Testing definition update...")
        try:
            response = await client.patch(
                f"{base_url}/definitions/efflorescence/definitions/0",
                json={
                    "cefr_level": "C1",
                    "frequency_band": 3,
                    "register": "formal",
                    "collocations": ["artistic efflorescence", "cultural efflorescence"]
                }
            )
            print(f"Definition update: {response.status_code}")
            if response.status_code == 200:
                print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"Error: {e}")
        
        # Test example regeneration
        print("\nTesting example regeneration...")
        try:
            response = await client.post(
                f"{base_url}/definitions/efflorescence/definitions/0/examples/regenerate",
                json={
                    "count": 3,
                    "style": "formal",
                    "context": "Use in academic writing"
                }
            )
            print(f"Example regeneration: {response.status_code}")
            if response.status_code == 200:
                print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"Error: {e}")
        
        # Test batch lookup
        print("\nTesting batch lookup...")
        try:
            response = await client.post(
                f"{base_url}/batch/lookup",
                json={
                    "words": ["efflorescence", "serendipity", "ephemeral"],
                    "force_refresh": False
                }
            )
            print(f"Batch lookup: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Summary: {result.get('summary')}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test CEFR level assessment
        print("\nTesting CEFR level assessment...")
        try:
            response = await client.post(
                f"{base_url}/definitions/efflorescence/definitions/0/cefr-level"
            )
            print(f"CEFR assessment: {response.status_code}")
            if response.status_code == 200:
                print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_endpoints())