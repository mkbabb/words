"""Database management and statistics commands."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.table import Table

from ...constants import DictionaryProvider
from ...models import (
    SynthesizedDictionaryEntry,
    Word,
)
from ...storage.mongodb import MongoDBStorage
from ..utils.formatting import format_error

console = Console()


@click.group()
def database_group() -> None:
    """💾 Database operations and statistics."""
    pass


@database_group.command("status")
def database_status() -> None:
    """Show database connection status and basic info."""
    console.print("[bold blue]Database Status[/bold blue]\n")

    # TODO: Implement actual database connection check
    console.print("[bold]Connection:[/bold] [red]✗ Not connected[/red]")
    console.print("[dim]Database integration not yet implemented.[/dim]")


@database_group.command("connect")
@click.option("--host", default="localhost", help="MongoDB host")
@click.option("--port", default=27017, help="MongoDB port")
@click.option("--database", default="floridify", help="Database name")
def connect_database(host: str, port: int, database: str) -> None:
    """Connect to MongoDB database.

    Tests connection and displays database information.
    """
    console.print("[bold blue]Connecting to MongoDB...[/bold blue]")
    console.print(f"Host: {host}:{port}")
    console.print(f"Database: {database}")
    console.print("[dim]Database connection not yet implemented.[/dim]")


@database_group.command("stats")
@click.option("--detailed", is_flag=True, help="Show detailed statistics")
@click.option(
    "--connection-string",
    default="mongodb://localhost:27017",
    help="MongoDB connection string",
)
@click.option("--database", default="floridify", help="Database name")
def database_stats(detailed: bool, connection_string: str, database: str) -> None:
    """Show database statistics and metrics."""
    asyncio.run(_database_stats_async(detailed, connection_string, database))


async def _database_stats_async(detailed: bool, connection_string: str, database_name: str) -> None:
    """Get real database statistics from MongoDB."""
    try:
        console.print("[bold blue]📊 Database Statistics[/bold blue]\n")

        # Connect to MongoDB
        storage = MongoDBStorage(connection_string, database_name)
        await storage.connect()

        # Get collection counts
        total_words = await Word.count()
        total_syntheses = await SynthesizedDictionaryEntry.count()

        # Overview statistics
        console.print("[bold]Overview:[/bold]")
        stats_table = Table(show_header=False)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="bold")

        stats_table.add_row("Total Words", f"{total_words:,}")
        stats_table.add_row("AI Syntheses", f"{total_syntheses:,}")

        console.print(stats_table)

        # Provider coverage analysis
        provider_stats = await _get_provider_coverage()
        if provider_stats:
            console.print("\n[bold]📈 Provider Coverage:[/bold]")
            provider_table = Table(show_header=True, header_style="bold blue")
            provider_table.add_column("Source")
            provider_table.add_column("Count", justify="right")

            for provider, count in provider_stats.items():
                provider_table.add_row(DictionaryProvider(provider).display_name, f"{count:,}")

            console.print(provider_table)

        if detailed and total_words > 0:
            # Quality metrics (only if we have data)
            console.print("\n[bold]📝 Quality Metrics:[/bold]")
            quality_stats = await _get_quality_metrics()

            if quality_stats:
                for metric, value in quality_stats.items():
                    console.print(f"• {metric}: {value}")

        # Database size info (approximation)
        estimated_size_mb = total_words * 2.5 + total_syntheses * 1.8  # Rough estimate
        console.print(f"\n💾 Estimated database size: {estimated_size_mb:.1f} MB")

        await storage.disconnect()

    except Exception as e:
        console.print(
            format_error(
                f"Failed to connect to database: {e}",
                "Make sure MongoDB is running and accessible.",
            )
        )


async def _get_provider_coverage() -> dict[str, int]:
    """Get count of entries by provider."""
    try:
        # Aggregate provider counts from dictionary entries
        pipeline = [
            {"$project": {"providers": {"$objectToArray": "$provider_data"}}},
            {"$unwind": "$providers"},
            {"$group": {"_id": "$providers.k", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]

        results = await Word.aggregate(pipeline).to_list()
        return {item["_id"]: item["count"] for item in results}

    except Exception:
        return {}


async def _get_quality_metrics() -> dict[str, str]:
    """Get quality metrics for the database."""
    try:
        metrics = {}

        # Count entries with multiple providers
        total_entries = await Word.count()
        if total_entries > 0:
            # Sample some entries to estimate coverage
            sample_entries = await Word.find().limit(100).to_list()

            if sample_entries:
                # Calculate average providers per word
                from ...models import ProviderData
                total_providers = 0
                for word in sample_entries:
                    provider_count = await ProviderData.find(ProviderData.word_id == str(word.id)).count()
                    total_providers += provider_count
                avg_providers = total_providers / len(sample_entries)
                metrics["Average providers per word"] = f"{avg_providers:.1f}"

                # Count entries with definitions
                entries_with_defs = sum(
                    1
                    for entry in sample_entries
                    if any(
                        provider_data.definitions for provider_data in entry.provider_data.values()
                    )
                )
                coverage_pct = (entries_with_defs / len(sample_entries)) * 100
                metrics["Words with definitions"] = f"{coverage_pct:.1f}%"

        return metrics

    except Exception:
        return {}


@database_group.command("backup")
@click.option("--output", "-o", type=click.Path(), help="Backup file path")
@click.option(
    "--format",
    "backup_format",
    type=click.Choice(["json", "bson"]),
    default="json",
    help="Backup format",
)
@click.option("--compress", is_flag=True, help="Compress backup file")
def backup_database(output: str | None, backup_format: str, compress: bool) -> None:
    """Create a backup of the database.

    Exports all dictionary entries and metadata to a file.
    """
    if output is None:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = "json.gz" if compress else backup_format
        output = f"floridify_backup_{timestamp}.{extension}"

    console.print("[bold blue]Creating database backup...[/bold blue]")
    console.print(f"Output: {output}")
    console.print(f"Format: {backup_format}")
    console.print(f"Compress: {compress}")
    console.print("[dim]Database backup not yet implemented.[/dim]")


@database_group.command("restore")
@click.argument("backup_file", type=click.Path(exists=True))
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def restore_database(backup_file: str, confirm: bool) -> None:
    """Restore database from a backup file.

    BACKUP_FILE: Path to the backup file
    """
    if not confirm:
        if not click.confirm("This will overwrite existing data. Continue?"):
            console.print("Operation cancelled.")
            return

    console.print(f"[bold blue]Restoring database from: {backup_file}[/bold blue]")
    console.print("[dim]Database restore not yet implemented.[/dim]")


@database_group.command("cleanup")
@click.option("--dry-run", is_flag=True, help="Show what would be cleaned without doing it")
@click.option("--older-than", default=30, help="Remove cache entries older than N days")
def cleanup_database(dry_run: bool, older_than: int) -> None:
    """Clean up old cache entries and optimize database.

    Removes expired API response cache and optimizes database performance.
    """
    console.print(f"[bold blue]Database cleanup (dry run: {dry_run})[/bold blue]")
    console.print(f"Removing cache entries older than {older_than} days")
    console.print("[dim]Database cleanup not yet implemented.[/dim]")


@database_group.command("reindex")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def reindex_database(confirm: bool) -> None:
    """Rebuild database indexes for optimal performance."""
    if not confirm:
        if not click.confirm("Reindexing may take several minutes. Continue?"):
            console.print("Operation cancelled.")
            return

    console.print("[bold blue]Rebuilding database indexes...[/bold blue]")
    console.print("[dim]Database reindexing not yet implemented.[/dim]")


@database_group.command("export")
@click.option(
    "--collection",
    type=click.Choice(["words", "cache", "all"]),
    default="words",
    help="Collection to export",
)
@click.option(
    "--format",
    "export_format",
    type=click.Choice(["json", "csv", "txt"]),
    default="json",
    help="Export format",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--filter", "filter_query", help="MongoDB filter query (JSON)")
def export_data(
    collection: str, export_format: str, output: str | None, filter_query: str | None
) -> None:
    """Export data from the database.

    Exports dictionary entries or cache data in various formats.
    """
    if output is None:
        output = f"floridify_{collection}.{export_format}"

    console.print(f"[bold blue]Exporting {collection} data...[/bold blue]")
    console.print(f"Format: {export_format}")
    console.print(f"Output: {output}")
    if filter_query:
        console.print(f"Filter: {filter_query}")
    console.print("[dim]Database export not yet implemented.[/dim]")


@database_group.command("import")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--format",
    "import_format",
    type=click.Choice(["json", "csv"]),
    help="Input format (auto-detected if not specified)",
)
@click.option("--collection", default="words", help="Target collection")
@click.option("--upsert", is_flag=True, help="Update existing entries")
def import_data(input_file: str, import_format: str | None, collection: str, upsert: bool) -> None:
    """Import data into the database.

    INPUT_FILE: File containing data to import
    """
    console.print(f"[bold blue]Importing data from: {input_file}[/bold blue]")
    console.print(f"Target collection: {collection}")
    console.print(f"Upsert mode: {upsert}")
    if import_format:
        console.print(f"Format: {import_format}")
    console.print("[dim]Database import not yet implemented.[/dim]")
