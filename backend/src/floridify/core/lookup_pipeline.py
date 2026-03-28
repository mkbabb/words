"""Core lookup pipeline for word definitions with AI synthesis."""

from __future__ import annotations

import asyncio
import platform
import time
import traceback

from ..ai import get_definition_synthesizer
from ..ai.synthesis import cluster_definitions
from ..api.core.exceptions import (
    NotFoundException,
    ProviderFetchError,
    ProviderTimeoutError,
    SynthesisError,
)
from ..models import Etymology
from ..models.base import Language
from ..models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Pronunciation,
    Word,
)
from ..providers.factory import create_connector
from ..storage.dictionary import save_entry_versioned
from ..storage.mongodb import get_best_existing_entry, get_storage, get_synthesized_entry
from ..utils.concurrency import gather_bounded
from ..utils.language_precedence import (
    merge_language_precedence,
    to_language_codes,
)
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

_PROVIDER_TIMEOUT_SECONDS = 30.0


def _log_background_failure(task: asyncio.Task) -> None:  # type: ignore[type-arg]
    """Done-callback for fire-and-forget tasks — logs exceptions instead of silently dropping them."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.warning(f"Background task failed: {exc}")


async def _ensure_primary_audio(entry: DictionaryEntry) -> None:
    """Generate audio for the primary language if pronunciation has none.

    Runs as a background task — errors are logged but never propagated.
    """
    if not entry.pronunciation_id:
        return

    try:
        pron = await Pronunciation.get(entry.pronunciation_id)
        if not pron or pron.audio_file_ids:
            return  # Already has audio or pronunciation missing

        # Resolve word text for TTS
        word_obj = await Word.get(entry.word_id)
        if not word_obj:
            return

        primary_language = entry.languages[0] if entry.languages else "en"

        from ..ai.synthesis.word_level import _generate_audio_files

        await _generate_audio_files(pron, word_obj.text, primary_language)
        logger.info(f"Background audio generated for '{word_obj.text}' ({primary_language})")
    except Exception as e:
        logger.warning(f"Background audio generation failed: {e}")


def _resolve_lookup_languages(
    requested_languages: list[Language],
) -> list[Language]:
    """Normalize lookup language precedence while preserving request order."""
    unique_languages: list[Language] = []
    for language in requested_languages:
        if language not in unique_languages:
            unique_languages.append(language)
    return unique_languages


async def _track_lookup(user_id: str, word: str) -> None:
    """Track a word lookup in the user's history. Fails silently."""
    try:
        from ..models.user import UserHistory

        history = await UserHistory.find_one({"clerk_id": user_id})
        if history:
            history.add_lookup(word)
            await history.save()
    except Exception:
        pass  # Don't fail lookup on history tracking error


