#!/usr/bin/env python3
"""
Batch synthesis script for processing multiple words efficiently.

This script provides:
- Rich console output with progress bars and cost tracking
- Time estimation and throughput monitoring
- Checkpoint/resume functionality
- Graceful shutdown and error recovery
- 50% cost reduction via OpenAI Batch API
"""

import asyncio
import json
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.floridify.ai.factory import get_definition_synthesizer, get_openai_connector
from src.floridify.constants import Language
from src.floridify.core.lookup_pipeline import lookup_word_pipeline
from src.floridify.utils.logging import get_logger

app = typer.Typer()
console = Console()
logger = get_logger(__name__)

# Global state for graceful shutdown
SHUTDOWN_REQUESTED = False


class BatchSynthesisState:
    """Manages checkpoint state for batch synthesis."""
    
    def __init__(self, checkpoint_file: Path):
        self.checkpoint_file = checkpoint_file
        self.processed_words: set[str] = set()
        self.failed_words: dict[str, str] = {}
        self.start_time = time.time()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.load()
    
    def load(self) -> None:
        """Load state from checkpoint file."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    self.processed_words = set(data.get('processed_words', []))
                    self.failed_words = data.get('failed_words', {})
                    self.start_time = data.get('start_time', time.time())
                    self.total_cost = data.get('total_cost', 0.0)
                    self.total_tokens = data.get('total_tokens', 0)
                    console.print(f"[green]✅ Loaded checkpoint with {len(self.processed_words)} processed words[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Failed to load checkpoint: {e}[/yellow]")
    
    def save(self) -> None:
        """Save state to checkpoint file."""
        try:
            data = {
                'processed_words': list(self.processed_words),
                'failed_words': self.failed_words,
                'start_time': self.start_time,
                'total_cost': self.total_cost,
                'total_tokens': self.total_tokens,
                'timestamp': datetime.now().isoformat()
            }
            with open(self.checkpoint_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]❌ Failed to save checkpoint: {e}[/red]")
    
    def mark_processed(self, word: str) -> None:
        """Mark a word as processed."""
        self.processed_words.add(word)
        self.save()
    
    def mark_failed(self, word: str, error: str) -> None:
        """Mark a word as failed."""
        self.failed_words[word] = error
        self.save()
    
    def update_costs(self, tokens: int, cost: float) -> None:
        """Update token and cost tracking."""
        self.total_tokens += tokens
        self.total_cost += cost
        self.save()
    
    def get_remaining_words(self, words: list[str]) -> list[str]:
        """Get words that haven't been processed yet."""
        return [w for w in words if w not in self.processed_words]


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    global SHUTDOWN_REQUESTED
    SHUTDOWN_REQUESTED = True
    console.print("\n[yellow]⚠️  Shutdown requested. Finishing current batch...[/yellow]")


def estimate_costs(word_count: int, avg_definitions_per_word: int = 5) -> dict[str, float]:
    """Estimate costs for batch synthesis."""
    # Rough estimates based on typical usage
    tokens_per_definition = 500
    tokens_per_word = tokens_per_definition * avg_definitions_per_word
    
    # GPT-4o pricing (as of 2025)
    input_cost_per_1k = 0.0025  # $2.50 per 1M tokens
    output_cost_per_1k = 0.01   # $10 per 1M tokens
    
    # Estimate token usage
    total_input_tokens = word_count * tokens_per_word * 0.7  # 70% input
    total_output_tokens = word_count * tokens_per_word * 0.3  # 30% output
    
    # Calculate costs
    regular_cost = (total_input_tokens / 1000 * input_cost_per_1k + 
                   total_output_tokens / 1000 * output_cost_per_1k)
    batch_cost = regular_cost * 0.5  # 50% discount for batch API
    
    return {
        'regular_cost': regular_cost,
        'batch_cost': batch_cost,
        'savings': regular_cost - batch_cost,
        'estimated_tokens': int(total_input_tokens + total_output_tokens)
    }


