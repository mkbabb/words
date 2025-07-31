"""Core lookup pipeline for word definitions with AI synthesis."""

from __future__ import annotations

import asyncio
import platform
import time
import traceback

from src.floridify.connectors.base import DictionaryConnector

from ..ai import get_definition_synthesizer
from ..ai.synthesis_functions import cluster_definitions
from ..connectors.apple_dictionary import AppleDictionaryConnector
from ..connectors.dictionary_com import DictionaryComConnector
from ..connectors.oxford import OxfordConnector
from ..connectors.wiktionary import WiktionaryConnector
from ..constants import DictionaryProvider, Language
from ..models.base import Etymology
from ..models.models import Definition, ProviderData, SynthesizedDictionaryEntry, Word
from ..storage.mongodb import get_storage, get_synthesized_entry
from ..utils.config import Config
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
        if platform.system() == "Darwin":
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

        # Handle force_refresh by deleting existing entry
        if force_refresh:
            existing = await get_synthesized_entry(word)
            if existing:
                logger.info(
                    f"🗑️  Deleting existing synthesized entry for '{best_match}' due to force_refresh"
                )
                await existing.delete()
        else:
            # Try to get a cached entry if not forcing refresh (regardless of AI setting)
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
            _get_provider_definition(
                word=best_match,
                provider=provider,
                language=languages[0],  # Use first language for provider fetch
                force_refresh=force_refresh,
                state_tracker=state_tracker,
            )
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
            logger.error(f"All providers failed and AI is disabled for '{best_match}'")
            return None

        # Synthesize with AI if enabled and we have provider data
        if not no_ai and providers_data:
            try:
                logger.info(
                    f"🤖 Starting AI synthesis for '{best_match}' with {len(providers_data)} providers"
                )
                ai_start = time.perf_counter()

                if state_tracker:
                    await state_tracker.update_stage(Stages.AI_SYNTHESIS)

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
                        definition_count=len(synthesized_entry.definition_ids),
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
            # When AI is disabled, create a non-AI synthesized entry from provider data
            logger.info(f"🔧 Creating non-AI synthesized entry for '{best_match}'")

            # In no-AI mode, only use the first provider's data
            if providers_data:
                return await _create_provider_mapped_entry(
                    word=best_match,
                    provider_data=providers_data[0],  # Use first provider only
                    state_tracker=state_tracker,
                )
            else:
                logger.warning("No provider data available for non-AI synthesis")
                return None

    except Exception as e:
        logger.error(f"❌ Lookup pipeline failed for '{word}': {e}")
        return None