@log_timing
@log_stage("Word Lookup Pipeline", "📚")
async def lookup_word_pipeline(
    word: str,
    providers: list[DictionaryProvider] | None = None,
    languages: list[Language] | None = None,
    semantic: bool = True,
    no_ai: bool = False,
    force_refresh: bool = False,
    skip_search: bool = False,
    state_tracker: StateTracker | None = None,
    user_id: str | None = None,
) -> DictionaryEntry | None:
    """Core lookup pipeline that normalizes, searches, gets provider definitions,
    and optionally synthesizes with AI.

    Args:
        word: Word to look up
        providers: Dictionary providers to use
        languages: Languages to search
        semantic: Enable semantic search
        no_ai: Skip AI synthesis
        force_refresh: Force refresh of cached data
        skip_search: Skip find_best_match (caller already resolved the word)
        state_tracker: Optional state tracker for progress updates

    Returns:
        Synthesized dictionary entry or None if not found

    """
    # Set defaults
    if providers is None:
        providers = [DictionaryProvider.WIKTIONARY, DictionaryProvider.WORDNET]
        # Add Apple Dictionary as default on macOS
        if platform.system() == "Darwin":
            providers.append(DictionaryProvider.APPLE_DICTIONARY)
    if languages is None:
        languages = [Language.ENGLISH]
    lookup_languages = _resolve_lookup_languages(requested_languages=languages)

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
        pipeline_start = time.perf_counter()

        # Search for the word using generalized search pipeline
        if skip_search:
            best_match = word
            logger.info(f"⚡ Skipping search — using word as-is: '{best_match}'")
            if state_tracker:
                await state_tracker.update_stage(Stages.SEARCH_START)
                await state_tracker.update_stage(Stages.SEARCH_COMPLETE)
        else:
            if state_tracker:
                await state_tracker.update_stage(Stages.SEARCH_START)

            search_start = time.perf_counter()
            best_match_result = await find_best_match(
                word=word,
                languages=[lookup_languages[0]],
                semantic=semantic,
            )
            search_duration = time.perf_counter() - search_start

            if state_tracker:
                await state_tracker.update_stage(Stages.SEARCH_COMPLETE)

            if best_match_result:
                best_match = best_match_result.word
                logger.info(
                    f"✅ Found best match: '{best_match}' "
                    f"(score: {best_match_result.score:.3f}, method: {best_match_result.method}, "
                    f"search_time: {search_duration:.2f}s)",
                )
            else:
                best_match = word
                logger.info(
                    f"No corpus match for '{word}' after {search_duration:.2f}s — "
                    f"proceeding to provider fetch with raw query",
                )

        # Handle force_refresh: skip cache but preserve history
        if force_refresh:
            existing = await get_synthesized_entry(best_match)
            if existing:
                logger.info(
                    f"🔄 Force refresh for '{best_match}' — existing entry preserved in version history",
                )
        else:
            # Unified cache check: synthesis preferred, then any provider entry
            existing, is_synthesis = await get_best_existing_entry(best_match)
            if existing:
                if is_synthesis or no_ai:
                    source = "synthesis" if is_synthesis else str(existing.provider)
                    logger.info(f"📋 Using cached {source} entry for '{best_match}'")
                    asyncio.create_task(_ensure_primary_audio(existing)).add_done_callback(
                        _log_background_failure
                    )
                    # Track lookup server-side if user is authenticated
                    if user_id:
                        await _track_lookup(user_id, word)
                    return existing
                # Non-synthesis entry with AI enabled — fall through to synthesis
                logger.info(
                    f"📋 Found {existing.provider} entry for '{best_match}', "
                    f"proceeding to AI synthesis"
                )

        # Get definitions from providers in parallel
        if state_tracker:
            await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)

        logger.info(
            f"🔄 Fetching from {len(providers)} providers in parallel: {[p.value for p in providers]}",
        )
        provider_fetch_start = time.perf_counter()

        # Fetch from all providers in parallel
        provider_tasks = [
            _get_provider_definition(
                word=best_match,
                provider=provider,
                languages=lookup_languages,
                force_refresh=force_refresh,
                state_tracker=state_tracker,
            )
            for provider in providers
        ]
        providers_results = await gather_bounded(*provider_tasks, limit=4, return_exceptions=True)

        # Filter out None results and exceptions
        providers_data = []
        for i, result in enumerate(providers_results):
            provider = providers[i]
            if isinstance(result, Exception):
                logger.warning(f"❌ Provider {provider.value} failed with exception: {result}")
            elif result is None:
                logger.warning(f"❌ Provider {provider.value} returned no data for '{best_match}'")
            else:
                providers_data.append(result)
                logger.debug(f"✅ Provider {provider.value} returned data for '{best_match}'")

        total_provider_time = time.perf_counter() - provider_fetch_start
        logger.info(
            f"✅ Fetched from {len(providers_data)}/{len(providers)} providers in {total_provider_time:.2f}s",
        )

        if state_tracker:
            await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)

        # TODO[CRITICAL]: Reinstate AI fallback when providers return no data, with
        # explicit reason codes + structured logs/metrics for every fallback invocation.
        # Temporary behavior: currently stops on provider miss.
        # Target behavior: AI fallback should run for provider-no-data cases with explicit logging.
        if not providers_data:
            logger.warning(f"All providers failed for '{best_match}'")
            return None

        # Synthesize with AI if enabled and we have provider data
        if not no_ai and providers_data:
            try:
                logger.info(
                    f"🤖 Starting AI synthesis for '{best_match}' with {len(providers_data)} providers",
                )
                ai_start = time.perf_counter()

                if state_tracker:
                    await state_tracker.update_stage(Stages.AI_SYNTHESIS)

                synthesized_entry = await _synthesize_with_ai(
                    word=best_match,
                    providers=providers_data,
                    languages=lookup_languages,
                    force_refresh=force_refresh,
                    state_tracker=state_tracker,
                )

                ai_duration = time.perf_counter() - ai_start

                if synthesized_entry:
                    logger.info(
                        f"✅ Successfully synthesized entry for '{best_match}' "
                        f"in {ai_duration:.2f}s",
                    )

                    # Log synthesis metrics
                    log_metrics(
                        word=best_match,
                        ai_synthesis_time=ai_duration,
                        total_pipeline_time=time.perf_counter() - pipeline_start,
                        definition_count=len(synthesized_entry.definition_ids),
                        provider_count=len(providers_data),
                    )
                    # Track lookup server-side if user is authenticated
                    if user_id:
                        await _track_lookup(user_id, word)
                    return synthesized_entry
                logger.error(
                    f"❌ AI synthesis returned empty result for '{best_match}' "
                    f"after {ai_duration:.2f}s",
                )
                return None
            except Exception as e:
                logger.error(f"❌ AI synthesis failed for '{best_match}': {e}")
                raise SynthesisError(best_match, "synthesis", str(e)) from e
        else:
            # When AI is disabled, create a non-AI synthesized entry from provider data
            logger.info(f"🔧 Creating non-AI synthesized entry for '{best_match}'")

            # In no-AI mode, only use the first provider's data
            if providers_data:
                result = await _create_provider_mapped_entry(
                    word=best_match,
                    provider_data=providers_data[0],  # Use first provider only
                    state_tracker=state_tracker,
                    no_ai=no_ai,
                )
                if result:
                    asyncio.create_task(_ensure_primary_audio(result)).add_done_callback(
                        _log_background_failure
                    )
                    # Track lookup server-side if user is authenticated
                    if user_id:
                        await _track_lookup(user_id, word)
                return result
            logger.warning("No provider data available for non-AI synthesis")
            return None

    except Exception as e:
        logger.error(f"❌ Lookup pipeline failed for '{word}': {e}")
        raise


