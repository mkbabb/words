"""Anki flashcard export command for word lists."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...ai.factory import create_openai_connector
from ...anki.constants import CardType
from ...anki.generator import AnkiCardGenerator
from ...constants import DictionaryProvider, Language
from ...core.lookup_pipeline import lookup_word_pipeline
from ...list import WordList
from ...storage.mongodb import _ensure_initialized
from ...utils.logging import get_logger
from ..utils.formatting import console

logger = get_logger(__name__)


@click.group(name="anki")
def anki_command() -> None:
    """Create and manage Anki flashcard decks from word lists."""
    pass


@anki_command.command()
@click.argument("word_list_name")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output path for .apkg file (defaults to word list name)",
)
@click.option(
    "--card-types",
    "-t",
    type=click.Choice([ct.value for ct in CardType], case_sensitive=False),
    multiple=True,
    default=["multiple_choice"],
    help="Types of flashcards to generate",
)
@click.option(
    "--max-cards", "-m", type=int, default=1, help="Maximum cards per type per word"
)
@click.option("--deck-name", "-d", help="Anki deck name (defaults to word list name)")
@click.option(
    "--direct/--no-direct",
    default=True,
    help="Try to export directly to Anki via AnkiConnect (default: True)",
)
@click.option(
    "--apkg-fallback/--no-apkg-fallback",
    default=True,
    help="Create .apkg file if direct export fails (default: True)",
)
def export(
    word_list_name: str,
    output: str | None,
    card_types: tuple[str, ...],
    max_cards: int,
    deck_name: str | None,
    direct: bool,
    apkg_fallback: bool,
) -> None:
    """Export word list as Anki flashcard deck.

    Supports both direct export to Anki (via AnkiConnect) and traditional .apkg file export.
    Direct export requires Anki to be running with AnkiConnect add-on installed.

    Generates GRE-level flashcards with beautiful Claude-inspired styling.
    Each word creates fill-in-blank and multiple choice cards using AI.

    Examples:
        floridify anki export vocabulary-list
        floridify anki export gre-words --output ~/decks/gre.apkg
        floridify anki export test-words --card-types fill_in_blank
    """
    asyncio.run(
        _export_async(
            word_list_name,
            output,
            card_types,
            max_cards,
            deck_name,
            direct,
            apkg_fallback,
        )
    )


async def _export_async(
    word_list_name: str,
    output: str | None,
    card_types: tuple[str, ...],
    max_cards: int,
    deck_name: str | None,
    direct: bool,
    apkg_fallback: bool,
) -> None:
    """Async implementation of Anki export."""
    await _ensure_initialized()

    # Load word list
    word_list = await WordList.find_one(WordList.name == word_list_name)
    if not word_list:
        console.print(f"[red]Error:[/red] Word list '{word_list_name}' not found")
        console.print(
            "Use '[cyan]floridify word-list list[/cyan]' to see available word lists"
        )
        return

    # Validate card types
    try:
        parsed_card_types = [CardType(ct) for ct in card_types]
    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid card type: {e}")
        return

    # Set up output path
    if output is None:
        output_path = Path(f"{word_list_name.replace(' ', '_')}.apkg")
    else:
        output_path = Path(output)

    # Set up deck name
    if deck_name is None:
        deck_name = word_list_name.title()

    console.print(f"Exporting word list '[green]{word_list_name}[/green]' to Anki deck")
    console.print(f"Output: {output_path}")
    console.print(f"Card types: {', '.join(ct.value for ct in parsed_card_types)}")
    console.print(f"Words to process: {word_list.unique_words}")

    # Initialize AI connector and card generator
    try:
        openai_connector = create_openai_connector()
        card_generator = AnkiCardGenerator(openai_connector)

        all_cards = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Process each word in the word list
            task = progress.add_task(
                "Generating flashcards...", total=word_list.unique_words
            )

            for word_freq in word_list.words:
                word_text = word_freq.text
                progress.update(task, description=f"Processing '{word_text}'")

                # Look up word to get dictionary entry using batch lookup
                try:
                    entry = await lookup_word_pipeline(
                        word=word_text,
                        providers=[DictionaryProvider.WIKTIONARY],
                        languages=[Language.ENGLISH],
                        semantic=False,
                        no_ai=False,
                    )

                    if entry:
                        # Generate cards for this entry
                        cards = await card_generator.generate_cards(
                            entry,
                            card_types=parsed_card_types,
                            max_cards_per_type=max_cards,
                        )
                        all_cards.extend(cards)

                        console.print(
                            f"  Generated {len(cards)} cards for '{word_text}'"
                        )
                    else:
                        console.print(
                            f"  [yellow]Warning:[/yellow] Could not find definition for '{word_text}'"
                        )

                except Exception as e:
                    logger.error(f"Error processing word '{word_text}': {e}")
                    console.print(
                        f"  [red]Error:[/red] Failed to process '{word_text}': {e}"
                    )

                progress.advance(task)

        if not all_cards:
            console.print(
                "[red]Error:[/red] No flashcards generated. Check that words have definitions."
            )
            return

        # Export flashcards (direct or .apkg)
        console.print(f"\\nExporting {len(all_cards)} flashcards...")

        if direct:
            # Try direct export to Anki
            success, apkg_path = card_generator.export_directly_to_anki(
                all_cards,
                deck_name,
                fallback_to_apkg=apkg_fallback,
                output_path=output_path,
            )

            if success and apkg_path is None:
                # Direct export succeeded, no .apkg file created
                console.print(
                    f"[green]Success![/green] Exported {len(all_cards)} flashcards directly to Anki"
                )
                console.print(f"Deck: [blue]{deck_name}[/blue] (available in Anki now)")
                console.print(
                    "\\n[dim]💡 Cards are now available in your Anki app![/dim]"
                )
            elif success and apkg_path:
                # .apkg file was imported directly into Anki
                console.print(
                    f"[green]Success![/green] Imported {len(all_cards)} flashcards into Anki"
                )
                console.print(f"Deck: [blue]{deck_name}[/blue] (available in Anki now)")
                console.print(f"Backup file: {apkg_path}")
                console.print(f"Preview: {apkg_path.with_suffix('.html')}")
            elif apkg_path:
                # Only .apkg file created
                console.print(
                    f"[yellow]Created .apkg file[/yellow] ({len(all_cards)} flashcards)"
                )
                console.print(f"Deck file: {apkg_path}")
                console.print(f"Preview: {apkg_path.with_suffix('.html')}")
                console.print(
                    "\\nImport the .apkg file into Anki to use the flashcards."
                )
            else:
                console.print("[red]Error:[/red] Failed to export flashcards")
        else:
            # Traditional .apkg export only
            apkg_path = card_generator.export_to_apkg(all_cards, output_path)

            if apkg_path:
                console.print(
                    f"[green]Success![/green] Exported {len(all_cards)} flashcards"
                )
                console.print(f"Deck file: {apkg_path}")
                console.print(f"Preview: {apkg_path.with_suffix('.html')}")
                console.print(
                    "\\nImport the .apkg file into Anki to use the flashcards."
                )
            else:
                console.print("[red]Error:[/red] Failed to export flashcards")

    except Exception as e:
        logger.error(f"Error during Anki export: {e}")
        console.print(f"[red]Error:[/red] {e}")


@anki_command.command()
def status() -> None:
    """Check AnkiConnect availability and status."""
    from ...anki.ankiconnect import AnkiDirectIntegration

    console.print("Checking AnkiConnect status...")

    integration = AnkiDirectIntegration()

    if integration.is_available():
        try:
            # Get additional info
            version = integration.ankiconnect.invoke("version")
            deck_names = integration.ankiconnect.get_deck_names()
            model_names = integration.ankiconnect.get_model_names()

            console.print("[green]✅ AnkiConnect is available![/green]")
            console.print(f"  Version: {version}")
            console.print(f"  Decks available: {len(deck_names)}")
            console.print(f"  Note types available: {len(model_names)}")
            console.print("\\n[dim]💡 Direct Anki export is enabled.[/dim]")

            # Show some deck names if available
            if deck_names:
                console.print("\\nSome available decks:")
                for deck in sorted(deck_names)[:5]:
                    console.print(f"  • {deck}")
                if len(deck_names) > 5:
                    console.print(f"  ... and {len(deck_names) - 5} more")

        except Exception as e:
            console.print(
                f"[yellow]⚠️ AnkiConnect responding but with errors:[/yellow] {e}"
            )
    else:
        console.print("[red]❌ AnkiConnect not available[/red]")
        console.print("\\n[dim]To enable direct Anki export:[/dim]")
        console.print("1. Install AnkiConnect add-on in Anki (code: 2055492159)")
        console.print("2. Ensure Anki is running")
        console.print("3. On macOS, disable App Nap for Anki:")
        console.print("   defaults write net.ichi2.anki NSAppSleepDisabled -bool true")
        console.print(
            "\\n[dim]Without AnkiConnect, .apkg files will be created for manual import.[/dim]"
        )


@anki_command.command()
def info() -> None:
    """Show information about Anki flashcard generation."""
    console.print(
        """
[bold blue]🎴 Anki Flashcard Generation[/bold blue]

[bold]Card Types:[/bold]
  [green]fill_in_blank[/green]     - Context sentences with strategic word removal
  [green]multiple_choice[/green]   - Definition-based questions with distractors

[bold]Features:[/bold]
  • GRE-level academic rigor
  • Claude-inspired beautiful styling
  • Interactive multiple choice with JavaScript
  • Comprehensive answer explanations
  • Examples and synonyms included

[bold]Export Format:[/bold]
  • Standard .apkg files compatible with all Anki platforms
  • HTML preview for web viewing
  • Professional typography and gradients

[bold]Usage:[/bold]
  1. Create a word list: [cyan]floridify word-list create vocab.txt[/cyan]
  2. Export to Anki: [cyan]floridify anki export vocabulary-list[/cyan]
  3. Import .apkg file into Anki desktop or mobile app

[dim]Cards test semantic understanding rather than rote memorization.[/dim]
    """
    )


# Export the command group
__all__ = ["anki_command"]
