"""Database management and statistics commands."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.table import Table

from ...models import (
    DictionaryEntry,
    Word,
)
from ...models.dictionary import DictionaryProvider
from ...storage.mongodb import MongoDBStorage
from ..utils.formatting import format_error

console = Console()


@click.group()
def database_group() -> None:
    """💾 Database operations and statistics."""


@database_group.command("status")
def database_status() -> None:
    """Show database connection status and basic info."""
    asyncio.run(_database_status_async())


async def _database_status_async() -> None:
    """Async implementation of database status check."""
    console.print("[bold blue]Database Status[/bold blue]\n")

    try:
        # Test database connection
        from ...storage.mongodb import get_storage

        storage = await get_storage()

        console.print("[bold]Connection:[/bold] [green]✓ Connected[/green]")

        # Just verify we can get storage without error
        if hasattr(storage, "database_name"):
            console.print(f"[bold]Database:[/bold] {storage.database_name}")
        if hasattr(storage, "connection_string"):
            console.print(f"[bold]Connection String:[/bold] {storage.connection_string}")

        # Get basic counts
        word_count = await Word.count()
        synthesis_count = await DictionaryEntry.find({"provider": "synthesis"}).count()

        console.print("[bold]Collections:[/bold]")
        console.print(f"  • Words: {word_count:,}")
        console.print(f"  • AI Syntheses: {synthesis_count:,}")

    except Exception as e:
        console.print("[bold]Connection:[/bold] [red]✗ Failed[/red]")
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Make sure MongoDB is running and accessible.[/dim]")


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
        total_syntheses = await DictionaryEntry.find({"provider": "synthesis"}).count()

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
            ),
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
                    provider_count = await ProviderData.find(
                        ProviderData.word_id == word.id,
                    ).count()
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
    type=click.Choice(["json"]),
    default="json",
    help="Backup format",
)
@click.option("--compress", is_flag=True, help="Compress backup file")
def backup_database(output: str | None, backup_format: str, compress: bool) -> None:
    """Create a backup of the database.

    Exports all dictionary entries and metadata to a file.
    """
    asyncio.run(_backup_database_async(output, backup_format, compress))


async def _backup_database_async(output: str | None, backup_format: str, compress: bool) -> None:
    """Async implementation of database backup."""
    import gzip
    import json
    from datetime import datetime
    from pathlib import Path

    from rich.progress import Progress, SpinnerColumn, TextColumn

    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = "json.gz" if compress else backup_format
        output = f"floridify_backup_{timestamp}.{extension}"

    console.print("[bold blue]Creating database backup...[/bold blue]")
    console.print(f"Output: {output}")
    console.print(f"Format: {backup_format}")
    console.print(f"Compress: {compress}\n")

    try:
        backup_data = {
            "metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "format_version": "1.0",
                "backup_type": "full",
            },
            "collections": {},
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Backup Words
            task = progress.add_task("Backing up words...", total=None)
            words = await Word.find_all().to_list()
            backup_data["collections"]["words"] = [word.model_dump(mode="json") for word in words]
            progress.update(task, description=f"Backed up {len(words)} words")
            progress.advance(task)

            # Backup Synthesized Entries
            task = progress.add_task("Backing up synthesized entries...", total=None)
            syntheses = await DictionaryEntry.find({"provider": "synthesis"}).to_list()
            backup_data["collections"]["synthesized_entries"] = [
                entry.model_dump(mode="json") for entry in syntheses
            ]
            progress.update(task, description=f"Backed up {len(syntheses)} synthesized entries")
            progress.advance(task)

        # Write backup file
        backup_json = json.dumps(backup_data, indent=2, default=str)

        output_path = Path(output)
        if compress:
            with gzip.open(output_path, "wt", encoding="utf-8") as f:
                f.write(backup_json)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(backup_json)

        file_size = output_path.stat().st_size / 1024 / 1024  # MB
        console.print("\n[green]✓ Backup created successfully[/green]")
        console.print(f"File: {output_path.absolute()}")
        console.print(f"Size: {file_size:.1f} MB")

    except Exception as e:
        console.print(f"[red]Backup failed:[/red] {e}")


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
@click.option("--older-than", default=30, help="Remove entries older than N days")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def cleanup_database(dry_run: bool, older_than: int, confirm: bool) -> None:
    """Clean up old entries and optimize database.

    Removes old provider data and orphaned entries.
    """
    asyncio.run(_cleanup_database_async(dry_run, older_than, confirm))


async def _cleanup_database_async(dry_run: bool, older_than: int, confirm: bool) -> None:
    """Async implementation of database cleanup."""
    from datetime import datetime, timedelta

    from ...models import ProviderData

    console.print(f"[bold blue]Database cleanup (dry run: {dry_run})[/bold blue]")
    console.print(f"Removing entries older than {older_than} days\n")

    if not dry_run and not confirm:
        if not click.confirm("This will permanently delete old data. Continue?"):
            console.print("Operation cancelled.")
            return

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=older_than)

        # Find old provider data entries
        old_providers = await ProviderData.find(
            ProviderData.updated_at < cutoff_date,
        ).to_list()

        console.print(f"Found {len(old_providers)} old provider entries")

        if old_providers and not dry_run:
            # Delete old provider data
            delete_result = await ProviderData.find(
                ProviderData.updated_at < cutoff_date,
            ).delete()

            deleted_count = delete_result.deleted_count if delete_result else 0
            console.print(f"[green]Deleted {deleted_count} old provider entries[/green]")
        elif old_providers:
            console.print(
                f"[yellow]Would delete {len(old_providers)} old provider entries[/yellow]"
            )

        # Find orphaned words (words with no provider data)
        words_with_no_data = []
        async for word in Word.find():
            provider_count = await ProviderData.find(
                ProviderData.word_id == word.id,
            ).count()
            if provider_count == 0:
                words_with_no_data.append(word)

        console.print(f"Found {len(words_with_no_data)} orphaned words")

        if words_with_no_data and not dry_run:
            # Clean up orphaned words
            for word in words_with_no_data:
                await word.delete()
            console.print(f"[green]Deleted {len(words_with_no_data)} orphaned words[/green]")
        elif words_with_no_data:
            console.print(f"[yellow]Would delete {len(words_with_no_data)} orphaned words[/yellow]")

        if not dry_run:
            console.print("\n[green]✓ Cleanup completed successfully[/green]")
        else:
            console.print("\n[blue]✓ Dry run completed - no changes made[/blue]")

    except Exception as e:
        console.print(f"[red]Cleanup failed:[/red] {e}")


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
    collection: str,
    export_format: str,
    output: str | None,
    filter_query: str | None,
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


@database_group.group("clear")
def clear_group() -> None:
    """Clear database collections and data."""


@clear_group.command("everything")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def clear_everything(confirm: bool) -> None:
    """Clear entire database - WARNING: This deletes ALL data."""
    asyncio.run(_clear_everything_async(confirm))


async def _clear_everything_async(confirm: bool) -> None:
    """Async implementation of clear everything."""
    if not confirm:
        console.print("[bold red]WARNING: This will delete ALL data in the database![/bold red]")
        if not click.confirm("Are you absolutely sure you want to continue?"):
            console.print("Operation cancelled.")
            return
        if not click.confirm("This action cannot be undone. Final confirmation?"):
            console.print("Operation cancelled.")
            return

    try:
        console.print("[bold red]Clearing entire database...[/bold red]")

        from ...models import (
            Definition,
            Example,
            Fact,
            Pronunciation,
            ProviderData,
            Word,
        )
        from ...wordlist import WordList

        # Delete collections individually
        total_deleted = 0

        # Delete synthesized entries first (references other collections)
        result = await DictionaryEntry.find({"provider": "synthesis"}).delete()
        synth_count = result.deleted_count if result else 0
        total_deleted += synth_count
        console.print(f"  Deleted {synth_count} DictionaryEntry synthesis documents")

        # Delete provider data
        result = await ProviderData.find().delete()
        provider_count = result.deleted_count if result else 0
        total_deleted += provider_count
        console.print(f"  Deleted {provider_count} ProviderData documents")

        # Delete examples, facts, definitions, pronunciations
        for model_class in [Example, Fact, Definition, Pronunciation]:
            result = await model_class.find().delete()
            count = result.deleted_count if result else 0
            total_deleted += count
            console.print(f"  Deleted {count} {model_class.__name__} documents")

        # Delete wordlists
        result = await WordList.find().delete()
        wordlist_count = result.deleted_count if result else 0
        total_deleted += wordlist_count
        console.print(f"  Deleted {wordlist_count} WordList documents")

        # Delete words last
        result = await Word.find().delete()
        word_count = result.deleted_count if result else 0
        total_deleted += word_count
        console.print(f"  Deleted {word_count} Word documents")

        console.print(f"\n[green]✓ Successfully deleted {total_deleted} total documents[/green]")
        console.print("[green]Database cleared completely.[/green]")

    except Exception as e:
        console.print(f"[red]Error clearing database: {e}[/red]")


@clear_group.command("words")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def clear_words(confirm: bool) -> None:
    """Clear all words and related data (definitions, examples, facts)."""
    asyncio.run(_clear_words_async(confirm))


async def _clear_words_async(confirm: bool) -> None:
    """Async implementation of clear words."""
    if not confirm:
        if not click.confirm("Delete all words and related data?"):
            console.print("Operation cancelled.")
            return

    try:
        console.print("[bold blue]Clearing all words and related data...[/bold blue]")

        from ...models import (
            Definition,
            Example,
            Fact,
            Pronunciation,
            ProviderData,
            Word,
        )

        # Delete in dependency order
        total_deleted = 0

        # Delete synthesized entries first (references words)
        result = await DictionaryEntry.find({"provider": "synthesis"}).delete()
        synth_count = result.deleted_count if result else 0
        total_deleted += synth_count
        console.print(f"  Deleted {synth_count} DictionaryEntry synthesis documents")

        # Delete provider data (references words)
        result = await ProviderData.find().delete()
        provider_count = result.deleted_count if result else 0
        total_deleted += provider_count
        console.print(f"  Deleted {provider_count} ProviderData documents")

        # Delete word-related data
        for model_class in [Example, Fact, Definition, Pronunciation]:
            result = await model_class.find().delete()
            count = result.deleted_count if result else 0
            total_deleted += count
            console.print(f"  Deleted {count} {model_class.__name__} documents")

        # Delete words last
        result = await Word.find().delete()
        word_count = result.deleted_count if result else 0
        total_deleted += word_count
        console.print(f"  Deleted {word_count} Word documents")

        console.print(
            f"\n[green]✓ Successfully deleted {total_deleted} word-related documents[/green]"
        )

    except Exception as e:
        console.print(f"[red]Error clearing words: {e}[/red]")


@clear_group.command("definitions")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def clear_definitions(confirm: bool) -> None:
    """Clear all definitions only."""
    asyncio.run(_clear_definitions_async(confirm))


async def _clear_definitions_async(confirm: bool) -> None:
    """Async implementation of clear definitions."""
    if not confirm:
        if not click.confirm("Delete all definitions?"):
            console.print("Operation cancelled.")
            return

    try:
        console.print("[bold blue]Clearing all definitions...[/bold blue]")

        from ...models import Definition

        result = await Definition.find().delete()
        deleted_count = result.deleted_count if result else 0

        console.print(f"[green]✓ Successfully deleted {deleted_count} definitions[/green]")

    except Exception as e:
        console.print(f"[red]Error clearing definitions: {e}[/red]")


@clear_group.command("syntheses")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def clear_syntheses(confirm: bool) -> None:
    """Clear all AI-synthesized entries."""
    asyncio.run(_clear_syntheses_async(confirm))


async def _clear_syntheses_async(confirm: bool) -> None:
    """Async implementation of clear syntheses."""
    if not confirm:
        if not click.confirm("Delete all AI-synthesized entries?"):
            console.print("Operation cancelled.")
            return

    try:
        console.print("[bold blue]Clearing all AI-synthesized entries...[/bold blue]")

        result = await DictionaryEntry.find({"provider": "synthesis"}).delete()
        deleted_count = result.deleted_count if result else 0

        console.print(f"[green]✓ Successfully deleted {deleted_count} synthesized entries[/green]")

    except Exception as e:
        console.print(f"[red]Error clearing syntheses: {e}[/red]")


@clear_group.command("providers")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def clear_providers(confirm: bool) -> None:
    """Clear all provider data."""
    asyncio.run(_clear_providers_async(confirm))


async def _clear_providers_async(confirm: bool) -> None:
    """Async implementation of clear providers."""
    if not confirm:
        if not click.confirm("Delete all provider data?"):
            console.print("Operation cancelled.")
            return

    try:
        console.print("[bold blue]Clearing all provider data...[/bold blue]")

        from ...models import ProviderData

        result = await ProviderData.find().delete()
        deleted_count = result.deleted_count if result else 0

        console.print(f"[green]✓ Successfully deleted {deleted_count} provider entries[/green]")

    except Exception as e:
        console.print(f"[red]Error clearing providers: {e}[/red]")
