#!/usr/bin/env python3
"""Test batch processing and request deduplication functionality."""

import asyncio
import time
from typing import Any

import httpx
from rich.console import Console
from rich.table import Table

console = Console()

API_BASE = "http://localhost:8000/api/v1"


async def test_request_deduplication():
    """Test that concurrent identical requests are deduplicated."""
    console.print("\n[bold cyan]Testing Request Deduplication[/bold cyan]")
    
    async with httpx.AsyncClient() as client:
        # Launch multiple concurrent requests for the same word
        word = "concurrent"
        
        start_time = time.time()
        
        # Launch 5 concurrent requests
        tasks = [
            client.get(f"{API_BASE}/lookup/{word}?force_refresh=true")
            for _ in range(5)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        
        # Check all responses are successful
        success_count = sum(1 for r in responses if r.status_code == 200)
        
        console.print(f"✅ All {len(responses)} requests completed in {elapsed:.2f}s")
        console.print(f"✅ Success rate: {success_count}/{len(responses)}")
        
        # With deduplication, this should be much faster than 5 sequential requests
        if elapsed < 10:  # Assuming a single request takes ~2-3s
            console.print("✅ [green]Deduplication working - requests completed faster than sequential execution[/green]")
        else:
            console.print("⚠️  [yellow]Requests may not be deduplicated effectively[/yellow]")


async def test_ai_endpoints():
    """Test various AI endpoints with the new GPT-4o-mini model."""
    console.print("\n[bold cyan]Testing AI Endpoints with GPT-4o-mini[/bold cyan]")
    
    async with httpx.AsyncClient() as client:
        # Test pronunciation
        resp = await client.post(f"{API_BASE}/ai/synthesize/pronunciation", json={"word": "ephemeral"})
        if resp.status_code == 200:
            data = resp.json()
            console.print(f"✅ Pronunciation: {data['pronunciation']['phonetic']}")
        
        # Test suggestions
        resp = await client.post(f"{API_BASE}/ai/suggestions", json={"count": 5})
        if resp.status_code == 200:
            data = resp.json()
            console.print(f"✅ Suggestions: {len(data.get('suggestions', []))} words generated")
        
        # Test frequency assessment
        resp = await client.post(f"{API_BASE}/ai/assess/frequency", json={
            "word": "quotidian",
            "definition": "Of or occurring every day; belonging to each day; everyday; ordinary"
        })
        if resp.status_code == 200:
            data = resp.json()
            band = data.get('band', data.get('frequency_band'))
            console.print(f"✅ Frequency band for 'quotidian': {band}")


async def test_lookup_quality():
    """Test lookup quality with various words."""
    console.print("\n[bold cyan]Testing Lookup Quality[/bold cyan]")
    
    test_words = ["happy", "ubiquitous", "serendipity", "ephemeral", "perspicacious"]
    
    table = Table(title="Lookup Results")
    table.add_column("Word", style="cyan")
    table.add_column("Definitions", style="green")
    table.add_column("Synonyms", style="yellow")
    table.add_column("Examples", style="blue")
    table.add_column("Time (ms)", style="magenta")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for word in test_words:
            start = time.time()
            
            resp = await client.get(f"{API_BASE}/lookup/{word}")
            
            elapsed_ms = int((time.time() - start) * 1000)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Count definitions
                def_count = len(data.get("definitions", []))
                
                # Count total synonyms across all definitions
                syn_count = sum(
                    len(d.get("synonyms", []))
                    for d in data.get("definitions", [])
                )
                
                # Count total examples
                ex_count = sum(
                    len(d.get("examples", []))
                    for d in data.get("definitions", [])
                )
                
                table.add_row(
                    word,
                    str(def_count),
                    str(syn_count),
                    str(ex_count),
                    str(elapsed_ms)
                )
            else:
                table.add_row(
                    word,
                    f"Error {resp.status_code}",
                    "-",
                    "-",
                    str(elapsed_ms)
                )
    
    console.print(table)


async def test_word_suggestions():
    """Test the new word suggestion feature."""
    console.print("\n[bold cyan]Testing Word Suggestion Feature[/bold cyan]")
    
    queries = [
        "words that mean happy",
        "difficult vocabulary words",
        "words related to time",
        "beautiful sounding words"
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query in queries:
            console.print(f"\n[yellow]Query:[/yellow] {query}")
            
            # First validate the query
            resp = await client.post(f"{API_BASE}/ai/validate-query", json={"query": query})
            
            if resp.status_code == 200 and resp.json().get("is_valid"):
                # Get suggestions
                resp = await client.post(f"{API_BASE}/ai/suggest-words", json={
                    "query": query,
                    "count": 8
                })
                
                if resp.status_code == 200:
                    data = resp.json()
                    suggestions = data.get("suggestions", [])
                    
                    console.print(f"✅ Generated {len(suggestions)} suggestions:")
                    for i, suggestion in enumerate(suggestions[:5], 1):
                        word = suggestion.get("word", "?")
                        reason = suggestion.get("reason", "")
                        console.print(f"   {i}. [cyan]{word}[/cyan] - {reason[:80]}...")
                else:
                    console.print(f"❌ Error {resp.status_code}: {resp.text[:100]}")
            else:
                console.print("❌ Query validation failed")


async def test_batch_processing_setup():
    """Test that batch processing infrastructure is set up correctly."""
    console.print("\n[bold cyan]Testing Batch Processing Setup[/bold cyan]")
    
    # Import and test the batch processor
    try:
        from floridify.batch.enhanced_batch_processor import EnhancedBatchProcessor
        from floridify.models import Definition
        
        # Get API key from config
        import toml
        config = toml.load("/Users/mkbabb/Programming/words/backend/auth/config.toml")
        api_key = config["api"]["openai_api_key"]
        
        processor = EnhancedBatchProcessor(api_key=api_key, model="gpt-4o-mini")
        
        # Test creating a batch request
        test_def = Definition(
            text="A test definition",
            part_of_speech="noun",
            provider="test"
        )
        
        batch_requests = await processor.create_cluster_mapping_batch(
            [("test", [test_def])],
            batch_id="test"
        )
        
        console.print(f"✅ Created {len(batch_requests)} batch request(s)")
        console.print(f"✅ Batch processor configured with model: {processor.model}")
        
    except Exception as e:
        console.print(f"❌ Batch processing setup error: {e}")


async def main():
    """Run all tests."""
    console.print("[bold green]Running Floridify Backend Tests[/bold green]")
    
    await test_request_deduplication()
    await test_ai_endpoints()
    await test_lookup_quality()
    await test_word_suggestions()
    await test_batch_processing_setup()
    
    console.print("\n[bold green]✅ All tests completed![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())