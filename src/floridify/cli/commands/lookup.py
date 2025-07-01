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
from ..utils.formatting import format_error, format_warning

console = Console()
logger = get_logger(__name__)


@click.command()
@click.argument("word")
@click.option(
    "--provider",
    type=click.Choice([p.value for p in DictionaryProvider], case_sensitive=False),
    default=DictionaryProvider.WIKTIONARY.value,
    help="Dictionary provider to use",
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
    provider: str,
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
    provider: str,
    language: tuple[str, ...],
    semantic: bool,
    no_ai: bool,
) -> None:
    """Async implementation of word lookup."""
    logger.info(f"Looking up word: '{word}' with provider: {provider}")

    try:
        # Normalize the query
        normalized_word = normalize_word(word)
        if normalized_word != word:
            logger.debug(f"Normalized: '{word}' � '{normalized_word}'")
            console.print(f"[dim]Normalized: {word} � {normalized_word}[/dim]")

        # Convert languages to enum
        languages = [Language(lang) for lang in language]
        provider_enum = DictionaryProvider(provider)

        # Search for the word
        search_results = await _search_word(
            word=normalized_word,
            languages=languages,
            semantic=semantic,
        )

        if not search_results:
            await _handle_no_results(
                word=normalized_word,
                provider=provider_enum,
                no_ai=no_ai,
            )
            return

        # Use the best match
        best_match = search_results[0].word
        logger.debug(
            f"Best match: '{best_match}' (score: {search_results[0].score:.3f})"
        )

        # Get definition from provider
        definition_data = await _get_provider_definition(best_match, provider_enum)

        # AI synthesis (unless disabled)
        if not no_ai and definition_data:
            synthesized_entry = await _synthesize_with_ai(
                Word(text=best_match), {provider: definition_data}
            )
            _display_synthesized_entry(synthesized_entry)
        elif definition_data:
            _display_provider_data(definition_data, provider_enum)
        else:
            await _handle_no_results(best_match, provider_enum, no_ai)

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
    word: str, provider: DictionaryProvider, no_ai: bool
) -> None:
    """Handle case when no results are found."""
    logger.warning(f"No results found for '{word}'")

    if no_ai or provider == DictionaryProvider.AI_SYNTHETIC:
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
        logger.error(f"AI fallback failed: {e}")
        console.print(format_error(f"Definition lookup failed: {e}"))


def _display_synthesized_entry(entry: Any) -> None:
    """Display synthesized dictionary entry with beautiful formatting."""
    if not entry or not entry.definitions:
        console.print(format_warning("No definitions available"))
        return

    # Header
    header = Text(entry.word.text, style="bold blue")
    if entry.pronunciation.phonetic:
        header.append(f" /{entry.pronunciation.phonetic}/", style="dim cyan")

    console.print(Panel(header, title="Definition", border_style="blue"))

    # Definitions by word type
    for definition in entry.definitions:
        console.print(f"\n[bold cyan]{definition.word_type.value}[/bold cyan]")
        console.print(f"  {definition.definition}")

        # Examples
        if definition.examples.generated:
            for example in definition.examples.generated:
                console.print(f"  [dim]Example: {example.sentence}[/dim]")

        # Synonyms
        if definition.synonyms:
            synonym_text = ", ".join([syn.word.text for syn in definition.synonyms[:5]])
            console.print(f"  [dim]Synonyms: {synonym_text}[/dim]")

    console.print()


def _display_provider_data(data: Any, provider: DictionaryProvider) -> None:
    """Display raw provider data."""
    console.print(
        Panel(
            f"Definition from {provider.display_name}",
            title=data.provider_name.title() if data else "No Data",
            border_style="yellow",
        )
    )

    if not data or not data.definitions:
        console.print("[yellow]No definitions available[/yellow]")
        return

    for definition in data.definitions:
        console.print(f"\n[bold cyan]{definition.word_type.value}[/bold cyan]")
        console.print(f"  {definition.definition}")

        if definition.examples.generated:
            for example in definition.examples.generated:
                console.print(f"  [dim]Example: {example.sentence}[/dim]")


# Add to CLI group in __init__.py
lookup_group = lookup
