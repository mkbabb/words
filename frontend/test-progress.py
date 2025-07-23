#!/usr/bin/env python3
import json
import urllib.request

def test_streaming_api():
    """Test the streaming API and extract progress values"""
    
    print("=== Testing Backend Streaming Progress Values ===\n")
    
    # Test 1: Single provider
    print("Test 1: Single Provider (wiktionary)")
    url = "http://localhost:8000/api/lookup/hello/stream?providers=wiktionary"
    
    progress_values = []
    stages_seen = []
    
    response = urllib.request.urlopen(url)
    for line in response:
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                try:
                    data = json.loads(line_str[5:])  # Skip 'data:' prefix
                    if 'progress' in data:
                        progress = data['progress']
                        stage = data['stage']
                        percent = round(progress * 100)
                        
                        progress_values.append(progress)
                        if stage not in stages_seen:
                            stages_seen.append(stage)
                        
                        print(f"  {stage}: {progress:.2f} ({percent}%)")
                except:
                    pass
    
    print(f"\nProgress values: {[f'{p:.2f}' for p in progress_values]}")
    print(f"Stages: {stages_seen}")
    
    # Check if progress is monotonic
    is_monotonic = all(progress_values[i] <= progress_values[i+1] 
                      for i in range(len(progress_values)-1))
    print(f"Monotonic increase: {'✅ Yes' if is_monotonic else '❌ No'}")
    
    # Test 2: Multiple providers
    print("\n\nTest 2: Multiple Providers (3 providers)")
    url = "http://localhost:8000/api/lookup/world/stream?providers=wiktionary&providers=oxford&providers=dictionary_com"
    
    progress_values = []
    provider_progress = {}
    
    response = urllib.request.urlopen(url)
    for line in response:
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data:'):
                try:
                    data = json.loads(line_str[5:])
                    if 'progress' in data:
                        progress = data['progress']
                        stage = data['stage']
                        percent = round(progress * 100)
                        
                        progress_values.append(progress)
                        
                        # Track provider-specific progress
                        if 'details' in data and 'provider' in data['details']:
                            provider = data['details']['provider']
                            if provider not in provider_progress:
                                provider_progress[provider] = []
                            provider_progress[provider].append(percent)
                            print(f"  {stage} [{provider}]: {progress:.2f} ({percent}%)")
                        else:
                            print(f"  {stage}: {progress:.2f} ({percent}%)")
                except:
                    pass
    
    print(f"\nProvider progress ranges:")
    for provider, values in provider_progress.items():
        if values:
            print(f"  {provider}: {min(values)}% - {max(values)}%")
    
    print("\n=== Analysis ===")
    print("Expected checkpoints:")
    print("  0% - Initialization")
    print("  10% - Search complete")
    print("  15% - Provider fetch start") 
    print("  15-40% - Provider fetching (divided by provider count)")
    print("  40% - AI clustering")
    print("  50-60% - AI synthesis")
    print("  80% - Storage save")
    print("  100% - Complete")

if __name__ == "__main__":
    test_streaming_api()