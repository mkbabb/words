#!/usr/bin/env python3
"""
Debug script to test streaming behavior for the word "fork"
"""

import asyncio
import json

import httpx


async def test_fork_streaming():
    """Test streaming lookup for the word 'fork'"""
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        url = "http://localhost:8000/api/v1/lookup/fork/stream"
        
        print(f"Testing streaming lookup for 'fork' at: {url}")
        print("=" * 50)
        
        try:
            async with client.stream("GET", url) as response:
                print(f"Response status: {response.status_code}")
                print(f"Content-Type: {response.headers.get('content-type')}")
                print("=" * 50)
                
                events = []
                current_event = None
                data_buffer = ""
                
                async for chunk in response.aiter_text():
                    data_buffer += chunk
                    
                    # Process complete lines
                    while '\n' in data_buffer:
                        line, data_buffer = data_buffer.split('\n', 1)
                        line = line.strip()
                        
                        if not line:
                            # Empty line indicates end of event
                            if current_event:
                                events.append(current_event)
                                print(f"Event: {current_event.get('event', 'data')}")
                                if current_event.get('data'):
                                    try:
                                        parsed_data = json.loads(current_event['data'])
                                        print(f"  Type: {parsed_data.get('type', 'unknown')}")
                                        print(f"  Stage: {parsed_data.get('stage', 'unknown')}")
                                        print(f"  Progress: {parsed_data.get('progress', 0)}%")
                                        if parsed_data.get('message'):
                                            print(f"  Message: {parsed_data['message']}")
                                        print("-" * 30)
                                    except json.JSONDecodeError:
                                        print(f"  Raw data: {current_event['data'][:100]}...")
                                        print("-" * 30)
                                current_event = None
                        elif line.startswith('event: '):
                            if current_event is None:
                                current_event = {}
                            current_event['event'] = line[7:]
                        elif line.startswith('data: '):
                            if current_event is None:
                                current_event = {}
                            current_event['data'] = line[6:]
                        elif line.startswith('id: '):
                            if current_event is None:
                                current_event = {}
                            current_event['id'] = line[4:]
                
                print(f"\nTotal events received: {len(events)}")
                
                # Check for completion event
                completion_events = [e for e in events if e.get('event') == 'complete']
                print(f"Completion events: {len(completion_events)}")
                
                if not completion_events:
                    print("⚠️ WARNING: No completion event received!")
                    
                    # Check last few events
                    print("\nLast few events:")
                    for event in events[-3:]:
                        print(f"  Event: {event.get('event', 'data')}")
                        if event.get('data'):
                            try:
                                data = json.loads(event['data'])
                                print(f"    Type: {data.get('type')}, Stage: {data.get('stage')}, Progress: {data.get('progress')}%")
                            except:
                                pass
                
                return events
        
        except Exception as e:
            print(f"Error during streaming: {e}")
            return []


async def test_regular_lookup():
    """Test regular (non-streaming) lookup for comparison"""
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        url = "http://localhost:8000/api/v1/lookup/fork"
        
        print(f"\nTesting regular lookup for 'fork' at: {url}")
        print("=" * 50)
        
        try:
            response = await client.get(url)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Word: {data.get('word')}")
                print(f"Definitions count: {len(data.get('definitions', []))}")
                print("✅ Regular lookup successful")
            else:
                print(f"❌ Regular lookup failed: {response.text}")
                
        except Exception as e:
            print(f"Error during regular lookup: {e}")


async def main():
    print("Starting fork lookup debug test...")
    
    # Test streaming first
    events = await test_fork_streaming()
    
    # Test regular lookup for comparison
    await test_regular_lookup()
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    if events:
        print(f"✅ Streaming test completed with {len(events)} events")
        
        # Analyze event types
        event_types = {}
        for event in events:
            if event.get('data'):
                try:
                    data = json.loads(event['data'])
                    event_type = data.get('type', 'unknown')
                    event_types[event_type] = event_types.get(event_type, 0) + 1
                except:
                    pass
        
        print(f"Event types: {event_types}")
        
        # Check for issues
        if 'complete' not in event_types:
            print("⚠️ ISSUE: No completion event detected in streaming response")
        else:
            print("✅ Completion event found")
            
    else:
        print("❌ Streaming test failed - no events received")


if __name__ == "__main__":
    asyncio.run(main())