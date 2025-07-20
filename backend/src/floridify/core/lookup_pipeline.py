"""Core lookup pipeline for word definitions with AI synthesis."""

from __future__ import annotations

import time

from ..ai import get_definition_synthesizer
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
from ..utils.state_tracker import PipelineStage, ProviderMetrics, StateTracker
from .search_pipeline import find_best_match

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
            await state_tracker.update(
                PipelineStage.SEARCH,
                0,
                f"Searching for '{word}'",
                {"word": word, "semantic": semantic},
            )

        search_start = time.time()
        best_match_result = await find_best_match(
            word=word,
            languages=languages,
            semantic=semantic,
        )
        search_duration = time.time() - search_start

        if state_tracker:
            await state_tracker.update(
                PipelineStage.SEARCH,
                10,
                f"Search complete for '{word}'",
                {
                    "word": word,
                    "found": bool(best_match_result),
                    "score": best_match_result.score if best_match_result else None,
                    "duration_ms": search_duration * 1000,
                },
                partial_data={"best_match": best_match_result.word if best_match_result else None},
            )

        if not best_match_result:
            logger.warning(f"No search results found for '{word}' after {search_duration:.2f}s")
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

        # Get definition from providers
        providers_data = []
        provider_fetch_start = time.time()
        total_providers = len(providers)
        provider_progress_base = 15
        provider_progress_range = 25  # 15-40%

        for i, provider in enumerate(providers):
            if state_tracker:
                progress = provider_progress_base + (i * provider_progress_range / total_providers)
                await state_tracker.update(
                    PipelineStage.PROVIDER_FETCH,
                    progress,
                    f"Fetching from {provider.value}",
                    {"provider": provider.value, "word": best_match},
                )

            logger.debug(f"🔄 Fetching from provider: {provider.value}")
            provider_start = time.time()

            provider_data, provider_metrics = await _get_provider_definition(
                best_match, provider, force_refresh, state_tracker
            )
            provider_duration = time.time() - provider_start

            if not provider_data:
                logger.warning(
                    f"❌ Provider {provider.value} failed for '{best_match}' "
                    f"after {provider_duration:.2f}s"
                )
                # Try AI fallback if provider fails and AI is enabled
                if not no_ai:
                    logger.info(f"Provider failed, trying AI fallback for '{best_match}'")
                    return await _ai_fallback_lookup(best_match, force_refresh, state_tracker)
                return None

            # Log successful provider fetch with quality metrics
            if provider_metrics:
                log_metrics(
                    provider=provider.value,
                    word=best_match,
                    fetch_time=provider_duration,
                    definition_count=provider_metrics.definitions_count,
                    has_pronunciation=provider_metrics.has_pronunciation,
                    has_etymology=provider_metrics.has_etymology,
                    completeness_score=provider_metrics.completeness_score,
                    response_size_bytes=provider_metrics.response_size_bytes,
                    connection_time_ms=provider_metrics.connection_time_ms,
                    download_time_ms=provider_metrics.download_time_ms,
                    parse_time_ms=provider_metrics.parse_time_ms,
                )
            else:
                log_metrics(
                    provider=provider.value,
                    word=best_match,
                    fetch_time=provider_duration,
                    definition_count=len(provider_data.definitions)
                    if provider_data.definitions
                    else 0,
                )

            providers_data.append(provider_data)

            if state_tracker:
                progress = provider_progress_base + (
                    (i + 1) * provider_progress_range / total_providers
                )
                await state_tracker.update(
                    PipelineStage.PROVIDER_FETCH,
                    progress,
                    f"Fetched from {provider.value}",
                    {
                        "provider": provider.value,
                        "word": best_match,
                        "success": True,
                        "duration_ms": provider_duration * 1000,
                        "definitions_count": len(provider_data.definitions) if provider_data else 0,
                        "quality_metrics": provider_metrics.__dict__ if provider_metrics else None,
                    },
                    partial_data={"provider_data": provider_data},
                )

        total_provider_time = time.time() - provider_fetch_start
        logger.info(
            f"✅ Fetched from {len(providers_data)} providers in {total_provider_time:.2f}s"
        )

        # Synthesize with AI if enabled
        if not no_ai:
            try:
                logger.info(f"🤖 Starting AI synthesis for '{best_match}'")
                ai_start = time.time()

                synthesized_entry = await _synthesize_with_ai(
                    word=best_match,
                    providers=providers_data,
                    force_refresh=force_refresh,
                    state_tracker=state_tracker,
                )

                ai_duration = time.time() - ai_start

                if synthesized_entry:
                    logger.info(
                        f"✅ Successfully synthesized entry for '{best_match}' "
                        f"in {ai_duration:.2f}s"
                    )

                    # Log synthesis metrics
                    log_metrics(
                        word=best_match,
                        ai_synthesis_time=ai_duration,
                        total_pipeline_time=time.time() - search_start,
                        definition_count=len(synthesized_entry.definitions)
                        if synthesized_entry.definitions
                        else 0,
                        provider_count=len(providers_data),
                    )

                    if state_tracker:
                        await state_tracker.update(
                            PipelineStage.COMPLETE,
                            100,
                            f"Lookup complete for '{best_match}'",
                            {
                                "word": best_match,
                                "total_duration_ms": state_tracker.get_total_duration_ms(),
                                "definitions_count": len(synthesized_entry.definitions)
                                if synthesized_entry.definitions
                                else 0,
                            },
                        )

                    return synthesized_entry
                else:
                    logger.warning(
                        f"⚠️  AI synthesis returned empty result for '{best_match}' "
                        f"after {ai_duration:.2f}s"
                    )
                    logger.info(
                        f"No provider data available, trying AI fallback for '{best_match}'"
                    )
                    return await _ai_fallback_lookup(best_match, force_refresh, state_tracker)
            except Exception as e:
                logger.error(f"❌ AI synthesis failed: {e}")
                return None
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
            total_time=time.time() - search_start if "search_start" in locals() else 0,
        )
        return None


