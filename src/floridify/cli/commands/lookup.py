"""Word lookup command with AI enhancement and beautiful output."""

from __future__ import annotations

import asyncio
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ...ai import create_definition_synthesizer
from ...connectors.dictionary_com import DictionaryComConnector
from ...connectors.wiktionary import WiktionaryConnector
from ...constants import DictionaryProvider, Language
from ...models import Word
from ...search import SearchEngine, SearchResult
from ...search.constants import SearchMethod
from ...utils.logging import get_logger
from ...utils.normalization import normalize_word
from ..utils.formatting import (
    format_error,
    format_meaning_based_definition,
    format_warning,
)

console = Console()
logger = get_logger(__name__)


@click.command()
@click.argument("word")
@click.option(
    "--provider",
    type=click.Choice([p.value for p in DictionaryProvider], case_sensitive=False),
    multiple=True,
    default=[DictionaryProvider.WIKTIONARY.value],
    help="Dictionary providers to use (can specify multiple)",
)
@click.option(
    "--language",
    type=click.Choice([lang.value for lang in Language], case_sensitive=False),
    multiple=True,
    default=[Language.ENGLISH.value, Language.FRENCH.value],
    help="Lexicon languages to search",
)
@click.option(
    "--semantic",
    is_flag=True,
    help="Force semantic search mode",
)
@click.option(
    "--no-ai",
    is_flag=True,
    help="Skip AI synthesis",
)
def lookup(
    word: str,
    provider: tuple[str, ...],
    language: tuple[str, ...],
    semantic: bool,
    no_ai: bool,
) -> None:
    """Look up word definitions with AI enhancement.

    WORD: The word to look up
    """
    asyncio.run(_lookup_async(word, provider, language, semantic, no_ai))


async def _lookup_async(
    word: str,
    provider: tuple[str, ...],
    language: tuple[str, ...],
    semantic: bool,
    no_ai: bool,
) -> None:
    """Async implementation of word lookup."""
    logger.info(f"Looking up word: '{word}' with providers: {', '.join(provider)}")

    try:
        # Normalize the query
        normalized_word = normalize_word(word)
        if normalized_word != word:
            logger.debug(f"Normalized: '{word}' � '{normalized_word}'")
            console.print(f"[dim]Normalized: {word} � {normalized_word}[/dim]")

        # Convert languages and providers to enums
        languages = [Language(lang) for lang in language]
        providers = [DictionaryProvider(p) for p in provider]

        # Search for the word
        search_results = await _search_word(
            word=normalized_word,
            languages=languages,
            semantic=semantic,
        )

        if not search_results:
            await _handle_no_results(
                word=normalized_word,
                providers=providers,
                no_ai=no_ai,
            )
            return

        # Use the best match
        best_match = search_results[0].word
        logger.debug(
            f"Best match: '{best_match}' (score: {search_results[0].score:.3f})"
        )

        # Get definitions from all providers
        provider_data = {}
        for provider_enum in providers:
            data = await _get_provider_definition(best_match, provider_enum)
            if data:
                provider_data[provider_enum.value] = data

        # AI synthesis (unless disabled)
        if not no_ai and provider_data:
            synthesized_entry = await _synthesize_with_ai(
                Word(text=best_match), provider_data
            )
            _display_synthesized_entry(synthesized_entry, provider_data)
        elif provider_data:
            _display_multiple_providers(provider_data)
        else:
            await _handle_no_results(best_match, providers, no_ai)

    except Exception as e:
        logger.error(f"Lookup failed: {e}")
        console.print(format_error(f"Lookup failed: {e}"))


async def _search_word(
    word: str, languages: list[Language], semantic: bool
) -> list[SearchResult]:
    """Search for word using the search engine."""
    logger.debug(
        f"Searching for '{word}' in languages: {[lang.value for lang in languages]}"
    )

    # Initialize search engine

    search_engine = SearchEngine(
        languages=languages,
        enable_semantic=semantic,
    )

    await search_engine.initialize()

    # Perform search
    if semantic:
        # Force semantic search
        results = await search_engine.search(
            word, max_results=10, methods=[SearchMethod.SEMANTIC]
        )
    else:
        # Use hybrid approach
        results = await search_engine.search(word, max_results=10)

    logger.debug(f"Search returned {len(results)} results")
    return results


