"""Core lookup pipeline for word definitions with AI synthesis."""

from __future__ import annotations

from ..ai import get_definition_synthesizer
from ..connectors.dictionary_com import DictionaryComConnector
from ..connectors.wiktionary import WiktionaryConnector
from ..constants import DictionaryProvider, Language
from ..models.models import ProviderData, SynthesizedDictionaryEntry
from ..utils.logging import get_logger
from .search_pipeline import find_best_match

logger = get_logger(__name__)


async def lookup_word_pipeline(
    word: str,
    providers: list[DictionaryProvider] | None = None,
    languages: list[Language] | None = None,
    semantic: bool = False,
    no_ai: bool = False,
    force_refresh: bool = False,
) -> SynthesizedDictionaryEntry | None:
    """Core lookup pipeline that normalizes, searches, gets provider definitions,
    and optionally synthesizes with AI.
    
    Args:
        word: Word to look up
        providers: Dictionary providers to use
        languages: Languages to search
        semantic: Enable semantic search
        no_ai: Skip AI synthesis
        force_refresh: Force refresh of cached data
        
    Returns:
        Synthesized dictionary entry or None if not found
    """
    # Set defaults
    if providers is None:
        providers = [DictionaryProvider.WIKTIONARY]
    if languages is None:
        languages = [Language.ENGLISH]
    
    try:
        # Search for the word using generalized search pipeline
        best_match_result = await find_best_match(
            word=word,
            languages=languages,
            semantic=semantic,
        )

        if not best_match_result:
            # Try AI fallback if no results and AI is enabled
            if not no_ai:
                logger.info(f"No search results, trying AI fallback for '{word}'")
                return await _ai_fallback_lookup(word, force_refresh)
            return None

        # Use the best match
        best_match = best_match_result.word
        logger.debug(f"Best match: '{best_match}' (score: {best_match_result.score:.3f})")

        # Get definition from providers
        providers_data = []
        for provider in providers:
            provider_data = await _get_provider_definition(best_match, provider, force_refresh)
            if not provider_data:
                # Try AI fallback if provider fails and AI is enabled
                if not no_ai:
                    logger.info(f"Provider failed, trying AI fallback for '{best_match}'")
                    return await _ai_fallback_lookup(best_match, force_refresh)
                return None
            providers_data.append(provider_data)

        # Synthesize with AI if enabled
        if not no_ai:
            try:
                synthesized_entry = await _synthesize_with_ai(
                    word=best_match,
                    providers=providers_data,
                    force_refresh=force_refresh,
                )
                if synthesized_entry:
                    logger.debug(f"Successfully synthesized entry for '{best_match}'")
                    return synthesized_entry
                else:
                    logger.info(f"No provider data available, trying AI fallback for '{best_match}'")
                    return await _ai_fallback_lookup(best_match, force_refresh)
            except Exception as e:
                logger.error(f"AI synthesis failed: {e}")
                return None
        else:
            # When AI is disabled, we can't return a SynthesizedDictionaryEntry
            logger.warning(f"AI synthesis disabled, cannot return synthesized entry for '{best_match}'")
            return None

    except Exception as e:
        logger.error(f"Lookup pipeline failed: {e}")
        return None



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
    word: str, providers: list[ProviderData], force_refresh: bool = False
) -> SynthesizedDictionaryEntry | None:
    """Synthesize definition using AI."""
    logger.debug(f"AI synthesis for '{word}'")

    try:
        synthesizer = get_definition_synthesizer()
        return await synthesizer.synthesize_entry(word, providers, force_refresh)
    except Exception as e:
        logger.error(f"AI synthesis failed: {e}")
        return None


async def _ai_fallback_lookup(
    word: str, force_refresh: bool = False
) -> SynthesizedDictionaryEntry | None:
    """AI fallback when no provider definitions are found."""
    logger.debug(f"AI fallback for '{word}'")

    try:
        synthesizer = get_definition_synthesizer()
        ai_entry = await synthesizer.generate_fallback_entry(word, force_refresh)

        if ai_entry and ai_entry.definitions:
            logger.debug(f"AI fallback successful for '{word}'")
            return ai_entry
        else:
            logger.warning(f"AI fallback failed for '{word}'")
            return None

    except Exception as e:
        logger.error(f"AI fallback failed: {e}")
        return None