"""Floridify CLI - Modern command-line interface for AI-enhanced dictionary operations."""

from __future__ import annotations

import click
from rich.console import Console

from .commands.anki import anki_group
from .commands.config import config_group
from .commands.database import database_group
from .commands.lookup import lookup_group
from .commands.process import process_group
from .commands.search import search_group

console = Console()


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    🚀 Floridify - AI-Enhanced Dictionary and Learning Tool

    Beautiful, intelligent vocabulary management with AI-powered definitions,
    semantic search, and Anki flashcard generation.
    """
    if ctx.invoked_subcommand is None:
        console.print("""
[bold blue]🚀 Floridify[/bold blue] - AI-Enhanced Dictionary and Learning Tool

[dim]Beautiful, intelligent vocabulary management with AI-powered definitions,
semantic search, and Anki flashcard generation.[/dim]

[bold]Quick Start:[/bold]
  [cyan]floridify search init[/cyan]           Initialize search index (first time)
  [cyan]floridify lookup serendipity[/cyan]     Look up a word with AI synthesis
  [cyan]floridify search word seren[/cyan]      Search for words and phrases
  [cyan]floridify anki create vocab.txt[/cyan] Create Anki deck from word list

[bold]Available Commands:[/bold]
  [green]lookup[/green]    🔍 Look up words and definitions
  [green]search[/green]    🔎 Fuzzy and semantic word search
  [green]anki[/green]      🎴 Create and manage Anki flashcard decks
  [green]process[/green]   📄 Process word lists from files
  [green]config[/green]    ⚙️  Manage configuration and API keys
  [green]database[/green]  💾 Database operations and statistics

[dim]Use 'floridify <command> --help' for detailed information about each command.[/dim]
        """)


# Register command groups
cli.add_command(lookup_group, name="lookup")
cli.add_command(search_group, name="search")
cli.add_command(anki_group, name="anki")
cli.add_command(process_group, name="process")
cli.add_command(config_group, name="config")
cli.add_command(database_group, name="database")

# Add aliases
cli.add_command(lookup_group, name="define")


if __name__ == "__main__":
    cli()
