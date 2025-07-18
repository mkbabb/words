#!/usr/bin/env python3
"""Test the SSE streaming endpoint for word lookups."""

import asyncio
import json
import httpx
import sys
from datetime import datetime


async def test_streaming_lookup(word: str = "serendipity", providers: list[str] = ["wiktionary"]):
    """Test the streaming lookup endpoint."""
    print(f"\n🔍 Testing streaming lookup for '{word}' with providers: {providers}")
    print("=" * 80)
    
    # Build query parameters
    params = {
        "providers": providers,
        "force_refresh": "false",
        "no_ai": "false"
    }
    
    url = f"http://localhost:8000/api/v1/lookup/{word}/stream"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", url, params=params) as response:
            print(f"📡 Connected to SSE stream (status: {response.status_code})")
            print("-" * 80)
            
            event_type = None
            event_data = []
            provider_results = []
            
            async for line in response.aiter_lines():
                line = line.strip()
                
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    event_data.append(data_str)
                elif line == "" and event_type:
                    # End of event, process it
                    full_data = "".join(event_data)
                    try:
                        data = json.loads(full_data)
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        
                        if event_type == "progress":
                            progress_bar = "█" * int(data["progress"] * 20) + "░" * (20 - int(data["progress"] * 20))
                            elapsed = data.get("details", {}).get("elapsed_ms", 0)
                            print(f"[{timestamp}] 📊 Progress: [{progress_bar}] {data['progress']:.1%} - {data['stage']}")
                            print(f"             📝 {data['message']} (elapsed: {elapsed:.0f}ms)")
                            
                            # Show additional details if available
                            if "details" in data and data["details"]:
                                for key, value in data["details"].items():
                                    if key not in ["elapsed_ms", "partial_results"]:
                                        print(f"                {key}: {value}")
                        
                        elif event_type == "provider_data":
                            provider = data.get("provider", "unknown")
                            def_count = data.get("definitions_count", 0)
                            provider_results.append(provider)
                            print(f"\n[{timestamp}] 📚 Provider Data Received: {provider}")
                            print(f"             ✅ Definitions: {def_count}")
                            print(f"             ✅ Pronunciation: {data.get('has_pronunciation', False)}")
                            print(f"             ✅ Etymology: {data.get('has_etymology', False)}")
                            
                            # Show first definition as preview
                            if data.get("data", {}).get("definitions"):
                                first_def = data["data"]["definitions"][0]
                                print(f"             📖 Preview: [{first_def.get('word_type', 'unknown')}] {first_def.get('definition', '')[:100]}...")
                        
                        elif event_type == "complete":
                            print(f"\n[{timestamp}] ✅ COMPLETE!")
                            print(f"             📖 Word: {data.get('word', '')}")
                            print(f"             🔢 Total Definitions: {len(data.get('definitions', []))}")
                            print(f"             🕐 Last Updated: {data.get('last_updated', '')}")
                            
                            # Show definition summary by type
                            defs_by_type = {}
                            for defn in data.get("definitions", []):
                                word_type = defn.get("word_type", "unknown")
                                defs_by_type[word_type] = defs_by_type.get(word_type, 0) + 1
                            
                            if defs_by_type:
                                print(f"             📊 By Type: {', '.join(f'{k}: {v}' for k, v in defs_by_type.items())}")
                            
                            if provider_results:
                                print(f"             🔄 Providers Used: {', '.join(provider_results)}")
                        
                        elif event_type == "error":
                            print(f"\n[{timestamp}] ❌ ERROR: {data.get('error', 'Unknown error')}")
                        
                    except json.JSONDecodeError as e:
                        print(f"[{timestamp}] ⚠️  Failed to parse event data: {e}")
                        print(f"             Raw data: {full_data}")
                    
                    # Reset for next event
                    event_type = None
                    event_data = []
            
            print("\n" + "=" * 80)
            print("✅ Stream closed")


async def test_multiple_providers():
    """Test with multiple providers."""
    await test_streaming_lookup("ephemeral", ["wiktionary", "dictionary_com"])


async def test_no_ai():
    """Test without AI synthesis."""
    print("\n🔍 Testing streaming lookup WITHOUT AI synthesis")
    print("=" * 80)
    
    url = "http://localhost:8000/api/v1/lookup/test/stream"
    params = {
        "providers": ["wiktionary"],
        "no_ai": "true"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("GET", url, params=params) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    print(line)


async def main():
    """Run all tests."""
    if len(sys.argv) > 1:
        word = sys.argv[1]
        providers = sys.argv[2:] if len(sys.argv) > 2 else ["wiktionary"]
        await test_streaming_lookup(word, providers)
    else:
        # Default test
        await test_streaming_lookup()
        
        # Test with multiple providers
        # await test_multiple_providers()


if __name__ == "__main__":
    asyncio.run(main())