def create_status_table(state: BatchSynthesisState, total_words: int) -> Table:
    """Create a status table for the current batch processing."""
    table = Table(title="Batch Synthesis Status", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    # Calculate metrics
    processed = len(state.processed_words)
    failed = len(state.failed_words)
    remaining = total_words - processed
    success_rate = (processed - failed) / processed * 100 if processed > 0 else 0
    elapsed = time.time() - state.start_time
    words_per_minute = processed / (elapsed / 60) if elapsed > 0 else 0
    eta = (remaining / words_per_minute * 60) if words_per_minute > 0 else 0
    
    # Add rows
    table.add_row("Total Words", f"{total_words:,}")
    table.add_row("Processed", f"{processed:,}")
    table.add_row("Failed", f"{failed:,}")
    table.add_row("Success Rate", f"{success_rate:.1f}%")
    table.add_row("Words/Minute", f"{words_per_minute:.1f}")
    table.add_row("Total Tokens", f"{state.total_tokens:,}")
    table.add_row("Total Cost", f"${state.total_cost:.2f}")
    table.add_row("Elapsed Time", str(timedelta(seconds=int(elapsed))))
    table.add_row("ETA", str(timedelta(seconds=int(eta))) if eta > 0 else "N/A")
    
    return table


async def process_word_batch(
    words: list[str],
    state: BatchSynthesisState,
    progress: Progress,
    task_id: Any
) -> None:
    """Process a batch of words with synthesis."""
    synthesizer = await get_definition_synthesizer()
    
    for word in words:
        if SHUTDOWN_REQUESTED:
            console.print("[yellow]⚠️  Shutdown requested, stopping batch processing[/yellow]")
            break
        
        if word in state.processed_words:
            progress.advance(task_id)
            continue
        
        try:
            # Update progress description
            progress.update(task_id, description=f"Processing '{word}'...")
            
            # First, lookup the word from providers
            lookup_result = await lookup_word_pipeline(
                word=word,
                force_refresh=False
            )
            
            if not lookup_result or not lookup_result.get('providers_data'):
                logger.warning(f"No provider data found for '{word}'")
                state.mark_failed(word, "No provider data")
                progress.advance(task_id)
                continue
            
            # Get providers data
            providers_data = lookup_result['providers_data']
            
            # Use batch synthesis method
            entry = await synthesizer.synthesize_entry_batch(
                word=word,
                providers_data=providers_data,
                language=Language.ENGLISH,
                force_refresh=True
            )
            
            if entry:
                state.mark_processed(word)
                # Estimate token usage (rough approximation)
                estimated_tokens = len(str(entry)) * 2
                estimated_cost = estimated_tokens / 1000 * 0.01 * 0.5  # Batch pricing
                state.update_costs(estimated_tokens, estimated_cost)
                logger.success(f"✅ Synthesized '{word}'")
            else:
                state.mark_failed(word, "Synthesis returned None")
                logger.error(f"❌ Failed to synthesize '{word}'")
            
        except Exception as e:
            error_msg = str(e)
            state.mark_failed(word, error_msg)
            logger.error(f"❌ Error processing '{word}': {error_msg}")
        
        finally:
            progress.advance(task_id)


@app.command()
def main(
    input_file: Path = typer.Argument(
        ..., 
        help="Text file containing words to process (one per line)"
    ),
    checkpoint_file: Path = typer.Option(
        Path("batch_synthesis_checkpoint.json"),
        "--checkpoint", "-c",
        help="Checkpoint file for resume functionality"
    ),
    batch_size: int = typer.Option(
        10,
        "--batch-size", "-b",
        help="Number of words to process in each batch"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show cost estimates without processing"
    )
):
    """Run batch synthesis on a list of words with progress tracking and checkpointing."""
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load words from file
    if not input_file.exists():
        console.print(f"[red]❌ Input file not found: {input_file}[/red]")
        raise typer.Exit(1)
    
    with open(input_file, 'r') as f:
        all_words = [line.strip() for line in f if line.strip()]
    
    if not all_words:
        console.print("[red]❌ No words found in input file[/red]")
        raise typer.Exit(1)
    
    # Initialize state
    state = BatchSynthesisState(checkpoint_file)
    remaining_words = state.get_remaining_words(all_words)
    
    console.print(f"\n[cyan]📚 Total words: {len(all_words)}[/cyan]")
    console.print(f"[cyan]✅ Already processed: {len(state.processed_words)}[/cyan]")
    console.print(f"[cyan]📝 Remaining: {len(remaining_words)}[/cyan]")
    
    # Show cost estimates
    if remaining_words:
        estimates = estimate_costs(len(remaining_words))
        
        estimate_panel = Panel(
            f"[green]Regular API Cost: ${estimates['regular_cost']:.2f}[/green]\n"
            f"[green]Batch API Cost: ${estimates['batch_cost']:.2f}[/green]\n"
            f"[yellow]Savings: ${estimates['savings']:.2f} (50% off)[/yellow]\n"
            f"[cyan]Estimated Tokens: {estimates['estimated_tokens']:,}[/cyan]",
            title="Cost Estimates",
            border_style="blue"
        )
        console.print(estimate_panel)
    
    if dry_run:
        console.print("\n[yellow]Dry run mode - exiting without processing[/yellow]")
        raise typer.Exit(0)
    
    if not remaining_words:
        console.print("\n[green]✅ All words have been processed![/green]")
        raise typer.Exit(0)
    
    # Confirm before proceeding
    if not typer.confirm("\n🚀 Proceed with batch synthesis?"):
        raise typer.Exit(0)
    
    # Run async processing
    asyncio.run(process_batch_async(remaining_words, state, batch_size))


async def process_batch_async(words: list[str], state: BatchSynthesisState, batch_size: int) -> None:
    """Async wrapper for batch processing with progress display."""
    
    # Create progress bars
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    
    with Live(progress, console=console, refresh_per_second=4) as live:
        # Add main progress task
        main_task = progress.add_task(
            "[cyan]Processing words...",
            total=len(words)
        )
        
        # Process in batches
        for i in range(0, len(words), batch_size):
            if SHUTDOWN_REQUESTED:
                break
            
            batch = words[i:i + batch_size]
            await process_word_batch(batch, state, progress, main_task)
            
            # Update live display with status table
            live.update(create_status_table(state, len(words)))
    
    # Final summary
    console.print("\n[green]✅ Batch synthesis complete![/green]")
    
    summary_table = create_status_table(state, len(words))
    console.print(summary_table)
    
    # Show failed words if any
    if state.failed_words:
        console.print(f"\n[red]❌ Failed words ({len(state.failed_words)}):[/red]")
        for word, error in list(state.failed_words.items())[:10]:
            console.print(f"  • {word}: {error}")
        if len(state.failed_words) > 10:
            console.print(f"  ... and {len(state.failed_words) - 10} more")


if __name__ == "__main__":
    app()