@log_timing
async def _get_provider_definition(
    word: str,
    provider: DictionaryProvider,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
) -> tuple[ProviderData | None, ProviderMetrics | None]:
    """Get definition from specified provider.

    Returns:
        Tuple of (provider_data, provider_metrics)
    """
    logger.debug(f"📖 Fetching definition from {provider.value} for '{word}'")
    start_time = time.time()

    # Initialize metrics
    metrics = ProviderMetrics(
        provider_name=provider.value,
        response_time_ms=0,
        response_size_bytes=0,
    )

    try:
        connector: WiktionaryConnector | DictionaryComConnector | None = None

        if provider == DictionaryProvider.WIKTIONARY:
            connector = WiktionaryConnector(force_refresh=force_refresh)
        elif provider == DictionaryProvider.OXFORD:
            # Would need API credentials from config
            logger.warning("Oxford provider requires API credentials")
            return None, metrics
        elif provider == DictionaryProvider.DICTIONARY_COM:
            connector = DictionaryComConnector(force_refresh=force_refresh)
        else:
            logger.warning(f"Unsupported provider: {provider.value}")
            return None, metrics

        if connector:
            fetch_start = time.time()
            result = await connector.fetch_definition(word, state_tracker)
            fetch_duration = time.time() - fetch_start

            if result:
                # Update metrics from result
                response_size = len(str(result.model_dump_json())) if result else 0
                metrics.response_size_bytes = response_size
                metrics.definitions_count = len(result.definitions) if result.definitions else 0
                metrics.has_pronunciation = bool(
                    result.raw_metadata and result.raw_metadata.get("pronunciation")
                )
                metrics.has_etymology = bool(
                    result.raw_metadata and result.raw_metadata.get("etymology")
                )
                metrics.has_examples = any(
                    d.examples and (d.examples.generated or d.examples.literature)
                    for d in (result.definitions or [])
                )
                metrics.success = True
                metrics.response_time_ms = fetch_duration * 1000
                metrics.calculate_completeness_score()

                log_provider_fetch(
                    provider_name=provider.value,
                    word=word,
                    success=True,
                    response_size=response_size,
                    duration=fetch_duration,
                )

                logger.debug(
                    f"✅ Provider {provider.value} returned {metrics.definitions_count} "
                    f"definitions for '{word}' (completeness: {metrics.completeness_score:.2f})"
                )
            else:
                metrics.success = False
                metrics.response_time_ms = fetch_duration * 1000

                log_provider_fetch(
                    provider_name=provider.value, word=word, success=False, duration=fetch_duration
                )
                logger.debug(f"⚠️  Provider {provider.value} returned no results for '{word}'")

            return result, metrics

        return None, metrics

    except Exception as e:
        duration = time.time() - start_time
        metrics.success = False
        metrics.error_message = str(e)
        metrics.response_time_ms = duration * 1000

        log_provider_fetch(
            provider_name=provider.value, word=word, success=False, duration=duration
        )
        logger.error(f"❌ Provider {provider.value} failed for '{word}': {e}")
        return None, metrics


@log_timing
@log_stage("AI Synthesis", "🤖")
async def _synthesize_with_ai(
    word: str,
    providers: list[ProviderData],
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
) -> SynthesizedDictionaryEntry | None:
    """Synthesize definition using AI."""
    logger.debug(f"🤖 Starting AI synthesis for '{word}' with {len(providers)} providers")

    # Log provider data quality
    total_definitions = sum(len(p.definitions) if p.definitions else 0 for p in providers)
    logger.debug(f"📊 Total definitions to synthesize: {total_definitions}")

    try:
        synthesizer = get_definition_synthesizer()
        result = await synthesizer.synthesize_entry(word, providers, force_refresh, state_tracker)

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
        start_time = time.time()

        ai_entry = await synthesizer.generate_fallback_entry(word, force_refresh, state_tracker)
        duration = time.time() - start_time

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

            if state_tracker:
                await state_tracker.update(
                    PipelineStage.COMPLETE,
                    100,
                    f"AI fallback complete for '{word}'",
                    {
                        "word": word,
                        "fallback": True,
                        "total_duration_ms": state_tracker.get_total_duration_ms(),
                        "definitions_count": len(ai_entry.definitions),
                    },
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
