"""Word lookup and definition commands with AI comprehension."""

from __future__ import annotations

import asyncio
from typing import Any

import click
from rich.console import Console

from ...ai.openai_connector import OpenAIConnector
from ...ai.synthesis import DefinitionSynthesizer
from ...config import Config
from ...connectors import (
    Connector,
    DictionaryComConnector,
    OxfordConnector,
    WiktionaryConnector,
)
from ...models import DictionaryEntry, ProviderData, Word
from ...storage.mongodb import MongoDBStorage
from ..utils.enhanced_lookup import EnhancedWordLookup
from ..utils.formatting import format_error, format_word_display

console = Console()


# Global connector instances with caching
_connectors: dict[str, Connector] = {}
_storage: MongoDBStorage | None = None
_ai_synthesizer: DefinitionSynthesizer | None = None


async def get_storage() -> MongoDBStorage:
    """Get or create the global storage instance."""
    global _storage
    if _storage is None:
        _storage = MongoDBStorage()
        await _storage.connect()
    return _storage


async def get_connector(
    provider: str,
) -> Connector | None:
    """Get or create a connector for the specified provider."""
    global _connectors

    if provider in _connectors:
        return _connectors[provider]

    # Create the appropriate connector
    connector: Connector | None = None

    if provider == "wiktionary":
        connector = WiktionaryConnector()
    elif provider == "oxford":
        # connector = OxfordConnector()
        pass
    elif provider == "dictionary_com":
        connector = DictionaryComConnector()

    if connector:
        _connectors[provider] = connector
        return connector

    return None


async def get_ai_synthesizer() -> DefinitionSynthesizer | None:
    """Get or create the global AI synthesizer."""
    global _ai_synthesizer

    if _ai_synthesizer is None:
        try:
            # Load configuration
            config = Config.from_file()

            # Get storage
            storage = await get_storage()

            # Create OpenAI connector with storage for caching
            openai_connector = OpenAIConnector(config.openai, storage)

            # Create synthesizer
            _ai_synthesizer = DefinitionSynthesizer(openai_connector, storage)

        except Exception as e:
            console.print(f"[red]Failed to initialize AI synthesizer: {e}[/red]")
            _ai_synthesizer = None

    return _ai_synthesizer


@click.group()
def lookup_group() -> None:
    """🔍 Look up words and get detailed definitions with AI comprehension."""
    pass


@lookup_group.command("word")
@click.argument("word")
@click.option(
    "--provider",
    type=click.Choice(["all", "wiktionary", "oxford", "dictionary_com", "ai"]),
    default="wiktionary",
    help="Dictionary provider to use",
)
@click.option("--save/--no-save", default=True, help="Save result to database")
@click.option("--examples", "-e", is_flag=True, help="Include usage examples")
@click.option("--synonyms", "-s", is_flag=True, help="Include synonyms")
@click.option(
    "--ai-comprehension/--no-ai",
    default=True,
    help="Display AI comprehension by default",
)
@click.option("--cache-hours", default=24, help="Maximum cache age in hours")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def lookup_word(
    word: str,
    provider: str,
    save: bool,
    examples: bool,
    synonyms: bool,
    ai_comprehension: bool,
    cache_hours: int,
    verbose: bool,
) -> None:
    """Look up a word and display its definition with AI comprehension.

    WORD: The word to look up
    """
    # Set verbose logging based on flag
    from ...utils.logging import set_verbose

    set_verbose(verbose)

    asyncio.run(
        _lookup_word_async(
            word, provider, save, examples, synonyms, ai_comprehension, cache_hours
        )
    )


