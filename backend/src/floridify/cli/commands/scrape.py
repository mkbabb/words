"""
CLI command for bulk scraping dictionary providers.

Provides a rich, interactive interface for systematically scraping entire language corpora
with progress monitoring, resume functionality, and beautiful visualizations.
"""

from __future__ import annotations

import asyncio
import signal
from typing import Any

import click
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

from ...connectors.batch.bulk_scraper import (
    BulkScraper,
    BulkScrapingConfig,
    bulk_scrape_wiktionary_wholesale,
)
from ...models.definition import DictionaryProvider, Language
from ...utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


class BulkScrapingInterface:
    """Rich interface for bulk scraping operations."""
    
    def __init__(self, scraper: BulkScraper | None = None):
        """Initialize the interface.
        
        Args:
            scraper: Optional scraper instance for monitoring
        """
        self.scraper = scraper
        self.should_stop = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Create progress tracker
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green", finished_style="bold green"),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=True,
        )
        
        # Layout for rich display
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=8),
        )
        self.layout["main"].split_row(
            Layout(name="progress", ratio=2),
            Layout(name="stats", ratio=1),
        )
    
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        console.print(f"\n[yellow]Received signal {signum}, stopping gracefully...[/yellow]")
        self.should_stop = True
        if self.scraper:
            self.scraper.stop()
    
    def create_header_panel(self, config: BulkScrapingConfig) -> Panel:
        """Create header panel with session information."""
        header_text = Text()
        header_text.append("Floridify Bulk Scraper", style="bold magenta")
        header_text.append(f" • {config.provider.display_name}", style="bold blue")
        header_text.append(f" • {config.language.value.title()}", style="bold green")
        
        return Panel(
            header_text,
            title="[bold white]Bulk Dictionary Scraping[/bold white]",
            border_style="blue",
        )
    
    def create_stats_panel(self, progress_data: Any) -> Panel:
        """Create statistics panel."""
        stats_table = Table(show_header=False, box=None, padding=(0, 1))
        stats_table.add_column("Metric", style="bold white")
        stats_table.add_column("Value", justify="right")
        
        # Success rate with color coding
        success_rate = progress_data.success_rate
        rate_color = "green" if success_rate > 0.8 else "yellow" if success_rate > 0.5 else "red"
        
        # Speed with color coding
        speed = progress_data.words_per_second
        speed_color = "green" if speed > 1.0 else "yellow" if speed > 0.5 else "red"
        
        stats_table.add_row("Total Words", f"{progress_data.total_words:,}")
        stats_table.add_row("Processed", f"{progress_data.processed_words:,}")
        stats_table.add_row("Successful", f"[green]{progress_data.successful_words:,}[/green]")
        stats_table.add_row("Failed", f"[red]{progress_data.failed_words:,}[/red]")
        stats_table.add_row("Skipped", f"[yellow]{progress_data.skipped_words:,}[/yellow]")
        stats_table.add_row("", "")  # Spacer
        stats_table.add_row("Success Rate", f"[{rate_color}]{success_rate:.1%}[/{rate_color}]")
        stats_table.add_row("Speed", f"[{speed_color}]{speed:.2f}[/{speed_color}] words/sec")
        stats_table.add_row("Batch", f"{progress_data.current_batch}")
        
        if progress_data.consecutive_errors > 0:
            error_color = "red" if progress_data.consecutive_errors > 5 else "yellow"
            stats_table.add_row(
                "Consecutive Errors", 
                f"[{error_color}]{progress_data.consecutive_errors}[/{error_color}]"
            )
        
        return Panel(
            stats_table,
            title="[bold white]Statistics[/bold white]",
            border_style="cyan",
        )
    
    def create_footer_panel(self, progress_data: Any) -> Panel:
        """Create footer panel with recent activity."""
        footer_lines = []
        
        # Current status
        if progress_data.current_word:
            footer_lines.append(f"[bold blue]Current:[/bold blue] {progress_data.current_word}")
        
        # Recent errors (last 3)
        if progress_data.error_messages:
            footer_lines.append("")
            footer_lines.append("[bold red]Recent Errors:[/bold red]")
            for error in progress_data.error_messages[-3:]:
                # Truncate long error messages
                error_text = error if len(error) <= 80 else error[:77] + "..."
                footer_lines.append(f"[red]  • {error_text}[/red]")
        
        # Session info
        footer_lines.append("")
        footer_lines.append(f"[dim]Session ID: {progress_data.session_id}[/dim]")
        
        footer_text = "\n".join(footer_lines) if footer_lines else "[dim]No recent activity[/dim]"
        
        return Panel(
            footer_text,
            title="[bold white]Activity Log[/bold white]",
            border_style="yellow",
        )
    
    async def run_with_monitoring(self, scraper: BulkScraper) -> Any:
        """Run scraper with rich monitoring interface."""
        self.scraper = scraper
        config = scraper.config
        
        with Live(self.layout, refresh_per_second=2, screen=True) as live:
            # Create progress task
            task_id = self.progress.add_task(
                f"Scraping {config.provider.display_name}",
                total=scraper.progress.total_words
            )
            
            # Start scraping in background
            scraping_task = asyncio.create_task(scraper.start_scraping())
            
            # Monitor progress
            while not scraping_task.done():
                if self.should_stop:
                    scraper.stop()
                    break
                
                # Get current progress
                progress_data = scraper.get_progress()
                
                # Update progress bar
                self.progress.update(
                    task_id,
                    completed=progress_data.processed_words,
                    total=progress_data.total_words,
                )
                
                # Update layout
                self.layout["header"].update(self.create_header_panel(config))
                self.layout["progress"].update(Panel(
                    self.progress,
                    title="[bold white]Progress[/bold white]",
                    border_style="green",
                ))
                self.layout["stats"].update(self.create_stats_panel(progress_data))
                self.layout["footer"].update(self.create_footer_panel(progress_data))
                
                # Update display
                live.refresh()
                
                # Small delay to prevent excessive updates
                await asyncio.sleep(0.5)
            
            # Wait for scraping to complete
            try:
                final_progress = await scraping_task
            except asyncio.CancelledError:
                console.print("\n[yellow]Scraping cancelled by user[/yellow]")
                final_progress = scraper.get_progress()
            
            # Final update
            progress_data = final_progress
            self.progress.update(
                task_id,
                completed=progress_data.processed_words,
                total=progress_data.total_words,
            )
            
            # Update layout one final time
            self.layout["header"].update(self.create_header_panel(config))
            self.layout["progress"].update(Panel(
                self.progress,
                title="[bold white]Progress - COMPLETED[/bold white]",
                border_style="green",
            ))
            self.layout["stats"].update(self.create_stats_panel(progress_data))
            self.layout["footer"].update(self.create_footer_panel(progress_data))
            
            live.refresh()
            
            # Show completion message
            await asyncio.sleep(2)  # Keep display visible for 2 seconds
            
        return final_progress


