"""Enhanced definition synthesizer using new data models and functional pipeline."""

from __future__ import annotations

import asyncio
from enum import Enum
from pathlib import Path

from ..caching.manager import get_version_manager
from ..caching.models import ResourceType
from ..core.state_tracker import Stages, StateTracker
from ..models.base import EditMetadata, Language, OperationType, SynthesisAuditEntry
from ..models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    SourceReference,
    Word,
)
from ..storage.dictionary import _provider_str, save_definition_versioned, save_entry_versioned
from ..storage.mongodb import get_storage
from ..utils.concurrency import gather_bounded
from ..utils.language_precedence import (
    to_language_codes,
)
from ..utils.logging import get_logger
from .adaptive_counts import compute_counts
from .connector import AIConnector, get_ai_connector
from .constants import SynthesisComponent
from .dedup import local_deduplicate_definitions
from .synthesis import (
    cluster_definitions,
    enhance_definitions_parallel,
    generate_facts,
    synthesize_definition_text,
    synthesize_etymology,
    synthesize_pronunciation,
)

logger = get_logger(__name__)


class DefinitionSynthesizer:
    """Synthesizes dictionary entries using new models and parallel processing."""

    def __init__(
        self,
        openai_connector: AIConnector,
        examples_count: int = 2,
        facts_count: int = 3,
        use_local_dedup: bool = True,
    ) -> None:
        # Wrap connector for batch logging
        self.ai = openai_connector  # wrap_connector_for_logging(openai_connector)
        self.examples_count = examples_count
        self.facts_count = facts_count
        self.use_local_dedup = use_local_dedup

    async def synthesize_entry(
        self,
        word: str,
        providers_data: list[DictionaryEntry],
        languages: list[Language],
        force_refresh: bool = False,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryEntry | None:
        """Synthesize a complete dictionary entry from provider data."""
        if not languages:
            raise ValueError("languages must contain at least one language")

        requested_language_codes = to_language_codes(languages)

        # Get or create Word document
        storage = await get_storage()
        word_obj = await storage.get_word(word)
        if not word_obj:
            word_obj = Word(text=word, languages=requested_language_codes)
            await word_obj.save()

        assert word_obj.id is not None
        primary_language = requested_language_codes[0]

        # Check for existing synthesized entry
        existing_synthesis = await DictionaryEntry.find_one(
            DictionaryEntry.word_id == word_obj.id,
            DictionaryEntry.provider == DictionaryProvider.SYNTHESIS,
        )
        if existing_synthesis and not force_refresh:
            logger.info(f"Using existing synthesized entry for '{word}'")
            return existing_synthesis

        # Extract all definitions from providers
        # Collect all definition IDs for batch query
        all_def_ids = []
        for provider_data in providers_data:
            all_def_ids.extend(provider_data.definition_ids)

        # Batch load all definitions in a single query
        all_definitions: list[Definition] = await Definition.find(
            {"_id": {"$in": all_def_ids}},
        ).to_list()

        if not all_definitions:
            logger.warning(f"No definitions found for '{word}'")
            return None

        # Build provenance: which provider entry + version contributed which definitions
        source_entries: list[SourceReference] = []
        manager = get_version_manager()
        for provider_entry in providers_data:
            provider_value = _provider_str(provider_entry.provider)
            resource_id = f"{word_obj.text if isinstance(word, Word) else word}:{provider_value}"
            try:
                latest = await manager.get_latest(resource_id, ResourceType.DICTIONARY)
                entry_version = latest.version_info.version if latest else "1.0.0"
            except Exception:
                entry_version = "1.0.0"

            source_entries.append(
                SourceReference(
                    provider=provider_entry.provider,
                    entry_id=provider_entry.id,
                    entry_version=entry_version,
                    definition_ids=list(provider_entry.definition_ids),
                )
            )

        # DEDUPLICATION: Local 3-tier pipeline or AI fallback
        logger.info(f"Deduplicating {len(all_definitions)} definitions before clustering")

        if self.use_local_dedup:
            dedup_response = await local_deduplicate_definitions(
                word=word,
                definitions=all_definitions,
            )
        else:
            dedup_response = await self.ai.deduplicate_definitions(
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

            # Copy instead of mutating the tracked Beanie Document in-place,
            # so the original provider definition is not overwritten if .save() is called later.
            deduped = primary_def.model_copy(update={"text": dedup_def.definition, "id": None})
            unique_definitions.append(deduped)

            # Track all processed indices
            processed_indices.update(dedup_def.source_indices)

            # Log which definitions were merged
            if len(dedup_def.source_indices) > 1:
                merged_indices = dedup_def.source_indices[1:]
                logger.debug(
                    f"Merged definitions at indices {merged_indices} into index {primary_idx}: "
                    f"{dedup_def.reasoning}",
                )

        logger.success(
            f"Deduplicated {len(all_definitions)} → {len(unique_definitions)} definitions "
            f"(removed {dedup_response.removed_count} duplicates)",
        )

        # Cluster unique definitions
        if state_tracker:
            await state_tracker.update_stage(Stages.AI_CLUSTERING)

        clustered_definitions = await cluster_definitions(
            word_obj,
            unique_definitions,
            self.ai,
            state_tracker,
        )

        # Synthesize core components in parallel
        if state_tracker:
            await state_tracker.update_stage(Stages.AI_SYNTHESIS)

        # Compute adaptive facts count
        adaptive = compute_counts(
            language=primary_language,
            definition_count=len(unique_definitions),
        )
        facts_count = adaptive.facts

        # Parallel synthesis with return_exceptions=True: definitions are required,
        # but pronunciation/etymology/facts are optional enhancements
        results = await asyncio.gather(
            self._synthesize_definitions(word_obj, clustered_definitions, state_tracker),
            synthesize_pronunciation(
                word_obj.text,
                providers_data,
                self.ai,
                state_tracker,
                language=primary_language,
            ),
            synthesize_etymology(word_obj, providers_data, self.ai, state_tracker),
            generate_facts(word_obj, unique_definitions, self.ai, facts_count, state_tracker),
            return_exceptions=True,
        )

        # Partial failure policy: definitions are required (re-raised on failure),
        # pronunciation/etymology/facts degrade gracefully to None/empty
        synthesized_definitions = results[0]
        if isinstance(synthesized_definitions, BaseException):
            logger.error(f"Definition synthesis failed for '{word}': {synthesized_definitions}")
            raise synthesized_definitions

        pronunciation = results[1]
        if isinstance(pronunciation, BaseException):
            logger.warning(f"Pronunciation synthesis failed for '{word}': {pronunciation}")
            pronunciation = None

        etymology = results[2]
        if isinstance(etymology, BaseException):
            logger.warning(f"Etymology synthesis failed for '{word}': {etymology}")
            etymology = None

        facts = results[3]
        if isinstance(facts, BaseException):
            logger.warning(f"Facts generation failed for '{word}': {facts}")
            facts = []

        # Create synthesized entry
        assert word_obj.id is not None  # Word should have been saved before this point

        entry = DictionaryEntry(
            provider=DictionaryProvider.SYNTHESIS,
            word_id=word_obj.id,
            languages=requested_language_codes,
            pronunciation_id=pronunciation.id if pronunciation else None,
            definition_ids=[d.id for d in synthesized_definitions if d.id is not None],
            etymology=etymology,
            fact_ids=[f.id for f in facts if f.id is not None],
            source_entries=source_entries,
            model_info=self.ai.last_model_info,  # Use full model info from AI
        )

        # Save entry using version manager with synthesis audit trail
        if state_tracker:
            await state_tracker.update_stage(Stages.STORAGE_SAVE)

        provider_names = [_provider_str(pe.provider) for pe in providers_data]
        edit_metadata = self._build_synthesis_edit_metadata(
            source_providers=provider_names,
            definitions_input=len(all_definitions),
            definitions_output=len(synthesized_definitions),
            dedup_removed=dedup_response.removed_count,
            clusters_created=len(
                {d.meaning_cluster.slug for d in synthesized_definitions if d.meaning_cluster}
            ),
        )

        await self._save_entry_with_version_manager(
            entry,
            word.text if isinstance(word, Word) else word,
            edit_metadata=edit_metadata,
        )
        logger.success(
            f"Created synthesized entry for '{word}' with {len(synthesized_definitions)} definitions",
        )

        # Enhance and synthesize definitions
        await enhance_definitions_parallel(
            definitions=synthesized_definitions,
            word=word_obj,
            ai=self.ai,
            force_refresh=force_refresh,
            state_tracker=state_tracker,
        )

        # Report batch analysis removed - simple_batch_logger not available

        return entry

    async def _synthesize_definitions(
        self,
        word: Word,
        clustered_definitions: list[Definition],
        state_tracker: StateTracker | None = None,
    ) -> list[Definition]:
        """Synthesize definitions by cluster using modular functions."""
        # Group by cluster slug
        clusters: dict[str, list[Definition]] = {}
        for definition in clustered_definitions:
            if definition.meaning_cluster:
                cluster_slug = definition.meaning_cluster.slug
                if cluster_slug not in clusters:
                    clusters[cluster_slug] = []
                clusters[cluster_slug].append(definition)

        # Create tasks for parallel synthesis
        synthesis_tasks = []

        async def synthesize_cluster(
            cluster_slug: str, cluster_defs: list[Definition]
        ) -> Definition:
            logger.info(
                f"Synthesizing cluster '{cluster_slug}' with {len(cluster_defs)} definitions"
            )

            # Convert definitions to dict format, retaining provider info
            def_dicts = []
            for d in cluster_defs:
                provider = d.providers[0] if d.providers else DictionaryProvider.WIKTIONARY
                # use_enum_values=True means provider may already be a string
                provider_str = provider.value if isinstance(provider, Enum) else provider
                def_dicts.append(
                    {
                        "text": d.text,
                        "part_of_speech": d.part_of_speech,
                        "provider": provider_str,
                    },
                )

            # Synthesize definition text
            synthesis_result = await synthesize_definition_text(
                clustered_definitions=def_dicts,
                word=word,
                ai=self.ai,
                state_tracker=state_tracker,
            )

            # Create and save definition with model info and providers
            assert word.id is not None  # Word should have been saved before this point

            # Collect all unique providers from cluster definitions
            providers_set = set()
            for d in cluster_defs:
                if d.providers:
                    providers_set.update(d.providers)

            # Track which provider defs contributed to this synthesized definition
            source_defs: list[SourceReference] = []
            for d in cluster_defs:
                if d.dictionary_entry_id and d.providers:
                    source_defs.append(
                        SourceReference(
                            provider=d.providers[0],
                            entry_id=d.dictionary_entry_id,
                            entry_version="",  # Filled from parent entry provenance
                            definition_ids=[d.id] if d.id else [],
                        )
                    )

            definition = Definition(
                word_id=word.id,
                part_of_speech=synthesis_result["part_of_speech"],
                text=synthesis_result["definition_text"],
                meaning_cluster=cluster_defs[0].meaning_cluster,
                providers=(
                    list(providers_set) if providers_set else [DictionaryProvider.SYNTHESIS]
                ),
                source_definitions=source_defs,
                model_info=self.ai.last_model_info,  # Set model info from AI connector
            )
            await save_definition_versioned(definition, word.text)
            return definition

        # Create tasks for all clusters
        for cluster_slug, cluster_defs in clusters.items():
            task = synthesize_cluster(cluster_slug, cluster_defs)
            synthesis_tasks.append(task)

        # Parallel cluster synthesis with bounded concurrency (max 4 concurrent AI calls)
        results = await gather_bounded(*synthesis_tasks, limit=4, return_exceptions=True)

        synthesized_definitions = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                cluster_slug = list(clusters.keys())[i]
                logger.error(
                    f"Cluster '{cluster_slug}' synthesis failed: {result}",
                    exc_info=result,
                )
            else:
                synthesized_definitions.append(result)

        return synthesized_definitions

    def _build_synthesis_edit_metadata(
        self,
        *,
        source_providers: list[str],
        definitions_input: int,
        definitions_output: int,
        dedup_removed: int,
        clusters_created: int,
        components_enhanced: list[str] | None = None,
    ) -> EditMetadata:
        """Build EditMetadata for a synthesis operation."""
        model_info = self.ai.last_model_info
        return EditMetadata(
            operation_type=OperationType.AI_SYNTHESIS,
            change_reason=f"AI synthesis from {len(source_providers)} providers",
            synthesis_audit=SynthesisAuditEntry(
                model_name=model_info.name if model_info else "unknown",
                components_enhanced=components_enhanced or [],
                total_tokens=model_info.total_tokens if model_info else None,
                response_time_ms=model_info.response_time_ms if model_info else None,
                source_providers=source_providers,
                definitions_input=definitions_input,
                definitions_output=definitions_output,
                dedup_removed=dedup_removed,
                clusters_created=clusters_created,
            ),
        )

    async def _save_entry_with_version_manager(
        self,
        entry: DictionaryEntry,
        word: str,
        edit_metadata: EditMetadata | None = None,
    ) -> None:
        """Save DictionaryEntry using the version manager.

        Args:
            entry: DictionaryEntry to save
            word: Word text for resource ID
            edit_metadata: Optional edit metadata for version audit trail

        """
        await save_entry_versioned(entry, word, edit_metadata=edit_metadata)

    async def resynthesize_from_provenance(
        self,
        word: str,
        languages: list[Language] | None = None,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryEntry | None:
        """Re-synthesize a word from its existing provider data.

        Finds all non-synthesis DictionaryEntry records for the word and runs
        the full synthesis pipeline (dedup → cluster → synthesize → enhance),
        creating a new versioned synthesized entry with provenance tracking.

        Args:
            word: Word text to re-synthesize
            languages: Override languages (defaults to word's existing languages)
            state_tracker: Optional progress tracking

        Returns:
            New synthesized DictionaryEntry, or None if no provider data exists

        """
        storage = await get_storage()
        word_obj = await storage.get_word(word)
        if not word_obj:
            logger.warning(f"Word '{word}' not found in database")
            return None

        # Find all non-synthesis provider entries for this word
        provider_entries: list[DictionaryEntry] = await DictionaryEntry.find(
            DictionaryEntry.word_id == word_obj.id,
            DictionaryEntry.provider != DictionaryProvider.SYNTHESIS,
        ).to_list()

        if not provider_entries:
            logger.warning(f"No provider data found for '{word}' — nothing to re-synthesize")
            return None

        resolved_languages = languages or list(word_obj.languages)
        if not resolved_languages:
            resolved_languages = [Language.ENGLISH]

        logger.info(
            f"Re-synthesizing '{word}' from {len(provider_entries)} provider entries: "
            f"{[_provider_str(e.provider) for e in provider_entries]}",
        )

        # Run full synthesis pipeline with force_refresh to create a new version
        return await self.synthesize_entry(
            word=word,
            providers_data=provider_entries,
            languages=resolved_languages,
            force_refresh=True,
            state_tracker=state_tracker,
        )

    async def regenerate_entry_components(
        self,
        entry_id: str,
        components: set[SynthesisComponent] | None = None,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryEntry | None:
        """Regenerate specific components of an existing synthesized dictionary entry.

        Args:
            entry_id: ID of the existing synthesized dictionary entry
            components: Set of component names to regenerate (uses default if None)
            state_tracker: Optional progress tracking

        Returns:
            Updated synthesized dictionary entry or None if not found

        """
        # Fetch existing entry
        entry = await DictionaryEntry.get(entry_id)
        if not entry:
            logger.error(f"Synthesized entry not found: {entry_id}")
            return None

        # Get associated word
        word = await Word.get(entry.word_id)
        if not word:
            logger.error(f"Word not found for entry: {entry.word_id}")
            return None

        # Load existing definitions
        definitions = []
        for def_id in entry.definition_ids:
            definition = await Definition.get(def_id)
            if definition:
                definitions.append(definition)

        if not definitions:
            logger.error(f"No definitions found for entry: {entry_id}")
            return None

        # Use default components if none specified
        if components is None:
            components = SynthesisComponent.default_definition_components()

        logger.info(f"Regenerating components {components} for entry {entry_id}")

        if state_tracker:
            await state_tracker.update_stage(
                Stages.AI_SYNTHESIS,
            )

        # Enhance definitions with force_refresh=True
        await enhance_definitions_parallel(
            definitions=definitions,
            word=word,
            ai=self.ai,
            components=components,
            force_refresh=True,  # Force regeneration of all specified components
            state_tracker=state_tracker,
        )

        # Refresh entry from database to get updated data
        entry = await DictionaryEntry.get(entry_id)

        if state_tracker:
            await state_tracker.update_stage(
                Stages.COMPLETE,
            )

        logger.info(f"Successfully regenerated components for entry {entry_id}")
        return entry


# Global singleton instance
_definition_synthesizer: DefinitionSynthesizer | None = None


def get_definition_synthesizer(
    config_path: str | Path | None = None,
    examples_count: int = 2,
    force_recreate: bool = False,
) -> DefinitionSynthesizer:
    """Get or create the global definition synthesizer singleton.

    Args:
        config_path: Path to configuration file
        examples_count: Number of examples to generate
        force_recreate: Force recreation of the synthesizer

    Returns:
        Initialized definition synthesizer instance

    """
    global _definition_synthesizer

    if _definition_synthesizer is None or force_recreate:
        logger.info("Initializing definition synthesizer singleton")
        connector = get_ai_connector(config_path, force_recreate)
        _definition_synthesizer = DefinitionSynthesizer(connector, examples_count=examples_count)
        logger.success("Definition synthesizer singleton initialized")

    return _definition_synthesizer