@log_timing
async def _get_provider_definition(
    word: str,
    provider: DictionaryProvider,
    language: Language = Language.ENGLISH,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
) -> ProviderData | None:
    """Get definition from specified provider.

    Returns:
        Tuple of (provider_data, provider_metrics)
    """
    logger.debug(f"📖 Fetching definition from {provider.value} for '{word}'")

    try:
        connector: DictionaryConnector

        if provider == DictionaryProvider.WIKTIONARY:
            connector = WiktionaryConnector(force_refresh=force_refresh)
        elif provider == DictionaryProvider.OXFORD:
            config = Config.from_file()
            if not config.oxford.app_id or not config.oxford.api_key:
                raise ValueError(
                    "Oxford Dictionary API credentials not configured. "
                    "Please update auth/config.toml with your Oxford app_id and api_key."
                )
            connector = OxfordConnector(
                app_id=config.oxford.app_id, api_key=config.oxford.api_key
            )
        elif provider == DictionaryProvider.DICTIONARY_COM:
            config = Config.from_file()
            if not config.dictionary_com.authorization:
                raise ValueError(
                    "Dictionary.com API authorization not configured. "
                    "Please update auth/config.toml with your Dictionary.com authorization token."
                )
            connector = DictionaryComConnector(
                api_key=config.dictionary_com.authorization, force_refresh=force_refresh
            )
        elif provider == DictionaryProvider.APPLE_DICTIONARY:
            connector = AppleDictionaryConnector()
        else:
            logger.warning(f"Unsupported provider: {provider.value}")
            return None

        storage = await get_storage()
        word_obj = await storage.get_word(word)

        if not word_obj:
            # Create new Word if doesn't exist
            word_obj = Word(
                text=word,
                normalized=word.lower(),
                language=language,
            )
            await word_obj.save()

        if connector:
            fetch_start = time.perf_counter()

            result = await connector.fetch_definition(word_obj, state_tracker)

            fetch_duration = time.perf_counter() - fetch_start

            if result:
                log_provider_fetch(
                    provider_name=provider.value,
                    word=word,
                    success=True,
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
        log_provider_fetch(provider_name=provider.value, word=word, success=False)

        logger.error(f"❌ Provider {provider.value} failed for '{word}': {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")

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
        len(p.definition_ids) if p.definition_ids else 0 for p in providers
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
                f"✅ AI synthesis complete: {len(result.definition_ids) if result.definition_ids else 0} "
                f"synthesized definitions"
            )
        else:
            logger.warning(f"⚠️  AI synthesis returned empty result for '{word}'")

        return result
    except Exception as e:
        import traceback

        logger.error(f"❌ AI synthesis failed for '{word}': {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return None


@log_timing
@log_stage("Provider Mapping", "🔄")
async def _create_provider_mapped_entry(
    word: str,
    provider_data: ProviderData,
    state_tracker: StateTracker | None = None,
) -> SynthesizedDictionaryEntry | None:
    """Create a synthesized entry from provider data without full AI synthesis.

    Uses AI only for deduplication and clustering, but not for content generation.
    """
    logger.info(
        f"📦 Creating provider-mapped entry for '{word}' from {provider_data.provider}"
    )

    try:
        # Get Word object
        word_obj = await Word.get(provider_data.word_id)
        if not word_obj:
            logger.error(f"Word object not found for ID: {provider_data.word_id}")
            return None

        # Load all definitions from provider
        all_definitions: list[Definition] = []
        for def_id in provider_data.definition_ids:
            definition = await Definition.get(def_id)
            if definition:
                all_definitions.append(definition)

        if not all_definitions:
            logger.warning("No definitions found for provider data")
            return None

        # Use AI for deduplication only
        logger.info(
            f"🔍 Deduplicating {len(all_definitions)} definitions (AI-assisted)"
        )
        synthesizer = get_definition_synthesizer()

        dedup_response = await synthesizer.ai.deduplicate_definitions(
            word=word,
            definitions=all_definitions,
        )

        # Create unique definitions list from deduplication results
        unique_definitions: list[Definition] = []
        processed_indices: set[int] = set()

        for dedup_def in dedup_response.deduplicated_definitions:
            # Use the first source index as the primary definition
            primary_idx = dedup_def.source_indices[0]
            primary_def = all_definitions[primary_idx]

            # Keep original definition text (no AI rewriting)
            unique_definitions.append(primary_def)

            # Track all processed indices
            processed_indices.update(dedup_def.source_indices)

        logger.info(
            f"✅ Deduplicated {len(all_definitions)} → {len(unique_definitions)} definitions"
        )

        # Use AI for clustering only
        if state_tracker:
            await state_tracker.update_stage(Stages.AI_CLUSTERING)

        logger.info("📊 Clustering definitions (AI-assisted)")

        clustered_definitions = await cluster_definitions(
            word_obj, unique_definitions, synthesizer.ai, state_tracker
        )

        # Save the clustered definitions to persist meaning_cluster assignments
        for definition in clustered_definitions:
            await definition.save()

        # Update definition IDs with clustered definitions
        clustered_def_ids = [d.id for d in clustered_definitions if d.id is not None]

        # Extract etymology if available
        etymology = None
        if hasattr(provider_data, "raw_data") and provider_data.raw_data:
            raw_data = provider_data.raw_data
            if "etymology" in raw_data and raw_data["etymology"]:
                etymology = Etymology(text=raw_data["etymology"])

        # Create the synthesized entry without AI content generation
        synthesized_entry = SynthesizedDictionaryEntry(
            word_id=provider_data.word_id,
            pronunciation_id=provider_data.pronunciation_id,
            definition_ids=clustered_def_ids,  # Use deduplicated and clustered definitions
            etymology=provider_data.etymology or etymology,
            fact_ids=[],  # No facts in non-AI mode
            model_info=None,  # No AI model info
            source_provider_data_ids=(
                [provider_data.id] if provider_data.id is not None else []
            ),
        )

        # Save the entry
        await synthesized_entry.save()

        logger.info(
            f"✅ Created provider-mapped entry for '{word}' with "
            f"{len(synthesized_entry.definition_ids)} clustered definitions"
        )

        if state_tracker:
            await state_tracker.update_stage(Stages.STORAGE_SAVE)

        return synthesized_entry

    except Exception as e:
        logger.error(f"❌ Failed to create provider-mapped entry: {e}")
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

        if ai_entry and ai_entry.definition_ids:
            logger.info(
                f"✅ AI fallback successful for '{word}': "
                f"{len(ai_entry.definition_ids)} definitions generated in {duration:.2f}s"
            )

            log_metrics(
                word=word,
                fallback_duration=duration,
                definition_count=len(ai_entry.definition_ids),
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
