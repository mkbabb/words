"""Word lookup command with AI enhancement and beautiful output."""

from __future__ import annotations

import asyncio
from typing import Any

import click
from rich.console import Console

from ...constants import DictionaryProvider, Language
from ...utils.logging import get_logger
from ..utils.formatting import (
    format_error,
    format_meaning_based_definition,
    format_warning,
)
from ..utils.lookup_core import lookup_word_pipeline

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
@click.option(
    "--force-refresh",
    is_flag=True,
    help="Force refresh all caches (bypass cache)",
)
def lookup(
    word: str,
    provider: tuple[str, ...],
    language: tuple[str, ...],
    semantic: bool,
    no_ai: bool,
    force_refresh: bool,
) -> None:
    """Look up word definitions with AI enhancement.

    WORD: The word to look up
    """
    asyncio.run(_lookup_async(word, provider, language, semantic, no_ai, force_refresh))


async def _lookup_async(
    word: str,
    provider: tuple[str, ...],
    language: tuple[str, ...],
    semantic: bool,
    no_ai: bool,
    force_refresh: bool,
) -> None:
    """Async implementation of word lookup."""
    logger.info(f"Looking up word: '{word}' with providers: {', '.join(provider)}")

    try:
        # Convert to enums
        languages = [Language(lang) for lang in language]
        providers = [DictionaryProvider(p) for p in provider]

        # Use the shared lookup pipeline
        result = await lookup_word_pipeline(
            word=word,
            providers=providers,
            languages=languages,
            semantic=semantic,
            no_ai=no_ai,
            force_refresh=force_refresh,
        )

        if result:
            # Group definitions by meaning cluster for display
            meaning_groups: dict[str, list[Any]] = {}

            for definition in result.definitions:
                cluster = getattr(definition, 'meaning_cluster', 'general') or 'general'
                if cluster not in meaning_groups:
                    meaning_groups[cluster] = []
                meaning_groups[cluster].append(definition)

            # Display the synthesized entry
            console.print(format_meaning_based_definition(result, languages, providers, meaning_groups))
        else:
            console.print(format_warning(f"No definition found for '{word}'"))
            if not no_ai:
                console.print(
                    "Consider checking the spelling or trying a different word."
                )

    except Exception as e:
        logger.error(f"Lookup failed: {e}")
        console.print(format_error(f"Lookup failed: {e}"))



lookup_group = lookup
