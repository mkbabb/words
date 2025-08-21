"""Search commands for CLI with proper SearchEngine integration."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.table import Table

from ...core.search_pipeline import search_word_pipeline
from ...models.base import Language
from ...search.constants import SearchMode
from ...search.language import get_language_search
from ...utils.logging import get_logger
from ..utils.formatting import format_error, format_warning

console = Console()
logger = get_logger(__name__)


@click.group()
def search_group() -> None:
    """🔎 Search functionality - find words across lexicons."""


@search_group.command("word")
@click.argument("query")
@click.option(
    "--language",
    type=click.Choice([lang.value for lang in Language], case_sensitive=False),
    multiple=True,
    default=[Language.ENGLISH.value],
    help="Lexicon languages to search",
)
@click.option(
    "--mode",
    type=click.Choice([mode.value for mode in SearchMode], case_sensitive=False),
    default=SearchMode.SMART.value,
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
def search_word(
    query: str,
    language: tuple[str, ...],
    mode: str,
    max_results: int,
    min_score: float | None,
    force_rebuild: bool,
) -> None:
    """Search for words in lexicons.

    QUERY: The word or phrase to search for
    """
    asyncio.run(_search_word_async(query, language, mode, max_results, min_score, force_rebuild))


@search_group.command("similar")
@click.argument("word")
@click.option(
    "--language",
    type=click.Choice([lang.value for lang in Language], case_sensitive=False),
    multiple=True,
    default=[Language.ENGLISH.value],
    help="Lexicon languages to search",
)
@click.option(
    "--max-results",
    type=int,
    default=10,
    help="Maximum number of similar words to show",
)
def search_similar(word: str, language: tuple[str, ...], max_results: int) -> None:
    """Find words similar to the given word using semantic search.

    WORD: The word to find similar words for
    """
    asyncio.run(_search_similar_async(word, language, max_results))


@search_group.command("stats")
@click.option(
    "--language",
    type=click.Choice([lang.value for lang in Language], case_sensitive=False),
    multiple=True,
    default=[Language.ENGLISH.value],
    help="Lexicon languages to show stats for",
)
def search_stats(language: tuple[str, ...]) -> None:
    """Show search engine statistics."""
    asyncio.run(_search_stats_async(language))


async def _search_word_async(
    query: str,
    language: tuple[str, ...],
    mode: str,
    max_results: int,
    min_score: float | None,
    force_rebuild: bool,
) -> None:
    """Async implementation of word search."""
    logger.info(f"Searching for: '{query}' (mode: {mode})")

    try:
        # Convert to enums
        languages = [Language(lang) for lang in language]

        # Perform search using the pipeline
        search_mode = SearchMode(mode)

        results = await search_word_pipeline(
            word=query,
            languages=languages,
            mode=search_mode,
            max_results=max_results,
            min_score=min_score,
            force_rebuild=force_rebuild,
        )

        if results:
            # Create a rich table for results
            table = Table(title=f"Search Results for '{query}'")
            table.add_column("Word", style="cyan")
            table.add_column("Score", style="green")
            table.add_column("Method", style="yellow")
            table.add_column("Type", style="blue")

            for result in results:
                word_type = "entry"
                table.add_row(result.word, f"{result.score:.3f}", result.method.value, word_type)

            console.print(table)
            console.print(f"\n✅ Found {len(results)} result(s)")
        else:
            console.print(format_warning(f"No results found for '{query}'"))
            if search_mode != SearchMode.SEMANTIC:
                console.print("💡 Try using --mode=semantic for broader matches")

    except Exception as e:
        logger.error(f"Search failed: {e}")
        console.print(format_error(f"Search failed: {e}"))


async def _search_similar_async(word: str, language: tuple[str, ...], max_results: int) -> None:
    """Async implementation of similar word search."""
    logger.info(f"Finding similar words for: '{word}'")

    try:
        # Convert to enums
        languages = [Language(lang) for lang in language]

        # Use semantic search to find similar words
        results = await search_word_pipeline(
            word=word,
            languages=languages,
            mode=SearchMode.SEMANTIC,  # Use semantic mode for similar words
            max_results=max_results + 1,  # +1 to account for the original word
            min_score=0.6,  # Default minimum score for similar words
        )

        # Filter out the original word
        filtered_results = [result for result in results if result.word.lower() != word.lower()][
            :max_results
        ]

        if filtered_results:
            # Create a rich table for similar words
            table = Table(title=f"Words Similar to '{word}'")
            table.add_column("Word", style="cyan")
            table.add_column("Similarity", style="green")
            table.add_column("Type", style="blue")

            for result in filtered_results:
                word_type = "entry"
                table.add_row(result.word, f"{result.score:.3f}", word_type)

            console.print(table)
            console.print(f"\n✅ Found {len(filtered_results)} similar word(s)")
        else:
            console.print(format_warning(f"No similar words found for '{word}'"))

    except Exception as e:
        logger.error(f"Similar word search failed: {e}")
        console.print(format_error(f"Similar word search failed: {e}"))


async def _search_stats_async(language: tuple[str, ...]) -> None:
    """Async implementation of search stats."""
    logger.info("Getting search engine statistics")

    try:
        # Convert to enums
        languages = [Language(lang) for lang in language]

        # Get language search instance
        search_engine = await get_language_search(languages=languages)

        # Get stats from the search engine
        stats = search_engine.get_stats()

        # Create a rich table for stats
        table = Table(title="Search Engine Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Languages", ", ".join(lang.value for lang in languages))
        table.add_row("Total Vocabulary", str(stats.get("vocabulary_size", "unknown")))
        table.add_row("Words", str(stats.get("words", "unknown")))
        table.add_row("Phrases", str(stats.get("phrases", "unknown")))
        table.add_row("Min Score Threshold", str(stats.get("min_score", "unknown")))

        console.print(table)

    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        console.print(format_error(f"Stats retrieval failed: {e}"))
