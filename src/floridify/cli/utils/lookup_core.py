"""Core lookup pipeline shared between CLI commands."""

from __future__ import annotations

from typing import Any

from ...ai import create_definition_synthesizer
from ...connectors.dictionary_com import DictionaryComConnector
from ...connectors.wiktionary import WiktionaryConnector
from ...constants import DictionaryProvider, Language
from ...models.dictionary import SynthesizedDictionaryEntry, Word
from ...search import SearchEngine
from ...search.constants import SearchMethod
from ...utils.logging import get_logger
from ...utils.normalization import normalize_word

logger = get_logger(__name__)

# Global search engine instance for batch operations
_search_engine_cache: SearchEngine | None = None


async def lookup_word_pipeline(
    word: str,
    provider: DictionaryProvider = DictionaryProvider.WIKTIONARY,
    language: Language = Language.ENGLISH,
    semantic: bool = False,
    no_ai: bool = False,
) -> SynthesizedDictionaryEntry | None:
    """
    Core lookup pipeline that normalizes, searches, gets provider definitions,
    and optionally synthesizes with AI.
    
    Returns the synthesized entry or None if no definition found.
    """
    logger.info(f"Looking up word: '{word}' with provider: {provider}")

    try:
        # Normalize the query
        normalized_word = normalize_word(word)
        if normalized_word != word:
            logger.debug(f"Normalized: '{word}' → '{normalized_word}'")

        # Search for the word
        search_results = await _search_word(
            word=normalized_word,
            languages=[language],
            semantic=semantic,
        )

        if not search_results:
            # Try AI fallback if no results and AI is enabled
            if not no_ai:
                logger.info(f"No search results, trying AI fallback for '{normalized_word}'")
                return await _ai_fallback_lookup(normalized_word)
            return None

        # Use the best match
        best_match = search_results[0].word
        logger.debug(
            f"Best match: '{best_match}' (score: {search_results[0].score:.3f})"
        )

        # Get definition from provider
        provider_data = await _get_provider_definition(best_match, provider)
        if not provider_data:
            # Try AI fallback if provider fails and AI is enabled
            if not no_ai:
                logger.info(f"Provider failed, trying AI fallback for '{best_match}'")
                return await _ai_fallback_lookup(best_match)
            return None

        # Synthesize with AI if enabled
        if not no_ai:
            try:
                word_obj = Word(text=best_match)
                providers_dict = {provider.value: provider_data}
                synthesized_entry = await _synthesize_with_ai(word_obj, providers_dict)
                
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
            logger.warning(f"AI synthesis disabled, cannot return synthesized entry for '{best_match}'")
            return None

    except Exception as e:
        logger.error(f"Lookup pipeline failed: {e}")
        return None


async def init_batch_search(
    languages: list[Language], semantic: bool = False
) -> SearchEngine:
    """Initialize search engine for batch operations."""
    global _search_engine_cache
    
    if _search_engine_cache is None:
        logger.info("🚀 Initializing search engine for batch processing")
        _search_engine_cache = SearchEngine(
            languages=languages,
            enable_semantic=semantic,
        )
        await _search_engine_cache.initialize()
    
    return _search_engine_cache


def clear_batch_search() -> None:
    """Clear cached search engine."""
    global _search_engine_cache
    _search_engine_cache = None


async def lookup_word_batch(
    word: str,
    search_engine: SearchEngine,
    provider: DictionaryProvider = DictionaryProvider.WIKTIONARY,
    no_ai: bool = False,
) -> SynthesizedDictionaryEntry | None:
    """
    Optimized lookup pipeline for batch operations that reuses search engine.
    
    Args:
        word: Word to look up
        search_engine: Pre-initialized search engine instance
        provider: Dictionary provider to use
        no_ai: Whether to skip AI synthesis
    
    Returns:
        Synthesized entry or None if no definition found
    """
    logger.debug(f"Batch lookup for word: '{word}' with provider: {provider}")

    try:
        # Normalize the query
        normalized_word = normalize_word(word)
        if normalized_word != word:
            logger.debug(f"Normalized: '{word}' → '{normalized_word}'")

        # Search using pre-initialized engine
        search_results = await search_engine.search(
            query=normalized_word,
            methods=[SearchMethod.EXACT],  # Start with exact match
        )

        if not search_results:
            # Try fuzzy search if exact fails
            search_results = await search_engine.search(
                query=normalized_word,
                methods=[SearchMethod.FUZZY],
            )

        if not search_results:
            # Try AI fallback if no results and AI is enabled
            if not no_ai:
                logger.info(f"No search results for '{normalized_word}', trying AI fallback")
                return await _ai_fallback_lookup(word)
            else:
                logger.warning(f"No search results found for '{normalized_word}'")
                return None

        # Get best match result
        best_match = search_results[0]
        logger.debug(f"Best match: '{best_match.word}' for query '{normalized_word}'")

        # Get definition from provider
        entry = await _get_provider_definition(
            word=best_match.word,
            provider=provider,
        )

        if not entry:
            if not no_ai:
                return await _ai_fallback_lookup(word)
            else:
                return None

        # AI synthesis
        if not no_ai:
            try:
                synthesizer = create_definition_synthesizer()
                # Convert entry to the format expected by synthesize_entry
                word_obj = Word(text=best_match.word)
                providers = {provider.value: entry}
                synthesized_entry = await synthesizer.synthesize_entry(word_obj, providers)
                
                if synthesized_entry:
                    logger.debug(f"Successfully synthesized definition for '{best_match.word}'")
                    return synthesized_entry
                else:
                    logger.warning(f"AI synthesis failed for '{best_match.word}'")
                    return None
                    
            except Exception as e:
                logger.error(f"AI synthesis failed: {e}")
                return None
        else:
            logger.warning(f"AI synthesis disabled, cannot return synthesized entry for '{best_match}'")
            return None

    except Exception as e:
        logger.error(f"Batch lookup failed for '{word}': {e}")
        return None


async def _search_word(
    word: str, languages: list[Language], semantic: bool
) -> list[Any]:
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
            logger.warning("Oxford provider requires API credentials")
            return None
        elif provider == DictionaryProvider.DICTIONARY_COM:
            connector = DictionaryComConnector()
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


async def _synthesize_with_ai(word: Word, providers: dict[str, Any]) -> SynthesizedDictionaryEntry | None:
    """Synthesize definition using AI."""
    logger.debug(f"AI synthesis for '{word.text}'")

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
        ai_entry = await synthesizer.generate_fallback_entry(Word(text=word))
        
        if ai_entry and ai_entry.definitions:
            logger.debug(f"AI fallback successful for '{word}'")
            return ai_entry
        else:
            logger.warning(f"AI fallback failed for '{word}'")
            return None

    except Exception as e:
        logger.error(f"AI fallback failed: {e}")
        return None