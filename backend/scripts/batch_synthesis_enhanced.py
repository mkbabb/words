#!/usr/bin/env python3
"""Enhanced batch synthesis script for processing entire word corpus with OpenAI Batch API."""

import asyncio
import json
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from rich.console import Console
from rich.layout import Layout
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
from rich.text import Text

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.floridify.ai.batch_processor import batch_synthesis
from src.floridify.ai.factory import get_openai_connector, get_definition_synthesizer
from src.floridify.core.lookup_pipeline import lookup_word_pipeline
from src.floridify.models import Language

console = Console()

# Cost constants (GPT-4o batch pricing as of Jan 2025)
BATCH_INPUT_COST_PER_1M = 1.50  # $1.50 per 1M input tokens
BATCH_OUTPUT_COST_PER_1M = 5.00  # $5.00 per 1M output tokens
ESTIMATED_TOKENS_PER_WORD = 12000  # After optimization
INPUT_OUTPUT_RATIO = 0.7  # 70% input, 30% output


@dataclass
class BatchMetrics:
    """Real-time batch processing metrics."""
    words_processed: int = 0
    words_successful: int = 0
    words_failed: int = 0
    total_words: int = 0
    
    tokens_used: int = 0
    current_cost: float = 0.0
    estimated_total_cost: float = 0.0
    
    start_time: datetime = field(default_factory=datetime.now)
    current_batch: int = 0
    total_batches: int = 0
    
    failed_words: List[Dict[str, str]] = field(default_factory=list)
    current_status: str = "Initializing"
    
    @property
    def success_rate(self) -> float:
        if self.words_processed == 0:
            return 100.0
        return (self.words_successful / self.words_processed) * 100
    
    @property
    def words_per_minute(self) -> float:
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        if elapsed > 0:
            return self.words_processed / elapsed
        return 0.0
    
    @property
    def estimated_time_remaining(self) -> Optional[timedelta]:
        if self.words_per_minute > 0 and self.words_processed < self.total_words:
            remaining = self.total_words - self.words_processed
            minutes = remaining / self.words_per_minute
            return timedelta(minutes=minutes)
        return None
    
    @property
    def cost_per_word(self) -> float:
        if self.words_processed > 0:
            return self.current_cost / self.words_processed
        return 0.0


@dataclass
class Checkpoint:
    """Checkpoint data for recovery."""
    processed_words: Set[str]
    failed_words: List[Dict[str, str]]
    metrics: BatchMetrics
    last_position: int
    timestamp: datetime