# CLI Commands

@click.group(name="scrape")
def scrape_group():
    """Scraping commands for systematic provider data collection."""
    pass


@scrape_group.command(name="wordhippo")
@click.option("--language", "-l", 
              type=click.Choice([lang.value for lang in Language]), 
              default=Language.ENGLISH.value,
              help="Language to scrape")
@click.option("--batch-size", "-b", default=100, help="Words per batch")
@click.option("--max-concurrent", "-c", default=5, help="Maximum concurrent operations")
@click.option("--resume-from", "-r", help="Word to resume scraping from")
@click.option("--force-refresh", is_flag=True, help="Force refresh existing data")
@click.option("--skip-existing/--include-existing", default=True, 
              help="Skip words that already have data")
def scrape_wordhippo(
    language: str,
    batch_size: int,
    max_concurrent: int,
    resume_from: str | None,
    force_refresh: bool,
    skip_existing: bool,
):
    """Bulk scrape WordHippo for comprehensive synonym/antonym/example data."""
    async def _run():
        language_enum = Language(language)
        
        console.print(f"\n[bold green]Starting WordHippo bulk scraping for {language_enum.value.title()}[/bold green]")
        console.print(f"[dim]Batch size: {batch_size}, Max concurrent: {max_concurrent}[/dim]")
        
        if resume_from:
            console.print(f"[yellow]Resuming from word: {resume_from}[/yellow]")
        
        config = BulkScrapingConfig(
            provider=DictionaryProvider.WORDHIPPO,
            language=language_enum,
            batch_size=batch_size,
            max_concurrent=max_concurrent,
            resume_from_word=resume_from,
            force_refresh=force_refresh,
            skip_existing=skip_existing,
        )
        
        from ...connectors.scraper.wordhippo import WordHippoConnector
        connector = WordHippoConnector()
        scraper = BulkScraper(connector, config)
        
        interface = BulkScrapingInterface()
        
        try:
            progress = await interface.run_with_monitoring(scraper)
            
            # Show final results
            console.print("\n[bold green]✅ WordHippo bulk scraping completed![/bold green]")
            console.print(f"[green]Processed: {progress.processed_words:,} words[/green]")
            console.print(f"[green]Success rate: {progress.success_rate:.1%}[/green]")
            console.print(f"[green]Average speed: {progress.words_per_second:.2f} words/sec[/green]")
            
        except Exception as e:
            console.print(f"\n[bold red]❌ Scraping failed: {e}[/bold red]")
        finally:
            await connector.close()
    
    asyncio.run(_run())


