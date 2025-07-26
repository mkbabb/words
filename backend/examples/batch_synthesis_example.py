#!/usr/bin/env python3
"""Example of using batch synthesis for large-scale processing.

This demonstrates how to efficiently process thousands of words using
the OpenAI Batch API, reducing costs by 50%.
"""

import asyncio
from pathlib import Path

from rich.console import Console

from src.floridify.ai.batch_processor import SynthesisBatchProcessor
from src.floridify.ai.factory import get_openai_connector
from src.floridify.models import Word, Definition
from src.floridify.constants import Language

console = Console()


async def example_batch_synthesis():
    """Demonstrate batch synthesis workflow."""
    console.print("[bold cyan]Floridify Batch Synthesis Example[/bold cyan]\n")
    
    # 1. Initialize components
    ai = get_openai_connector()
    batch_processor = SynthesisBatchProcessor(ai)
    
    # 2. Prepare test data (in production, you'd load from database/file)
    test_words = [
        "happy", "sad", "beautiful", "ugly", "fast", "slow",
        "big", "small", "hot", "cold", "light", "dark",
        "good", "bad", "new", "old", "first", "last"
    ]
    
    console.print(f"Processing {len(test_words)} words using batch synthesis\n")
    
    # 3. Create word objects with definitions (simplified)
    words_with_data = []
    
    for word_text in test_words:
        # Create word object
        word = Word(
            text=word_text,
            normalized=word_text.lower(),
            language=Language.ENGLISH
        )
        
        # Create sample definitions (in production, fetch from providers)
        definitions = [
            Definition(
                text=f"Primary meaning of {word_text}",
                part_of_speech="adjective",
                provider="test"
            ),
            Definition(
                text=f"Secondary meaning of {word_text}",
                part_of_speech="adjective",
                provider="test"
            )
        ]
        
        words_with_data.append((word, definitions))
    
    # 4. Process in batches
    console.print("[blue]Submitting synthesis batch to OpenAI...[/blue]")
    
    result = await batch_processor.process_words_batch(
        words_with_data,
        components={"synonyms", "examples", "cefr_level"},  # Select components
        batch_size=10  # Words per batch
    )
    
    # 5. Display results
    console.print("\n[green]Batch Submission Complete![/green]")
    console.print(f"Status: {result['status']}")
    console.print(f"Total batches: {result['batches']}")
    console.print(f"Total words: {result['total_words']}")
    
    console.print("\n[yellow]Batch Jobs:[/yellow]")
    for job in result['batch_jobs']:
        console.print(f"  - Batch ID: {job['batch_id']}")
        console.print(f"    OpenAI ID: {job['openai_batch_id']}")
        console.print(f"    Requests: {job['requests']}")
        console.print(f"    Status: {job['status']}\n")
    
    # 6. Cost estimation
    total_requests = sum(job['requests'] for job in result['batch_jobs'])
    estimated_tokens = total_requests * 500  # ~500 tokens per request
    
    # GPT-4o-mini pricing with batch discount
    immediate_cost = (estimated_tokens / 1_000_000) * 0.15
    batch_cost = immediate_cost * 0.5  # 50% discount
    
    console.print("[cyan]Cost Comparison:[/cyan]")
    console.print(f"  Immediate mode: ${immediate_cost:.4f}")
    console.print(f"  Batch mode: ${batch_cost:.4f}")
    console.print(f"  Savings: ${immediate_cost - batch_cost:.4f} (50%)\n")
    
    # 7. Show how to check status
    console.print("[blue]To check batch status later:[/blue]")
    console.print("```python")
    console.print("# Check status of a specific batch")
    console.print(f"status = await batch_processor.check_batch_status('{result['batch_jobs'][0]['openai_batch_id']}')")
    console.print("print(status)")
    console.print("```\n")
    
    return result


async def example_full_workflow():
    """Demonstrate the complete batch workflow with polling."""
    console.print("\n[bold cyan]Full Batch Workflow Example[/bold cyan]\n")
    
    # Initialize
    ai = get_openai_connector()
    batch_processor = SynthesisBatchProcessor(ai)
    
    # Small test set for demonstration
    test_words = ["example", "demonstration", "test"]
    
    console.print(f"Running full workflow for {len(test_words)} words\n")
    
    # Run the complete workflow (submit, poll, process)
    result = await batch_processor.run_full_batch_synthesis(
        test_words,
        poll_interval=30  # Check every 30 seconds
    )
    
    console.print(f"\n[green]Workflow Complete![/green]")
    console.print(f"Total processed: {result['total_processed']}")
    console.print(f"Total errors: {result['total_errors']}")
    
    return result


async def example_custom_components():
    """Show how to customize which components to synthesize."""
    console.print("\n[bold cyan]Custom Components Example[/bold cyan]\n")
    
    from src.floridify.ai.constants import SynthesisComponent
    
    # Show available components
    console.print("[yellow]Available synthesis components:[/yellow]")
    for component in SynthesisComponent:
        console.print(f"  - {component.value}")
    
    console.print("\n[blue]Example: Processing with only specific components[/blue]")
    
    # Select specific components
    selected_components = {
        SynthesisComponent.SYNONYMS.value,
        SynthesisComponent.EXAMPLES.value,
        SynthesisComponent.CEFR_LEVEL.value,
        SynthesisComponent.FREQUENCY_BAND.value
    }
    
    console.print(f"Selected: {', '.join(selected_components)}")
    
    # This would be passed to process_words_batch
    console.print("\n```python")
    console.print("result = await batch_processor.process_words_batch(")
    console.print("    words_with_data,")
    console.print(f"    components={selected_components},")
    console.print("    batch_size=100")
    console.print(")")
    console.print("```")


def main():
    """Run all examples."""
    console.print("[bold green]Floridify Batch Synthesis Examples[/bold green]\n")
    console.print("This demonstrates how to use batch processing for")
    console.print("large-scale synthesis operations with 50% cost savings.\n")
    
    async def run_examples():
        # Basic batch submission
        await example_batch_synthesis()
        
        # Custom components
        await example_custom_components()
        
        # Full workflow (commented out as it would actually submit to OpenAI)
        # await example_full_workflow()
        
        console.print("\n[bold green]✅ Examples complete![/bold green]")
        console.print("\nFor production use:")
        console.print("1. Load words from your database")
        console.print("2. Submit batches during off-peak hours")
        console.print("3. Poll for completion periodically")
        console.print("4. Process results and update database")
        console.print("5. Monitor costs and performance")
    
    asyncio.run(run_examples())


if __name__ == "__main__":
    main()