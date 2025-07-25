"""Enhanced definition synthesizer using new data models and functional pipeline."""

from __future__ import annotations

from ..constants import DictionaryProvider, Language
from ..core.state_tracker import Stages, StateTracker
from ..models import (
    Definition,
    ModelInfo,
    ProviderData,
    SynthesizedDictionaryEntry,
    Word,
)
from ..storage.mongodb import get_storage
from ..utils.logging import get_logger
from .connector import OpenAIConnector
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
        self.ai = openai_connector
        self.examples_count = examples_count
        self.facts_count = facts_count

    async def synthesize_entry(
        self,
        word: str,
        providers_data: list[ProviderData],
        language: Language = Language.ENGLISH,
        force_refresh: bool = False,
        state_tracker: StateTracker | None = None,
    ) -> SynthesizedDictionaryEntry | None:
        """Synthesize a complete dictionary entry from provider data."""

        # Get or create Word document
        storage = await get_storage()
        word_obj = await storage.get_word(word)
        if not word_obj:
            word_obj = Word(text=word, normalized=word.lower(), language=language)
            await word_obj.save()

        # Check for existing synthesized entry
        if not force_refresh:
            existing = await SynthesizedDictionaryEntry.find_one(
                SynthesizedDictionaryEntry.word_id == str(word_obj.id)
            )
            if existing:
                logger.info(f"Using existing synthesized entry for '{word}'")
                return existing

        # Extract all definitions from providers
        all_definitions: list[Definition] = []

        for provider_data in providers_data:
            # Load definitions
            for def_id in provider_data.definition_ids:
                definition = await Definition.get(def_id)
                if definition:
                    all_definitions.append(definition)

        if not all_definitions:
            logger.warning(f"No definitions found for '{word}'")
            return None

        # DEDUPLICATION: Remove exact duplicates before clustering
        unique_definitions: list[Definition] = []
        seen_definitions: set[tuple[str, str]] = set()

        for definition in all_definitions:
            # Create a key based on part of speech and normalized text
            key = (
                definition.part_of_speech,
                definition.text.strip().lower()
            )

            if key not in seen_definitions:
                seen_definitions.add(key)
                unique_definitions.append(definition)
            else:
                logger.debug(f"Skipping duplicate definition: {definition.text[:50]}...")

        logger.info(
            f"Deduplicated {len(all_definitions)} definitions to {len(unique_definitions)} unique definitions for '{word}'"
        )

        # Cluster unique definitions
        if state_tracker:
            await state_tracker.update_stage(Stages.AI_CLUSTERING)

        clustered_definitions = await cluster_definitions(
            word_obj, unique_definitions, self.ai, state_tracker
        )

        # Synthesize core components
        if state_tracker:
            await state_tracker.update_stage(Stages.AI_SYNTHESIS, progress=65)

        # Synthesize definitions for each cluster
        synthesized_definitions = await self._synthesize_definitions(
            word_obj, clustered_definitions, state_tracker
        )

        # Synthesize pronunciation
        pronunciation = await synthesize_pronunciation(
            word_obj, providers_data, self.ai, state_tracker
        )

        # Synthesize etymology
        etymology = await synthesize_etymology(
            word_obj, providers_data, self.ai, state_tracker
        )

        # Generate facts
        facts = await generate_facts(
            word_obj, synthesized_definitions, self.ai, self.facts_count
        )

        # Create synthesized entry
        entry = SynthesizedDictionaryEntry(
            word_id=str(word_obj.id),
            pronunciation_id=str(pronunciation.id) if pronunciation else None,
            definition_ids=[str(d.id) for d in synthesized_definitions],
            etymology=etymology,
            fact_ids=[str(f.id) for f in facts],
            model_info=ModelInfo(
                name=self.ai.model_name,
                generation_count=1,
                confidence=0,  # Will be set later
            ),
            source_provider_data_ids=[str(pd.id) for pd in providers_data],
        )

        # Save entry
        if state_tracker:
            await state_tracker.update_stage(Stages.STORAGE_SAVE, progress=90)

        await entry.save()
        logger.success(
            f"Created synthesized entry for '{word}' with {len(synthesized_definitions)} definitions"
        )

        # Enhance and synthesize definitions
        await enhance_definitions_parallel(
            definitions=synthesized_definitions,
            word=word_obj,
            ai=self.ai,
            force_refresh=force_refresh,
            state_tracker=state_tracker,
        )

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

        synthesized_definitions = []

        # Process each cluster
        for cluster_id, cluster_defs in clusters.items():
            logger.info(
                f"Synthesizing cluster '{cluster_id}' with {len(cluster_defs)} definitions"
            )

            # Convert definitions to dict format for synthesis
            # Note: We don't have provider info on Definition model, so use "wiktionary" as default
            def_dicts = [
                {
                    "text": d.text,
                    "part_of_speech": d.part_of_speech,
                    "provider": "wiktionary",  # Default provider since we don't track this on Definition
                }
                for d in cluster_defs
            ]

            # Synthesize definition text using modular function
            synthesis_result = await synthesize_definition_text(
                clustered_definitions=def_dicts,
                word=word.text,
                ai=self.ai,
                state_tracker=state_tracker,
            )

            # Create definition
            definition = Definition(
                word_id=str(word.id),
                part_of_speech=synthesis_result["part_of_speech"],
                text=synthesis_result["definition_text"],
                meaning_cluster=cluster_defs[
                    0
                ].meaning_cluster,  # Use cluster from source
            )
            await definition.save()

            # Update definition with synonyms and example IDs
            await definition.save()
            synthesized_definitions.append(definition)

        return synthesized_definitions

    async def generate_fallback_entry(
        self,
        word: str,
        language: Language = Language.ENGLISH,
        force_refresh: bool = False,
        state_tracker: StateTracker | None = None,
    ) -> SynthesizedDictionaryEntry | None:
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

        if not dictionary_entry or not dictionary_entry.provider_data:
            logger.warning(f"No definitions generated for '{word}'")
            return None

        # Convert to provider data format
        definitions: list[Definition] = []
        for idx, ai_def in enumerate(dictionary_entry.provider_data.definitions):
            # Create definition
            definition = Definition(
                word_id=str(word_obj.id),
                part_of_speech=ai_def.part_of_speech,
                text=ai_def.definition,
            )
            await definition.save()

        # Create tmp provider data
        provider_data = ProviderData(
            word_id=str(word_obj.id),
            provider=DictionaryProvider.AI_FALLBACK,
            definition_ids=[str(d.id) for d in definitions],
        )
        await provider_data.save()

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
