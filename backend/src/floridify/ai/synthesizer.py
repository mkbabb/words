"""Definition synthesizer for creating unified dictionary entries."""

from __future__ import annotations

import time
from datetime import datetime

from ..constants import DictionaryProvider
from ..models import (
    Definition,
    Examples,
    GeneratedExample,
    Pronunciation,
    ProviderData,
    SynthesizedDictionaryEntry,
)
from ..storage.mongodb import _ensure_initialized, get_synthesized_entry, save_synthesized_entry
from ..utils.logging import get_logger
from ..utils.state_tracker import PipelineStage, StateTracker
from .connector import OpenAIConnector

logger = get_logger(__name__)


class DefinitionSynthesizer:
    """Synthesizes dictionary entries from multiple providers_data using AI."""

    def __init__(self, openai_connector: OpenAIConnector, examples_count: int = 2) -> None:
        self.ai = openai_connector
        self.examples_count = examples_count

    async def synthesize_entry(
        self,
        word: str,
        providers_data: list[ProviderData],
        force_refresh: bool = False,
        state_tracker: StateTracker | None = None,
    ) -> SynthesizedDictionaryEntry | None:
        """Synthesize a complete dictionary entry from provider data using meaning clusters."""

        # Check if we already have a synthesized entry (unless force_refresh is True)
        if not force_refresh:
            existing = await get_synthesized_entry(word)

            if existing is not None:
                logger.info(f"📋 Using cached synthesized entry for '{word}'")
                return existing

        # Generate pronunciation if not available
        pronunciation = await self._synthesize_pronunciation(word)

        # Extract all definitions with their full Definition objects for clustering
        all_definition_objects: list[Definition] = []
        all_definition_tuples: list[tuple[str, str, str]] = []

        for provider_data in providers_data:
            for definition in provider_data.definitions:
                all_definition_objects.append(definition)
                all_definition_tuples.append(
                    (
                        provider_data.provider_name,
                        definition.word_type,
                        definition.definition,
                    )
                )

        if not all_definition_objects:
            logger.warning(f"No definitions found for '{word}'")
            return None

        # Extract cluster mappings using AI
        logger.info(f"🔍 Analyzing {len(all_definition_objects)} definitions for cluster mappings")

        if state_tracker:
            await state_tracker.update(
                PipelineStage.AI_CLUSTERING,
                40,
                f"Clustering {len(all_definition_objects)} definitions",
                {"word": word, "definitions_count": len(all_definition_objects)},
            )

        cluster_response = await self.ai.extract_cluster_mapping(word, all_definition_tuples)

        if state_tracker:
            await state_tracker.update(
                PipelineStage.AI_CLUSTERING,
                50,
                f"Clustered into {len(cluster_response.cluster_mappings)} groups",
                {
                    "word": word,
                    "cluster_count": len(cluster_response.cluster_mappings),
                    "definitions_count": len(all_definition_objects),
                },
            )

        # Update Definition objects with their cluster assignments
        cluster_descriptions = {}
        for cluster_mapping in cluster_response.cluster_mappings:
            cluster_id = cluster_mapping.cluster_id
            cluster_descriptions[cluster_id] = cluster_mapping.cluster_description
            for idx in cluster_mapping.definition_indices:
                if 0 <= idx < len(all_definition_objects):
                    all_definition_objects[idx].meaning_cluster = cluster_id

        # Synthesize definitions for each cluster
        synthesized_definitions = await self._synthesize_definitions(
            word=word,
            clustered_definitions=all_definition_objects,
            cluster_descriptions=cluster_descriptions,
            state_tracker=state_tracker,
        )

        # Ensure MongoDB is initialized before creating the entry
        await _ensure_initialized()

        # Create synthesized entry
        entry = SynthesizedDictionaryEntry(
            word=word,
            pronunciation=pronunciation,
            definitions=synthesized_definitions,
            last_updated=datetime.now(),
        )

        # Save to database
        if state_tracker:
            await state_tracker.update(
                PipelineStage.STORAGE_SAVE, 80, f"Saving entry for '{word}'", {"word": word}
            )

        try:
            await save_synthesized_entry(entry)

            if state_tracker:
                await state_tracker.update(
                    PipelineStage.STORAGE_SAVE,
                    90,
                    f"Saved entry for '{word}'",
                    {"word": word, "success": True},
                )
        except Exception as e:
            logger.error(f"Failed to save synthesized entry for '{word}': {e}")
            # Still return the entry even if saving failed
            if state_tracker:
                await state_tracker.update(
                    PipelineStage.STORAGE_SAVE,
                    90,
                    f"Failed to save entry for '{word}'",
                    {"word": word, "success": False, "error": str(e)},
                )

        return entry

    async def generate_fallback_entry(
        self, word: str, force_refresh: bool = False, state_tracker: StateTracker | None = None
    ) -> SynthesizedDictionaryEntry | None:
        """Generate a complete fallback entry using AI."""
        logger.info(f"🔮 Starting AI fallback generation for '{word}'")

        # Generate fallback provider data
        dictionary_entry = await self.ai.lookup_fallback(word)

        if dictionary_entry is None or dictionary_entry.provider_data is None:
            logger.info(f"🚫 No valid definitions generated for '{word}'")
            # Ensure MongoDB is initialized before creating the entry
            await _ensure_initialized()
            # Return minimal entry for nonsense words
            return SynthesizedDictionaryEntry(
                word=word,
                pronunciation=Pronunciation(),
                last_updated=datetime.now(),
            )

        # Convert AI response to full provider data
        definitions: list[Definition] = []
        for definition in dictionary_entry.provider_data.definitions:
            # Generate examples for fallback using configured count
            examples_response = await self.ai.examples(
                word=word,
                word_type=definition.word_type,
                definition=definition.definition,
                count=self.examples_count,
            )

            examples = Examples(
                generated=[
                    GeneratedExample(sentence=sentence)
                    for sentence in examples_response.example_sentences
                ]
            )

            full_def = Definition(
                word_type=definition.word_type,
                definition=definition.definition,
                examples=examples,
            )

            definitions.append(full_def)

        provider_data = ProviderData(
            provider_name=DictionaryProvider.AI_FALLBACK.value,
            definitions=definitions,
            last_updated=datetime.now(),
            raw_metadata={
                "synthesis_confidence": dictionary_entry.confidence,
                "model_name": self.ai.model_name,
            },
        )

        providers_data = [provider_data]

        logger.success(
            f"🎉 Successfully created AI fallback entry for '{word}' "
            f"with {len(definitions)} definitions"
        )

        return await self.synthesize_entry(
            word=word,
            providers_data=providers_data,
            force_refresh=force_refresh,
        )

    async def _synthesize_definitions(
        self,
        word: str,
        clustered_definitions: list[Definition],
        cluster_descriptions: dict[str, str],
        state_tracker: StateTracker | None = None,
    ) -> list[Definition]:
        """Synthesize definitions by processing each cluster and creating normalized definitions.

        Args:
            word: The word to synthesize definitions for.
            clustered_definitions: List of Definition objects with meaning_cluster assigned.
            cluster_descriptions: Mapping of cluster_id to human-readable descriptions.
        """

        if not clustered_definitions:
            return []

        synthesized_definitions: list[Definition] = []

        # Group definitions by cluster
        clusters: dict[str, list[Definition]] = {}
        for definition in clustered_definitions:
            cluster_id = definition.meaning_cluster
            if cluster_id:
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(definition)

        # Process each cluster
        total_clusters = len(clusters)
        for i, (cluster_id, cluster_definitions) in enumerate(clusters.items()):
            logger.info(
                f"🧠 Synthesizing definitions for cluster '{cluster_id}' "
                f"with {len(cluster_definitions)} definitions"
            )
            cluster_start = time.time()

            if state_tracker:
                # Progress from 50-60% for synthesis
                progress = 50 + (i * 10 / total_clusters)
                await state_tracker.update(
                    PipelineStage.AI_SYNTHESIS,
                    progress,
                    f"Synthesizing cluster {i + 1}/{total_clusters}",
                    {
                        "word": word,
                        "cluster_id": cluster_id,
                        "cluster_index": i + 1,
                        "total_clusters": total_clusters,
                        "definitions_in_cluster": len(cluster_definitions),
                    },
                )

            try:
                # Synthesize definitions for this cluster using full Definition objects
                synthesis_response = await self.ai.synthesize_definitions(
                    word=word,
                    definitions=cluster_definitions,
                    meaning_cluster=cluster_id,
                )

                cluster_duration = time.time() - cluster_start
                logger.debug(
                    f"✅ Cluster '{cluster_id}' synthesized in {cluster_duration:.2f}s "
                    f"(confidence: {synthesis_response.confidence:.2f})"
                )

                if not synthesis_response.definitions:
                    logger.warning(f"⚠️  No definitions synthesized for cluster '{cluster_id}'")
                    continue

                # Create synthesized definitions for this cluster
                for synthesized_def in synthesis_response.definitions:
                    word_type = synthesized_def.word_type

                    # Generate examples using configured count
                    example_response = await self.ai.examples(
                        word=word,
                        word_type=word_type,
                        definition=synthesized_def.definition,
                        count=self.examples_count,
                    )

                    examples = Examples(
                        generated=[
                            GeneratedExample(sentence=sentence)
                            for sentence in example_response.example_sentences
                        ]
                    )

                    # Enhance synonyms if needed
                    enhanced_synonyms = await self._enhance_synonyms(
                        word=word,
                        word_type=word_type,
                        definition=synthesized_def.definition,
                        existing_synonyms=synthesized_def.synonyms,
                    )

                    # Create the final synthesized definition
                    final_def = Definition(
                        word_type=word_type,
                        definition=synthesized_def.definition,
                        synonyms=enhanced_synonyms,
                        examples=examples,
                        meaning_cluster=cluster_id,
                        raw_metadata={
                            "synthesis_confidence": synthesis_response.confidence,
                            "example_confidence": example_response.confidence,
                            "sources_used": synthesis_response.sources_used,
                            "cluster_description": cluster_descriptions.get(cluster_id, ""),
                            "original_definition_count": len(cluster_definitions),
                        },
                    )

                    synthesized_definitions.append(final_def)

            except Exception as e:
                cluster_duration = time.time() - cluster_start
                logger.error(
                    f"❌ Failed to synthesize cluster '{cluster_id}' after {cluster_duration:.2f}s: {e}"
                )
                # TODO: Add metrics logging
                # log_metrics(
                #     stage="cluster_synthesis_error",
                #     cluster_id=cluster_id,
                #     error=str(e),
                #     duration=cluster_duration
                # )
                continue

        logger.success(
            f"✅ Successfully synthesized {len(synthesized_definitions)} definitions for '{word}'"
        )
        return synthesized_definitions

    async def _enhance_synonyms(
        self,
        word: str,
        word_type: str,
        definition: str,
        existing_synonyms: list[str],
    ) -> list[str]:
        """Enhance synonyms by augmenting existing list if needed."""

        # If we already have at least 2 synonyms, don't augment
        if len(existing_synonyms) >= 2:
            return existing_synonyms

        logger.info(f"🔗 Enhancing synonyms for '{word}' ({word_type})")

        try:
            # Generate synonyms using the existing prompt
            synonym_response = await self.ai.synonyms(
                word=word,
                word_type=word_type,
                definition=definition,
                count=10,
            )

            # Extract just the words from the synonym candidates
            generated_synonyms = [
                candidate.word
                for candidate in synonym_response.synonyms
                if candidate.word.lower() != word.lower()
            ]

            # Combine and deduplicate
            all_synonyms = existing_synonyms + generated_synonyms

            # Remove duplicates while preserving order
            unique_synonyms = []
            seen = set()
            for synonym in all_synonyms:
                if synonym.lower() not in seen:
                    unique_synonyms.append(synonym)
                    seen.add(synonym.lower())

            logger.success(
                f"✨ Enhanced synonyms for '{word}': {len(unique_synonyms)} total synonyms"
            )

            return unique_synonyms

        except Exception as e:
            logger.error(f"Failed to enhance synonyms for '{word}': {e}")
            return existing_synonyms

    async def _synthesize_pronunciation(self, word: str) -> Pronunciation:
        """Synthesize pronunciation from providers_data or generate with AI."""
        try:
            pronunciation_response = await self.ai.pronunciation(word)
            return Pronunciation(
                phonetic=pronunciation_response.phonetic,
                ipa=pronunciation_response.ipa,
            )
        except Exception as e:
            logger.error(f"Failed to generate pronunciation for {word}: {e}")
            return Pronunciation(phonetic="", ipa=None)