async def _lookup_word_async(
    word: str,
    provider: str,
    save: bool,
    examples: bool,
    synonyms: bool,
    ai_comprehension: bool,
    cache_hours: int,
) -> None:
    """Enhanced async word lookup with normalization, search fallback, and AI generation."""
    try:
        with console.status(f"[bold blue]Looking up '{word}' with enhanced search..."):
            # Initialize enhanced lookup system
            config = Config.from_file()
            storage = await get_storage()
            enhanced_lookup = EnhancedWordLookup(config, storage)
            await enhanced_lookup.initialize()

            # Determine which providers to use
            providers = []
            if provider == "all":
                provider_names = ["wiktionary", "oxford", "dictionary_com"]
            elif provider != "ai":
                provider_names = [provider]
            else:
                provider_names = []

            # Get provider connectors
            for provider_name in provider_names:
                connector = await get_connector(provider_name)
                if connector:
                    providers.append(connector)

            # Use enhanced lookup with fallback pipeline
            normalized_word, provider_data_list = (
                await enhanced_lookup.lookup_with_fallback(word, providers)
            )

            if not normalized_word:
                console.print(
                    format_error(
                        f"No definitions found for '{word}'",
                        "Word not found in any source including AI fallback.",
                    )
                )
                return

            # Show provider feedback
            for provider_data in provider_data_list:
                provider_name = provider_data.provider_name
                if provider_name == "ai_fallback":
                    console.print(
                        f"🤖 [yellow]AI Fallback[/yellow] - Generated {len(provider_data.definitions)} definitions"
                    )
                else:
                    console.print(
                        f"✓ [green]{provider_name.title()}[/green] - Found {len(provider_data.definitions)} definitions"
                    )

            # Generate AI synthesis if enabled and we have non-AI data
            ai_provider_data = None
            if (
                ai_comprehension
                and provider_data_list
                and not all(
                    pd.provider_name == "ai_fallback" for pd in provider_data_list
                )
            ):
                try:
                    synthesizer = await get_ai_synthesizer()
                    if synthesizer:
                        # Convert provider_data_list to the format expected by synthesizer
                        provider_dict = {}
                        for provider_data in provider_data_list:
                            provider_dict[provider_data.provider_name] = provider_data

                        # Use the word synthesis method from DefinitionSynthesizer
                        entry = await synthesizer.synthesize_word_entry(
                            normalized_word, provider_dict
                        )
                        if entry and "ai_synthesis" in entry.providers:
                            ai_provider_data = entry.providers["ai_synthesis"]
                            console.print(
                                "✓ [magenta]AI Synthesis[/magenta] - Generated comprehensive definition"
                            )
                except Exception as e:
                    console.print(f"✗ [red]AI Synthesis[/red] - {str(e)}")

            # Create or update dictionary entry
            await get_storage()

            # Try to find existing entry
            existing_entry = await DictionaryEntry.find_one(
                DictionaryEntry.word.text == normalized_word.lower()
            )

            if existing_entry:
                entry = existing_entry
                # Update with new provider data
                for provider_data in provider_data_list:
                    entry.add_provider_data(provider_data)
            else:
                # Create new entry
                entry = DictionaryEntry(
                    word=Word(text=normalized_word.lower()),
                    pronunciation=_extract_pronunciation(provider_data_list),
                    providers={},
                )
                # Add all provider data
                for provider_data in provider_data_list:
                    entry.add_provider_data(provider_data)

            # Add AI synthesis if available
            if ai_provider_data:
                entry.add_provider_data(ai_provider_data)

            # Save to database if requested
            if save:
                await entry.save()
                console.print("💾 [dim]Saved to database[/dim]")

            # Display the comprehensive result
            console.print()
            console.print(
                format_word_display(
                    entry, show_examples=examples, show_synonyms=synonyms
                )
            )

            # Show provider summary
            provider_names = list(entry.providers.keys())
            console.print(
                f"\n✨ Found {len(provider_names)} sources: {', '.join(provider_names)}"
            )

    except Exception as e:
        console.print(format_error(f"Lookup failed: {str(e)}"))


def _extract_pronunciation(provider_data_list: list[ProviderData]) -> Any:
    """Extract pronunciation from provider data."""
    from ...models import Pronunciation

    # Try to find pronunciation from any provider
    for provider_data in provider_data_list:
        # Check for AI fallback phonetic pronunciation in raw_metadata
        if provider_data.provider_name == "ai_fallback" and provider_data.raw_metadata:
            phonetic = provider_data.raw_metadata.get("phonetic_pronunciation")
            if phonetic:
                return Pronunciation(phonetic=phonetic, ipa=None)

        # Check for pronunciation in definitions
        for definition in provider_data.definitions:
            if hasattr(definition, "pronunciation") and definition.pronunciation:
                return definition.pronunciation

    # Fallback pronunciation
    return Pronunciation(phonetic="", ipa=None)


