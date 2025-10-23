"""Word lookup command with AI enhancement and beautiful output."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console

from ...api.services.loaders import DictionaryEntryLoader
from ...core.lookup_pipeline import lookup_word_pipeline
from ...models.dictionary import Definition, DictionaryProvider, Language
from ...models.parameters import LookupParams
from ...models.responses import LookupResponse
from ...utils.json_output import print_json
from ...utils.logging import get_logger
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
    default=[Language.ENGLISH.value],
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
    "--force",
    is_flag=True,
    help="Force refresh all caches (bypass cache)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON (matches API response format)",
)
def lookup(
    word: str,
    provider: tuple[str, ...],
    language: tuple[str, ...],
    semantic: bool,
    no_ai: bool,
    force_refresh: bool,
    output_json: bool,
) -> None:
    """Look up word definitions with AI enhancement.

    WORD: The word to look up

    Use --json for machine-readable output that matches the API response format.
    """
    asyncio.run(
        _lookup_async(word, provider, language, semantic, no_ai, force_refresh, output_json)
    )


async def _lookup_async(
    word: str,
    provider: tuple[str, ...],
    language: tuple[str, ...],
    semantic: bool,
    no_ai: bool,
    force_refresh: bool,
    output_json: bool,
) -> None:
    """Async implementation of word lookup."""
    logger.info(f"Looking up word: '{word}' with providers: {', '.join(provider)}")

    try:
        # Initialize storage
        from ...storage.mongodb import get_storage

        await get_storage()

        # Use shared parameter model for consistency with API
        params = LookupParams(
            providers=list(provider),
            languages=list(language),
            force_refresh=force_refresh,
            no_ai=no_ai,
        )

        # Use the shared lookup pipeline
        result = await lookup_word_pipeline(
            word=word,
            providers=params.providers,
            languages=params.languages,
            semantic=semantic,
            no_ai=params.no_ai,
            force_refresh=params.force_refresh,
        )

        if result:
            # JSON output mode - matches API response format exactly
            if output_json:
                # Convert to API-compatible response using shared loader
                response_dict = await DictionaryEntryLoader.load_as_lookup_response(entry=result)
                response = LookupResponse(**response_dict)
                print_json(response)
            else:
                # Rich terminal output
                # Group definitions by meaning cluster for display
                meaning_groups: dict[str, list[Definition]] = {}

                for definition in result.definitions:
                    # Get meaning cluster
                    cluster = definition.meaning_cluster or "general"
                    if cluster not in meaning_groups:
                        meaning_groups[cluster] = []
                    meaning_groups[cluster].append(definition)

                # Display the synthesized entry
                console.print(
                    format_meaning_based_definition(
                        result, params.languages, params.providers, meaning_groups
                    ),
                )
        else:
            if output_json:
                # JSON error format
                error_response = {"error": "Not found", "word": word}
                print_json(error_response)
            else:
                console.print(format_warning(f"No definition found for '{word}'"))
                if not no_ai:
                    console.print("Consider checking the spelling or trying a different word.")

    except Exception as e:
        logger.error(f"Lookup failed: {e}")
        console.print(format_error(f"Lookup failed: {e}"))


lookup_group = lookup
