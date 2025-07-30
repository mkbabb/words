"""Similar command for finding synonyms with efflorescence ranking."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ...ai import get_openai_connector
from ...constants import DictionaryProvider, Language
from ...core.lookup_pipeline import lookup_word_pipeline
from ...utils.logging import get_logger
from ..utils.formatting import format_error, format_warning

console = Console()
logger = get_logger(__name__)


@click.command()
@click.argument("word")
@click.option(
    "--count",
    "-n",
    type=int,
    default=10,
    help="Number of synonyms to generate (default: 10)",
)
@click.option(
    "--show-definitions",
    is_flag=True,
    help="Show synthesized definitions for each synonym",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force refresh all caches (bypass cache)",
)
def similar(
    word: str,
    count: int,
    show_definitions: bool,
    force: bool,
) -> None:
    """Generate beautiful synonyms ordered by relevance and efflorescence.

    Generates synonyms that balance semantic accuracy with linguistic beauty,
    including words from Latin, French, and other languages that capture
    complex meanings in colorful expressions.

    WORD: The word to find synonyms for
    """
    asyncio.run(_similar_async(word, count, show_definitions, force))


async def _similar_async(
    word: str,
    count: int,
    show_definitions: bool,
    force: bool,
) -> None:
    """Async implementation of similar command."""
    logger.info(f"Finding synonyms for: '{word}' (count: {count})")

    try:
        # First, get the definition of the word to generate better synonyms
        entry = await lookup_word_pipeline(
            word=word,
            providers=[DictionaryProvider.WIKTIONARY],
            languages=[Language.ENGLISH, Language.FRENCH],
            semantic=False,
            no_ai=False,
            force_refresh=force,
        )

        if not entry or not entry.definitions:
            console.print(format_warning(f"No definition found for '{word}'"))
            console.print("Using basic synonym generation without context.")
            base_definition = f"The word '{word}'"
            part_of_speech = "unknown"
        else:
            # Use the first definition as context
            base_definition = entry.definitions[0].definition
            part_of_speech = entry.definitions[0].part_of_speech

        # Generate synonyms using AI
        # Create a minimal Definition object for the synthesis function
        from beanie import PydanticObjectId

        from ...ai.synthesis_functions import synthesize_synonyms
        from ...models import Definition
        definition_obj = Definition(
            word_id=PydanticObjectId(),  # Temporary ID
            part_of_speech=part_of_speech,
            text=base_definition,
            synonyms=[],
            antonyms=[],
            example_ids=[],
        )

        ai_connector = get_openai_connector()
        synonyms = await synthesize_synonyms(
            word=word, definition=definition_obj, ai=ai_connector, count=count, force_refresh=force
        )

        if not synonyms:
            console.print(format_warning(f"No synonyms generated for '{word}'"))
            return

        # Display synonyms in a beautiful table
        await _display_synonyms(word, synonyms, show_definitions, force)

    except Exception as e:
        logger.error(f"Similar command failed: {e}")
        console.print(format_error(f"Failed to find synonyms for '{word}': {e}"))


async def _display_synonyms(
    original_word: str,
    synonyms: list[str],
    show_definitions: bool,
    force: bool,
) -> None:
    """Display synonyms in a beautiful format."""
    # Create header
    header = Text()
    header.append("Synonyms for ", style="dim")
    header.append(original_word, style="bold bright_blue")

    # Create synonyms table
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Word/Phrase", style="bold cyan", width=20)
    table.add_column("Language", style="yellow", width=10)
    table.add_column("Relevance", style="green", width=10)
    table.add_column("Beauty", style="magenta", width=10)
    table.add_column("Explanation", style="white", width=40)

    # Simplified display for list of synonyms
    for i, synonym in enumerate(synonyms):
        # Simple relevance based on position in list
        relevance = 1.0 - (i * 0.1)  # Decrease by 10% for each position
        relevance_text = f"{relevance:.0%}"

        # Color-code relevance
        if relevance >= 0.9:
            relevance_style = "bright_green"
        elif relevance >= 0.7:
            relevance_style = "green"
        elif relevance >= 0.5:
            relevance_style = "yellow"
        else:
            relevance_style = "red"

        table.add_row(
            synonym,  # Just the synonym string
            "English",  # Default language
            Text(relevance_text, style=relevance_style),
            "-",  # No beauty score available
            "-",  # No explanation available
        )

    # Display the main table
    panel = Panel(
        table,
        title=header,
        title_align="left",
        border_style="blue",
        padding=(1, 1),
    )
    console.print(panel)

    # Show definitions if requested
    if show_definitions:
        await _show_synonym_definitions(synonyms, force)


async def _show_synonym_definitions(
    synonyms: list[str],
    force: bool,
) -> None:
    """Show synthesized definitions for each synonym."""
    console.print("\n" + "─" * 70)
    console.print(
        Text("Definitions", style="bold blue"),
        Text(" (showing top 5 synonyms)", style="dim"),
    )

    # Limit to top 5 synonyms to avoid overwhelming output
    top_synonyms = synonyms[:5]

    for i, synonym in enumerate(top_synonyms, 1):
        try:
            # Get definition for this synonym
            entry = await lookup_word_pipeline(
                word=synonym,  # Just the string
                providers=[DictionaryProvider.WIKTIONARY],
                languages=[Language.ENGLISH, Language.FRENCH],
                semantic=True,  # Use semantic search for better matches
                no_ai=False,
                force_refresh=force,
            )

            if entry and entry.definitions:
                # Create a simple definition display
                definition_text = Text()
                definition_text.append(f"{i}. ", style="dim")
                definition_text.append(synonym, style="bold cyan")
                definition_text.append("\n")
                definition_text.append(f"   {entry.definitions[0].definition}", style="white")

                console.print(definition_text)
            else:
                # Fallback if no definition found
                fallback_text = Text()
                fallback_text.append(f"{i}. ", style="dim")
                fallback_text.append(synonym, style="bold cyan")
                fallback_text.append("\n")
                fallback_text.append("   No definition available", style="dim italic")

                console.print(fallback_text)

        except Exception as e:
            logger.warning(f"Failed to get definition for '{synonym}': {e}")
            continue

        # Add spacing between definitions
        if i < len(top_synonyms):
            console.print()


# Make the command available
similar_command = similar
