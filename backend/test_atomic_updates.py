#!/usr/bin/env python3
"""Test script for atomic update endpoints to identify race conditions and issues."""

import asyncio
import httpx
from typing import Any


class AtomicUpdateTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def create_test_word(self) -> dict[str, Any]:
        """Create a test word for experiments."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/words",
            json={
                "text": f"test_word_{asyncio.get_event_loop().time()}",
                "normalized": "test_word",
                "language": "en"
            }
        )
        response.raise_for_status()
        return response.json()["data"]
    
    async def test_concurrent_updates(self, word_id: str, initial_version: int):
        """Test concurrent updates to the same field."""
        print(f"\n=== Testing concurrent updates on word {word_id} ===")
        
        async def update_field(value: str, expected_version: int) -> dict[str, Any]:
            try:
                response = await self.client.patch(
                    f"{self.base_url}/api/v1/atomic/word/{word_id}/field",
                    json={
                        "field": "offensive_flag",
                        "value": value,
                        "version": expected_version
                    }
                )
                return {"success": True, "status": response.status_code, "data": response.json()}
            except httpx.HTTPStatusError as e:
                return {"success": False, "status": e.response.status_code, "error": e.response.text}
        
        # Launch concurrent updates with same version
        tasks = [
            update_field(True, initial_version),
            update_field(False, initial_version),
            update_field(True, initial_version),
        ]
        
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in results if r["success"])
        print(f"Concurrent updates: {success_count}/{len(tasks)} succeeded")
        
        for i, result in enumerate(results):
            print(f"  Update {i+1}: {result['status']} - {'Success' if result['success'] else 'Failed'}")
            if not result['success'] and 'version' in str(result.get('error', '')):
                print(f"    Version conflict detected (expected behavior)")
        
        return results
    
    async def test_field_injection(self, word_id: str, version: int):
        """Test field injection vulnerabilities."""
        print(f"\n=== Testing field injection on word {word_id} ===")
        
        dangerous_fields = [
            "__class__",
            "__dict__",
            "_id",
            "id",
            "__init__",
            "save",
            "__module__",
            "nonexistent_field",
            "version",  # Should this be updatable?
            "_sa_instance_state",  # SQLAlchemy internal
            "../../etc/passwd",  # Path traversal attempt
            "text.split",  # Nested attribute access
            "text.__class__",
            "",  # Empty field
            None,  # None field
        ]
        
        for field in dangerous_fields:
            if field is None:
                continue
                
            try:
                response = await self.client.patch(
                    f"{self.base_url}/api/v1/atomic/word/{word_id}/field",
                    json={
                        "field": field,
                        "value": "injected_value",
                        "version": version
                    }
                )
                print(f"  Field '{field}': Status {response.status_code} - VULNERABILITY!")
                if response.status_code == 200:
                    print(f"    WARNING: Successfully updated '{field}' - potential security issue")
            except httpx.HTTPStatusError as e:
                print(f"  Field '{field}': Status {e.response.status_code} - Protected")
    
    async def test_race_condition_window(self, word_id: str, initial_version: int):
        """Test the race condition window between read and write."""
        print(f"\n=== Testing race condition window ===")
        
        async def slow_update(delay: float) -> dict[str, Any]:
            # Simulate slow processing
            await asyncio.sleep(delay)
            
            try:
                response = await self.client.patch(
                    f"{self.base_url}/api/v1/atomic/word/{word_id}/field",
                    json={
                        "field": "first_known_use",
                        "value": f"Updated at {delay}s delay",
                        "version": initial_version
                    }
                )
                return {"success": True, "delay": delay, "data": response.json()}
            except httpx.HTTPStatusError as e:
                return {"success": False, "delay": delay, "status": e.response.status_code}
        
        # Launch updates with different delays
        tasks = [
            slow_update(0.0),    # Immediate
            slow_update(0.1),    # 100ms delay
            slow_update(0.2),    # 200ms delay
            slow_update(0.05),   # 50ms delay
        ]
        
        results = await asyncio.gather(*tasks)
        
        print("Race condition results:")
        for result in sorted(results, key=lambda x: x["delay"]):
            status = "Success" if result["success"] else f"Failed ({result.get('status', 'unknown')})"
            print(f"  Delay {result['delay']}s: {status}")
    
    async def test_type_validation(self, word_id: str, version: int):
        """Test type validation for different field types."""
        print(f"\n=== Testing type validation ===")
        
        test_cases = [
            ("offensive_flag", "not_a_boolean", "String for boolean field"),
            ("offensive_flag", 123, "Number for boolean field"),
            ("offensive_flag", {"key": "value"}, "Object for boolean field"),
            ("offensive_flag", [True, False], "Array for boolean field"),
            ("homograph_number", "not_a_number", "String for number field"),
            ("homograph_number", True, "Boolean for number field"),
            ("text", 12345, "Number for string field"),
            ("text", True, "Boolean for string field"),
            ("language", "invalid_language_code_that_is_too_long", "Invalid enum value"),
        ]
        
        for field, value, description in test_cases:
            try:
                response = await self.client.patch(
                    f"{self.base_url}/api/v1/atomic/word/{word_id}/field",
                    json={
                        "field": field,
                        "value": value,
                        "version": version
                    }
                )
                print(f"  {description}: Status {response.status_code} - Type validation FAILED!")
                version = response.json()["new_version"]  # Update version if successful
            except httpx.HTTPStatusError as e:
                print(f"  {description}: Status {e.response.status_code} - Type validation working")
    
    async def test_mongodb_atomicity(self, word_id: str, initial_version: int):
        """Test if updates are truly atomic at the MongoDB level."""
        print(f"\n=== Testing MongoDB atomicity ===")
        
        # Create many concurrent updates to stress test atomicity
        async def stress_update(index: int) -> dict[str, Any]:
            try:
                response = await self.client.patch(
                    f"{self.base_url}/api/v1/atomic/word/{word_id}/field",
                    json={
                        "field": "first_known_use",
                        "value": f"Update {index}",
                        "version": initial_version
                    }
                )
                return {"success": True, "index": index, "version": response.json()["new_version"]}
            except httpx.HTTPStatusError:
                return {"success": False, "index": index}
        
        # Launch 20 concurrent updates
        tasks = [stress_update(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        successful = [r for r in results if r["success"]]
        print(f"Stress test: {len(successful)}/20 updates succeeded")
        
        if len(successful) > 1:
            print("  WARNING: Multiple updates succeeded with same version!")
            print("  This indicates a race condition in the implementation")
    
    async def run_all_tests(self):
        """Run all atomic update tests."""
        print("Starting atomic update security and concurrency tests...")
        
        # Create test word
        word = await self.create_test_word()
        word_id = word["id"]
        version = word["version"]
        
        print(f"Created test word: {word_id} (version {version})")
        
        # Run tests
        await self.test_concurrent_updates(word_id, version)
        await self.test_field_injection(word_id, version)
        await self.test_race_condition_window(word_id, version)
        await self.test_type_validation(word_id, version)
        await self.test_mongodb_atomicity(word_id, version)
        
        print("\nTests completed!")


async def main():
    tester = AtomicUpdateTester()
    try:
        await tester.run_all_tests()
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())