@scrape_group.command(name="dictionary-com")
@click.option("--language", "-l", 
              type=click.Choice([lang.value for lang in Language]), 
              default=Language.ENGLISH.value,
              help="Language to scrape")
@click.option("--batch-size", "-b", default=100, help="Words per batch")
@click.option("--max-concurrent", "-c", default=5, help="Maximum concurrent operations")
@click.option("--resume-from", "-r", help="Word to resume scraping from")
@click.option("--force-refresh", is_flag=True, help="Force refresh existing data")
@click.option("--skip-existing/--include-existing", default=True, 
              help="Skip words that already have data")
def scrape_dictionary_com(
    language: str,
    batch_size: int,
    max_concurrent: int,
    resume_from: str | None,
    force_refresh: bool,
    skip_existing: bool,
):
    """Bulk scrape Dictionary.com with thesaurus.com integration."""
    async def _run():
        language_enum = Language(language)
        
        console.print(f"\n[bold green]Starting Dictionary.com + Thesaurus.com bulk scraping for {language_enum.value.title()}[/bold green]")
        
        config = BulkScrapingConfig(
            provider=DictionaryProvider.DICTIONARY_COM,
            language=language_enum,
            batch_size=batch_size,
            max_concurrent=max_concurrent,
            resume_from_word=resume_from,
            force_refresh=force_refresh,
            skip_existing=skip_existing,
        )
        
        from ...connectors.scraper.dictionary_com import DictionaryComConnector
        connector = DictionaryComConnector()
        scraper = BulkScraper(connector, config)
        
        interface = BulkScrapingInterface()
        
        try:
            progress = await interface.run_with_monitoring(scraper)
            
            console.print("\n[bold green]✅ Dictionary.com bulk scraping completed![/bold green]")
            console.print(f"[green]Processed: {progress.processed_words:,} words[/green]")
            console.print(f"[green]Success rate: {progress.success_rate:.1%}[/green]")
            
        except Exception as e:
            console.print(f"\n[bold red]❌ Scraping failed: {e}[/bold red]")
        finally:
            await connector.close()
    
    asyncio.run(_run())


@scrape_group.command(name="wiktionary-wholesale")
@click.option("--language", "-l", 
              type=click.Choice([lang.value for lang in Language]), 
              default=Language.ENGLISH.value,
              help="Language to download")
@click.option("--download-all", is_flag=True, 
              help="Download complete Wiktionary dump instead of vocabulary-based scraping")
def scrape_wiktionary_wholesale(language: str, download_all: bool):
    """Download and process complete Wiktionary dumps."""
    async def _run():
        language_enum = Language(language)
        
        if download_all:
            console.print(f"\n[bold green]Starting Wiktionary wholesale download for {language_enum.value.title()}[/bold green]")
            console.print("[yellow]This will download the complete Wiktionary dump (several GB)[/yellow]")
            
            if not click.confirm("Continue with wholesale download?"):
                return
            
            progress = await bulk_scrape_wiktionary_wholesale(
                language=language_enum,
                download_all=True
            )
            
            console.print("\n[bold green]✅ Wiktionary wholesale download completed![/bold green]")
            console.print(f"[green]Processed: {progress.processed_words:,} entries[/green]")
        else:
            console.print(f"\n[bold green]Starting Wiktionary vocabulary-based scraping for {language_enum.value.title()}[/bold green]")
            
            config = BulkScrapingConfig(
                provider=DictionaryProvider.WIKTIONARY,
                language=language_enum,
                batch_size=50,  # Smaller batches for API-based scraping
                max_concurrent=3,  # Lower concurrency for respectful API usage
            )
            
            from ...connectors.wholesale.wiktionary_wholesale import WiktionaryWholesaleConnector
            connector = WiktionaryWholesaleConnector(language=language_enum)
            scraper = BulkScraper(connector, config)
            
            interface = BulkScrapingInterface()
            progress = await interface.run_with_monitoring(scraper)
            
            console.print("\n[bold green]✅ Wiktionary scraping completed![/bold green]")
            console.print(f"[green]Processed: {progress.processed_words:,} words[/green]")
    
    asyncio.run(_run())


@scrape_group.command(name="status")
def show_status():
    """Show current bulk scraping status and statistics."""
    # This could be extended to show active sessions, database statistics, etc.
    console.print("[bold blue]Bulk Scraping Status[/bold blue]")
    console.print("[yellow]Feature coming soon - will show active sessions and database statistics[/yellow]")