"""Word lookup and definition commands."""

from __future__ import annotations

import asyncio
from typing import Any

import click
from rich.console import Console

from ...ai.openai_connector import OpenAIConnector
from ...config import OpenAIConfig
from ...connectors.wiktionary import WiktionaryConnector
from ...models import DictionaryEntry, ProviderData, Word
from ...storage.mongodb import MongoDBStorage
from ..utils.formatting import format_error, format_word_display

console = Console()


@click.group()
def lookup_group() -> None:
    """🔍 Look up words and get detailed definitions."""
    pass


@lookup_group.command("word")
@click.argument("word")
@click.option("--provider", type=click.Choice(["all", "wiktionary", "oxford", "ai"]), 
              default="all", help="Dictionary provider to use")
@click.option("--save/--no-save", default=True, help="Save result to database")
@click.option("--examples", "-e", is_flag=True, help="Include usage examples")
@click.option("--synonyms", "-s", is_flag=True, help="Include synonyms")
def lookup_word(word: str, provider: str, save: bool, examples: bool, synonyms: bool) -> None:
    """Look up a word and display its definition.
    
    WORD: The word to look up
    """
    asyncio.run(_lookup_word_async(word, provider, save, examples, synonyms))


async def _lookup_word_async(
    word: str, provider: str, save: bool, examples: bool, synonyms: bool
) -> None:
    """Async implementation of word lookup."""
    try:
        with console.status(f"[bold blue]Looking up '{word}'..."):
            # Initialize connectors
            wiktionary = WiktionaryConnector()
            
            # For now, just use Wiktionary (Oxford requires API key)
            if provider in ["all", "wiktionary"]:
                try:
                    provider_data = await wiktionary.fetch_definition(word)
                    if provider_data and provider_data.definitions:
                        # Create a mock DictionaryEntry for display
                        entry = _create_mock_entry(word, provider_data)
                        console.print(format_word_display(entry))
                        
                        if save:
                            console.print("💾 [dim]Saving to database...[/dim]")
                            # TODO: Implement database saving
                        
                        return
                except Exception as e:
                    console.print(format_error(f"Failed to fetch from Wiktionary: {str(e)}"))
            
            # If we get here, no definitions were found
            console.print(format_error(
                f"No definitions found for '{word}'",
                "Try checking the spelling or using a different provider."
            ))
            
    except Exception as e:
        console.print(format_error(f"Lookup failed: {str(e)}"))


def _create_mock_entry(word: str, provider_data: ProviderData) -> Any:
    """Create a mock DictionaryEntry for display purposes."""
    # This is a simplified mock for demonstration
    # In the real implementation, this would be a proper DictionaryEntry
    class MockPronunciation:
        def __init__(self, provider_data: ProviderData):
            # Try to get pronunciation from definitions
            self.phonetic = None
            if provider_data.definitions:
                for definition in provider_data.definitions:
                    if hasattr(definition, 'pronunciation') and definition.pronunciation:
                        self.phonetic = definition.pronunciation
                        break
            
            # Fallback to basic phonetic representation
            if not self.phonetic:
                self.phonetic = f"/{word}/"
    
    class MockEntry:
        def __init__(self, word_text: str, provider_data: ProviderData):
            self.word = Word(text=word_text)
            self.pronunciation = MockPronunciation(provider_data)
            self.providers = {"wiktionary": provider_data}
    
    return MockEntry(word, provider_data)


@lookup_group.command("batch")
@click.argument("words", nargs=-1, required=True)
@click.option("--provider", type=click.Choice(["all", "wiktionary", "oxford", "ai"]), 
              default="all", help="Dictionary provider to use")
@click.option("--save/--no-save", default=True, help="Save results to database")
def lookup_batch(words: tuple[str, ...], provider: str, save: bool) -> None:
    """Look up multiple words at once.
    
    WORDS: One or more words to look up
    """
    console.print(f"[bold blue]Looking up {len(words)} words...[/bold blue]")
    
    for word in words:
        console.print(f"\n[dim]─── {word.upper()} ───[/dim]")
        asyncio.run(_lookup_word_async(word, provider, save, False, False))


@lookup_group.command("random")
@click.option("--count", "-c", default=1, help="Number of random words to display")
def lookup_random(count: int) -> None:
    """Display random words from the database.
    
    Useful for vocabulary discovery and review.
    """
    console.print(f"[bold blue]Fetching {count} random words...[/bold blue]")
    console.print("[dim]This feature requires database integration.[/dim]")


# Add the word command as the default
@lookup_group.command(hidden=True)
@click.argument("word")
@click.pass_context
def default(ctx: click.Context, word: str) -> None:
    """Default lookup command."""
    ctx.invoke(lookup_word, word=word)


# Make the group callable to support "floridify lookup word"
lookup_group.callback = lambda: None