async def _get_provider_definition(word: str, provider: DictionaryProvider) -> Any:
    """Get definition from specified provider."""
    logger.debug(f"Fetching definition from {provider.value}")

    try:
        connector: WiktionaryConnector | DictionaryComConnector | None = None
        if provider == DictionaryProvider.WIKTIONARY:
            connector = WiktionaryConnector()
        elif provider == DictionaryProvider.OXFORD:
            # Would need API credentials from config
            console.print(format_warning("Oxford provider requires API credentials"))
            return None
        elif provider == DictionaryProvider.DICTIONARY_COM:
            connector = DictionaryComConnector()
        elif provider == DictionaryProvider.AI_SYNTHETIC:
            # Skip provider lookup for AI-only mode
            return None
        else:
            raise ValueError(f"Unknown provider: {provider}")

        if connector:
            return await connector.fetch_definition(word)
        return None

    except Exception as e:
        logger.error(f"Provider {provider.value} failed: {e}")
        console.print(format_warning(f"{provider.value} lookup failed: {e}"))
        return None


async def _synthesize_with_ai(word: Word, providers: dict[str, Any]) -> Any:
    """Synthesize definition using AI."""
    logger.debug(f"AI synthesis for '{word.text}'")

    try:
        synthesizer = create_definition_synthesizer()
        return await synthesizer.synthesize_entry(word, providers)
    except Exception as e:
        logger.error(f"AI synthesis failed: {e}")
        console.print(format_warning(f"AI synthesis failed: {e}"))
        return None


async def _handle_no_results(
    word: str, providers: list[DictionaryProvider], no_ai: bool
) -> None:
    """Handle case when no results are found."""
    logger.warning(f"No results found for '{word}'")

    if no_ai or DictionaryProvider.AI_SYNTHETIC in providers:
        console.print(format_error(f"No definition found for '{word}'"))
        return

    # Try AI fallback
    console.print("[yellow]No definition found. Trying AI fallback...[/yellow]")

    try:
        synthesizer = create_definition_synthesizer()
        ai_entry = await synthesizer.generate_fallback_entry(Word(text=word))

        if ai_entry and ai_entry.definitions:
            _display_synthesized_entry(ai_entry)
        else:
            console.print(format_error(f"No definition available for '{word}'"))

    except Exception as e:
        error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
        logger.error(f"AI fallback failed: {error_msg}")
        console.print(format_error(f"Definition lookup failed: {error_msg}"))


def _display_synthesized_entry(
    entry: Any, provider_data: dict[str, Any] | None = None
) -> None:
    """Display synthesized dictionary entry with beautiful formatting."""
    if not entry or not entry.definitions:
        console.print(format_warning("No definitions available"))
        return

    # Extract sources for display
    sources = list(provider_data.keys()) if provider_data else ["AI Generated"]

    # Group definitions by AI-extracted meaning clusters if available
    meaning_groups = _group_definitions_by_ai_clusters(entry.definitions)

    # Always use meaning-based formatter (it handles single meanings properly)
    formatted_panel = format_meaning_based_definition(entry, meaning_groups, sources)

    console.print(formatted_panel)


def _group_definitions_by_ai_clusters(definitions: list[Any]) -> dict[str, list[Any]]:
    """Group definitions by AI-extracted meaning clusters."""
    groups: dict[str, list[Any]] = {}

    for definition in definitions:
        # Use AI-extracted meaning cluster if available
        if hasattr(definition, 'meaning_cluster') and definition.meaning_cluster:
            meaning_key = definition.meaning_cluster
        else:
            # Fallback to generic grouping
            meaning_key = "general"

        if meaning_key not in groups:
            groups[meaning_key] = []
        groups[meaning_key].append(definition)

    return groups


def _display_multiple_providers(provider_data: dict[str, Any]) -> None:
    """Display data from multiple providers."""
    console.print(
        Panel(
            Text("Multiple Provider Results"),
            title="Dictionary Lookup",
            border_style="blue",
        )
    )

    for provider_name, data in provider_data.items():
        console.print(f"\n[bold cyan]{provider_name.title()}[/bold cyan]")
        if data and hasattr(data, 'definitions') and data.definitions:
            for definition in data.definitions[:2]:  # Show first 2 definitions
                console.print(
                    f"  {definition.word_type.value}: {definition.definition}"
                )
        else:
            console.print("  [dim]No definitions available[/dim]")

    console.print("\n[dim]💡 Use AI synthesis for enhanced definitions[/dim]")


lookup_group = lookup
