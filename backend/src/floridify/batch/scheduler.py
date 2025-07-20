"""Batch job scheduler for incremental dictionary index building."""

from __future__ import annotations

import asyncio
import json

# import schedule  # Optional dependency for scheduling
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from ..ai.connector import OpenAIConnector as AIConnector
from ..connectors.wiktionary import WiktionaryConnector
from ..search.core import SearchEngine
from ..storage.mongodb import MongoDBStorage as MongoDB
from .batch_processor import BatchJobConfig, BatchProcessor

console = Console()


class ScheduleFrequency(Enum):
    """Scheduling frequency options."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MANUAL = "manual"


@dataclass
class SchedulerConfig:
    """Configuration for batch job scheduler."""

    frequency: ScheduleFrequency = ScheduleFrequency.DAILY
    run_time: str = "02:00"  # 2 AM
    max_words_per_run: int = 10000
    max_cost_per_run: float = 50.0  # USD
    enable_auto_scaling: bool = True
    min_batch_size: int = 500
    max_batch_size: int = 2000
    state_file: Path = Path("./batch_scheduler_state.json")
    log_file: Path = Path("./batch_scheduler.log")


@dataclass
class SchedulerState:
    """Persistent state for the scheduler."""

    last_run: datetime | None = None
    total_words_processed: int = 0
    total_cost_incurred: float = 0.0
    successful_runs: int = 0
    failed_runs: int = 0
    current_word_offset: int = 0
    processing_errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.processing_errors is None:
            self.processing_errors = []


class BatchScheduler:
    """Schedules and manages batch processing jobs for incremental index building."""

    def __init__(
        self,
        config: SchedulerConfig,
        ai_connector: AIConnector,
        search_engine: SearchEngine,
        mongodb: MongoDB,
    ):
        self.config = config
        self.ai_connector = ai_connector
        self.search_engine = search_engine
        self.mongodb = mongodb

        # Load or initialize state
        self.state = self._load_state()

        # Setup logging
        self._setup_logging()

        # Track active processors
        self.active_processors: dict[str, BatchProcessor] = {}

        console.print("[blue]Batch Scheduler initialized[/blue]")

    def _load_state(self) -> SchedulerState:
        """Load scheduler state from disk."""
        if self.config.state_file.exists():
            try:
                with open(self.config.state_file) as f:
                    data = json.load(f)
                    # Convert datetime strings back to datetime objects
                    if data.get("last_run"):
                        data["last_run"] = datetime.fromisoformat(data["last_run"])
                    return SchedulerState(**data)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load state file: {e}[/yellow]")

        return SchedulerState()

    def _save_state(self) -> None:
        """Save scheduler state to disk."""
        try:
            # Convert datetime objects to strings for JSON serialization
            state_dict = asdict(self.state)
            if state_dict["last_run"] and self.state.last_run:
                state_dict["last_run"] = self.state.last_run.isoformat()

            self.config.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config.state_file, "w") as f:
                json.dump(state_dict, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving state: {e}[/red]")

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        self.config.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log message to file and console."""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} [{level}] {message}"

        # Write to log file
        try:
            with open(self.config.log_file, "a") as f:
                f.write(log_entry + "\n")
        except Exception:
            pass  # Don't fail if logging fails

        # Also print to console with appropriate color
        if level == "ERROR":
            console.print(f"[red]{log_entry}[/red]")
        elif level == "WARNING":
            console.print(f"[yellow]{log_entry}[/yellow]")
        else:
            console.print(f"[blue]{log_entry}[/blue]")

    def calculate_optimal_batch_size(self) -> int:
        """Calculate optimal batch size based on recent performance."""
        # Start with base configuration
        base_size = (self.config.min_batch_size + self.config.max_batch_size) // 2

        if not self.config.enable_auto_scaling:
            return base_size

        # Adjust based on recent success rate
        if self.state.successful_runs > self.state.failed_runs * 2:
            # High success rate - can increase batch size
            return min(self.config.max_batch_size, int(base_size * 1.2))
        elif self.state.failed_runs > self.state.successful_runs:
            # High failure rate - decrease batch size
            return max(self.config.min_batch_size, int(base_size * 0.8))

        return base_size

    def estimate_processing_cost(self, word_count: int) -> float:
        """Estimate cost for processing given number of words."""
        # Rough estimation based on OpenAI Batch API pricing
        # Assumes: 2 requests per word (cluster + synthesis), ~500 tokens per request
        estimated_tokens = word_count * 2 * 500

        # GPT-4o-mini batch pricing: $0.075 per 1M input tokens, $0.300 per 1M output tokens
        # Assume 70% input, 30% output tokens
        input_tokens = estimated_tokens * 0.7
        output_tokens = estimated_tokens * 0.3

        input_cost = (input_tokens / 1_000_000) * 0.075
        output_cost = (output_tokens / 1_000_000) * 0.300

        return input_cost + output_cost

    def should_run_processing(self) -> tuple[bool, str]:
        """Determine if processing should run based on various criteria."""
        now = datetime.now()

        # Check if enough time has passed since last run
        if self.state.last_run:
            time_since_last = now - self.state.last_run

            if self.config.frequency == ScheduleFrequency.HOURLY:
                min_interval = timedelta(hours=1)
            elif self.config.frequency == ScheduleFrequency.DAILY:
                min_interval = timedelta(days=1)
            elif self.config.frequency == ScheduleFrequency.WEEKLY:
                min_interval = timedelta(weeks=1)
            else:  # MANUAL
                return False, "Manual mode - run explicitly"

            if time_since_last < min_interval:
                return False, f"Too soon since last run ({time_since_last})"

        # Check if we're within cost limits
        if self.state.total_cost_incurred >= self.config.max_cost_per_run:
            return False, f"Cost limit reached (${self.state.total_cost_incurred:.2f})"

        # Check if there are words to process
        # This would require checking the search engine for unprocessed words

        return True, "Ready to process"

    async def run_batch_processing(self, word_limit: int | None = None) -> dict[str, Any]:
        """Run a single batch processing session."""
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._log(f"Starting batch processing run: {run_id}")

        try:
            # Calculate processing parameters
            if word_limit is None:
                word_limit = self.config.max_words_per_run

            batch_size = self.calculate_optimal_batch_size()
            estimated_cost = self.estimate_processing_cost(word_limit)

            self._log(
                f"Processing parameters: {word_limit} words, batch size {batch_size}, estimated cost ${estimated_cost:.2f}"
            )

            # Check cost limit
            if estimated_cost > self.config.max_cost_per_run:
                word_limit = int(word_limit * (self.config.max_cost_per_run / estimated_cost))
                estimated_cost = self.estimate_processing_cost(word_limit)
                self._log(f"Reduced word limit to {word_limit} to stay within cost limit")

            # Create batch processor configuration
            batch_config = BatchJobConfig(
                batch_size=batch_size,
                max_concurrent_batches=3,  # Conservative for overnight processing
                output_directory=Path("./batch_output") / run_id,
                filter_preset="moderate",
                providers=[WiktionaryConnector()],
                force_refresh=False,
                enable_clustering=True,
                enable_synthesis=True,
            )

            # Create and run batch processor
            processor = BatchProcessor(
                config=batch_config,
                ai_connector=self.ai_connector,
                search_engine=self.search_engine,
                mongodb=self.mongodb,
            )

            self.active_processors[run_id] = processor

            # Run processing
            result = await processor.run_batch_processing(word_limit)

            # Update state
            self.state.last_run = datetime.now()

            if result["status"] == "completed":
                self.state.successful_runs += 1
                self.state.total_words_processed += result.get("total_words_processed", 0)

                # Update cost (use actual cost if available, otherwise estimate)
                actual_cost = result.get("actual_cost", estimated_cost)
                self.state.total_cost_incurred += actual_cost

                self._log(
                    f"Batch processing completed successfully: {result['total_words_processed']} words processed"
                )
            else:
                self.state.failed_runs += 1
                error_msg = result.get("error", "Unknown error")
                if self.state.processing_errors is not None:
                    self.state.processing_errors.append(
                        f"{datetime.now().isoformat()}: {error_msg}"
                    )

                    # Keep only last 10 errors
                    self.state.processing_errors = self.state.processing_errors[-10:]

                self._log(f"Batch processing failed: {error_msg}", "ERROR")

            # Save state
            self._save_state()

            # Cleanup
            del self.active_processors[run_id]

            return result

        except Exception as e:
            self.state.failed_runs += 1
            if self.state.processing_errors is not None:
                self.state.processing_errors.append(f"{datetime.now().isoformat()}: {str(e)}")
            self._log(f"Batch processing exception: {e}", "ERROR")
            self._save_state()

            if run_id in self.active_processors:
                del self.active_processors[run_id]

            return {"status": "failed", "error": str(e)}

    def setup_schedule(self) -> None:
        """Setup the processing schedule."""
        if self.config.frequency == ScheduleFrequency.MANUAL:
            self._log("Manual mode - no automatic scheduling")
            return

        # For now, just log scheduling setup - actual scheduling would require schedule library
        self._log(f"Scheduling setup: {self.config.frequency.value} at {self.config.run_time}")

        # TODO: Implement actual scheduling when schedule library is available
        # Clear any existing schedules
        # schedule.clear()
        #
        # if self.config.frequency == ScheduleFrequency.HOURLY:
        #     schedule.every().hour.at(":00").do(self._scheduled_run)
        #     self._log("Scheduled hourly processing")
        # elif self.config.frequency == ScheduleFrequency.DAILY:
        #     schedule.every().day.at(self.config.run_time).do(self._scheduled_run)
        #     self._log(f"Scheduled daily processing at {self.config.run_time}")
        # elif self.config.frequency == ScheduleFrequency.WEEKLY:
        #     # Run on Sunday by default
        #     schedule.every().sunday.at(self.config.run_time).do(self._scheduled_run)
        #     self._log(f"Scheduled weekly processing on Sunday at {self.config.run_time}")

    def _scheduled_run(self) -> None:
        """Wrapper for scheduled execution."""
        should_run, reason = self.should_run_processing()

        if should_run:
            self._log("Starting scheduled batch processing")
            # Run in async context
            asyncio.create_task(self.run_batch_processing())
        else:
            self._log(f"Skipping scheduled run: {reason}")

    async def start_scheduler(self) -> None:
        """Start the scheduler daemon."""
        self._log("Starting batch processing scheduler")
        self.setup_schedule()

        # Simple scheduler loop - would be enhanced with actual schedule library
        while True:
            # schedule.run_pending()  # Would use schedule library
            await asyncio.sleep(60)  # Check every minute

    def get_status_report(self) -> dict[str, Any]:
        """Get current scheduler status."""
        should_run, reason = self.should_run_processing()

        status = {
            "scheduler_config": {
                "frequency": self.config.frequency.value,
                "run_time": self.config.run_time,
                "max_words_per_run": self.config.max_words_per_run,
                "max_cost_per_run": self.config.max_cost_per_run,
            },
            "state": {
                "last_run": self.state.last_run.isoformat() if self.state.last_run else None,
                "total_words_processed": self.state.total_words_processed,
                "total_cost_incurred": self.state.total_cost_incurred,
                "successful_runs": self.state.successful_runs,
                "failed_runs": self.state.failed_runs,
                "success_rate": (
                    self.state.successful_runs
                    / max(1, self.state.successful_runs + self.state.failed_runs)
                )
                * 100,
            },
            "current_status": {
                "should_run": should_run,
                "reason": reason,
                "active_processors": len(self.active_processors),
                "optimal_batch_size": self.calculate_optimal_batch_size(),
            },
            "recent_errors": self.state.processing_errors[-5:]
            if self.state.processing_errors
            else [],
        }

        return status

    def display_status(self) -> None:
        """Display scheduler status in a formatted table."""
        status = self.get_status_report()

        console.print("\n[bold blue]Batch Scheduler Status[/bold blue]")

        # Configuration table
        config_table = Table(title="Configuration")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="yellow")

        for key, value in status["scheduler_config"].items():
            config_table.add_row(key.replace("_", " ").title(), str(value))

        console.print(config_table)

        # State table
        state_table = Table(title="Processing State")
        state_table.add_column("Metric", style="cyan")
        state_table.add_column("Value", style="yellow")

        state = status["state"]
        state_table.add_row("Last Run", state["last_run"] or "Never")
        state_table.add_row("Words Processed", f"{state['total_words_processed']:,}")
        state_table.add_row("Cost Incurred", f"${state['total_cost_incurred']:.2f}")
        state_table.add_row("Successful Runs", str(state["successful_runs"]))
        state_table.add_row("Failed Runs", str(state["failed_runs"]))
        state_table.add_row("Success Rate", f"{state['success_rate']:.1f}%")

        console.print(state_table)

        # Current status
        current = status["current_status"]
        console.print(f"\n[green]Ready to run:[/green] {current['should_run']}")
        console.print(f"[blue]Reason:[/blue] {current['reason']}")
        console.print(f"[blue]Active processors:[/blue] {current['active_processors']}")
        console.print(f"[blue]Optimal batch size:[/blue] {current['optimal_batch_size']}")

        # Recent errors
        if status["recent_errors"]:
            console.print("\n[red]Recent Errors:[/red]")
            for error in status["recent_errors"]:
                console.print(f"  - {error}")

    async def manual_run(self, word_limit: int | None = None) -> dict[str, Any]:
        """Manually trigger a batch processing run."""
        self._log(f"Manual batch processing triggered (limit: {word_limit})")
        return await self.run_batch_processing(word_limit)

    def reset_state(self) -> None:
        """Reset scheduler state (use with caution)."""
        console.print("[yellow]Resetting scheduler state...[/yellow]")
        self.state = SchedulerState()
        self._save_state()
        self._log("Scheduler state reset", "WARNING")
