#!/usr/bin/env python3
"""Test script to verify enum serialization in cache."""

import asyncio
import pickle
from enum import Enum

from floridify.caching.core import get_global_cache
from floridify.caching.models import CacheNamespace


class TestEnum(str, Enum):
    """Test enum for serialization."""

    VALUE_A = "value_a"
    VALUE_B = "value_b"


async def test_enum_serialization():
    """Test how enums are serialized and deserialized."""
    cache = await get_global_cache()

    # Test 1: Store dict with enum values (string)
    test_dict_strings = {
        "field1": "value_a",
        "field2": "value_b",
    }

    # Test 2: Store dict with enum objects
    test_dict_enums = {
        "field1": TestEnum.VALUE_A,
        "field2": TestEnum.VALUE_B,
    }

    # Test 3: Store dict with mixed types
    test_dict_mixed = {
        "field1": TestEnum.VALUE_A,
        "field2": "value_b",
        "field3": {"nested": TestEnum.VALUE_B},
    }

    print("\n=== Test 1: Dict with string values ===")
    await cache.set(CacheNamespace.DEFAULT, "test_strings", test_dict_strings)
    result1 = await cache.get(CacheNamespace.DEFAULT, "test_strings")
    print(f"Original: {test_dict_strings}")
    print(f"Retrieved: {result1}")
    print(f"Type of field1: {type(result1['field1'])}")
    print(f"Are they equal? {test_dict_strings == result1}")

    print("\n=== Test 2: Dict with enum objects ===")
    await cache.set(CacheNamespace.DEFAULT, "test_enums", test_dict_enums)
    result2 = await cache.get(CacheNamespace.DEFAULT, "test_enums")
    print(f"Original: {test_dict_enums}")
    print(f"Retrieved: {result2}")
    print(f"Type of field1: {type(result2['field1'])}")
    print(f"Is field1 an enum? {isinstance(result2['field1'], Enum)}")
    print(f"Are they equal? {test_dict_enums == result2}")

    print("\n=== Test 3: Dict with mixed types ===")
    await cache.set(CacheNamespace.DEFAULT, "test_mixed", test_dict_mixed)
    result3 = await cache.get(CacheNamespace.DEFAULT, "test_mixed")
    print(f"Original: {test_dict_mixed}")
    print(f"Retrieved: {result3}")
    print(f"Type of field1: {type(result3['field1'])}")
    print(f"Type of field2: {type(result3['field2'])}")
    print(f"Type of nested field: {type(result3['field3']['nested'])}")
    print(f"Is field1 an enum? {isinstance(result3['field1'], Enum)}")
    print(f"Are they equal? {test_dict_mixed == result3}")

    print("\n=== Test 4: Direct pickle vs diskcache ===")
    # Test what pickle does
    pickled = pickle.dumps(test_dict_enums, protocol=pickle.HIGHEST_PROTOCOL)
    unpickled = pickle.loads(pickled)
    print(f"Pickle preserves enum type: {isinstance(unpickled['field1'], Enum)}")

    # Test what filesystem backend does
    backend = cache.l2_backend
    await backend.set("test_direct", test_dict_enums)
    direct_result = await backend.get("test_direct")
    print(f"Backend preserves enum type: {isinstance(direct_result['field1'], Enum)}")

    print("\n=== Conclusion ===")
    if isinstance(result2['field1'], Enum):
        print("❌ PROBLEM: Enums are preserved as objects (not serialized to strings)")
        print("   This causes JSON serialization to fail when the dict is returned to the API")
    else:
        print("✅ OK: Enums are converted to strings")


if __name__ == "__main__":
    asyncio.run(test_enum_serialization())
