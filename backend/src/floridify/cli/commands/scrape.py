"""CLI command for bulk scraping dictionary providers.

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

from ...models.dictionary import DictionaryProvider, Language
from ...providers.scrape import (
    BulkScraper,
    BulkScrapingConfig,
    cleanup_old_sessions,
    delete_session,
    get_session,
    list_sessions,
    resume_session,
)
from ...utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


class BulkScrapingInterface:
    """Rich interface for bulk scraping operations."""

    def __init__(self, scraper: Any | None = None):
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
        console.print(f"\\n[yellow]Received signal {signum}, stopping gracefully...[/yellow]")
        self.should_stop = True
        if self.scraper:
            self.scraper.stop()

    def create_header_panel(self, config: Any) -> Panel:
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
                f"[{error_color}]{progress_data.consecutive_errors}[/{error_color}]",
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

        footer_text = "\\n".join(footer_lines) if footer_lines else "[dim]No recent activity[/dim]"

        return Panel(
            footer_text,
            title="[bold white]Activity Log[/bold white]",
            border_style="yellow",
        )

    async def run_with_monitoring(self, scraper: Any) -> Any:
        """Run scraper with rich monitoring interface."""
        self.scraper = scraper
        config = scraper.config

        with Live(self.layout, refresh_per_second=2, screen=True) as live:
            # Create progress task
            task_id = self.progress.add_task(
                f"Scraping {config.provider.display_name}",
                total=scraper.progress.total_words,
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
                self.layout["progress"].update(
                    Panel(
                        self.progress,
                        title="[bold white]Progress[/bold white]",
                        border_style="green",
                    )
                )
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
                console.print("\\n[yellow]Scraping cancelled by user[/yellow]")
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
            self.layout["progress"].update(
                Panel(
                    self.progress,
                    title="[bold white]Progress - COMPLETED[/bold white]",
                    border_style="green",
                )
            )
            self.layout["stats"].update(self.create_stats_panel(progress_data))
            self.layout["footer"].update(self.create_footer_panel(progress_data))

            live.refresh()

            # Show completion message
            await asyncio.sleep(2)  # Keep display visible for 2 seconds

        return final_progress


# Generic scraping function - DRY principle
async def run_scraping_session(
    provider: DictionaryProvider,
    language: str,
    batch_size: int,
    max_concurrent: int,
    resume_session_id: str | None,
    session_name: str | None,
    force_refresh: bool,
    skip_existing: bool,
) -> None:
    """Generic scraping function used by all provider commands."""
    language_enum = Language(language)

    console.print(
        f"\\n[bold green]Starting {provider.display_name} bulk scraping for {language_enum.value.title()}[/bold green]"
    )
    console.print(f"[dim]Batch size: {batch_size}, Max concurrent: {max_concurrent}[/dim]")

    # Handle session resumption
    if resume_session_id:
        console.print(
            f"[yellow]Resuming {provider.display_name} scraping session: {resume_session_id}[/yellow]"
        )
        result = await resume_session(resume_session_id)
        if not result:
            console.print(f"[red]Error:[/red] Could not resume session {resume_session_id}")
            return
        scraper, session = result
        console.print(
            f"[green]Resumed session:[/green] {session.get_progress_percentage():.1f}% complete"
        )
    else:
        # Create new session
        config = BulkScrapingConfig(
            provider=provider,
            language=language_enum,
            batch_size=batch_size,
            max_concurrent=max_concurrent,
            force_refresh=force_refresh,
            skip_existing=skip_existing,
        )

        scraper = BulkScraper(provider, config)

        # Set session name if provided
        if session_name:
            scraper.session.session_name = session_name
            await scraper.session.save()
            console.print(f"[blue]Session name:[/blue] {session_name}")

        console.print(f"[blue]Session ID:[/blue] {scraper.session.session_id[:8]}")

    interface = BulkScrapingInterface()

    try:
        progress = await interface.run_with_monitoring(scraper)

        console.print(
            f"\\n[bold green]✅ {provider.display_name} bulk scraping completed![/bold green]"
        )
        console.print(f"[green]Processed: {progress.processed_words:,} words[/green]")
        console.print(f"[green]Success rate: {progress.success_rate:.1%}[/green]")
        console.print(f"[green]Average speed: {progress.words_per_second:.2f} words/sec[/green]")

    except Exception as e:
        console.print(f"\\n[bold red]❌ Scraping failed: {e}[/bold red]")


# Generic click options decorator - DRY principle
def scraper_options(default_concurrent: int = 5):
    """Decorator with common scraper options."""

    def decorator(func):
        func = click.option(
            "--language",
            "-l",
            type=click.Choice([lang.value for lang in Language]),
            default=Language.ENGLISH.value,
            help="Language to scrape",
        )(func)
        func = click.option("--batch-size", "-b", default=100, help="Words per batch")(func)
        func = click.option(
            "--max-concurrent",
            "-c",
            default=default_concurrent,
            help="Maximum concurrent operations",
        )(func)
        func = click.option("--resume-session", "-r", help="Resume from existing session ID")(func)
        func = click.option("--session-name", "-n", help="Name for this scraping session")(func)
        func = click.option("--force-refresh", is_flag=True, help="Force refresh existing data")(
            func
        )
        func = click.option(
            "--skip-existing/--include-existing",
            default=True,
            help="Skip words that already have data",
        )(func)
        return func

    return decorator


# CLI Commands - DRY with minimal duplication


@click.group(name="scrape")
def scrape_group():
    """Scraping commands for systematic provider data collection."""


@scrape_group.command(name="wordhippo")
@scraper_options(default_concurrent=5)
def scrape_wordhippo(
    language, batch_size, max_concurrent, resume_session, session_name, force_refresh, skip_existing
):
    """Bulk scrape WordHippo for comprehensive synonym/antonym/example data."""
    asyncio.run(
        run_scraping_session(
            DictionaryProvider.WORDHIPPO,
            language,
            batch_size,
            max_concurrent,
            resume_session,
            session_name,
            force_refresh,
            skip_existing,
        )
    )


@scrape_group.command(name="oxford")
@scraper_options(default_concurrent=3)
def scrape_oxford(
    language, batch_size, max_concurrent, resume_session, session_name, force_refresh, skip_existing
):
    """Bulk scrape Oxford Dictionary API for comprehensive definitions."""
    asyncio.run(
        run_scraping_session(
            DictionaryProvider.OXFORD,
            language,
            batch_size,
            max_concurrent,
            resume_session,
            session_name,
            force_refresh,
            skip_existing,
        )
    )


@scrape_group.command(name="merriam-webster")
@scraper_options(default_concurrent=3)
def scrape_merriam_webster(
    language, batch_size, max_concurrent, resume_session, session_name, force_refresh, skip_existing
):
    """Bulk scrape Merriam-Webster Dictionary API."""
    asyncio.run(
        run_scraping_session(
            DictionaryProvider.MERRIAM_WEBSTER,
            language,
            batch_size,
            max_concurrent,
            resume_session,
            session_name,
            force_refresh,
            skip_existing,
        )
    )


@scrape_group.command(name="free-dictionary")
@scraper_options(default_concurrent=5)
def scrape_free_dictionary(
    language, batch_size, max_concurrent, resume_session, session_name, force_refresh, skip_existing
):
    """Bulk scrape FreeDictionary API for comprehensive definitions."""
    asyncio.run(
        run_scraping_session(
            DictionaryProvider.FREE_DICTIONARY,
            language,
            batch_size,
            max_concurrent,
            resume_session,
            session_name,
            force_refresh,
            skip_existing,
        )
    )


@scrape_group.command(name="apple-dictionary")
@scraper_options(default_concurrent=5)
def scrape_apple_dictionary(
    language, batch_size, max_concurrent, resume_session, session_name, force_refresh, skip_existing
):
    """Bulk scrape Apple Dictionary (macOS) for local definitions."""
    asyncio.run(
        run_scraping_session(
            DictionaryProvider.APPLE_DICTIONARY,
            language,
            batch_size,
            max_concurrent,
            resume_session,
            session_name,
            force_refresh,
            skip_existing,
        )
    )


@scrape_group.command(name="wiktionary-wholesale")
@click.option(
    "--language",
    "-l",
    type=click.Choice([lang.value for lang in Language]),
    default=Language.ENGLISH.value,
    help="Language to download",
)
@click.option(
    "--download-all",
    is_flag=True,
    help="Download complete Wiktionary dump instead of vocabulary-based scraping",
)
def scrape_wiktionary_wholesale(language: str, download_all: bool):
    """Download and process complete Wiktionary dumps."""

    async def _run():
        language_enum = Language(language)

        if download_all:
            console.print(
                f"\\n[bold green]Starting Wiktionary wholesale download for {language_enum.value.title()}[/bold green]"
            )
            console.print(
                "[yellow]This will download the complete Wiktionary dump (several GB)[/yellow]"
            )

            if not click.confirm("Continue with wholesale download?"):
                return

            progress = await scrape_wiktionary_wholesale(
                language=language_enum,
                download_all=True,
            )

            console.print("\\n[bold green]✅ Wiktionary wholesale download completed![/bold green]")
            console.print(f"[green]Processed: {progress.processed_words:,} entries[/green]")
        else:
            console.print(
                f"\\n[bold green]Starting Wiktionary vocabulary-based scraping for {language_enum.value.title()}[/bold green]"
            )

            await run_scraping_session(
                DictionaryProvider.WIKTIONARY,
                language,
                50,
                3,
                None,
                None,
                False,
                True,
            )

    asyncio.run(_run())


# Session Management Commands


@scrape_group.command(name="sessions")
def list_sessions_cmd():
    """List all scraping sessions."""

    async def _run():
        sessions = await list_sessions()

        if not sessions:
            console.print("[yellow]No scraping sessions found.[/yellow]")
            return

        table = Table(title="Scraping Sessions")
        table.add_column("Session ID", style="cyan")
        table.add_column("Name", style="blue")
        table.add_column("Provider", style="green")
        table.add_column("Language", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("Progress", justify="right")
        table.add_column("Success Rate", justify="right")
        table.add_column("Created", style="dim")

        for session in sessions:
            session_id = session["session_id"][:8]
            name = session["session_name"] or "[dim]unnamed[/dim]"
            provider = session["provider"]
            language = session["language"]
            status = session["status"]
            progress = f"{session['progress_percentage']:.1f}%"
            success_rate = f"{session['success_rate']:.1%}" if session["success_rate"] > 0 else "—"
            created = session["created_at"][:10]  # Just date part

            # Color-code status
            if status == "completed":
                status = f"[green]{status}[/green]"
            elif status == "running":
                status = f"[yellow]{status}[/yellow]"
            elif status == "failed":
                status = f"[red]{status}[/red]"

            table.add_row(
                session_id, name, provider, language, status, progress, success_rate, created
            )

        console.print(table)
        console.print(f"\\n[dim]Total sessions: {len(sessions)}[/dim]")
        console.print("[dim]Use 'floridify scrape resume <session_id>' to continue a session[/dim]")

    asyncio.run(_run())


@scrape_group.command(name="resume")
@click.argument("session_id")
def resume_session_cmd(session_id: str) -> None:
    """Resume a scraping session by ID."""

    async def _run():
        console.print(f"\\n[bold yellow]Resuming scraping session: {session_id}[/bold yellow]")

        result = await resume_session(session_id)
        if not result:
            console.print(f"[red]Error:[/red] Could not resume session {session_id}")
            console.print("Use 'floridify scrape sessions' to list available sessions")
            return

        scraper, session = result
        console.print(
            f"[green]Resumed session:[/green] {session.get_progress_percentage():.1f}% complete"
        )
        console.print(f"[blue]Provider:[/blue] {session.provider.display_name}")
        console.print(f"[blue]Language:[/blue] {session.language.value.title()}")

        interface = BulkScrapingInterface()

        try:
            progress = await interface.run_with_monitoring(scraper)

            console.print("\\n[bold green]✅ Scraping session completed![/bold green]")
            console.print(f"[green]Processed: {progress.processed_words:,} words[/green]")
            console.print(f"[green]Success rate: {progress.success_rate:.1%}[/green]")

        except Exception as e:
            console.print(f"\\n[bold red]❌ Scraping failed: {e}[/bold red]")

    asyncio.run(_run())


@scrape_group.command(name="delete")
@click.argument("session_id")
@click.confirmation_option(prompt="Are you sure you want to delete this session?")
def delete_session_cmd(session_id: str) -> None:
    """Delete a scraping session."""

    async def _run():
        success = await delete_session(session_id)
        if success:
            console.print(f"[green]✅ Deleted session {session_id}[/green]")
        else:
            console.print(f"[red]❌ Failed to delete session {session_id}[/red]")

    asyncio.run(_run())


@scrape_group.command(name="cleanup")
@click.option("--days", "-d", default=30, help="Delete sessions older than N days")
def cleanup_sessions_cmd(days: int) -> None:
    """Clean up old scraping sessions."""

    async def _run():
        console.print(f"[yellow]Cleaning up sessions older than {days} days...[/yellow]")

        cleaned_count = await cleanup_old_sessions(days)

        if cleaned_count > 0:
            console.print(f"[green]✅ Cleaned up {cleaned_count} old sessions[/green]")
        else:
            console.print("[blue]No old sessions to clean up[/blue]")

    asyncio.run(_run())


@scrape_group.command(name="status")
@click.argument("session_id", required=False)
def show_status(session_id: str | None) -> None:
    """Show scraping status or details for a specific session."""

    async def _run():
        if session_id:
            # Show specific session details
            session = await get_session(session_id)
            if not session:
                console.print(f"[red]Session {session_id} not found[/red]")
                return

            stats = session.get_statistics()

            console.print(f"[bold blue]Session Details: {session_id}[/bold blue]")
            console.print(f"[blue]Name:[/blue] {stats['session_name'] or 'unnamed'}")
            console.print(f"[blue]Provider:[/blue] {stats['provider']}")
            console.print(f"[blue]Language:[/blue] {stats['language']}")
            console.print(f"[blue]Status:[/blue] {stats['status']}")
            console.print(f"[blue]Progress:[/blue] {stats['progress_percentage']:.1f}%")
            console.print(f"[blue]Total Words:[/blue] {stats['total_words']:,}")
            console.print(f"[blue]Processed:[/blue] {stats['processed_words']:,}")
            console.print(f"[blue]Successful:[/blue] {stats['successful_words']:,}")
            console.print(f"[blue]Failed:[/blue] {stats['failed_words']:,}")
            console.print(f"[blue]Success Rate:[/blue] {stats['success_rate']:.1%}")
            if stats["words_per_second"] > 0:
                console.print(f"[blue]Speed:[/blue] {stats['words_per_second']:.2f} words/sec")
            console.print(f"[blue]Created:[/blue] {stats['created_at']}")
            if stats["started_at"]:
                console.print(f"[blue]Started:[/blue] {stats['started_at']}")
            if stats["completed_at"]:
                console.print(f"[blue]Completed:[/blue] {stats['completed_at']}")
        else:
            # Show general scraping status
            sessions = await list_sessions()
            active_sessions = [s for s in sessions if s["status"] == "running"]
            completed_sessions = [s for s in sessions if s["status"] == "completed"]
            failed_sessions = [s for s in sessions if s["status"] == "failed"]

            console.print("[bold blue]Bulk Scraping Status[/bold blue]")
            console.print(f"[green]Total Sessions:[/green] {len(sessions)}")
            console.print(f"[yellow]Active:[/yellow] {len(active_sessions)}")
            console.print(f"[green]Completed:[/green] {len(completed_sessions)}")
            console.print(f"[red]Failed:[/red] {len(failed_sessions)}")

            if active_sessions:
                console.print("\\n[yellow]Active Sessions:[/yellow]")
                for session in active_sessions:
                    console.print(
                        f"  • {session['session_id'][:8]} - {session['provider']} ({session['progress_percentage']:.1f}%)"
                    )

    asyncio.run(_run())