@log_timing
async def _get_provider_definition(
    word: str,
    provider: DictionaryProvider,
    languages: list[Language],
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
) -> DictionaryEntry | None:
    """Get definition from specified provider.

    Returns:
        Tuple of (provider_data, provider_metrics)

    """
    logger.debug(f"📖 Fetching definition from {provider.value} for '{word}'")

    try:
        # Use factory function to create connector
        try:
            connector = create_connector(provider)
        except ValueError as e:
            raise ProviderFetchError(provider.value, str(e))

        storage = await get_storage()
        word_obj = await storage.get_word(word)
        requested_language_codes = to_language_codes(languages)

        if not word_obj:
            # Create new Word if doesn't exist
            word_obj = Word(
                text=word,
                normalized=word.lower(),
                languages=requested_language_codes,
            )
            await word_obj.save()
        else:
            # Word exists: merge requested languages into existing (requested take precedence)
            merged = merge_language_precedence(
                requested_languages=requested_language_codes,
                existing_languages=list(word_obj.languages),
            )
            if merged != list(word_obj.languages):
                old_languages = list(word_obj.languages)
                word_obj.languages = merged
                await word_obj.save()
                logger.debug(
                    f"Updated languages for '{word}': {old_languages} → {merged}",
                )

        # Check if this provider's data already exists in the DB (skip external fetch)
        if not force_refresh and word_obj:
            db_entry = await DictionaryEntry.find_one(
                DictionaryEntry.word_id == word_obj.id,
                DictionaryEntry.provider == provider,
                {"definition_ids": {"$exists": True, "$ne": []}},
            )
            if db_entry and db_entry.definition_ids:
                logger.info(
                    f"⚡ DB hit for '{word}' provider={provider.value} "
                    f"({len(db_entry.definition_ids)} definitions) — skipping external fetch"
                )
                return db_entry

        if connector:
            fetch_start = time.perf_counter()

            # Per-provider timeout to prevent a single slow provider from blocking
            try:
                result = await asyncio.wait_for(
                    connector.fetch_definition(word_obj, state_tracker),
                    timeout=_PROVIDER_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.warning(
                    f"Provider {provider.value} timed out after {_PROVIDER_TIMEOUT_SECONDS}s for '{word}'"
                )
                raise ProviderTimeoutError(provider.value, _PROVIDER_TIMEOUT_SECONDS)

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
                logger.debug(f"⚠️  Provider {provider.value} returned no results for '{word}'")

            return result

        return None

    except Exception as e:
        log_provider_fetch(provider_name=provider.value, word=word, success=False)

        logger.error(f"❌ Provider {provider.value} failed for '{word}': {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")

        raise ProviderFetchError(provider.value, str(e)) from e


@log_timing
@log_stage("AI Synthesis", "🤖")
async def _synthesize_with_ai(
    word: str,
    providers: list[DictionaryEntry],
    languages: list[Language],
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
) -> DictionaryEntry | None:
    """Synthesize definition using AI."""
    logger.debug(f"🤖 Starting AI synthesis for '{word}' with {len(providers)} providers")

    # Log provider data quality
    total_definitions = sum(len(p.definition_ids) if p.definition_ids else 0 for p in providers)
    logger.debug(f"📊 Total definitions to synthesize: {total_definitions}")

    try:
        synthesizer = get_definition_synthesizer()
        result = await synthesizer.synthesize_entry(
            word=word,
            providers_data=providers,
            languages=languages,
            force_refresh=force_refresh,
            state_tracker=state_tracker,
        )

        if result:
            logger.debug(
                f"✅ AI synthesis complete: {len(result.definition_ids) if result.definition_ids else 0} "
                f"synthesized definitions",
            )
        else:
            logger.warning(f"⚠️  AI synthesis returned empty result for '{word}'")

        return result
    except Exception as e:
        logger.error(f"❌ AI synthesis failed for '{word}': {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise SynthesisError(word, "ai", str(e)) from e


@log_timing
@log_stage("Provider Mapping", "🔄")
async def _create_provider_mapped_entry(
    word: str,
    provider_data: DictionaryEntry,
    state_tracker: StateTracker | None = None,
    no_ai: bool = False,
) -> DictionaryEntry | None:
    """Create a synthesized entry from provider data without full AI synthesis.

    When no_ai=True, skips all AI calls (dedup + clustering) and uses raw provider
    definitions directly. When no_ai=False, uses AI for deduplication and clustering
    but not for content generation.
    """
    logger.info(f"📦 Creating provider-mapped entry for '{word}' from {provider_data.provider}")

    try:
        # Get Word object
        word_obj = await Word.get(provider_data.word_id)
        if not word_obj:
            logger.error(f"Word object not found for ID: {provider_data.word_id}")
            raise NotFoundException("Word", str(provider_data.word_id))

        # Load all definitions from provider
        all_definitions: list[Definition] = []
        for def_id in provider_data.definition_ids:
            definition = await Definition.get(def_id)
            if definition:
                all_definitions.append(definition)

        if not all_definitions:
            logger.warning("No definitions found for provider data")
            raise ProviderFetchError("mapping", "No definitions found for provider data")

        if no_ai:
            # Skip all AI operations — use raw provider definitions as-is
            logger.info(
                f"⚡ no_ai=True: using {len(all_definitions)} raw provider definitions (no dedup/clustering)",
            )
            final_def_ids = [d.id for d in all_definitions if d.id is not None]
        else:
            # Use AI for deduplication only
            logger.info(f"🔍 Deduplicating {len(all_definitions)} definitions (AI-assisted)")
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
                f"✅ Deduplicated {len(all_definitions)} → {len(unique_definitions)} definitions",
            )

            # Use AI for clustering only
            if state_tracker:
                await state_tracker.update_stage(Stages.AI_CLUSTERING)

            logger.info("📊 Clustering definitions (AI-assisted)")

            clustered_definitions = await cluster_definitions(
                word_obj,
                unique_definitions,
                synthesizer.ai,
                state_tracker,
            )

            # Save the clustered definitions to persist meaning_cluster assignments
            for definition in clustered_definitions:
                await definition.save()

            # Update definition IDs with clustered definitions
            final_def_ids = [d.id for d in clustered_definitions if d.id is not None]

        # Extract etymology if available
        etymology = None
        if provider_data.raw_data and provider_data.raw_data.get("etymology"):
            etymology = Etymology(text=provider_data.raw_data["etymology"])

        # Create the synthesized entry without AI content generation
        synthesized_entry = DictionaryEntry(
            resource_id=f"{word}:synthesis",
            provider=DictionaryProvider.SYNTHESIS,
            word_id=word_obj.id,
            languages=to_language_codes(list(word_obj.languages)),
            pronunciation_id=provider_data.pronunciation_id,
            definition_ids=final_def_ids,
            etymology=provider_data.etymology or etymology,
            fact_ids=[],  # No facts in non-AI mode
            model_info=None,  # No AI model info
        )

        # Save the entry with version history
        await save_entry_versioned(synthesized_entry, word)

        logger.info(
            f"✅ Created provider-mapped entry for '{word}' with "
            f"{len(synthesized_entry.definition_ids)} definitions",
        )

        if state_tracker:
            await state_tracker.update_stage(Stages.STORAGE_SAVE)

        return synthesized_entry

    except Exception as e:
        logger.error(f"❌ Failed to create provider-mapped entry: {e}")
        raise SynthesisError(word, "mapping", str(e)) from e
