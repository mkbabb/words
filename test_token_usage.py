#!/usr/bin/env python3
"""Test token usage for word lookup pipeline."""

import asyncio
import json
import httpx
from datetime import datetime


async def test_word_lookup(word: str = "example"):
    """Test lookup and extract token usage from logs."""
    
    # Force refresh lookup
    async with httpx.AsyncClient() as client:
        print(f"\n🔍 Looking up '{word}' with force refresh...")
        
        # Make the API call
        response = await client.get(
            f"http://localhost:8000/api/v1/lookup/{word}",
            params={"force_refresh": "true"},
            timeout=60.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Lookup successful: {len(data.get('definitions', []))} definitions found")
            
            # Print some basic stats
            definitions = data.get('definitions', [])
            total_examples = sum(len(d.get('examples', [])) for d in definitions)
            total_synonyms = sum(len(d.get('synonyms', [])) for d in definitions)
            
            print(f"\n📊 Content Stats:")
            print(f"  - Definitions: {len(definitions)}")
            print(f"  - Total examples: {total_examples}")
            print(f"  - Total synonyms: {total_synonyms}")
            print(f"  - Pronunciation: {'Yes' if data.get('pronunciation') else 'No'}")
            
            # Estimate content size
            json_str = json.dumps(data)
            print(f"  - Response size: {len(json_str):,} characters")
            
            return data
        else:
            print(f"❌ Lookup failed: {response.status_code}")
            return None


async def get_ai_endpoints_info():
    """Get information about AI endpoints and their token estimates."""
    
    async with httpx.AsyncClient() as client:
        # Get OpenAPI spec
        response = await client.get("http://localhost:8000/openapi.json")
        if response.status_code == 200:
            spec = response.json()
            
            print("\n🤖 AI Endpoints and Token Estimates:")
            ai_paths = {k: v for k, v in spec['paths'].items() if '/ai/' in k}
            
            for path, methods in ai_paths.items():
                for method, details in methods.items():
                    if method in ['post', 'get']:
                        summary = details.get('summary', 'No summary')
                        description = details.get('description', '')
                        
                        # Extract token estimates from description
                        if 'Rate Limited:' in description:
                            token_part = description.split('Rate Limited:')[1].split('\n')[0]
                            print(f"\n  {method.upper()} {path}")
                            print(f"    Summary: {summary}")
                            print(f"    Tokens: {token_part.strip()}")


async def estimate_total_cost():
    """Estimate total cost for English dictionary."""
    
    # Based on the AI endpoint analysis, estimate tokens per operation
    token_estimates = {
        'cluster_mapping': 500,      # Extract meaning clusters
        'synthesis': 800,           # Synthesize definitions per cluster
        'examples': 400,            # Generate examples
        'synonyms': 300,            # Generate synonyms
        'pronunciation': 100,       # Generate pronunciation
        'word_forms': 150,          # Identify word forms
        'frequency': 100,           # Assess frequency
        'facts': 500,               # Generate facts
    }
    
    # Estimate for a typical word with multiple meanings
    avg_clusters_per_word = 3  # Average meaning clusters
    
    tokens_per_word = (
        token_estimates['cluster_mapping'] +  # One cluster extraction
        (token_estimates['synthesis'] * avg_clusters_per_word) +  # Synthesis per cluster
        (token_estimates['examples'] * avg_clusters_per_word) +   # Examples per meaning
        token_estimates['synonyms'] +  # Synonyms (once per word)
        token_estimates['pronunciation'] +  # Pronunciation
        token_estimates['word_forms'] +  # Word forms
        token_estimates['frequency']  # Frequency assessment
    )
    
    print("\n💰 Cost Estimation for English Dictionary:")
    print(f"\n📊 Token Estimates per Operation:")
    for op, tokens in token_estimates.items():
        print(f"  - {op}: {tokens:,} tokens")
    
    print(f"\n📈 Per Word Calculation:")
    print(f"  - Average clusters/meanings: {avg_clusters_per_word}")
    print(f"  - Total tokens per word: {tokens_per_word:,}")
    
    # Dictionary sizes
    dictionary_sizes = {
        'Common English (10k words)': 10_000,
        'Standard Dictionary (50k)': 50_000,
        'Comprehensive (170k)': 170_000,
        'Oxford English Dict (600k)': 600_000,
    }
    
    # OpenAI pricing for GPT-4o (as of the code)
    input_price_per_1m = 2.50   # $2.50 per 1M input tokens
    output_price_per_1m = 10.00  # $10.00 per 1M output tokens
    
    # Assume 70% input, 30% output ratio
    input_ratio = 0.7
    output_ratio = 0.3
    
    print(f"\n💵 Cost Calculations (GPT-4o pricing):")
    print(f"  - Input: ${input_price_per_1m}/1M tokens")
    print(f"  - Output: ${output_price_per_1m}/1M tokens")
    print(f"  - Ratio: {input_ratio*100:.0f}% input, {output_ratio*100:.0f}% output")
    
    for dict_name, word_count in dictionary_sizes.items():
        total_tokens = word_count * tokens_per_word
        input_tokens = total_tokens * input_ratio
        output_tokens = total_tokens * output_ratio
        
        input_cost = (input_tokens / 1_000_000) * input_price_per_1m
        output_cost = (output_tokens / 1_000_000) * output_price_per_1m
        total_cost = input_cost + output_cost
        
        print(f"\n  {dict_name}:")
        print(f"    - Total tokens: {total_tokens:,}")
        print(f"    - Input tokens: {input_tokens:,.0f} (${input_cost:,.2f})")
        print(f"    - Output tokens: {output_tokens:,.0f} (${output_cost:,.2f})")
        print(f"    - Total cost: ${total_cost:,.2f}")


async def main():
    """Run all tests."""
    
    # Test specific word lookup
    await test_word_lookup("example")
    
    # Get AI endpoint info
    await get_ai_endpoints_info()
    
    # Estimate total costs
    await estimate_total_cost()


if __name__ == "__main__":
    asyncio.run(main())