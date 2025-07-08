#!/usr/bin/env python3
"""CLI for batch processing operations."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

from src.floridify.ai.connector import OpenAIConnector as AIConnector
from src.floridify.batch import BatchJobConfig, BatchProcessor, FilterPresets
from src.floridify.batch.scheduler import BatchScheduler, ScheduleFrequency, SchedulerConfig
from src.floridify.connectors.wiktionary import WiktionaryConnector
from src.floridify.search.core import SearchEngine
from src.floridify.storage.mongodb import MongoDBStorage as MongoDB

console = Console()

async def get_initialized_components() -> tuple[AIConnector, SearchEngine, MongoDB]:
    """Initialize and return core components."""
    console.print("[blue]Initializing components...[/blue]")
    
    # Initialize AI connector
    ai_connector = AIConnector()
    
    # Initialize MongoDB
    mongodb = MongoDB()
    await mongodb.connect()
    
    # Initialize search engine
    search_engine = SearchEngine(languages=["en"], enable_semantic=False)
    await search_engine.initialize()
    
    return ai_connector, search_engine, mongodb

@click.group()
def cli() -> None:
    """Batch processing CLI for Floridify dictionary synthesis."""
    pass

@cli.command()
@click.option("--words", "-w", type=int, help="Maximum number of words to process")
@click.option("--batch-size", "-b", type=int, default=1000, help="Words per batch file")
@click.option("--filter-preset", "-f", 
              type=click.Choice(["minimal", "standard", "aggressive"]),
              default="standard", help="Word filtering preset")
@click.option("--force", is_flag=True, help="Process all words, ignoring cache")
@click.option("--output-dir", "-o", type=Path, help="Output directory for batch files")
def process(
    words: int | None,
    batch_size: int,
    filter_preset: str,
    force: bool,
    output_dir: Path | None,
) -> None:
    """Run batch processing for dictionary synthesis."""
    async def _process() -> None:
        ai_connector, search_engine, mongodb = await get_initialized_components()
        
        try:
            # Configure batch processing
            config = BatchJobConfig(
                batch_size=batch_size,
                max_concurrent_batches=3,
                output_directory=output_dir or Path("./batch_output"),
                filter_preset=filter_preset,
                providers=[WiktionaryConnector()],
                force_refresh=force,
                enable_clustering=True,
                enable_synthesis=True
            )
            
            # Create processor
            processor = BatchProcessor(
                config=config,
                ai_connector=ai_connector,
                search_engine=search_engine,
                mongodb=mongodb
            )
            
            # Run processing
            result = await processor.run_batch_processing(words)
            
            if result["status"] == "completed":
                console.print("[green]Batch processing completed successfully![/green]")
                console.print(f"Processed: {result['total_words_processed']:,} words")
                console.print(f"Success rate: {result['success_rate']:.1f}%")
            else:
                console.print(f"[red]Batch processing failed: {result.get('error', 'Unknown error')}[/red]")
                sys.exit(1)
            
        finally:
            await mongodb.close()
    
    asyncio.run(_process())

@cli.command()
@click.option("--filter-preset", "-f", 
              type=click.Choice(["minimal", "standard", "aggressive"]),
              default="standard", help="Word filtering preset")
@click.option("--limit", "-l", type=int, help="Limit number of words to display")
def filter_words(filter_preset: str, limit: int | None) -> None:
    """Test word filtering on current corpus."""
    async def _filter() -> None:
        ai_connector, search_engine, mongodb = await get_initialized_components()
        
        try:
            # Get word corpus
            words = []
            if hasattr(search_engine, 'fuzzy_matcher') and search_engine.fuzzy_matcher:
                words.extend(search_engine.fuzzy_matcher.word_list)
            
            if hasattr(search_engine, 'exact_matcher') and search_engine.exact_matcher:
                words.extend(search_engine.exact_matcher.word_dict.keys())
            
            unique_words = list(set(words))
            console.print(f"[blue]Found {len(unique_words):,} unique words in corpus[/blue]")
            
            # Apply filtering
            if filter_preset == "minimal":
                word_filter = FilterPresets.minimal()
            elif filter_preset == "aggressive":
                word_filter = FilterPresets.aggressive()
            else:
                word_filter = FilterPresets.standard()
            
            filtered_words, stats = word_filter.filter_word_list(unique_words)
            
            # Display results
            console.print(word_filter.get_filter_summary())
            
            if limit and filtered_words:
                console.print(f"\n[blue]First {min(limit, len(filtered_words))} filtered words:[/blue]")
                for word in filtered_words[:limit]:
                    console.print(f"  - {word}")
            
        finally:
            await mongodb.close()
    
    asyncio.run(_filter())

@cli.group()
def scheduler() -> None:
    """Batch processing scheduler commands."""
    pass

@scheduler.command()
@click.option("--frequency", "-f", 
              type=click.Choice(["hourly", "daily", "weekly", "manual"]),
              default="daily", help="Scheduling frequency")
@click.option("--run-time", "-t", default="02:00", help="Run time (HH:MM)")
@click.option("--max-words", "-w", type=int, default=10000, help="Max words per run")
@click.option("--max-cost", "-c", type=float, default=50.0, help="Max cost per run (USD)")
def start(
    frequency: str,
    run_time: str,
    max_words: int,
    max_cost: float
) -> None:
    """Start the batch processing scheduler."""
    async def _start() -> None:
        ai_connector, search_engine, mongodb = await get_initialized_components()
        
        try:
            # Configure scheduler
            config = SchedulerConfig(
                frequency=ScheduleFrequency(frequency),
                run_time=run_time,
                max_words_per_run=max_words,
                max_cost_per_run=max_cost,
                enable_auto_scaling=True
            )
            
            # Create scheduler
            batch_scheduler = BatchScheduler(
                config=config,
                ai_connector=ai_connector,
                search_engine=search_engine,
                mongodb=mongodb
            )
            
            console.print("[green]Starting batch processing scheduler...[/green]")
            console.print("Press Ctrl+C to stop")
            
            # Start scheduler
            await batch_scheduler.start_scheduler()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Scheduler stopped by user[/yellow]")
        finally:
            await mongodb.close()
    
    asyncio.run(_start())

@scheduler.command()
def status() -> None:
    """Show scheduler status."""
    async def _status() -> None:
        ai_connector, search_engine, mongodb = await get_initialized_components()
        
        try:
            # Create minimal scheduler for status check
            config = SchedulerConfig()
            batch_scheduler = BatchScheduler(
                config=config,
                ai_connector=ai_connector,
                search_engine=search_engine,
                mongodb=mongodb
            )
            
            batch_scheduler.display_status()
            
        finally:
            await mongodb.close()
    
    asyncio.run(_status())

@scheduler.command()
@click.option("--words", "-w", type=int, help="Maximum number of words to process")
def run_once(words: int | None) -> None:
    """Manually run batch processing once."""
    async def _run_once() -> None:
        ai_connector, search_engine, mongodb = await get_initialized_components()
        
        try:
            config = SchedulerConfig()
            batch_scheduler = BatchScheduler(
                config=config,
                ai_connector=ai_connector,
                search_engine=search_engine,
                mongodb=mongodb
            )
            
            result = await batch_scheduler.manual_run(words)
            
            if result["status"] == "completed":
                console.print("[green]Manual batch processing completed![/green]")
            else:
                console.print(f"[red]Manual batch processing failed: {result.get('error')}[/red]")
                sys.exit(1)
            
        finally:
            await mongodb.close()
    
    asyncio.run(_run_once())

@cli.command()
def estimate_cost() -> None:
    """Estimate processing costs for the current word corpus."""
    async def _estimate() -> None:
        ai_connector, search_engine, mongodb = await get_initialized_components()
        
        try:
            # Get filtered word count
            words = []
            if hasattr(search_engine, 'fuzzy_matcher') and search_engine.fuzzy_matcher:
                words.extend(search_engine.fuzzy_matcher.word_list)
            
            if hasattr(search_engine, 'exact_matcher') and search_engine.exact_matcher:
                words.extend(search_engine.exact_matcher.word_dict.keys())
            
            unique_words = list(set(words))
            
            # Apply standard filtering
            word_filter = FilterPresets.standard()
            filtered_words, stats = word_filter.filter_word_list(unique_words)
            
            # Estimate costs for different scenarios
            scenarios = [
                ("Full corpus", len(filtered_words)),
                ("10K words", min(10000, len(filtered_words))),
                ("1K words", min(1000, len(filtered_words))),
                ("100 words", min(100, len(filtered_words)))
            ]
            
            console.print("\n[bold blue]Cost Estimation[/bold blue]")
            console.print("(Based on OpenAI Batch API pricing with 50% discount)")
            
            from rich.table import Table
            table = Table()
            table.add_column("Scenario", style="cyan")
            table.add_column("Words", justify="right")
            table.add_column("Estimated Cost", justify="right", style="yellow")
            table.add_column("Processing Time", justify="right")
            
            for scenario_name, word_count in scenarios:
                if word_count == 0:
                    continue
                
                # Rough estimation: 2 requests per word, ~500 tokens per request
                estimated_tokens = word_count * 2 * 500
                input_tokens = estimated_tokens * 0.7
                output_tokens = estimated_tokens * 0.3
                
                input_cost = (input_tokens / 1_000_000) * 0.075
                output_cost = (output_tokens / 1_000_000) * 0.300
                total_cost = input_cost + output_cost
                
                # Estimate processing time (batches process within 24h, usually much faster)
                batch_count = (word_count + 999) // 1000  # Round up
                estimated_hours = min(24, batch_count * 0.5)  # Rough estimate
                
                table.add_row(
                    scenario_name,
                    f"{word_count:,}",
                    f"${total_cost:.2f}",
                    f"~{estimated_hours:.1f}h"
                )
            
            console.print(table)
            console.print("\n[yellow]Note: Actual costs may vary based on definition complexity and AI model responses[/yellow]")
            
        finally:
            await mongodb.close()
    
    asyncio.run(_estimate())

if __name__ == "__main__":
    cli()