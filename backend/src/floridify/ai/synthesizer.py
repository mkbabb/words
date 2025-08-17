"""Enhanced definition synthesizer using new data models and functional pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..caching.manager import get_version_manager
from ..caching.models import CacheNamespace
from ..core.state_tracker import Stages, StateTracker
from ..models import (
    Definition,
    DictionaryProvider,
    Language,
    Word,
)
from ..models.dictionary import DictionaryEntry
from ..models.versioned import ResourceType, VersionConfig
from ..storage.mongodb import get_storage
from ..utils.logging import get_logger
from .connector import OpenAIConnector
from .constants import SynthesisComponent
from .synthesis_functions import (
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
        openai_connector: OpenAIConnector,
        examples_count: int = 2,
        facts_count: int = 3,
    ) -> None:
        # Wrap connector for batch logging
        self.ai = openai_connector  # wrap_connector_for_logging(openai_connector)
        self.examples_count = examples_count
        self.facts_count = facts_count

    async def synthesize_entry(
        self,
        word: str,
        providers_data: list[DictionaryEntry],
        language: Language = Language.ENGLISH,
        force_refresh: bool = False,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryEntry | None:
        """Synthesize a complete dictionary entry from provider data."""
        # Get or create Word document
        storage = await get_storage()
        word_obj = await storage.get_word(word)
        if not word_obj:
            word_obj = Word(text=word, language=language)
            await word_obj.save()

        # Check for existing synthesized entry
        if not force_refresh:
            existing = await DictionaryEntry.find_one(
                DictionaryEntry.word_id == word_obj.id,
                DictionaryEntry.provider == DictionaryProvider.SYNTHESIS,
            )
            if existing:
                logger.info(f"Using existing synthesized entry for '{word}'")
                return existing

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

        # DEDUPLICATION: Use AI to identify and merge near-duplicates before clustering
        logger.info(
            f"Deduplicating {len(all_definitions)} definitions before clustering"
        )

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

            # Update the definition text with the deduplicated version
            primary_def.text = dedup_def.definition
            unique_definitions.append(primary_def)

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

        # Run all synthesis operations in parallel
        synthesized_definitions, pronunciation, etymology, facts = await asyncio.gather(
            self._synthesize_definitions(
                word_obj, clustered_definitions, state_tracker
            ),
            synthesize_pronunciation(
                word_obj.text, providers_data, self.ai, state_tracker
            ),
            synthesize_etymology(word_obj, providers_data, self.ai, state_tracker),
            generate_facts(
                word_obj, unique_definitions, self.ai, self.facts_count, state_tracker
            ),
        )

        # Create synthesized entry
        assert word_obj.id is not None  # Word should have been saved before this point

        entry = DictionaryEntry(
            provider=DictionaryProvider.SYNTHESIS,
            word_id=word_obj.id,
            pronunciation_id=pronunciation.id if pronunciation else None,
            definition_ids=[d.id for d in synthesized_definitions if d.id is not None],
            etymology=etymology,
            fact_ids=[f.id for f in facts if f.id is not None],
            model_info=self.ai.last_model_info,  # Use full model info from AI
        )

        # Save entry using version manager
        if state_tracker:
            await state_tracker.update_stage(Stages.STORAGE_SAVE)

        await self._save_entry_with_version_manager(entry, word.text if isinstance(word, Word) else word)
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
        # Group by cluster
        clusters: dict[str, list[Definition]] = {}
        for definition in clustered_definitions:
            if definition.meaning_cluster:
                cluster_id = definition.meaning_cluster.id
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(definition)

        # Create tasks for parallel synthesis
        synthesis_tasks = []

        async def synthesize_cluster(
            cluster_id: str, cluster_defs: list[Definition]
        ) -> Definition:
            logger.info(
                f"Synthesizing cluster '{cluster_id}' with {len(cluster_defs)} definitions"
            )

            # Convert definitions to dict format, retaining provider info
            def_dicts = []
            for d in cluster_defs:
                provider = (
                    d.providers[0] if d.providers else DictionaryProvider.WIKTIONARY
                )
                def_dicts.append(
                    {
                        "text": d.text,
                        "part_of_speech": d.part_of_speech,
                        "provider": provider.value,
                    }
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

            definition = Definition(
                word_id=word.id,
                part_of_speech=synthesis_result["part_of_speech"],
                text=synthesis_result["definition_text"],
                meaning_cluster=cluster_defs[0].meaning_cluster,
                providers=(
                    list(providers_set)
                    if providers_set
                    else [DictionaryProvider.SYNTHESIS]
                ),
                model_info=self.ai.last_model_info,  # Set model info from AI connector
            )
            await definition.save()
            return definition

        # Create tasks for all clusters
        for cluster_id, cluster_defs in clusters.items():
            task = synthesize_cluster(cluster_id, cluster_defs)
            synthesis_tasks.append(task)

        # Execute all syntheses in parallel

        synthesized_definitions = await asyncio.gather(*synthesis_tasks)

        return synthesized_definitions

    async def generate_fallback_entry(
        self,
        word: str,
        language: Language = Language.ENGLISH,
        force_refresh: bool = False,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryEntry | None:
        """Generate a complete fallback entry using AI."""
        logger.info(f"Generating AI fallback for '{word}'")

        # Get or create Word
        storage = await get_storage()
        word_obj = await storage.get_word(word)
        if not word_obj:
            word_obj = Word(
                text=word,
                normalized=word.lower(),
                language=language,
            )
            await word_obj.save()

        if state_tracker:
            await state_tracker.update_stage(Stages.AI_FALLBACK)

        # Generate fallback definitions
        dictionary_entry = await self.ai.lookup_fallback(word)

        if not dictionary_entry or not hasattr(dictionary_entry, 'definitions') or not dictionary_entry.definitions:
            logger.warning(f"No definitions generated for '{word}'")
            return None

        # Convert to provider data format
        definitions: list[Definition] = []
        for ai_def in dictionary_entry.definitions:
            # Create definition
            assert (
                word_obj.id is not None
            )  # Word should have been saved before this point
            definition = Definition(
                word_id=word_obj.id,
                part_of_speech=ai_def.part_of_speech,
                text=ai_def.definition,
            )
            await definition.save()
            definitions.append(definition)  # Add to the list!

        # Create tmp provider data
        assert word_obj.id is not None  # Word should have been saved before this point
        provider_data = DictionaryEntry(
            resource_id=f"{word}:{DictionaryProvider.AI_FALLBACK.value}",
            provider=DictionaryProvider.AI_FALLBACK,
            word_id=word_obj.id,
            definition_ids=[d.id for d in definitions if d.id is not None],
        )
        await self._save_entry_with_version_manager(provider_data, word)

        # Synthesize complete entry
        synthesized_entry = await self.synthesize_entry(
            word=word,
            providers_data=[provider_data],
            language=language,
            force_refresh=force_refresh,
            state_tracker=state_tracker,
        )

        # Clean up temporary provider data and definitions
        await provider_data.delete()
        for definition in definitions:
            await definition.delete()

        return synthesized_entry

    async def _save_entry_with_version_manager(
        self,
        entry: DictionaryEntry,
        word: str,
    ) -> None:
        """Save DictionaryEntry using the version manager.
        
        Args:
            entry: DictionaryEntry to save
            word: Word text for resource ID
        """
        manager = get_version_manager()
        
        # Create resource ID based on word and provider
        resource_id = f"{word}:{entry.provider.value}"
        
        # Convert entry to dict format for storage
        entry_dict = entry.model_dump(mode="json")
        
        # Prepare metadata
        metadata: dict[str, Any] = {
            "word": word,
            "provider": entry.provider.value,
            "word_id": str(entry.word_id) if entry.word_id else None,
        }
        
        # Add model info to metadata if available
        if entry.model_info:
            if isinstance(entry.model_info, dict):
                metadata["model_info"] = entry.model_info
            else:
                metadata["model_info"] = entry.model_info.model_dump(mode="json")
        
        # Save using version manager
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=entry_dict,
            config=VersionConfig(),
            metadata=metadata,
        )
        
        # Also save to MongoDB for compatibility
        await entry.save()
        
        logger.debug(f"Saved dictionary entry '{resource_id}' using version manager")

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
        from .constants import SynthesisComponent

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

        from .connector import get_openai_connector

        logger.info("Initializing definition synthesizer singleton")
        connector = get_openai_connector(config_path, force_recreate)
        _definition_synthesizer = DefinitionSynthesizer(
            connector, examples_count=examples_count
        )
        logger.success("Definition synthesizer singleton initialized")

    return _definition_synthesizer
