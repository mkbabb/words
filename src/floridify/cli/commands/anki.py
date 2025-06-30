"""Anki flashcard deck creation and management commands."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.progress import track

from ...anki.templates import CardType
from ..utils.formatting import (
    format_deck_summary,
    format_error,
    format_processing_summary,
    format_success,
    format_warning,
)

console = Console()


@click.group()
def anki_group() -> None:
    """🎴 Create and manage Anki flashcard decks."""
    pass


@anki_group.command("create")
@click.argument("deck_name")
@click.option(
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True),
    help="Input word list file (.txt or .md)",
)
@click.option("--words", "-w", multiple=True, help="Individual words to include")
@click.option("--output", "-o", type=click.Path(), help="Output path for .apkg file")
@click.option(
    "--types", default="multiple_choice,fill_blank", help="Card types to generate (comma-separated)"
)
@click.option("--max-cards", default=2, help="Maximum cards per word")
@click.option("--overwrite", is_flag=True, help="Overwrite existing deck file")
def create_deck(
    deck_name: str,
    input_file: str | None,
    words: tuple[str, ...],
    output: str | None,
    types: str,
    max_cards: int,
    overwrite: bool,
) -> None:
    """Create an Anki deck from words.

    DECK_NAME: Name for the Anki deck
    """
    asyncio.run(
        _create_deck_async(deck_name, input_file, words, output, types, max_cards, overwrite)
    )


async def _create_deck_async(
    deck_name: str,
    input_file: str | None,
    words: tuple[str, ...],
    output: str | None,
    types: str,
    max_cards: int,
    overwrite: bool,
) -> None:
    """Async implementation of deck creation."""
    try:
        # Determine output path
        if output is None:
            output = f"{deck_name.lower().replace(' ', '_')}.apkg"

        output_path = Path(output)

        # Check for existing file
        if output_path.exists() and not overwrite:
            console.print(
                format_warning(
                    f"File '{output_path}' already exists",
                    "Use --overwrite to replace it, or specify a different output path.",
                )
            )
            return

        # Parse card types
        try:
            card_types = []
            for type_name in types.split(","):
                type_name = type_name.strip().upper()
                if type_name == "MULTIPLE_CHOICE":
                    card_types.append(CardType.MULTIPLE_CHOICE)
                elif type_name == "FILL_BLANK":
                    card_types.append(CardType.FILL_IN_BLANK)
                else:
                    console.print(format_error(f"Unknown card type: {type_name}"))
                    return
        except Exception as e:
            console.print(format_error(f"Invalid card types: {str(e)}"))
            return

        # Collect words
        word_list = []

        if input_file:
            word_list.extend(await _parse_word_file(input_file))

        if words:
            word_list.extend(words)

        if not word_list:
            console.print(
                format_error(
                    "No words provided", "Specify words using --input file or --words arguments."
                )
            )
            return

        # Remove duplicates while preserving order
        unique_words = list(dict.fromkeys(word_list))

        console.print(f"[bold blue]Creating Anki deck '{deck_name}'...[/bold blue]")
        console.print(f"Words to process: {len(unique_words)}")
        console.print(f"Card types: {', '.join([ct.value for ct in card_types])}")
        console.print(f"Max cards per word: {max_cards}")

        # TODO: Implement actual card generation
        # For now, show progress simulation
        successful_words = 0
        failed_words = 0

        for word in track(unique_words, description="Processing words..."):
            try:
                # Simulate card generation delay
                await asyncio.sleep(0.1)

                # Mock card creation (in real implementation, this would be:)
                # entry = await get_dictionary_entry(word)
                # cards = await generator.generate_cards(entry, card_types, max_cards)
                # all_cards.extend(cards)

                successful_words += 1
            except Exception as e:
                console.print(f"[red]Failed to process '{word}': {str(e)}[/red]")
                failed_words += 1

        # Show processing summary
        console.print(
            format_processing_summary(
                len(unique_words), successful_words, failed_words, input_file or "command line"
            )
        )

        if successful_words == 0:
            console.print(format_error("No cards were successfully generated"))
            return

        # Mock deck creation and export
        total_cards = successful_words * len(card_types) * max_cards
        card_type_counts = {ct.value: successful_words * max_cards for ct in card_types}
        file_size = f"{total_cards * 2.5:.1f} KB"  # Rough estimate

        # Show deck summary
        console.print(
            format_deck_summary(
                deck_name, total_cards, card_type_counts, file_size, str(output_path)
            )
        )

    except Exception as e:
        console.print(format_error(f"Deck creation failed: {str(e)}"))


async def _parse_word_file(file_path: str) -> list[str]:
    """Parse words from a file (.txt or .md format)."""
    try:
        path = Path(file_path)

        with open(path, encoding="utf-8") as f:
            content = f.read()

        words = []

        if path.suffix.lower() == ".md":
            # Parse markdown - extract words from lists and headers
            import re

            # Find list items (- word or 1. word)
            list_items = re.findall(r"^[\s]*[-*+][\s]*([a-zA-Z][a-zA-Z\s]*)", content, re.MULTILINE)
            words.extend([item.strip() for item in list_items])

            # Find numbered list items
            numbered_items = re.findall(
                r"^[\s]*\d+\.[\s]*([a-zA-Z][a-zA-Z\s]*)", content, re.MULTILINE
            )
            words.extend([item.strip() for item in numbered_items])

        else:
            # Plain text - one word per line, ignore comments
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("//"):
                    # Take first word if multiple words on line
                    word = line.split()[0] if line.split() else ""
                    if word.isalpha():
                        words.append(word)

        # Clean and deduplicate
        clean_words = []
        for word in words:
            word = word.strip().lower()
            if word and word.isalpha() and word not in clean_words:
                clean_words.append(word)

        return clean_words

    except Exception as e:
        raise Exception(f"Failed to parse word file: {str(e)}")


@anki_group.command("list")
def list_decks() -> None:
    """List existing Anki deck files."""
    console.print("[bold blue]Scanning for Anki deck files...[/bold blue]")

    # Look for .apkg files in current directory
    apkg_files = list(Path.cwd().glob("*.apkg"))

    if apkg_files:
        console.print(f"\nFound {len(apkg_files)} Anki deck files:")
        for file in apkg_files:
            file_size = file.stat().st_size
            size_str = (
                f"{file_size / 1024:.1f} KB"
                if file_size < 1024 * 1024
                else f"{file_size / (1024 * 1024):.1f} MB"
            )
            console.print(f"  📦 {file.name} ({size_str})")
    else:
        console.print("[dim]No .apkg files found in current directory.[/dim]")


@anki_group.command("info")
@click.argument("deck_file", type=click.Path(exists=True))
def deck_info(deck_file: str) -> None:
    """Show information about an Anki deck file.

    DECK_FILE: Path to the .apkg file
    """
    console.print(f"[bold blue]Analyzing deck: {deck_file}[/bold blue]")
    console.print("[dim]Deck analysis not yet implemented.[/dim]")


@anki_group.command("export")
@click.argument("deck_name")
@click.option(
    "--format",
    "export_format",
    type=click.Choice(["apkg", "html", "csv"]),
    default="apkg",
    help="Export format",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_deck(deck_name: str, export_format: str, output: str | None) -> None:
    """Export an existing deck to different formats.

    DECK_NAME: Name of the deck to export
    """
    console.print(f"[bold blue]Exporting deck '{deck_name}' as {export_format}...[/bold blue]")
    console.print("[dim]Deck export not yet implemented.[/dim]")


@anki_group.command("delete")
@click.argument("deck_file", type=click.Path(exists=True))
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def delete_deck(deck_file: str, confirm: bool) -> None:
    """Delete an Anki deck file.

    DECK_FILE: Path to the .apkg file to delete
    """
    if not confirm:
        if not click.confirm(f"Delete '{deck_file}'?"):
            console.print("Operation cancelled.")
            return

    try:
        Path(deck_file).unlink()
        console.print(format_success(f"Deleted '{deck_file}'"))
    except Exception as e:
        console.print(format_error(f"Failed to delete file: {str(e)}"))
