"""Core lookup pipeline for word definitions with AI synthesis."""

from __future__ import annotations

import asyncio
import platform
import time

from src.floridify.storage.mongodb import get_synthesized_entry

from ..ai import get_definition_synthesizer
from ..connectors.apple_dictionary import AppleDictionaryConnector
from ..connectors.dictionary_com import DictionaryComConnector
from ..connectors.wiktionary import WiktionaryConnector
from ..constants import DictionaryProvider, Language
from ..models.models import ProviderData, SynthesizedDictionaryEntry
from ..utils.logging import (
    get_logger,
    log_metrics,
    log_provider_fetch,
    log_stage,
    log_timing,
)
from .search_pipeline import find_best_match
from .state_tracker import Stages, StateTracker

logger = get_logger(__name__)


@log_timing
@log_stage("Word Lookup Pipeline", "📚")
async def lookup_word_pipeline(
    word: str,
    providers: list[DictionaryProvider] | None = None,
    languages: list[Language] | None = None,
    semantic: bool = False,
    no_ai: bool = False,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
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
        state_tracker: Optional state tracker for progress updates

    Returns:
        Synthesized dictionary entry or None if not found
    """
    # Set defaults
    if providers is None:
        providers = [DictionaryProvider.WIKTIONARY]
        # Add Apple Dictionary as default on macOS
        if platform.system() == 'Darwin':
            providers.append(DictionaryProvider.APPLE_DICTIONARY)
    if languages is None:
        languages = [Language.ENGLISH]

    # Log initial pipeline parameters
    log_metrics(
        word=word,
        providers=[p.value for p in providers],
        languages=[lang.value for lang in languages],
        semantic=semantic,
        no_ai=no_ai,
        force_refresh=force_refresh,
    )

    try:
        # Search for the word using generalized search pipeline
        if state_tracker:
            await state_tracker.update_stage(Stages.SEARCH_START)

        search_start = time.perf_counter()
        best_match_result = await find_best_match(
            word=word,
            languages=languages,
            semantic=semantic,
        )
        search_duration = time.perf_counter() - search_start

        if state_tracker:
            await state_tracker.update_stage(Stages.SEARCH_COMPLETE)

        if not best_match_result:
            logger.warning(
                f"No search results found for '{word}' after {search_duration:.2f}s"
            )
            # Try AI fallback if no results and AI is enabled
            if not no_ai:
                logger.info(f"No search results, trying AI fallback for '{word}'")
                return await _ai_fallback_lookup(word, force_refresh, state_tracker)

            return None

        # Use the best match
        best_match = best_match_result.word
        logger.info(
            f"✅ Found best match: '{best_match}' "
            f"(score: {best_match_result.score:.3f}, method: {best_match_result.method}, "
            f"search_time: {search_duration:.2f}s)"
        )

        # Try to get a cached entry first
        if not no_ai and not force_refresh:
            existing = await get_synthesized_entry(word)
            if existing:
                logger.info(f"📋 Using cached synthesized entry for '{best_match}'")
                return existing

        # Get definitions from providers in parallel
        if state_tracker:
            await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)

        logger.info(
            f"🔄 Fetching from {len(providers)} providers in parallel: {[p.value for p in providers]}"
        )
        provider_fetch_start = time.perf_counter()

        # Fetch from all providers in parallel
        provider_tasks = [
            _get_provider_definition(best_match, provider, force_refresh, state_tracker)
            for provider in providers
        ]
        providers_results = await asyncio.gather(
            *provider_tasks, return_exceptions=True
        )

        # Filter out None results and exceptions
        providers_data = []
        for i, result in enumerate(providers_results):
            provider = providers[i]
            if isinstance(result, Exception):
                logger.warning(
                    f"❌ Provider {provider.value} failed with exception: {result}"
                )
            elif result is None:
                logger.warning(
                    f"❌ Provider {provider.value} returned no data for '{best_match}'"
                )
            else:
                providers_data.append(result)
                logger.debug(
                    f"✅ Provider {provider.value} returned data for '{best_match}'"
                )

        total_provider_time = time.perf_counter() - provider_fetch_start
        logger.info(
            f"✅ Fetched from {len(providers_data)}/{len(providers)} providers in {total_provider_time:.2f}s"
        )

        if state_tracker:
            await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)

        # Only try AI fallback if ALL providers failed
        if not providers_data and not no_ai:
            logger.info(f"All providers failed, trying AI fallback for '{best_match}'")
            return await _ai_fallback_lookup(best_match, force_refresh, state_tracker)
        elif not providers_data:
            logger.warning(
                f"All providers failed and AI is disabled for '{best_match}'"
            )
            return None

        # Synthesize with AI if enabled and we have provider data
        if not no_ai and providers_data:
            try:
                logger.info(
                    f"🤖 Starting AI synthesis for '{best_match}' with {len(providers_data)} providers"
                )
                ai_start = time.perf_counter()

                synthesized_entry = await _synthesize_with_ai(
                    word=best_match,
                    providers=providers_data,
                    language=languages[0],  # Use first language for synthesis
                    force_refresh=force_refresh,
                    state_tracker=state_tracker,
                )

                ai_duration = time.perf_counter() - ai_start

                if synthesized_entry:
                    logger.info(
                        f"✅ Successfully synthesized entry for '{best_match}' "
                        f"in {ai_duration:.2f}s"
                    )

                    # Log synthesis metrics
                    log_metrics(
                        word=best_match,
                        ai_synthesis_time=ai_duration,
                        total_pipeline_time=time.perf_counter() - search_start,
                        definition_count=(
                            len(synthesized_entry.definitions)
                            if synthesized_entry.definitions
                            else 0
                        ),
                        provider_count=len(providers_data),
                    )
                    return synthesized_entry
                else:
                    logger.warning(
                        f"⚠️  AI synthesis returned empty result for '{best_match}' "
                        f"after {ai_duration:.2f}s"
                    )
                    # Try fallback if synthesis fails
                    return await _ai_fallback_lookup(
                        best_match, force_refresh, state_tracker
                    )
            except Exception as e:
                logger.error(f"❌ AI synthesis failed: {e}")
                # Try fallback if synthesis fails
                return await _ai_fallback_lookup(
                    best_match, force_refresh, state_tracker
                )
        else:
            # When AI is disabled, we can't return a SynthesizedDictionaryEntry
            logger.warning(
                f"AI synthesis disabled, cannot return synthesized entry for '{best_match}'"
            )
            return None

    except Exception as e:
        logger.error(f"❌ Lookup pipeline failed for '{word}': {e}")
        log_metrics(
            word=word,
            error=str(e),
            total_time=(
                time.perf_counter() - search_start if "search_start" in locals() else 0
            ),
        )
        return None


@log_timing
async def _get_provider_definition(
    word: str,
    provider: DictionaryProvider,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
) -> ProviderData | None:
    """Get definition from specified provider.

    Returns:
        Tuple of (provider_data, provider_metrics)
    """
    logger.debug(f"📖 Fetching definition from {provider.value} for '{word}'")
    start_time = time.perf_counter()

    try:
        connector: (
            WiktionaryConnector
            | DictionaryComConnector
            | AppleDictionaryConnector
            | None
        ) = None

        if provider == DictionaryProvider.WIKTIONARY:
            connector = WiktionaryConnector(force_refresh=force_refresh)
        elif provider == DictionaryProvider.OXFORD:
            # Would need API credentials from config
            logger.warning("Oxford provider requires API credentials")
            return None
        elif provider == DictionaryProvider.DICTIONARY_COM:
            connector = DictionaryComConnector(force_refresh=force_refresh)
        elif provider == DictionaryProvider.APPLE_DICTIONARY:
            connector = AppleDictionaryConnector()
        else:
            logger.warning(f"Unsupported provider: {provider.value}")
            return None

        if connector:
            fetch_start = time.perf_counter()
            result = await connector.fetch_definition(word, state_tracker)
            fetch_duration = time.perf_counter() - fetch_start

            if result:
                # Update metrics from result
                response_size = len(str(result.model_dump_json())) if result else 0

                log_provider_fetch(
                    provider_name=provider.value,
                    word=word,
                    success=True,
                    response_size=response_size,
                    duration=fetch_duration,
                )
            else:

                log_provider_fetch(
                    provider_name=provider.value,
                    word=word,
                    success=False,
                    duration=fetch_duration,
                )
                logger.debug(
                    f"⚠️  Provider {provider.value} returned no results for '{word}'"
                )

            return result

        return None

    except Exception as e:
        duration = time.perf_counter() - start_time

        log_provider_fetch(
            provider_name=provider.value, word=word, success=False, duration=duration
        )
        logger.error(f"❌ Provider {provider.value} failed for '{word}': {e}")
        return None


@log_timing
@log_stage("AI Synthesis", "🤖")
async def _synthesize_with_ai(
    word: str,
    providers: list[ProviderData],
    language: Language = Language.ENGLISH,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
) -> SynthesizedDictionaryEntry | None:
    """Synthesize definition using AI."""
    logger.debug(
        f"🤖 Starting AI synthesis for '{word}' with {len(providers)} providers"
    )

    # Log provider data quality
    total_definitions = sum(
        len(p.definitions) if p.definitions else 0 for p in providers
    )
    logger.debug(f"📊 Total definitions to synthesize: {total_definitions}")

    try:
        synthesizer = get_definition_synthesizer()
        result = await synthesizer.synthesize_entry(
            word=word,
            providers_data=providers,
            language=language,
            force_refresh=force_refresh,
            state_tracker=state_tracker,
        )

        if result:
            logger.debug(
                f"✅ AI synthesis complete: {len(result.definitions) if result.definitions else 0} "
                f"synthesized definitions"
            )
        else:
            logger.warning(f"⚠️  AI synthesis returned empty result for '{word}'")

        return result
    except Exception as e:
        logger.error(f"❌ AI synthesis failed for '{word}': {e}")
        return None


@log_timing
@log_stage("AI Fallback", "🔮")
async def _ai_fallback_lookup(
    word: str, force_refresh: bool = False, state_tracker: StateTracker | None = None
) -> SynthesizedDictionaryEntry | None:
    """AI fallback when no provider definitions are found."""
    logger.info(f"🔮 Attempting AI fallback generation for '{word}'")

    try:
        synthesizer = get_definition_synthesizer()
        start_time = time.perf_counter()

        ai_entry = await synthesizer.generate_fallback_entry(
            word, Language.ENGLISH, force_refresh, state_tracker
        )
        duration = time.perf_counter() - start_time

        if ai_entry and ai_entry.definitions:
            logger.info(
                f"✅ AI fallback successful for '{word}': "
                f"{len(ai_entry.definitions)} definitions generated in {duration:.2f}s"
            )

            log_metrics(
                word=word,
                fallback_duration=duration,
                definition_count=len(ai_entry.definitions),
                is_fallback=True,
            )

            return ai_entry
        else:
            logger.warning(
                f"⚠️  AI fallback returned no definitions for '{word}' after {duration:.2f}s"
            )
            return None

    except Exception as e:
        logger.error(f"❌ AI fallback failed for '{word}': {e}")
        return None
