#!/usr/bin/env python3
"""Calculate cost savings using OpenAI Batch API with GPT-4o-mini."""

def calculate_batch_api_costs():
    """Calculate costs using Batch API with GPT-4o-mini."""
    
    print("\n💰 OpenAI Batch API Cost Analysis")
    print("=" * 70)
    
    # Token usage per word (your estimate)
    tokens_per_word = 20_000
    
    # Model pricing (as of January 2025)
    models = {
        "GPT-4o (Standard API)": {
            "input_per_1m": 2.50,
            "output_per_1m": 10.00,
            "batch_discount": 0.5,  # 50% discount
        },
        "GPT-4o-mini (Standard API)": {
            "input_per_1m": 0.15,  # $0.15 per 1M tokens
            "output_per_1m": 0.60,  # $0.60 per 1M tokens
            "batch_discount": 0.5,  # 50% discount
        }
    }
    
    # Dictionary sizes
    dictionaries = [
        ("Common English", 10_000),
        ("Standard Dictionary", 50_000),
        ("Comprehensive", 170_000),
        ("Oxford English Dictionary", 600_000),
    ]
    
    # Token split (70% input, 30% output)
    input_ratio = 0.7
    output_ratio = 0.3
    
    print(f"\n📊 Assumptions:")
    print(f"  - Tokens per word: {tokens_per_word:,}")
    print(f"  - Input/Output ratio: {int(input_ratio*100)}%/{int(output_ratio*100)}%")
    print(f"  - Batch API discount: 50% off standard pricing")
    
    # Calculate costs for each model and API type
    for dict_name, word_count in dictionaries:
        print(f"\n\n{'='*70}")
        print(f"📚 {dict_name} ({word_count:,} words)")
        print(f"{'='*70}")
        
        total_tokens = word_count * tokens_per_word
        input_tokens = total_tokens * input_ratio
        output_tokens = total_tokens * output_ratio
        
        print(f"\nTotal tokens: {total_tokens:,}")
        print(f"  - Input: {input_tokens:,.0f}")
        print(f"  - Output: {output_tokens:,.0f}")
        
        for model_name, pricing in models.items():
            print(f"\n🤖 {model_name}:")
            
            # Standard API costs
            standard_input_cost = (input_tokens / 1_000_000) * pricing["input_per_1m"]
            standard_output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]
            standard_total = standard_input_cost + standard_output_cost
            
            # Batch API costs (50% discount)
            batch_input_cost = standard_input_cost * pricing["batch_discount"]
            batch_output_cost = standard_output_cost * pricing["batch_discount"]
            batch_total = batch_input_cost + batch_output_cost
            
            print(f"  Standard API: ${standard_total:,.2f}")
            print(f"  Batch API: ${batch_total:,.2f} (saves ${standard_total - batch_total:,.2f})")
    
    # Highlight the most cost-effective option
    print(f"\n\n{'='*70}")
    print("🎯 MOST COST-EFFECTIVE: GPT-4o-mini with Batch API")
    print(f"{'='*70}")
    
    # Calculate for GPT-4o-mini Batch API specifically
    mini_pricing = models["GPT-4o-mini (Standard API)"]
    
    for dict_name, word_count in dictionaries:
        total_tokens = word_count * tokens_per_word
        input_tokens = total_tokens * input_ratio
        output_tokens = total_tokens * output_ratio
        
        # Batch API costs for GPT-4o-mini
        batch_input_cost = (input_tokens / 1_000_000) * mini_pricing["input_per_1m"] * 0.5
        batch_output_cost = (output_tokens / 1_000_000) * mini_pricing["output_per_1m"] * 0.5
        batch_total = batch_input_cost + batch_output_cost
        
        # Compare to original GPT-4o estimate
        gpt4o_standard = (input_tokens / 1_000_000) * 2.50 + (output_tokens / 1_000_000) * 10.00
        
        savings_percentage = ((gpt4o_standard - batch_total) / gpt4o_standard) * 100
        
        print(f"\n{dict_name} ({word_count:,} words):")
        print(f"  - GPT-4o-mini Batch API: ${batch_total:,.2f}")
        print(f"  - vs GPT-4o Standard: ${gpt4o_standard:,.2f}")
        print(f"  - Savings: ${gpt4o_standard - batch_total:,.2f} ({savings_percentage:.1f}% reduction)")
    
    # Additional considerations
    print(f"\n\n📝 Additional Considerations:")
    print("  - Batch API processes within 24 hours (not real-time)")
    print("  - Higher rate limits: 250M tokens enqueued for batch processing")
    print("  - Perfect for dictionary building (not time-sensitive)")
    print("  - Can process in chunks to manage costs and monitor quality")
    print("  - GPT-4o-mini maintains high quality (82% MMLU score)")


if __name__ == "__main__":
    calculate_batch_api_costs()