@lookup_group.command("batch")
@click.argument("words", nargs=-1, required=True)
@click.option(
    "--provider",
    type=click.Choice(["all", "wiktionary", "oxford", "dictionary_com", "ai"]),
    default="all",
    help="Dictionary provider to use",
)
@click.option("--save/--no-save", default=True, help="Save results to database")
@click.option("--ai-comprehension/--no-ai", default=True, help="Generate AI synthesis")
def lookup_batch(
    words: tuple[str, ...], provider: str, save: bool, ai_comprehension: bool
) -> None:
    """Look up multiple words at once with AI comprehension.

    WORDS: One or more words to look up
    """
    console.print(
        f"[bold blue]Looking up {len(words)} words with AI comprehension...[/bold blue]"
    )

    for i, word in enumerate(words, 1):
        console.print(f"\n[dim]─── {word.upper()} ({i}/{len(words)}) ───[/dim]")
        asyncio.run(
            _lookup_word_async(word, provider, save, False, False, ai_comprehension, 24)
        )


@lookup_group.command("random")
@click.option("--count", "-c", default=1, help="Number of random words to display")
@click.option(
    "--ai-comprehension/--no-ai", default=True, help="Display AI comprehension"
)
def lookup_random(count: int, ai_comprehension: bool) -> None:
    """Display random words from the database with AI comprehension.

    Useful for vocabulary discovery and review.
    """
    asyncio.run(_lookup_random_async(count, ai_comprehension))


async def _lookup_random_async(count: int, ai_comprehension: bool) -> None:
    """Async implementation of random word lookup."""
    try:
        await get_storage()

        # Get random entries from database
        entries = await DictionaryEntry.find().limit(count).to_list()

        if not entries:
            console.print(
                "[dim]No words found in database. Try adding some words first.[/dim]"
            )
            return

        console.print(
            f"[bold blue]🎲 {count} random words from your collection:[/bold blue]"
        )

        for i, entry in enumerate(entries, 1):
            console.print(f"\n[dim]─── WORD {i}/{len(entries)} ───[/dim]")
            console.print(
                format_word_display(entry, show_examples=True, show_synonyms=True)
            )

    except Exception as e:
        console.print(format_error(f"Failed to fetch random words: {str(e)}"))


@lookup_group.command("history")
@click.option("--count", "-c", default=10, help="Number of recent lookups to show")
def lookup_history(count: int) -> None:
    """Show recent word lookup history."""
    asyncio.run(_lookup_history_async(count))


async def _lookup_history_async(count: int) -> None:
    """Show recent word lookup history."""
    try:
        # Get recent entries sorted by last_updated
        entries = (
            await DictionaryEntry.find()
            .sort(-DictionaryEntry.last_updated)
            .limit(count)
            .to_list()
        )

        if not entries:
            console.print("[dim]No lookup history found.[/dim]")
            return

        console.print(f"[bold blue]📚 Recent {len(entries)} word lookups:[/bold blue]")

        from rich.table import Table

        table = Table(title="Lookup History")
        table.add_column("Word", style="cyan")
        table.add_column("Providers", style="green")
        table.add_column("Last Updated", style="yellow")

        for entry in entries:
            providers = ", ".join(entry.providers.keys())
            last_updated = entry.last_updated.strftime("%Y-%m-%d %H:%M")
            table.add_row(entry.word.text.title(), providers, last_updated)

        console.print(table)

    except Exception as e:
        console.print(format_error(f"Failed to fetch history: {str(e)}"))


# Add the word command as the default
@lookup_group.command(hidden=True)
@click.argument("word")
@click.pass_context
def default(ctx: click.Context, word: str) -> None:
    """Default lookup command."""
    ctx.invoke(lookup_word, word=word)


# Make the group callable to support "floridify lookup word"
lookup_group.callback = lambda: None
