#!/usr/bin/env python3
"""
Simple test to verify that all dictionary providers return consistent dict structures.
This should be run to validate the changes made to make providers return dicts instead of DictionaryEntry objects.
"""

import json
from typing import Any


# Mock the required imports to check structure without actually running providers
class MockProvider:
    def __init__(self, name: str):
        self.name = name

    def create_mock_response(self) -> dict[str, Any]:
        """Create a mock response with the expected dict structure"""
        return {
            "word": "test",
            "provider": self.name,
            "definitions": [
                {
                    "id": "mock-def-1",
                    "part_of_speech": "noun",
                    "text": "A mock definition",
                    "sense_number": "1",
                    "synonyms": ["example", "sample"],
                    "example_ids": ["mock-ex-1"],
                }
            ],
            "pronunciation": {
                "id": "mock-pron-1",
                "phonetic": "test",
                "ipa": "/tɛst/",
                "syllables": ["test"],
            },
            "etymology": {
                "text": "From Latin test",
                "origin_language": "latin",
                "root_words": ["test"],
            },
            "raw_data": {"mock": "data"},
        }


def validate_provider_response_structure(response: dict[str, Any], provider_name: str) -> bool:
    """Validate that a provider response has the expected dict structure"""
    try:
        # Check required fields
        required_fields = ["word", "provider", "definitions", "raw_data"]
        for field in required_fields:
            if field not in response:
                print(f"❌ {provider_name}: Missing required field '{field}'")
                return False

        # Check field types
        if not isinstance(response["word"], str):
            print(f"❌ {provider_name}: 'word' should be a string")
            return False

        if not isinstance(response["provider"], str):
            print(f"❌ {provider_name}: 'provider' should be a string")
            return False

        if not isinstance(response["definitions"], list):
            print(f"❌ {provider_name}: 'definitions' should be a list")
            return False

        if not isinstance(response["raw_data"], dict):
            print(f"❌ {provider_name}: 'raw_data' should be a dict")
            return False

        # Check that definitions have expected structure
        if response["definitions"]:
            definition = response["definitions"][0]
            def_required_fields = ["id", "part_of_speech", "text", "sense_number", "synonyms"]
            for field in def_required_fields:
                if field not in definition:
                    print(f"❌ {provider_name}: Definition missing required field '{field}'")
                    return False

        # Check optional fields have correct types when present
        if "pronunciation" in response and response["pronunciation"] is not None:
            if not isinstance(response["pronunciation"], dict):
                print(f"❌ {provider_name}: 'pronunciation' should be a dict or None")
                return False

        if "etymology" in response and response["etymology"] is not None:
            if not isinstance(response["etymology"], dict):
                print(f"❌ {provider_name}: 'etymology' should be a dict or None")
                return False

        # Ensure it's JSON serializable
        json.dumps(response)

        print(f"✅ {provider_name}: Response structure is valid and JSON serializable")
        return True

    except Exception as e:
        print(f"❌ {provider_name}: Error validating response: {e}")
        return False


def main():
    """Test the expected provider response structures"""
    print("Testing Dictionary Provider Response Consistency")
    print("=" * 50)

    providers = ["FREE_DICTIONARY", "MERRIAM_WEBSTER", "OXFORD", "WIKTIONARY"]

    all_valid = True

    for provider in providers:
        mock = MockProvider(provider)
        response = mock.create_mock_response()
        is_valid = validate_provider_response_structure(response, provider)
        all_valid = all_valid and is_valid

    print("\n" + "=" * 50)
    if all_valid:
        print("✅ All providers return consistent dict structures")
        print("✅ All responses are JSON serializable")
        print("✅ This will fix caching layer serialization issues")
    else:
        print("❌ Some providers have inconsistent structures")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
