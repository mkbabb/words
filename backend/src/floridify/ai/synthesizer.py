"""Enhanced definition synthesizer using new data models and functional pipeline."""

from __future__ import annotations

import asyncio
from typing import Any

from ..constants import DictionaryProvider, Language
from ..core.state_tracker import Stages, StateTracker
from ..models import (
    Definition,
    Etymology,
    Example,
    MeaningCluster,
    ModelInfo,
    Pronunciation,
    ProviderData,
    SynthesizedDictionaryEntry,
    Word,
)
from ..storage.mongodb import get_storage
from ..utils.logging import get_logger
from .connector import OpenAIConnector
from .synthesis_functions import (
    assess_definition_cefr,
    assess_definition_frequency,
    classify_definition_register,
    detect_regional_variants,
    enhance_definition_antonyms,
    extract_grammar_patterns,
    generate_usage_notes,
    identify_collocations,
    identify_definition_domain,
    synthesize_facts,
    synthesize_word_forms,
)

logger = get_logger(__name__)


class EnhancedDefinitionSynthesizer:
    """Synthesizes dictionary entries using new models and parallel processing."""

    def __init__(
        self,
        openai_connector: OpenAIConnector,
        examples_count: int = 2,
        facts_count: int = 3,
        parallel_enhancement: bool = True,
    ) -> None:
        self.ai = openai_connector
        self.examples_count = examples_count
        self.facts_count = facts_count
        self.parallel_enhancement = parallel_enhancement

    async def synthesize_entry(
        self,
        word: str,
        providers_data: list[ProviderData],
        force_refresh: bool = False,
        state_tracker: StateTracker | None = None,
    ) -> SynthesizedDictionaryEntry | None:
        """Synthesize a complete dictionary entry from provider data."""
        
        # Get or create Word document
        storage = await get_storage()
        word_obj = await storage.get_word(word)
        if not word_obj:
            word_obj = Word(
                text=word,
                normalized=word.lower(),
                language=Language.ENGLISH,
            )
            await word_obj.save()

        # Check for existing synthesized entry
        if not force_refresh:
            existing = await SynthesizedDictionaryEntry.find_one(
                SynthesizedDictionaryEntry.word_id == word_obj.id
            )
            if existing:
                logger.info(f"Using existing synthesized entry for '{word}'")
                return existing

        # Extract all definitions from providers
        all_definitions = []
        provider_metadata = {}
        
        for provider_data in providers_data:
            provider_metadata[provider_data.provider.value] = {
                "definition_count": len(provider_data.definition_ids),
                "has_pronunciation": provider_data.pronunciation_id is not None,
                "has_etymology": provider_data.etymology is not None,
            }
            
            # Load definitions
            for def_id in provider_data.definition_ids:
                definition = await Definition.get(def_id)
                if definition:
                    all_definitions.append(definition)

        if not all_definitions:
            logger.warning(f"No definitions found for '{word}'")
            return None

        # Cluster definitions
        if state_tracker:
            await state_tracker.update_stage(Stages.AI_CLUSTERING)
        
        clustered_definitions = await self._cluster_definitions(
            word_obj, all_definitions, state_tracker
        )

        # Synthesize core components
        if state_tracker:
            await state_tracker.update_stage(Stages.AI_SYNTHESIS, progress=65)

        # Synthesize pronunciation
        pronunciation = await self._synthesize_pronunciation(
            word_obj, providers_data
        )

        # Synthesize etymology
        etymology = await self._synthesize_etymology(
            word_obj, providers_data
        )

        # Synthesize definitions for each cluster
        synthesized_definitions = await self._synthesize_definitions(
            word_obj, clustered_definitions, state_tracker
        )

        # Generate facts
        facts = await synthesize_facts(
            word_obj, synthesized_definitions, self.ai, self.facts_count
        )

        # Update word forms
        word_forms = await synthesize_word_forms(word_obj, self.ai)
        if word_forms:
            word_obj.word_forms = word_forms
            await word_obj.save()

        # Create synthesized entry
        entry = SynthesizedDictionaryEntry(
            word_id=word_obj.id,
            pronunciation_id=pronunciation.id if pronunciation else None,
            definition_ids=[d.id for d in synthesized_definitions],
            etymology=etymology,
            fact_ids=[f.id for f in facts],
            model_info=ModelInfo(
                name=self.ai.model_name,
                generation_count=1,
                confidence=0.9,  # TODO: Calculate from component confidences
            ),
            source_provider_data_ids=[pd.id for pd in providers_data],
        )

        # Save entry
        if state_tracker:
            await state_tracker.update_stage(Stages.STORAGE_SAVE, progress=90)

        await entry.save()
        logger.success(f"Created synthesized entry for '{word}' with {len(synthesized_definitions)} definitions")

        # Enhance definitions in parallel if enabled
        if self.parallel_enhancement:
            await self._parallel_enhance_definitions(
                synthesized_definitions, word_obj, state_tracker
            )

        return entry

    async def _cluster_definitions(
        self,
        word: Word,
        definitions: list[Definition],
        state_tracker: StateTracker | None = None,
    ) -> list[Definition]:
        """Cluster definitions by meaning using AI."""
        
        # Prepare definition tuples for clustering
        definition_tuples = []
        for definition in definitions:
            # Get provider name from provider data
            provider_name = "unknown"
            if definition.provider_data_id:
                provider_data = await ProviderData.get(definition.provider_data_id)
                if provider_data:
                    provider_name = provider_data.provider.value
            
            definition_tuples.append((
                provider_name,
                definition.part_of_speech,
                definition.text,
            ))

        # Extract cluster mappings
        cluster_response = await self.ai.extract_cluster_mapping(
            word.text, definition_tuples
        )

        # Apply cluster assignments
        for cluster_mapping in cluster_response.cluster_mappings:
            cluster = MeaningCluster(
                id=cluster_mapping.cluster_id,
                name=cluster_mapping.cluster_description,
                description=cluster_mapping.cluster_description,
                order=cluster_mapping.relevancy,
                relevance=cluster_mapping.relevancy,
            )
            
            for idx in cluster_mapping.definition_indices:
                if 0 <= idx < len(definitions):
                    definitions[idx].meaning_cluster = cluster

        return definitions

    async def _synthesize_pronunciation(
        self,
        word: Word,
        providers_data: list[ProviderData],
    ) -> Pronunciation | None:
        """Synthesize pronunciation from providers or generate."""
        
        # Check providers for pronunciation
        for provider_data in providers_data:
            if provider_data.pronunciation_id:
                pronunciation = await Pronunciation.get(provider_data.pronunciation_id)
                if pronunciation:
                    return pronunciation

        # Generate if not found
        try:
            response = await self.ai.pronunciation(word.text)
            pronunciation = Pronunciation(
                word_id=word.id,
                phonetic=response.phonetic,
                ipa_american=response.ipa,
                syllables=[],
                stress_pattern=None,
            )
            await pronunciation.save()
            return pronunciation
        except Exception as e:
            logger.error(f"Failed to generate pronunciation for {word.text}: {e}")
            return None

    async def _synthesize_etymology(
        self,
        word: Word,
        providers_data: list[ProviderData],
    ) -> Etymology | None:
        """Synthesize etymology from providers."""
        
        # Collect etymology data
        etymology_data = []
        for provider_data in providers_data:
            if provider_data.etymology:
                etymology_data.append({
                    "name": provider_data.provider.value,
                    "etymology_text": provider_data.etymology.text,
                })

        if not etymology_data:
            return None

        try:
            response = await self.ai.extract_etymology(word.text, etymology_data)
            return Etymology(
                text=response.text,
                origin_language=response.origin_language,
                root_words=response.root_words,
                first_known_use=response.first_known_use,
            )
        except Exception as e:
            logger.error(f"Failed to synthesize etymology for {word.text}: {e}")
            return None

    async def _synthesize_definitions(
        self,
        word: Word,
        clustered_definitions: list[Definition],
        state_tracker: StateTracker | None = None,
    ) -> list[Definition]:
        """Synthesize definitions by cluster."""
        
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
            logger.info(f"Synthesizing cluster '{cluster_id}' with {len(cluster_defs)} definitions")
            
            # Synthesize using AI
            synthesis_response = await self.ai.synthesize_definitions(
                word=word.text,
                definitions=cluster_defs,
                meaning_cluster=cluster_id,
            )

            # Create new definitions from synthesis
            for synth_def in synthesis_response.definitions:
                # Generate examples
                example_response = await self.ai.examples(
                    word=word.text,
                    word_type=synth_def.word_type,
                    definition=synth_def.definition,
                    count=self.examples_count,
                )

                # Create definition
                definition = Definition(
                    word_id=word.id,
                    part_of_speech=synth_def.word_type,
                    text=synth_def.definition,
                    meaning_cluster=cluster_defs[0].meaning_cluster,  # Use cluster from source
                    synonyms=synth_def.synonyms[:10],  # Limit synonyms
                    antonyms=[],
                    example_ids=[],
                )
                await definition.save()

                # Create and save examples
                for example_text in example_response.example_sentences:
                    example = Example(
                        definition_id=definition.id,
                        text=example_text,
                        type="generated",
                        model_info=ModelInfo(
                            name=self.ai.model_name,
                            generation_count=1,
                            confidence=example_response.confidence,
                        ),
                    )
                    await example.save()
                    definition.example_ids.append(example.id)

                # Update definition with example IDs
                await definition.save()
                synthesized_definitions.append(definition)

        return synthesized_definitions

    async def _parallel_enhance_definitions(
        self,
        definitions: list[Definition],
        word: Word,
        state_tracker: StateTracker | None = None,
    ) -> None:
        """Enhance definitions with additional fields in parallel."""
        
        logger.info(f"Enhancing {len(definitions)} definitions in parallel")
        
        tasks = []
        for definition in definitions:
            # Antonyms
            tasks.append(self._enhance_field(
                definition, "antonyms",
                enhance_definition_antonyms(definition, word.text, self.ai)
            ))
            
            # CEFR level
            tasks.append(self._enhance_field(
                definition, "cefr_level",
                assess_definition_cefr(definition, word.text, self.ai)
            ))
            
            # Frequency band
            tasks.append(self._enhance_field(
                definition, "frequency_band",
                assess_definition_frequency(definition, word.text, self.ai)
            ))
            
            # Register
            tasks.append(self._enhance_field(
                definition, "register",
                classify_definition_register(definition, self.ai)
            ))
            
            # Domain
            tasks.append(self._enhance_field(
                definition, "domain",
                identify_definition_domain(definition, self.ai)
            ))
            
            # Grammar patterns
            tasks.append(self._enhance_field(
                definition, "grammar_patterns",
                extract_grammar_patterns(definition, self.ai)
            ))
            
            # Collocations
            tasks.append(self._enhance_field(
                definition, "collocations",
                identify_collocations(definition, word.text, self.ai)
            ))
            
            # Usage notes
            tasks.append(self._enhance_field(
                definition, "usage_notes",
                generate_usage_notes(definition, word.text, self.ai)
            ))
            
            # Regional variants
            tasks.append(self._enhance_field(
                definition, "region",
                detect_regional_variants(definition, self.ai)
            ))

        # Execute all enhancements in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and failures
        successes = sum(1 for r in results if r and not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))
        
        logger.info(f"Definition enhancement complete: {successes} successes, {failures} failures")
        
        if state_tracker:
            await state_tracker.update_stage(Stages.AI_SYNTHESIS, progress=95)

    async def _enhance_field(
        self,
        definition: Definition,
        field_name: str,
        enhancement_coro: Any,
    ) -> bool:
        """Enhance a single field of a definition."""
        try:
            result = await enhancement_coro
            if result is not None:
                setattr(definition, field_name, result)
                await definition.save()
                return True
        except Exception as e:
            logger.error(f"Failed to enhance {field_name}: {e}")
        return False

    async def generate_fallback_entry(
        self,
        word: str,
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
                language=Language.ENGLISH,
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
        definitions = []
        for ai_def in dictionary_entry.provider_data.definitions:
            # Generate examples
            example_response = await self.ai.examples(
                word=word,
                word_type=ai_def.word_type,
                definition=ai_def.definition,
                count=self.examples_count,
            )

            # Create definition
            definition = Definition(
                word_id=word_obj.id,
                part_of_speech=ai_def.word_type,
                text=ai_def.definition,
                meaning_cluster=MeaningCluster(
                    id=f"ai_{ai_def.word_type}",
                    name=f"{ai_def.word_type.title()} (AI)",
                    description=ai_def.definition[:100],
                    order=0,
                    relevance=ai_def.relevancy,
                ),
                synonyms=ai_def.synonyms,
                antonyms=[],
                example_ids=[],
            )
            await definition.save()

            # Create examples
            for example_text in example_response.example_sentences:
                example = Example(
                    definition_id=definition.id,
                    text=example_text,
                    type="generated",
                    model_info=ModelInfo(
                        name=self.ai.model_name,
                        generation_count=1,
                        confidence=example_response.confidence,
                    ),
                )
                await example.save()
                definition.example_ids.append(example.id)

            await definition.save()
            definitions.append(definition)

        # Create provider data
        provider_data = ProviderData(
            word_id=word_obj.id,
            provider=DictionaryProvider.AI_FALLBACK,
            definition_ids=[d.id for d in definitions],
            pronunciation_id=None,
            etymology=None,
            raw_data={
                "synthesis_confidence": dictionary_entry.confidence,
                "model_name": self.ai.model_name,
            },
        )
        await provider_data.save()

        # Synthesize complete entry
        return await self.synthesize_entry(
            word=word,
            providers_data=[provider_data],
            force_refresh=force_refresh,
            state_tracker=state_tracker,
        )


# Alias for backward compatibility
DefinitionSynthesizer = EnhancedDefinitionSynthesizer