"""Enhanced definition synthesizer using new data models and functional pipeline."""

from __future__ import annotations

from ..constants import DictionaryProvider, Language
from ..core.state_tracker import Stages, StateTracker
from ..models import (
    Definition,
    Example,
    MeaningCluster,
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
    synthesize_definition_text,
    synthesize_etymology,
    synthesize_examples,
    generate_facts,
    synthesize_pronunciation,
    synthesize_synonyms,
    synthesize_word_forms,
)

logger = get_logger(__name__)


class DefinitionSynthesizer:
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

    def _calculate_confidence(
        self,
        has_pronunciation: bool,
        definition_count: int,
        has_etymology: bool,
        fact_count: int,
        provider_count: int,
    ) -> float:
        """Calculate confidence score based on completeness of data.
        
        Args:
            has_pronunciation: Whether pronunciation data exists
            definition_count: Number of definitions synthesized
            has_etymology: Whether etymology data exists
            fact_count: Number of facts generated
            provider_count: Number of source providers
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        weights = {
            "pronunciation": 0.15,
            "definitions": 0.35,
            "etymology": 0.15,
            "facts": 0.15,
            "providers": 0.20,
        }
        
        score = 0.0
        score += weights["pronunciation"] if has_pronunciation else 0.0
        score += weights["definitions"] * min(1.0, definition_count / 3.0)
        score += weights["etymology"] if has_etymology else 0.0
        score += weights["facts"] * min(1.0, fact_count / 2.0)
        score += weights["providers"] * min(1.0, provider_count / 2.0)
        
        return round(min(1.0, score), 2)

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
                SynthesizedDictionaryEntry.word_id == str(word_obj.id)
            )
            if existing:
                logger.info(f"Using existing synthesized entry for '{word}'")
                return existing

        # Extract all definitions from providers
        all_definitions = []
        provider_metadata = {}
        
        for provider_data in providers_data:
            provider_metadata[provider_data.provider] = {
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
        
        clustered_definitions = await cluster_definitions(
            word_obj, all_definitions, self.ai, state_tracker
        )

        # Synthesize core components
        if state_tracker:
            await state_tracker.update_stage(Stages.AI_SYNTHESIS, progress=65)

        # Synthesize pronunciation
        pronunciation = await synthesize_pronunciation(
            word_obj, providers_data, self.ai, state_tracker
        )

        # Synthesize etymology
        etymology = await synthesize_etymology(
            word_obj, providers_data, self.ai, state_tracker
        )

        # Synthesize definitions for each cluster
        synthesized_definitions = await self._synthesize_definitions(
            word_obj, clustered_definitions, state_tracker
        )

        # Generate facts
        facts = await generate_facts(
            word_obj, synthesized_definitions, self.ai, self.facts_count
        )

        # Update word forms
        word_forms = await synthesize_word_forms(word_obj, self.ai)
        if word_forms:
            word_obj.word_forms = word_forms
            await word_obj.save()

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
                confidence=self._calculate_confidence(
                    has_pronunciation=bool(pronunciation),
                    definition_count=len(synthesized_definitions),
                    has_etymology=bool(etymology),
                    fact_count=len(facts),
                    provider_count=len(providers_data),
                ),
            ),
            source_provider_data_ids=[str(pd.id) for pd in providers_data],
        )

        # Save entry
        if state_tracker:
            await state_tracker.update_stage(Stages.STORAGE_SAVE, progress=90)

        await entry.save()
        logger.success(f"Created synthesized entry for '{word}' with {len(synthesized_definitions)} definitions")

        # Enhance definitions in parallel if enabled
        if self.parallel_enhancement:
            await enhance_definitions_parallel(
                synthesized_definitions, word_obj, self.ai, state_tracker=state_tracker
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
            logger.info(f"Synthesizing cluster '{cluster_id}' with {len(cluster_defs)} definitions")
            
            # Convert definitions to dict format for synthesis
            def_dicts = [
                {
                    "text": d.text,
                    "part_of_speech": d.part_of_speech,
                    "provider": d.provider_ids[0] if d.provider_ids else "unknown",
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
                meaning_cluster=cluster_defs[0].meaning_cluster,  # Use cluster from source
                synonyms=[],  # Will be generated separately
                antonyms=[],  # Will be generated separately
                example_ids=[],
                frequency_band=None,  # Will be enriched later
            )
            await definition.save()
            
            # Generate synonyms using modular function
            synonyms = await synthesize_synonyms(
                definition=definition,
                word=word.text,
                ai=self.ai,
                state_tracker=state_tracker,
            )
            definition.synonyms = synonyms
            
            # Generate examples using modular function
            examples = await synthesize_examples(
                definition=definition,
                word=word.text,
                ai=self.ai,
                state_tracker=state_tracker,
            )
            
            # Create and save example objects
            for example_text in examples:
                example = Example(
                    definition_id=str(definition.id),
                    text=example_text,
                    type="generated",
                    model_info=ModelInfo(
                        name=self.ai.model_name,
                        generation_count=1,
                        confidence=0.85,  # Default confidence
                    ),
                )
                await example.save()
                definition.example_ids.append(str(example.id))
            
            # Update definition with synonyms and example IDs
            await definition.save()
            synthesized_definitions.append(definition)

        return synthesized_definitions

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
        for idx, ai_def in enumerate(dictionary_entry.provider_data.definitions):
            # Create a simple meaning cluster for AI-generated definitions
            meaning_cluster = MeaningCluster(
                id=f"ai_{ai_def.word_type}_{idx}",
                name=f"{ai_def.word_type.title()} (AI)",
                description=f"AI-generated {ai_def.word_type} definition",
                order=idx,
                relevance=ai_def.relevancy,
            )
            
            # Create definition
            definition = Definition(
                word_id=str(word_obj.id),
                part_of_speech=ai_def.word_type,
                text=ai_def.definition,
                meaning_cluster=meaning_cluster,
                synonyms=[],  # Will be generated separately
                antonyms=[],  # Will be enhanced later
                example_ids=[],
                frequency_band=None,  # Will be enriched later
            )
            await definition.save()
            
            # Generate synonyms using modular function
            synonyms = await synthesize_synonyms(
                definition=definition,
                word=word,
                ai=self.ai,
                state_tracker=state_tracker,
            )
            definition.synonyms = synonyms
            
            # Generate examples using modular function
            examples = await synthesize_examples(
                definition=definition,
                word=word,
                ai=self.ai,
                state_tracker=state_tracker,
            )
            
            # Create and save example objects
            for example_text in examples:
                example = Example(
                    definition_id=str(definition.id),
                    text=example_text,
                    type="generated",
                    model_info=ModelInfo(
                        name=self.ai.model_name,
                        generation_count=1,
                        confidence=0.85,  # Default confidence
                    ),
                )
                await example.save()
                definition.example_ids.append(str(example.id))

            await definition.save()
            definitions.append(definition)

        # Create provider data
        provider_data = ProviderData(
            word_id=str(word_obj.id),
            provider=DictionaryProvider.AI_FALLBACK,
            definition_ids=[str(d.id) for d in definitions],
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


