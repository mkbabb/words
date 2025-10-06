"""Fast, lightweight CLI entry point with lazy loading."""

from __future__ import annotations

import importlib
from typing import Any

import click
from rich.console import Console

console = Console()


class LazyGroup(click.Group):
    """Lazy-loading Click group that imports commands only when needed."""

    def __init__(self, import_name: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.import_name = import_name

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        # Import the actual command module only when the command is invoked
        try:
            module = importlib.import_module(self.import_name)
            # Get the command group from the module
            if hasattr(module, f"{cmd_name}_command"):
                return getattr(module, f"{cmd_name}_command")
            if hasattr(module, f"{cmd_name}_group"):
                return getattr(module, f"{cmd_name}_group")
            return None
        except ImportError:
            return None

    def list_commands(self, ctx: click.Context) -> list[str]:
        # Return a static list of commands without importing modules
        return [
            "lookup",
            "search",
            "scrape",
            "wordlist",
            "config",
            "database",
            "wotd-ml",
        ]


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """🚀 Floridify - AI-Enhanced Dictionary and Learning Tool

    Beautiful, intelligent vocabulary management with AI-powered definitions,
    semantic search, and Anki flashcard generation.
    """
    if ctx.invoked_subcommand is None:
        console.print("""
[bold blue]🚀 Floridify[/bold blue] - AI-Enhanced Dictionary and Learning Tool

[dim]Beautiful, intelligent vocabulary management with AI-powered definitions,
semantic search, and Anki flashcard generation.[/dim]

[bold]Quick Start:[/bold]
  [cyan]floridify search init[/cyan]               Initialize search index (first time)
  [cyan]floridify lookup serendipity[/cyan]         Look up a word with AI synthesis
  [cyan]floridify search word seren[/cyan]          Search for words and phrases
  [cyan]floridify scrape wordhippo[/cyan]           Scrape WordHippo for corpus
  [cyan]floridify wordlist create vocab.txt[/cyan]  Process word list with lookup

[bold]Available Commands:[/bold]
  [green]lookup[/green]      🔍 Look up words and definitions
  [green]search[/green]      🔎 Fuzzy and semantic word search
  [green]wotd-ml[/green]     🚀 WOTD ML with multi-model support
  [green]wordlist[/green]    📄 Manage word lists with dictionary lookup
  [green]scrape[/green]      🚀 Scraping for systematic provider data collection
  [green]config[/green]      ⚙️  Manage configuration and API keys
  [green]database[/green]    💾 Database operations and statistics
  [green]completion[/green]  🔧 Generate shell completion scripts

[dim]Use 'floridify <command> --help' for detailed information about each command.[/dim]
        """)


# Define lazy-loaded commands
@cli.command()
@click.argument("word")
@click.option(
    "--provider",
    type=click.Choice(
        [
            "wiktionary",
            "oxford",
            "apple_dictionary",
            "merriam_webster",
            "free_dictionary",
            "wordhippo",
            "ai_fallback",
            "synthesis",
        ],
    ),
    multiple=True,
    default=["wiktionary"],
    help="Dictionary providers to use",
)
@click.option("--language", "-l", multiple=True, default=["en"], help="Language code")
@click.option("--no-ai", is_flag=True, help="Disable AI synthesis")
@click.option("--force", is_flag=True, help="Force refresh from providers")
@click.option("--semantic", is_flag=True, help="Use semantic search")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def lookup(word: str, provider: tuple[str, ...], language: tuple[str, ...], no_ai: bool, force: bool, semantic: bool, output_json: bool) -> None:
    """Look up word definitions with AI enhancement."""
    import asyncio

    from .commands.lookup import _lookup_async

    asyncio.run(_lookup_async(word, provider, language, semantic, no_ai, force, output_json))


@cli.group(invoke_without_command=True)
@click.pass_context
def scrape(ctx: click.Context) -> None:
    """Scraping commands for systematic provider data collection."""
    if ctx.invoked_subcommand is None:
        console.print("""
[bold]Scraping Commands:[/bold]
  [green]apple-dictionary[/green]     Bulk scrape Apple Dictionary (macOS)
  [green]wordhippo[/green]            Bulk scrape WordHippo for synonyms/antonyms
  [green]free-dictionary[/green]      Bulk scrape FreeDictionary API
  [green]wiktionary-wholesale[/green] Download complete Wiktionary dumps
  [green]sessions[/green]             List all scraping sessions
  [green]status[/green]               Show scraping status
  [green]resume[/green]               Resume a scraping session
  [green]delete[/green]               Delete a scraping session
  [green]cleanup[/green]              Clean up old sessions

[dim]Use 'floridify scrape <command> --help' for detailed options.[/dim]
        """)


# Define individual scrape subcommands with lazy loading
@scrape.command()
@click.option(
    "--skip-existing/--include-existing",
    default=True,
    help="Skip words that already have data",
)
@click.option("--force-refresh", is_flag=True, help="Force refresh existing data")
@click.option("-n", "--session-name", help="Name for this scraping session")
@click.option("-r", "--resume-session", help="Resume from existing session ID")
@click.option("-c", "--max-concurrent", type=int, help="Maximum concurrent operations")
@click.option("-b", "--batch-size", type=int, help="Words per batch")
@click.option(
    "-l",
    "--language",
    type=click.Choice(["en", "fr", "es", "de", "it"]),
    default="en",
    help="Language to scrape",
)
def apple_dictionary(**kwargs: Any) -> None:
    """Bulk scrape Apple Dictionary (macOS) for local definitions."""
    from .commands.scrape import scrape_apple_dictionary

    scrape_apple_dictionary(**kwargs)


@scrape.command()
@click.option(
    "--skip-existing/--include-existing",
    default=True,
    help="Skip words that already have data",
)
@click.option("--force-refresh", is_flag=True, help="Force refresh existing data")
@click.option("-n", "--session-name", help="Name for this scraping session")
@click.option("-r", "--resume-session", help="Resume from existing session ID")
@click.option("-c", "--max-concurrent", type=int, help="Maximum concurrent operations")
@click.option("-b", "--batch-size", type=int, help="Words per batch")
@click.option(
    "-l",
    "--language",
    type=click.Choice(["en", "fr", "es", "de", "it"]),
    default="en",
    help="Language to scrape",
)
def wordhippo(**kwargs: Any) -> None:
    """Bulk scrape WordHippo for comprehensive synonym/antonym/example data."""
    from .commands.scrape import scrape_wordhippo

    scrape_wordhippo(**kwargs)


@scrape.command()
@click.option(
    "--skip-existing/--include-existing",
    default=True,
    help="Skip words that already have data",
)
@click.option("--force-refresh", is_flag=True, help="Force refresh existing data")
@click.option("-n", "--session-name", help="Name for this scraping session")
@click.option("-r", "--resume-session", help="Resume from existing session ID")
@click.option("-c", "--max-concurrent", type=int, help="Maximum concurrent operations")
@click.option("-b", "--batch-size", type=int, help="Words per batch")
@click.option(
    "-l",
    "--language",
    type=click.Choice(["en", "fr", "es", "de", "it"]),
    default="en",
    help="Language to scrape",
)
def free_dictionary(**kwargs: Any) -> None:
    """Bulk scrape FreeDictionary API for comprehensive coverage."""
    from .commands.scrape import scrape_free_dictionary

    scrape_free_dictionary(**kwargs)


@scrape.command()
@click.option(
    "--skip-existing/--include-existing",
    default=True,
    help="Skip words that already have data",
)
@click.option("--force-refresh", is_flag=True, help="Force refresh existing data")
@click.option("-n", "--session-name", help="Name for this scraping session")
@click.option("-r", "--resume-session", help="Resume from existing session ID")
@click.option("-c", "--max-concurrent", type=int, help="Maximum concurrent operations")
@click.option("-b", "--batch-size", type=int, help="Words per batch")
@click.option(
    "-l",
    "--language",
    type=click.Choice(["en", "fr", "es", "de", "it"]),
    default="en",
    help="Language to scrape",
)
def wiktionary_wholesale(**kwargs: Any) -> None:
    """Download and process complete Wiktionary dumps."""
    from .commands.scrape import scrape_wiktionary_wholesale

    scrape_wiktionary_wholesale(**kwargs)


@scrape.command()
def sessions() -> None:
    """List all scraping sessions."""
    from .commands.scrape import list_sessions

    list_sessions()


@scrape.command()
@click.argument("session_id", required=False)
def status(session_id: str | None = None) -> None:
    """Show scraping status or details for a specific session."""
    from .commands.scrape import show_status

    show_status(session_id)


@scrape.command()
@click.argument("session_id")
def resume(session_id: str) -> None:
    """Resume a scraping session by ID."""
    from .commands.scrape import resume_session

    resume_session(session_id)


@scrape.command()
@click.argument("session_id")
@click.confirmation_option(prompt="Are you sure you want to delete this session?")
def delete(session_id: str) -> None:
    """Delete a scraping session."""
    from .commands.scrape import delete_session

    delete_session(session_id)


@scrape.command()
@click.confirmation_option(prompt="Are you sure you want to clean up old sessions?")
def cleanup() -> None:
    """Clean up old scraping sessions."""
    from .commands.scrape import cleanup_sessions

    cleanup_sessions()


@cli.group(invoke_without_command=True)
@click.pass_context
def search(ctx: click.Context) -> None:
    """🔎 Search functionality - find words across lexicons."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register search subcommands
@search.command("word")
@click.argument("query")
@click.option(
    "--language",
    type=click.Choice(["en", "fr", "es", "de"], case_sensitive=False),
    multiple=True,
    default=["en"],
    help="Lexicon languages to search",
)
@click.option(
    "--mode",
    type=click.Choice(["smart", "exact", "fuzzy", "semantic"], case_sensitive=False),
    default="smart",
    help="Search mode: smart (default), exact, fuzzy, semantic",
)
@click.option(
    "--min-score",
    type=float,
    help="Minimum relevance score (0.0-1.0)",
)
@click.option(
    "--force-rebuild",
    is_flag=True,
    help="Force rebuild of search indices",
)
@click.option(
    "--max-results",
    type=int,
    default=20,
    help="Maximum number of results to show",
)
@click.option(
    "--corpus-id",
    type=str,
    help="Specific corpus ID to search (overrides --language)",
)
@click.option(
    "--corpus-name",
    type=str,
    help="Specific corpus name to search (overrides --language)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON (matches API response format)",
)
def search_word(
    query: str,
    language: tuple[str, ...],
    mode: str,
    max_results: int,
    min_score: float | None,
    force_rebuild: bool,
    corpus_id: str | None,
    corpus_name: str | None,
    output_json: bool,
) -> None:
    """Search for words in lexicons."""
    import asyncio

    from .commands.search import _search_word_async

    asyncio.run(
        _search_word_async(
            query,
            language,
            mode,
            max_results,
            min_score,
            force_rebuild,
            corpus_id,
            corpus_name,
            output_json,
        )
    )


@search.command("similar")
@click.argument("word")
@click.option(
    "--language",
    type=click.Choice(["en", "fr", "es", "de"], case_sensitive=False),
    multiple=True,
    default=["en"],
    help="Lexicon languages to search",
)
@click.option(
    "--max-results",
    type=int,
    default=10,
    help="Maximum number of similar words to show",
)
def search_similar(word: str, language: tuple[str, ...], max_results: int) -> None:
    """Find words similar to the given word using semantic search."""
    import asyncio

    from .commands.search import _search_similar_async

    asyncio.run(_search_similar_async(word, language, max_results))


@search.command("stats")
@click.option(
    "--language",
    type=click.Choice(["en", "fr", "es", "de"], case_sensitive=False),
    multiple=True,
    default=["en"],
    help="Lexicon languages to show stats for",
)
def search_stats(language: tuple[str, ...]) -> None:
    """Show search engine statistics."""
    import asyncio

    from .commands.search import _search_stats_async

    asyncio.run(_search_stats_async(language))


@cli.command()
@click.argument("file_path")
def wordlist(file_path: str) -> None:
    """Manage word lists with dictionary lookup and storage."""
    from .commands.wordlist import wordlist_command

    wordlist_command(file_path)


@cli.group(invoke_without_command=True)
@click.pass_context
def config(ctx: click.Context) -> None:
    """⚙️ Manage configuration and API keys."""
    if ctx.invoked_subcommand is None:
        from .commands.config import config_group

        ctx.invoke(config_group)


@cli.group(invoke_without_command=True)
@click.pass_context
def database(ctx: click.Context) -> None:
    """💾 Database operations and statistics."""
    if ctx.invoked_subcommand is None:
        from .commands.database import database_group

        ctx.invoke(database_group)


@cli.command()
def wotd_ml() -> None:
    """🚀 WOTD ML with multi-model support."""
    from .commands.wotd_ml import wotd_ml_command

    wotd_ml_command()


@cli.command()
@click.option(
    "--shell",
    type=click.Choice(["zsh", "bash"]),
    default="zsh",
    help="Shell to generate completion for",
)
def completion(shell: str) -> None:
    """Generate shell completion script for floridify."""
    from .completion import generate_zsh_completion

    if shell == "zsh":
        completion_script = generate_zsh_completion()
        click.echo(completion_script)
        click.echo("\n# To install, run:", err=True)
        click.echo(
            "# floridify completion --shell zsh > ~/.local/share/zsh/site-functions/_floridify",
            err=True,
        )
        click.echo("# Or add to your ~/.zshrc:", err=True)
        click.echo('# eval "$(floridify completion --shell zsh)"', err=True)
    else:
        click.echo("Bash completion not yet implemented", err=True)


# Add aliases
cli.add_command(lookup, name="define")


if __name__ == "__main__":
    cli()