class EnhancedBatchProcessor:
    """Enhanced batch processor with checkpoint recovery and monitoring."""
    
    def __init__(
        self,
        words_file: Path,
        checkpoint_file: Path,
        batch_size: int = 50,
        max_concurrent_batches: int = 3,
        checkpoint_interval: int = 100,
    ) -> None:
        self.words_file = words_file
        self.checkpoint_file = checkpoint_file
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches
        self.checkpoint_interval = checkpoint_interval
        
        self.metrics = BatchMetrics()
        self.processed_words: Set[str] = set()
        self.shutdown_requested = False
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle graceful shutdown."""
        console.print("\n[yellow]Shutdown requested. Finishing current batch...[/yellow]")
        self.shutdown_requested = True
    
    async def load_checkpoint(self) -> Optional[int]:
        """Load checkpoint if exists."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, "r") as f:
                    data = json.load(f)
                
                self.processed_words = set(data["processed_words"])
                self.metrics.words_processed = len(self.processed_words)
                self.metrics.words_successful = data["metrics"]["words_successful"]
                self.metrics.words_failed = data["metrics"]["words_failed"]
                self.metrics.tokens_used = data["metrics"]["tokens_used"]
                self.metrics.current_cost = data["metrics"]["current_cost"]
                self.metrics.failed_words = data["failed_words"]
                
                console.print(
                    f"[green]Resumed from checkpoint: {len(self.processed_words)} words processed[/green]"
                )
                return data["last_position"]
            except Exception as e:
                console.print(f"[red]Failed to load checkpoint: {e}[/red]")
        return 0
    
    async def save_checkpoint(self, position: int) -> None:
        """Save current progress to checkpoint."""
        checkpoint_data = {
            "processed_words": list(self.processed_words),
            "failed_words": self.metrics.failed_words,
            "metrics": {
                "words_successful": self.metrics.words_successful,
                "words_failed": self.metrics.words_failed,
                "tokens_used": self.metrics.tokens_used,
                "current_cost": self.metrics.current_cost,
            },
            "last_position": position,
            "timestamp": datetime.now().isoformat(),
        }
        
        with open(self.checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f, indent=2)
    
    async def load_words(self) -> List[str]:
        """Load words from file, skipping already processed."""
        with open(self.words_file, "r") as f:
            all_words = [line.strip() for line in f if line.strip()]
        
        # Filter out already processed words
        words_to_process = [w for w in all_words if w not in self.processed_words]
        
        self.metrics.total_words = len(all_words)
        console.print(f"[cyan]Total words: {len(all_words):,}[/cyan]")
        console.print(f"[cyan]Already processed: {len(self.processed_words):,}[/cyan]")
        console.print(f"[cyan]To process: {len(words_to_process):,}[/cyan]")
        
        return words_to_process
    
    async def estimate_cost(self, num_words: int) -> float:
        """Estimate total cost for processing words."""
        total_tokens = num_words * ESTIMATED_TOKENS_PER_WORD
        input_tokens = total_tokens * INPUT_OUTPUT_RATIO
        output_tokens = total_tokens * (1 - INPUT_OUTPUT_RATIO)
        
        input_cost = (input_tokens / 1_000_000) * BATCH_INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * BATCH_OUTPUT_COST_PER_1M
        
        return input_cost + output_cost
    
    async def process_batch(self, words: List[str]) -> Dict[str, Any]:
        """Process a batch of words using the AI synthesis pipeline."""
        results = {"successful": [], "failed": []}
        
        # Initialize AI components
        ai_connector = get_openai_connector()
        synthesizer = get_definition_synthesizer()
        
        # Use batch synthesis context
        async with batch_synthesis(ai_connector) as batch:
            tasks = []
            
            for word in words:
                try:
                    # Run lookup pipeline to get word data
                    lookup_result = await lookup_word_pipeline(
                        word=word,
                        languages=[Language.ENGLISH],
                        force_refresh=False,
                    )
                    
                    if lookup_result and lookup_result.synthesized_entry:
                        # Skip if already synthesized
                        results["successful"].append(word)
                        continue
                    
                    # Synthesize using batch API
                    if lookup_result and lookup_result.combined_data:
                        task = synthesizer.synthesize_entry_batch(
                            word=word,
                            combined_data=lookup_result.combined_data,
                        )
                        tasks.append((word, task))
                
                except Exception as e:
                    results["failed"].append({
                        "word": word,
                        "error": str(e),
                    })
            
            # Wait for batch execution
            if tasks:
                for word, task in tasks:
                    try:
                        result = await task
                        results["successful"].append(word)
                    except Exception as e:
                        results["failed"].append({
                            "word": word,
                            "error": str(e),
                        })
        
        return results
    
    def create_layout(self) -> Layout:
        """Create the Rich layout for display."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress", size=12),
            Layout(name="metrics", size=8),
        )
        
        return layout
    
    def create_header(self) -> Panel:
        """Create header panel."""
        return Panel(
            Text("ENHANCED BATCH SYNTHESIS", style="bold bright_blue", justify="center"),
            style="bright_blue",
        )
    
    def create_progress_panel(self, progress: Progress) -> Panel:
        """Create progress panel."""
        return Panel(
            progress,
            title="[bold]Processing Progress[/bold]",
            border_style="blue",
        )
    
    def create_metrics_panel(self) -> Panel:
        """Create metrics panel."""
        # Cost metrics
        cost_table = Table(show_header=False, box=None, padding=(0, 1))
        cost_table.add_column("Metric", style="dim")
        cost_table.add_column("Value", justify="right")
        
        cost_color = "red" if self.metrics.current_cost > 100 else "green"
        cost_table.add_row("Current Cost:", f"[{cost_color}]${self.metrics.current_cost:.2f}[/{cost_color}]")
        cost_table.add_row("Est. Total Cost:", f"${self.metrics.estimated_total_cost:.2f}")
        cost_table.add_row("Cost per Word:", f"${self.metrics.cost_per_word:.4f}")
        
        # Performance metrics
        perf_table = Table(show_header=False, box=None, padding=(0, 1))
        perf_table.add_column("Metric", style="dim")
        perf_table.add_column("Value", justify="right")
        
        perf_table.add_row("Success Rate:", f"[green]{self.metrics.success_rate:.1f}%[/green]")
        perf_table.add_row("Words/min:", f"[cyan]{self.metrics.words_per_minute:.1f}[/cyan]")
        
        if self.metrics.estimated_time_remaining:
            eta = self.metrics.estimated_time_remaining
            hours = int(eta.total_seconds() // 3600)
            minutes = int((eta.total_seconds() % 3600) // 60)
            perf_table.add_row("ETA:", f"[yellow]{hours}h {minutes}m[/yellow]")
        else:
            perf_table.add_row("ETA:", "[dim]Calculating...[/dim]")
        
        # Status
        status_color = "green" if self.metrics.success_rate > 95 else "yellow"
        status_table = Table(show_header=False, box=None, padding=(0, 1))
        status_table.add_column("", style="dim")
        status_table.add_column("", justify="right")
        
        status_table.add_row("Status:", f"[{status_color}]{self.metrics.current_status}[/{status_color}]")
        status_table.add_row("Failed Words:", f"[red]{self.metrics.words_failed}[/red]")
        
        # Combine tables
        metrics_layout = Table(show_header=False, box=None)
        metrics_layout.add_column()
        metrics_layout.add_column()
        metrics_layout.add_column()
        
        metrics_layout.add_row(cost_table, perf_table, status_table)
        
        return Panel(
            metrics_layout,
            title="[bold]Metrics[/bold]",
            border_style="cyan",
        )
    
    async def run(self) -> None:
        """Run the batch processing with monitoring."""
        # Load checkpoint
        start_position = await self.load_checkpoint()
        
        # Load words
        words = await self.load_words()
        if not words:
            console.print("[green]All words already processed![/green]")
            return
        
        # Estimate costs
        self.metrics.estimated_total_cost = await self.estimate_cost(len(words))
        
        # Create layout
        layout = self.create_layout()
        
        # Progress tracking
        overall_progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )
        
        batch_progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        )
        
        # Create progress group
        progress_group = Panel(
            Layout(name="progress")
            .split_column(
                Layout(overall_progress, name="overall"),
                Layout(batch_progress, name="batch"),
            ),
            title="[bold]Progress[/bold]",
            border_style="blue",
        )
        
        # Add tasks
        overall_task = overall_progress.add_task(
            "[cyan]Overall Progress", total=len(words)
        )
        
        # Process in batches
        with Live(layout, console=console, refresh_per_second=4) as live:
            # Update layout
            layout["header"].update(self.create_header())
            layout["progress"].update(progress_group)
            
            # Process batches
            for i in range(0, len(words), self.batch_size):
                if self.shutdown_requested:
                    break
                
                # Get batch
                batch_words = words[i:i + self.batch_size]
                self.metrics.current_batch = i // self.batch_size + 1
                self.metrics.total_batches = (len(words) + self.batch_size - 1) // self.batch_size
                
                # Update status
                self.metrics.current_status = f"Processing batch {self.metrics.current_batch}/{self.metrics.total_batches}"
                
                # Add batch task
                batch_task = batch_progress.add_task(
                    f"[magenta]Batch {self.metrics.current_batch}", total=len(batch_words)
                )
                
                # Process batch
                results = await self.process_batch(batch_words)
                
                # Update metrics
                for word in results["successful"]:
                    self.processed_words.add(word)
                    self.metrics.words_processed += 1
                    self.metrics.words_successful += 1
                    overall_progress.update(overall_task, advance=1)
                    batch_progress.update(batch_task, advance=1)
                
                for failed in results["failed"]:
                    self.processed_words.add(failed["word"])
                    self.metrics.words_processed += 1
                    self.metrics.words_failed += 1
                    self.metrics.failed_words.append(failed)
                    overall_progress.update(overall_task, advance=1)
                    batch_progress.update(batch_task, advance=1)
                
                # Update cost estimate
                self.metrics.tokens_used += len(batch_words) * ESTIMATED_TOKENS_PER_WORD
                input_tokens = self.metrics.tokens_used * INPUT_OUTPUT_RATIO
                output_tokens = self.metrics.tokens_used * (1 - INPUT_OUTPUT_RATIO)
                
                self.metrics.current_cost = (
                    (input_tokens / 1_000_000) * BATCH_INPUT_COST_PER_1M +
                    (output_tokens / 1_000_000) * BATCH_OUTPUT_COST_PER_1M
                )
                
                # Update display
                layout["metrics"].update(self.create_metrics_panel())
                
                # Save checkpoint
                if self.metrics.words_processed % self.checkpoint_interval == 0:
                    await self.save_checkpoint(i + len(batch_words))
                
                # Remove batch task
                batch_progress.remove_task(batch_task)
                
                # Small delay between batches
                await asyncio.sleep(1)
        
        # Final checkpoint
        await self.save_checkpoint(len(words))
        
        # Display summary
        self.display_summary()
    
    def display_summary(self) -> None:
        """Display final summary."""
        summary = Table(title="Batch Processing Summary", show_header=True)
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="green", justify="right")
        
        summary.add_row("Total Words Processed", f"{self.metrics.words_processed:,}")
        summary.add_row("Successful", f"{self.metrics.words_successful:,}")
        summary.add_row("Failed", f"{self.metrics.words_failed:,}")
        summary.add_row("Success Rate", f"{self.metrics.success_rate:.1f}%")
        summary.add_row("Total Cost", f"${self.metrics.current_cost:.2f}")
        summary.add_row("Average Cost/Word", f"${self.metrics.cost_per_word:.4f}")
        
        elapsed = datetime.now() - self.metrics.start_time
        hours = int(elapsed.total_seconds() // 3600)
        minutes = int((elapsed.total_seconds() % 3600) // 60)
        summary.add_row("Total Time", f"{hours}h {minutes}m")
        summary.add_row("Processing Rate", f"{self.metrics.words_per_minute:.1f} words/min")
        
        console.print("\n", summary)
        
        if self.metrics.failed_words:
            console.print(f"\n[yellow]Failed words saved to checkpoint file[/yellow]")


async def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enhanced batch synthesis for word dictionary"
    )
    parser.add_argument(
        "words_file",
        type=Path,
        help="Path to file containing words to process",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of words per batch (default: 50)",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("batch_checkpoint.json"),
        help="Checkpoint file path (default: batch_checkpoint.json)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Maximum concurrent batches (default: 3)",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=100,
        help="Save checkpoint every N words (default: 100)",
    )
    
    args = parser.parse_args()
    
    # Verify words file exists
    if not args.words_file.exists():
        console.print(f"[red]Error: Words file not found: {args.words_file}[/red]")
        sys.exit(1)
    
    # Create processor
    processor = EnhancedBatchProcessor(
        words_file=args.words_file,
        checkpoint_file=args.checkpoint,
        batch_size=args.batch_size,
        max_concurrent_batches=args.max_concurrent,
        checkpoint_interval=args.checkpoint_interval,
    )
    
    # Run processing
    console.print("[bold cyan]Starting Enhanced Batch Synthesis[/bold cyan]")
    console.print(f"[dim]Press Ctrl+C for graceful shutdown[/dim]\n")
    
    try:
        await processor.run()
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise
    finally:
        console.print("\n[green]Batch processing complete![/green]")


if __name__ == "__main__":
    asyncio.run(main())