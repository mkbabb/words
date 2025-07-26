#!/usr/bin/env python3
"""Analyze actual token usage from a real API call."""

import asyncio
import httpx
import json
import time
from typing import Dict, Any


async def lookup_with_detailed_tracking(word: str = "example") -> Dict[str, Any]:
    """Perform lookup and track all API operations."""
    
    print(f"\n🔍 Performing detailed lookup of '{word}' with force refresh...")
    print("=" * 60)
    
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        # Use streaming endpoint to see all operations
        url = f"http://localhost:8000/api/v1/lookup/{word}/stream"
        params = {"force_refresh": "true"}
        
        operations = []
        
        async with client.stream('GET', url, params=params, timeout=60.0) as response:
            async for line in response.aiter_lines():
                if line.startswith('data:'):
                    try:
                        data = json.loads(line[5:])
                        
                        if 'stage' in data:
                            stage = data['stage']
                            progress = data.get('progress', 0)
                            message = data.get('message', '')
                            
                            print(f"\n📍 Stage: {stage} ({progress}%)")
                            if message:
                                print(f"   Message: {message}")
                            
                            operations.append({
                                'stage': stage,
                                'progress': progress,
                                'message': message,
                                'timestamp': time.time() - start_time
                            })
                    except json.JSONDecodeError:
                        pass
                elif line.startswith('event: complete'):
                    # Get the complete data
                    next_line = await response.aiter_lines().__anext__()
                    if next_line.startswith('data:'):
                        final_data = json.loads(next_line[5:])
                        
                        if 'details' in final_data and 'result' in final_data['details']:
                            result = final_data['details']['result']
                            
                            print(f"\n✅ Lookup completed in {time.time() - start_time:.2f} seconds")
                            print(f"\n📊 Final Statistics:")
                            print(f"  - Definitions: {len(result.get('definitions', []))}")
                            
                            # Calculate content size for each definition
                            total_chars = 0
                            for i, defn in enumerate(result.get('definitions', [])):
                                defn_chars = len(json.dumps(defn))
                                total_chars += defn_chars
                                print(f"  - Definition {i+1}: {defn_chars:,} chars ({defn['part_of_speech']})")
                            
                            print(f"  - Total content: {total_chars:,} characters")
                            
                            return {
                                'result': result,
                                'operations': operations,
                                'duration': time.time() - start_time
                            }
    
    return None


async def estimate_tokens_from_content(data: Dict[str, Any]) -> Dict[str, int]:
    """Estimate tokens based on content size and operations."""
    
    # Rough estimation: 1 token ≈ 4 characters for English text
    char_to_token_ratio = 4
    
    result = data.get('result', {})
    operations = data.get('operations', [])
    
    print("\n💡 Token Estimation Based on Content:")
    print("=" * 60)
    
    token_estimates = {}
    
    # Estimate tokens for each operation based on content
    definitions = result.get('definitions', [])
    
    # 1. Cluster Mapping - processes all definition texts
    cluster_input_chars = sum(len(d.get('text', '')) for d in definitions) * len(definitions)
    token_estimates['cluster_mapping'] = {
        'input': cluster_input_chars // char_to_token_ratio,
        'output': 200  # Structured cluster response
    }
    
    # 2. Synthesis - for each cluster/definition
    for i, defn in enumerate(definitions):
        synthesis_key = f'synthesis_def_{i+1}'
        # Input: all related definitions + prompt
        input_chars = len(json.dumps(defn)) + 500  # prompt overhead
        output_chars = len(defn.get('text', ''))
        
        token_estimates[synthesis_key] = {
            'input': input_chars // char_to_token_ratio,
            'output': output_chars // char_to_token_ratio
        }
    
    # 3. Examples generation
    total_examples = sum(len(d.get('examples', [])) for d in definitions)
    if total_examples > 0:
        example_chars = sum(len(ex.get('text', '')) for d in definitions for ex in d.get('examples', []))
        token_estimates['examples'] = {
            'input': 300 * len(definitions),  # Prompt per definition
            'output': example_chars // char_to_token_ratio
        }
    
    # 4. Synonyms
    total_synonyms = sum(len(d.get('synonyms', [])) for d in definitions)
    if total_synonyms > 0:
        token_estimates['synonyms'] = {
            'input': 200 * len(definitions),
            'output': total_synonyms * 10  # ~10 tokens per synonym
        }
    
    # 5. Other operations
    if result.get('pronunciation'):
        token_estimates['pronunciation'] = {
            'input': 50,
            'output': 50
        }
    
    # Print estimation summary
    total_input = 0
    total_output = 0
    
    for operation, tokens in token_estimates.items():
        input_tokens = tokens['input']
        output_tokens = tokens['output']
        total_input += input_tokens
        total_output += output_tokens
        
        print(f"\n{operation}:")
        print(f"  Input: {input_tokens:,} tokens")
        print(f"  Output: {output_tokens:,} tokens")
        print(f"  Total: {input_tokens + output_tokens:,} tokens")
    
    print(f"\n📊 Total Token Estimates:")
    print(f"  - Total Input: {total_input:,} tokens")
    print(f"  - Total Output: {total_output:,} tokens")
    print(f"  - Grand Total: {total_input + total_output:,} tokens")
    
    # Calculate cost
    input_cost = (total_input / 1_000_000) * 2.50
    output_cost = (total_output / 1_000_000) * 10.00
    total_cost = input_cost + output_cost
    
    print(f"\n💰 Estimated Cost (GPT-4o):")
    print(f"  - Input: ${input_cost:.4f}")
    print(f"  - Output: ${output_cost:.4f}")
    print(f"  - Total: ${total_cost:.4f}")
    
    return {
        'total_input': total_input,
        'total_output': total_output,
        'total': total_input + total_output,
        'cost': total_cost
    }


async def main():
    """Run detailed token analysis."""
    
    # Perform detailed lookup
    data = await lookup_with_detailed_tracking("example")
    
    if data:
        # Estimate tokens from content
        token_stats = await estimate_tokens_from_content(data)
        
        # Extrapolate to full dictionary
        print("\n🌍 Extrapolation to Full English Dictionary:")
        print("=" * 60)
        
        tokens_per_word = token_stats['total']
        cost_per_word = token_stats['cost']
        
        dictionaries = [
            ("Common English", 10_000),
            ("Standard Dictionary", 50_000),
            ("Comprehensive", 170_000),
            ("Oxford English Dictionary", 600_000)
        ]
        
        for name, word_count in dictionaries:
            total_tokens = word_count * tokens_per_word
            total_cost = word_count * cost_per_word
            
            print(f"\n{name} ({word_count:,} words):")
            print(f"  - Total tokens: {total_tokens:,}")
            print(f"  - Estimated cost: ${total_cost:,.2f}")


if __name__ == "__main__":
    asyncio.run(main())