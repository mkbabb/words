"""List command for batch dictionary operations."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ...core.lookup_pipeline import lookup_word_pipeline
from ...list import WordList
from ...list.parser import generate_name, parse_file
from ...storage.mongodb import _ensure_initialized
from ...utils.logging import get_logger
from ..utils.formatting import console

logger = get_logger(__name__)

# Global batch size for dictionary lookup processing
BATCH_SIZE = 10


@click.group(name="list")
def list_command() -> None:
    """Manage word lists with dictionary lookup and storage."""
    pass


@list_command.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--name", "-n", help="Word list name (auto-generated if not provided)")
def create(
    input_file: str,
    name: str | None,
) -> None:
    """Create a new word list from file."""
    asyncio.run(
        _create_async(
            Path(input_file),
            name,
        )
    )


async def _create_async(
    input_file: Path,
    name: str | None,
) -> None:
    """Async implementation of create command."""
    logger.info(f"Processing word list from: {input_file}")

    # Note: provider, language, semantic, no_ai parameters used for lookup configuration

    # Parse the word list
    parsed = parse_file(input_file)

    console.print(f"Parsed {len(parsed.words)} words from {input_file.name}")

    # Generate name if not provided
    if not name:
        name = generate_name(parsed.words)
        console.print(f"Generated name: [cyan]{name}[/cyan]")

    # Initialize database
    await _ensure_initialized()

    # Check if word list already exists
    existing = await WordList.find_one(WordList.name == name)
    if existing:
        console.print(f"Word list '[yellow]{name}[/yellow]' already exists")
        if not click.confirm("Update existing word list?"):
            return
        word_list = existing
    else:
        word_list = WordList(
            name=name,
            hash_id=WordList.generate_hash(parsed.words),
            metadata=parsed.metadata,
        )

    # Add words to the list
    word_list.add_words(parsed.words)

    # Save word list before processing lookups
    await word_list.save()

    console.print(
        f"Word list '[green]{name}[/green]' saved with {word_list.unique_words} unique words"
    )
    console.print(f"Total occurrences: {word_list.total_words}")
    console.print("Starting batch dictionary lookup...")

    # Process words with dictionary lookup in batches
    await _process_words_batch([wf.text for wf in word_list.words])

    console.print("Dictionary lookup processing completed!")


@list_command.command()
@click.argument("name")
@click.option(
    "--num",
    "-n",
    type=int,
    default=None,
    help="Number of most frequent words to show (default: all)",
)
def show(name: str, num: int | None) -> None:
    """Show details of a word list."""
    asyncio.run(_show_async(name, num))


async def _show_async(name: str, num: int | None) -> None:
    """Async implementation of show command."""
    await _ensure_initialized()

    word_list = await WordList.find_one(WordList.name == name)
    if not word_list:
        console.print(f"Word list '[red]{name}[/red]' not found")
        return

    console.print(f"Word List: [cyan]{word_list.name}[/cyan]")
    console.print(f"Hash ID: {word_list.hash_id}")
    console.print(f"Unique words: {word_list.unique_words}")
    console.print(f"Total occurrences: {word_list.total_words}")
    console.print(f"Created: {word_list.created_at.strftime('%Y-%m-%d %H:%M')}")
    console.print(f"Updated: {word_list.updated_at.strftime('%Y-%m-%d %H:%M')}")

    # Show most frequent words with heat mapping
    # If num is None, get all words (up to 20 for display), otherwise get the requested number
    num = num if num is not None and num > 0 else len(word_list.words)
    most_frequent = word_list.get_most_frequent(num)
    num = min(num, len(most_frequent))  # Limit to available words

    console.print(f"\nMost frequent words (showing {num}):")

    # Create frequency heat map
    max_freq = max(wf.frequency for wf in most_frequent)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=4)
    table.add_column("Word", style="bold")
    table.add_column("Frequency", justify="right")
    table.add_column("Heat", width=10)

    for i, wf in enumerate(most_frequent[:num], 1):
        # Calculate heat intensity (0-100)
        heat_percent = int((wf.frequency / max_freq) * 100)

        # Color based on frequency
        if heat_percent >= 80:
            heat_color = "red"
            heat_bar = "█" * 8
        elif heat_percent >= 60:
            heat_color = "yellow"
            heat_bar = "█" * 6 + "▓" * 2
        elif heat_percent >= 40:
            heat_color = "green"
            heat_bar = "█" * 4 + "▓" * 4
        elif heat_percent >= 20:
            heat_color = "blue"
            heat_bar = "█" * 2 + "▓" * 6
        else:
            heat_color = "dim"
            heat_bar = "▓" * 8

        table.add_row(
            str(i),
            wf.text,
            f"{wf.frequency}x",
            f"[{heat_color}]{heat_bar}[/{heat_color}]",
        )

    console.print(table)


@list_command.command("all")
def list_word_lists() -> None:
    """List all word lists."""
    asyncio.run(_list_async())


async def _list_async() -> None:
    """Async implementation of list command."""
    await _ensure_initialized()

    word_lists = await WordList.find_all().to_list()
    if not word_lists:
        console.print("No word lists found")
        return

    console.print(f"Found {len(word_lists)} word lists:\n")

    for wl in sorted(word_lists, key=lambda x: x.updated_at, reverse=True):
        console.print(f"[cyan]{wl.name}[/cyan]")
        console.print(f"  {wl.unique_words} unique words, {wl.total_words} total")
        console.print(f"  Updated: {wl.updated_at.strftime('%Y-%m-%d %H:%M')}")
        console.print()


@list_command.command()
@click.argument("name")
@click.argument("input_file", type=click.Path(exists=True))
def update(name: str, input_file: str) -> None:
    """Update an existing word list with new words."""
    asyncio.run(_update_async(name, Path(input_file)))


async def _update_async(name: str, input_file: Path) -> None:
    """Async implementation of update command."""
    await _ensure_initialized()

    word_list = await WordList.find_one(WordList.name == name)
    if not word_list:
        console.print(f"Word list '[red]{name}[/red]' not found")
        return

    # Parse new words
    parsed = parse_file(input_file)

    console.print(f"Adding {len(parsed.words)} words to '[cyan]{name}[/cyan]'")

    old_count = word_list.unique_words
    word_list.add_words(parsed.words)

    # Process new words with dictionary lookup
    new_words_to_process = [
        wf.text
        for wf in word_list.words
        if wf.text.lower() in [w.lower() for w in parsed.words]
    ]
    await _process_words_batch(new_words_to_process)

    await word_list.save()

    new_words = word_list.unique_words - old_count
    console.print(f"Added {new_words} new words to '[green]{name}[/green]'")
    console.print(
        f"Total: {word_list.unique_words} unique words, {word_list.total_words} occurrences"
    )


@list_command.command()
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to delete this word list?")
def delete(name: str) -> None:
    """Delete a word list."""
    asyncio.run(_delete_async(name))


async def _delete_async(name: str) -> None:
    """Async implementation of delete command."""
    await _ensure_initialized()

    word_list = await WordList.find_one(WordList.name == name)
    if not word_list:
        console.print(f"Word list '[red]{name}[/red]' not found")
        return

    await word_list.delete()
    console.print(f"Deleted word list '[red]{name}[/red]'")


async def _process_words_batch(
    words: list[str],
) -> None:
    """Process words in batches with dictionary lookup pipeline."""
    if not words:
        return

    total_words = len(words)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(
            f"Processing {total_words} words...", total=total_words
        )

        # Process in batches
        for i in range(0, total_words, BATCH_SIZE):
            batch = words[i : i + BATCH_SIZE] if words else []

            # Create lookup tasks for each word in batch
            tasks = []
            for word in batch:
                tasks.append(_lookup_word(word))

            # Execute batch
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Track success/failure
                successful = 0
                for word, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to process '{word}': {result}")
                    elif result:
                        successful += 1
                        logger.debug(f"Successfully processed '{word}'")
                    else:
                        logger.debug(f"No definition found for '{word}'")

                logger.debug(
                    f"Batch {i//BATCH_SIZE + 1}: {successful}/{len(batch)} successful"
                )

            except Exception as e:
                logger.warning(f"Batch processing error: {e}")

            progress.update(task, advance=len(batch))

    logger.info(f"Completed processing {total_words} words")


async def _lookup_word(word: str) -> bool:
    """Lookup a single word through the full lookup pipeline."""
    try:
        result = await lookup_word_pipeline(
            word=word,
        )

        if result:
            logger.debug(f"Successfully looked up '{word}'")
            return True
        else:
            logger.debug(f"No definition found for '{word}'")
            return False

    except Exception as e:
        logger.warning(f"Error looking up '{word}': {e}")
        return False
