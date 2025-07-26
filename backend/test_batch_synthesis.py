#!/usr/bin/env python3
"""Test batch synthesis implementation."""

import asyncio
import time
from typing import Any

from rich.console import Console
from rich.table import Table

from src.floridify.ai.factory import get_openai_connector
from src.floridify.ai.models import SynonymGenerationResponse, ExampleGenerationResponse
from src.floridify.models import Word, Definition
from src.floridify.constants import Language
from src.floridify.ai.synthesis_functions import enhance_definitions_parallel

console = Console()


async def create_test_data() -> tuple[Word, list[Definition]]:
    """Create test word and definitions."""
    # Create a test word
    word = Word(
        text="test",
        normalized="test",
        language=Language.ENGLISH
    )
    
    # Create test definitions
    definitions = [
        Definition(
            text="To assess or evaluate through examination",
            part_of_speech="verb",
            provider="test",
            word_id="test_word_id"
        ),
        Definition(
            text="A procedure to establish quality or performance",
            part_of_speech="noun",
            provider="test",
            word_id="test_word_id"
        ),
        Definition(
            text="To challenge or try someone's patience",
            part_of_speech="verb",
            provider="test",
            word_id="test_word_id"
        )
    ]
    
    return word, definitions


async def test_immediate_mode():
    """Test traditional immediate mode execution."""
    console.print("\n[bold cyan]Testing Immediate Mode[/bold cyan]")
    
    # Get test data
    word, definitions = await create_test_data()
    
    # Get AI connector in immediate mode
    ai = get_openai_connector()
    
    start_time = time.time()
    
    # Run enhancement in immediate mode
    await enhance_definitions_parallel(
        definitions=definitions,
        word=word,
        ai=ai,
        components={"synonyms", "examples"},  # Just test these two
        force_refresh=True,
        batch_mode=False  # Immediate mode
    )
    
    elapsed = time.time() - start_time
    
    console.print(f"✅ Immediate mode completed in {elapsed:.2f}s")
    
    # Display results
    display_results(definitions, "Immediate Mode")
    
    return elapsed


async def test_batch_mode():
    """Test new batch mode execution."""
    console.print("\n[bold cyan]Testing Batch Mode[/bold cyan]")
    
    # Get test data
    word, definitions = await create_test_data()
    
    # Get AI connector
    ai = get_openai_connector()
    
    start_time = time.time()
    
    # Run enhancement in batch mode
    await enhance_definitions_parallel(
        definitions=definitions,
        word=word,
        ai=ai,
        components={"synonyms", "examples"},  # Just test these two
        force_refresh=True,
        batch_mode=True  # Batch mode
    )
    
    elapsed = time.time() - start_time
    
    console.print(f"✅ Batch mode completed in {elapsed:.2f}s")
    
    # Display results
    display_results(definitions, "Batch Mode")
    
    return elapsed


def display_results(definitions: list[Definition], mode: str):
    """Display enhancement results in a table."""
    table = Table(title=f"{mode} Results")
    table.add_column("Definition", style="cyan", width=40)
    table.add_column("Synonyms", style="green", width=30)
    table.add_column("Examples", style="yellow", width=40)
    
    for defn in definitions:
        synonyms = ", ".join(defn.synonyms[:3]) if defn.synonyms else "None"
        if len(defn.synonyms) > 3:
            synonyms += f" (+{len(defn.synonyms) - 3} more)"
            
        examples = defn.example_ids  # In a real scenario, we'd load the Example objects
        example_text = f"{len(examples)} examples" if examples else "None"
        
        table.add_row(
            defn.text[:40] + "..." if len(defn.text) > 40 else defn.text,
            synonyms,
            example_text
        )
    
    console.print(table)


async def test_batch_accumulation():
    """Test how requests are accumulated in batch mode."""
    console.print("\n[bold cyan]Testing Batch Accumulation[/bold cyan]")
    
    # Create AI connector in batch mode
    ai = get_openai_connector()
    ai.enable_batch_mode()
    
    # Make several AI calls without executing
    console.print("Making AI calls (accumulating)...")
    
    # Test direct API calls
    promise1 = await ai.synthesize_synonyms("happy", "feeling joy", "adjective", [], 5)
    console.print(f"Call 1: Batch size = {ai.batch_size}")
    
    promise2 = await ai.synthesize_synonyms("sad", "feeling sorrow", "adjective", [], 5)
    console.print(f"Call 2: Batch size = {ai.batch_size}")
    
    promise3 = await ai.generate_examples("run", "verb", "to move quickly", 3)
    console.print(f"Call 3: Batch size = {ai.batch_size}")
    
    # Execute the batch
    console.print(f"\nExecuting batch with {ai.batch_size} requests...")
    batch_result = await ai.execute_batch(wait_for_completion=True, timeout_minutes=5)
    
    console.print(f"Batch result: {batch_result['status']}")
    
    if batch_result["status"] == "completed":
        # Get results from promises
        result1 = await promise1
        result2 = await promise2
        result3 = await promise3
        
        if isinstance(result1, SynonymGenerationResponse):
            console.print(f"\nResult 1 (synonyms for 'happy'): {[s.word for s in result1.synonyms[:3]]}")
        
        if isinstance(result2, SynonymGenerationResponse):
            console.print(f"Result 2 (synonyms for 'sad'): {[s.word for s in result2.synonyms[:3]]}")
            
        if isinstance(result3, ExampleGenerationResponse):
            console.print(f"Result 3 (examples for 'run'): {len(result3.example_sentences)} examples")


async def test_cost_comparison():
    """Compare costs between immediate and batch modes."""
    console.print("\n[bold cyan]Cost Comparison[/bold cyan]")
    
    # Test data
    num_definitions = 5
    num_components = 10
    total_requests = num_definitions * num_components
    
    # Token estimates (rough)
    avg_tokens_per_request = 500
    total_tokens = total_requests * avg_tokens_per_request
    
    # Pricing (GPT-4o-mini)
    immediate_cost = (total_tokens / 1_000_000) * 0.15  # $0.15/1M input tokens
    batch_cost = immediate_cost * 0.5  # 50% discount
    
    table = Table(title="Cost Comparison")
    table.add_column("Mode", style="cyan")
    table.add_column("Requests", style="green")
    table.add_column("Est. Tokens", style="yellow")
    table.add_column("Est. Cost", style="red")
    
    table.add_row(
        "Immediate",
        str(total_requests),
        f"{total_tokens:,}",
        f"${immediate_cost:.4f}"
    )
    
    table.add_row(
        "Batch (50% off)",
        str(total_requests),
        f"{total_tokens:,}",
        f"${batch_cost:.4f}"
    )
    
    table.add_row(
        "Savings",
        "-",
        "-",
        f"${immediate_cost - batch_cost:.4f} ({((immediate_cost - batch_cost) / immediate_cost * 100):.0f}%)"
    )
    
    console.print(table)


async def main():
    """Run all tests."""
    console.print("[bold green]Floridify Batch Synthesis Test Suite[/bold green]")
    
    try:
        # Test accumulation first
        await test_batch_accumulation()
        
        # Compare execution modes
        # Note: These would need actual MongoDB setup to work fully
        # immediate_time = await test_immediate_mode()
        # batch_time = await test_batch_mode()
        
        # Show cost comparison
        await test_cost_comparison()
        
        console.print("\n[bold green]✅ All tests completed![/bold green]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())