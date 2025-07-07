"""Core lookup pipeline shared between CLI commands."""

from __future__ import annotations

from ...ai import create_definition_synthesizer
from ...connectors.dictionary_com import DictionaryComConnector
from ...connectors.wiktionary import WiktionaryConnector
from ...constants import DictionaryProvider, Language
from ...models.models import ProviderData, SynthesizedDictionaryEntry
from ...search import SearchEngine
from ...search.constants import SearchMethod
from ...search.core import SearchResult
from ...utils.logging import get_logger
from ...utils.text_utils import normalize_word

logger = get_logger(__name__)


async def lookup_word_pipeline(
    word: str,
    providers: list[DictionaryProvider] = [DictionaryProvider.WIKTIONARY],
    languages: list[Language] = [Language.ENGLISH],
    semantic: bool = False,
    no_ai: bool = False,
    force_refresh: bool = False,
) -> SynthesizedDictionaryEntry | None:
    """
    Core lookup pipeline that normalizes, searches, gets provider definitions,
    and optionally synthesizes with AI.

    Returns the synthesized entry or None if no definition found.
    """
    try:
        # Normalize the query
        normalized_word = normalize_word(word)

        if normalized_word != word:
            logger.debug(f"Normalized: '{word}' → '{normalized_word}'")

        # Search for the word
        search_results = await _search_word(
            word=normalized_word,
            languages=languages,
            semantic=semantic,
        )

        if not search_results:
            # Try AI fallback if no results and AI is enabled
            if not no_ai:
                logger.info(
                    f"No search results, trying AI fallback for '{normalized_word}'"
                )
                return await _ai_fallback_lookup(normalized_word)

            return None

        # Use the best match
        best_match = search_results[0].word
        logger.debug(
            f"Best match: '{best_match}' (score: {search_results[0].score:.3f})"
        )

        # Get definition from provider
        providers_data = []

        for provider in providers:
            provider_data = await _get_provider_definition(best_match, provider, force_refresh)

            if not provider_data:
                # Try AI fallback if provider fails and AI is enabled
                if not no_ai:
                    logger.info(
                        f"Provider failed, trying AI fallback for '{best_match}'"
                    )
                    return await _ai_fallback_lookup(best_match)

                return None

            providers_data.append(provider_data)

        # Synthesize with AI if enabled
        if not no_ai:
            try:
                synthesized_entry = await _synthesize_with_ai(
                    word=best_match,
                    providers=providers_data,
                )

                if synthesized_entry:
                    logger.debug(f"Successfully synthesized entry for '{best_match}'")
                    return synthesized_entry
                else:
                    logger.warning(f"AI synthesis failed for '{best_match}'")
                    return None

            except Exception as e:
                logger.error(f"AI synthesis failed: {e}")
                return None
        else:
            # When AI is disabled, we can't return a SynthesizedDictionaryEntry
            # This function should only be used when AI synthesis is expected
            logger.warning(
                f"AI synthesis disabled, cannot return synthesized entry for '{best_match}'"
            )
            return None

    except Exception as e:
        logger.error(f"Lookup pipeline failed: {e}")
        return None


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


async def _get_provider_definition(
    word: str, provider: DictionaryProvider, force_refresh: bool = False
) -> ProviderData | None:
    """Get definition from specified provider."""
    logger.debug(f"Fetching definition from {provider.value}")

    try:
        connector: WiktionaryConnector | DictionaryComConnector | None = None

        if provider == DictionaryProvider.WIKTIONARY:
            connector = WiktionaryConnector(force_refresh=force_refresh)
        elif provider == DictionaryProvider.OXFORD:
            # Would need API credentials from config
            logger.warning("Oxford provider requires API credentials")
            return None
        elif provider == DictionaryProvider.DICTIONARY_COM:
            connector = DictionaryComConnector(force_refresh=force_refresh)
        else:
            logger.warning(f"Unsupported provider: {provider.value}")
            return None

        if connector:
            result = await connector.fetch_definition(word)
            logger.debug(f"Provider {provider.value} returned: {bool(result)}")
            return result

        return None

    except Exception as e:
        logger.error(f"Provider {provider.value} failed: {e}")
        return None


async def _synthesize_with_ai(
    word: str, providers: list[ProviderData]
) -> SynthesizedDictionaryEntry | None:
    """Synthesize definition using AI."""
    logger.debug(f"AI synthesis for '{word}'")

    try:
        synthesizer = create_definition_synthesizer()
        return await synthesizer.synthesize_entry(word, providers)
    except Exception as e:
        logger.error(f"AI synthesis failed: {e}")
        return None


async def _ai_fallback_lookup(word: str) -> SynthesizedDictionaryEntry | None:
    """AI fallback when no provider definitions are found."""
    logger.debug(f"AI fallback for '{word}'")

    try:
        synthesizer = create_definition_synthesizer()
        ai_entry = await synthesizer.generate_fallback_entry(word)

        if ai_entry and ai_entry.definitions:
            logger.debug(f"AI fallback successful for '{word}'")
            return ai_entry
        else:
            logger.warning(f"AI fallback failed for '{word}'")
            return None

    except Exception as e:
        logger.error(f"AI fallback failed: {e}")
        return None
