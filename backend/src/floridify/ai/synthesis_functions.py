"""Functional synthesis components for AI pipeline."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from ..core.state_tracker import StateTracker

from ..audio import AudioSynthesizer
from ..core.state_tracker import Stages
from ..models import (
    Collocation,
    Definition,
    Etymology,
    Example,
    Fact,
    GrammarPattern,
    MeaningCluster,
    ModelInfo,
    Pronunciation,
    ProviderData,
    SynthesizedDictionaryEntry,
    UsageNote,
    Word,
    WordForm,
)
from ..utils.logging import get_logger
from .connector import OpenAIConnector
from .constants import (
    DEFAULT_ANTONYM_COUNT,
    DEFAULT_EXAMPLE_COUNT,
    DEFAULT_SYNONYM_COUNT,
    SynthesisComponent,
)
from .models import QueryValidationResponse, WordSuggestionResponse

logger = get_logger(__name__)

# Type alias for synthesis functions
SynthesisFunc = Callable[..., Any]


async def synthesize_pronunciation(
    word: str,
    providers_data: list[dict[str, Any]] | list[ProviderData],
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> Pronunciation | None:
    """Synthesize pronunciation: enhance existing or create new."""

    # Find existing pronunciation
    existing_pronunciation = await _find_existing_pronunciation(providers_data)

    if existing_pronunciation:
        return await _enhance_pronunciation(
            existing_pronunciation, word, ai, state_tracker
        )
    else:
        return await _create_pronunciation(word, ai, state_tracker)


async def _find_existing_pronunciation(
    providers_data: list[dict[str, Any]] | list[ProviderData],
) -> Pronunciation | None:
    """Find existing pronunciation from provider data."""
    for provider in providers_data:
        if isinstance(provider, ProviderData):
            if provider.pronunciation_id:
                pronunciation = await Pronunciation.get(provider.pronunciation_id)
                if pronunciation:
                    return pronunciation
        else:
            if provider.get("pronunciation"):
                return cast(Pronunciation, provider["pronunciation"])
    return None


async def _enhance_pronunciation(
    pronunciation: Pronunciation,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None,
) -> Pronunciation:
    """Enhance existing pronunciation with missing data."""
    needs_enhancement = not pronunciation.phonetic or not pronunciation.ipa

    if needs_enhancement:
        try:
            if state_tracker:
                await state_tracker.update(
                    stage=Stages.AI_SYNTHESIS,
                    message=f"Enhancing pronunciation for {word}",
                )

            response = await ai.pronunciation(word)
            pronunciation.phonetic = response.phonetic
            pronunciation.ipa = response.ipa
            await pronunciation.save()

        except Exception as e:
            logger.error(f"Failed to enhance pronunciation for {word}: {e}")

    # Generate audio if missing
    if not pronunciation.audio_file_ids:
        await _generate_audio_files(pronunciation, word)

    return pronunciation


async def _create_pronunciation(
    word: str, ai: OpenAIConnector, state_tracker: StateTracker | None
) -> Pronunciation | None:
    """Create new pronunciation from scratch."""
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Generating pronunciation for {word}",
            )

        response = await ai.pronunciation(word)

        # Create Word object if we need word_id (assuming word parameter should be Word object)
        word_obj = await Word.find_one(Word.text == word)
        if not word_obj:
            word_obj = Word(text=word, normalized=word.lower())
            await word_obj.save()

        pronunciation = Pronunciation(
            word_id=str(word_obj.id),
            phonetic=response.phonetic,
            ipa=response.ipa,
        )
        await pronunciation.save()

        # Generate audio files
        await _generate_audio_files(pronunciation, word)

        return pronunciation

    except Exception as e:
        logger.error(f"Failed to create pronunciation for {word}: {e}")
        return None


async def _generate_audio_files(pronunciation: Pronunciation, word: str) -> None:
    """Generate audio files for pronunciation."""
    try:
        audio_synthesizer = AudioSynthesizer()
        audio_files = await audio_synthesizer.synthesize_pronunciation(
            pronunciation, word
        )

        if audio_files:
            pronunciation.audio_file_ids = [str(audio.id) for audio in audio_files]
            await pronunciation.save()
            logger.info(f"Generated {len(audio_files)} audio files for {word}")

    except Exception as audio_error:
        logger.warning(f"Failed to generate audio for {word}: {audio_error}")


async def synthesize_etymology(
    word: Word,
    providers_data: list[dict[str, Any]] | list[ProviderData],
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> Etymology | None:
    """Extract and synthesize etymology from provider data."""

    # Collect etymology data from providers
    etymology_data = []

    for provider in providers_data:
        if isinstance(provider, ProviderData):
            # ProviderData format
            if provider.etymology:
                etymology_data.append(
                    {
                        "name": provider.provider.value,
                        "etymology_text": provider.etymology.text,
                    }
                )
        else:
            # Dict format
            if provider.get("etymology"):
                etymology_data.append(
                    {
                        "name": provider["name"],
                        "etymology_text": provider["etymology"],
                    }
                )

    if not etymology_data:
        return None

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Extracting etymology for {word.text}",
            )
        response = await ai.extract_etymology(word.text, etymology_data)
        return Etymology(
            text=response.text,
            origin_language=response.origin_language,
            root_words=response.root_words,
            first_known_use=response.first_known_use,
        )
    except Exception as e:
        logger.error(f"Failed to synthesize etymology for {word.text}: {e}")
        return None


async def synthesize_word_forms(
    word: Word,
    part_of_speech: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[WordForm]:
    """Generate word forms for a word."""

    # Determine primary part of speech from definitions
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Generating word forms for {word.text}",
            )
        response = await ai.identify_word_forms(word.text, part_of_speech)
        return [
            WordForm(
                form_type=form.type,  # type:ignore
                text=form.text,
            )
            for form in response.forms
        ]
    except Exception as e:
        logger.error(f"Failed to synthesize word forms for {word.text}: {e}")
        return []


async def synthesize_antonyms(
    word: str,
    definition: Definition,
    ai: OpenAIConnector,
    count: int = 5,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
) -> list[str]:
    """Synthesize antonyms: enhance existing or generate new to reach target count."""
    count = count or DEFAULT_ANTONYM_COUNT
    
    # Get existing antonyms (empty if force_refresh)
    existing_antonyms = [] if force_refresh else (definition.antonyms or [])
    
    # If we already have enough antonyms, return them
    if len(existing_antonyms) >= count:
        return existing_antonyms[:count]
    
    # Calculate how many new antonyms we need
    needed_count = count - len(existing_antonyms)
    
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, 
                message=f"Synthesizing {needed_count} new antonyms for {word} (total: {count})"
            )
        
        response = await ai.synthesize_antonyms(
            word=word,
            definition=definition.text,
            part_of_speech=definition.part_of_speech,
            existing_antonyms=existing_antonyms,
            count=needed_count,
        )
        
        # Union existing and new antonyms, removing duplicates
        all_antonyms = existing_antonyms.copy()
        for antonym in response.antonyms:
            if antonym not in all_antonyms:
                all_antonyms.append(antonym)
        
        return all_antonyms[:count]
        
    except Exception as e:
        logger.error(f"Failed to synthesize antonyms: {e}")
        return existing_antonyms


async def assess_definition_cefr(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> str | None:
    """Assess CEFR level for a definition."""

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message=f"Assessing CEFR level for {word}"
            )
        response = await ai.assess_cefr_level(word, definition.text)
        return response.level
    except Exception as e:
        logger.error(f"Failed to assess CEFR level: {e}")
        return None


async def assess_definition_frequency(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> int | None:
    """Assess frequency band for a definition."""

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Assessing frequency band for {word}",
            )
        response = await ai.assess_frequency_band(word, definition.text)
        return response.band
    except Exception as e:
        logger.error(f"Failed to assess frequency band: {e}")
        return None


async def classify_definition_register(
    definition: Definition,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> str | None:
    """Classify register for a definition."""

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message="Classifying register for definition"
            )
        response = await ai.classify_register(definition.text)
        return response.language_register
    except Exception as e:
        logger.error(f"Failed to classify register: {e}")
        return None


async def assess_definition_domain(
    definition: Definition,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> str | None:
    """Identify domain for a definition."""

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message="Identifying domain for definition"
            )
        response = await ai.assess_domain(definition.text)
        return response.domain
    except Exception as e:
        logger.error(f"Failed to identify domain: {e}")
        return None


async def assess_grammar_patterns(
    definition: Definition,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[GrammarPattern]:
    """Extract grammar patterns for a definition."""

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message="Extracting grammar patterns"
            )
        response = await ai.assess_grammar_patterns(
            definition.text,
            definition.part_of_speech,
        )
        return [
            GrammarPattern(
                pattern=pattern,
                description=desc,
            )
            for pattern, desc in zip(response.patterns, response.descriptions)
        ]
    except Exception as e:
        logger.error(f"Failed to extract grammar patterns: {e}")
        return []


async def assess_collocations(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[Collocation]:
    """Identify collocations for a definition."""

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Identifying collocations for {word}",
            )
        response = await ai.assess_collocations(
            word=word,
            definition=definition.text,
            part_of_speech=definition.part_of_speech,
        )
        return [
            Collocation(
                text=coll.phrase,
                type=coll.type,
                frequency=coll.frequency,
            )
            for coll in response.collocations
        ]
    except Exception as e:
        logger.error(f"Failed to identify collocations: {e}")
        return []


async def usage_note_generation(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[UsageNote]:
    """Generate usage notes for a definition."""

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message=f"Generating usage notes for {word}"
            )
        response = await ai.usage_note_generation(word, definition.text)
        return [
            UsageNote(
                type=note.type,  # type: ignore
                text=note.text,
            )
            for note in response.notes
        ]
    except Exception as e:
        logger.error(f"Failed to generate usage notes: {e}")
        return []


async def assess_regional_variants(
    definition: Definition,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[str]:
    """Detect regional variants for a definition."""

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message="Detecting regional variants"
            )
        response = await ai.assess_regional_variants(definition.text)
        return response.regions
    except Exception as e:
        logger.error(f"Failed to detect regional variants: {e}")
        return []


async def generate_facts(
    word: Word,
    definitions: list[Definition],
    ai: OpenAIConnector,
    count: int = 3,
    state_tracker: StateTracker | None = None,
) -> list[Fact]:
    """Generate interesting facts about a word."""

    # Use primary definition for context
    primary_def = definitions[0].text if definitions else ""

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message=f"Generating facts for {word.text}"
            )
        response = await ai.generate_facts(
            word=word.text,
            definition=primary_def,
            count=count,
        )

        facts = []
        for idx, fact_text in enumerate(response.facts):
            # Determine category from response
            category = (
                response.categories[idx]
                if idx < len(response.categories)
                else "general"
            )

            # Ensure category is valid - map to allowed Fact categories
            category_mapping = {
                "general": "usage",
                "technical": "linguistic",
                "scientific": "linguistic",
                "cultural": "cultural",
                "etymology": "etymology",
                "historical": "historical",
                "usage": "usage",
                "linguistic": "linguistic",
            }
            category = category_mapping.get(category.lower(), "usage")

            fact = Fact(
                word_id=str(word.id),
                content=fact_text,
                category=category,  # type: ignore[arg-type]
                model_info=ModelInfo(
                    name=ai.model_name,
                    confidence=response.confidence,
                    generation_count=1,
                ),
            )
            await fact.save()
            facts.append(fact)

        return facts
    except Exception as e:
        logger.error(f"Failed to synthesize facts for {word.text}: {e}")
        return []


async def synthesize_synonyms(
    word: str,
    definition: Definition,
    ai: OpenAIConnector,
    count: int = 10,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
) -> list[str]:
    """Synthesize synonyms: enhance existing or generate new to reach target count."""
    count = count or DEFAULT_SYNONYM_COUNT
    
    # Get existing synonyms (empty if force_refresh)
    existing_synonyms = [] if force_refresh else (definition.synonyms or [])
    
    # If we already have enough synonyms, return them
    if len(existing_synonyms) >= count:
        return existing_synonyms[:count]
    
    # Calculate how many new synonyms we need
    needed_count = count - len(existing_synonyms)
    
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, 
                message=f"Synthesizing {needed_count} new synonyms for {word} (total: {count})"
            )

        response = await ai.synthesize_synonyms(
            word=word,
            definition=definition.text,
            part_of_speech=definition.part_of_speech,
            existing_synonyms=existing_synonyms,
            count=needed_count,
        )

        # Union existing and new synonyms, removing duplicates
        all_synonyms = existing_synonyms.copy()
        for candidate in response.synonyms:
            if candidate.word not in all_synonyms:
                all_synonyms.append(candidate.word)
        
        logger.info(f"Synthesized {len(all_synonyms)} total synonyms for '{word}'")
        return all_synonyms[:count]

    except Exception as e:
        logger.error(f"Failed to synthesize synonyms: {e}")
        if state_tracker:
            await state_tracker.update_error(f"Synonym synthesis failed: {str(e)}")
        return existing_synonyms


async def generate_examples(
    word: str,
    definition: Definition,
    ai: OpenAIConnector,
    count: int = 3,
    state_tracker: StateTracker | None = None,
) -> list[str]:
    """Generate contextual example sentences for a definition."""
    count = count or DEFAULT_EXAMPLE_COUNT

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Generating {count} examples for {word}",
            )

        response = await ai.generate_examples(
            word=word,
            part_of_speech=definition.part_of_speech,
            definition=definition.text,
            count=count,
        )

        examples = response.example_sentences
        logger.info(f"Generated {len(examples)} examples for '{word}'")
        return examples

    except Exception as e:
        logger.error(f"Failed to generate examples: {e}")
        if state_tracker:
            await state_tracker.update_error(f"Example generation failed: {str(e)}")
        return []


async def synthesize_definition_text(
    clustered_definitions: list[dict[str, Any]],
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> dict[str, Any]:
    """Synthesize definition text from clustered meanings."""
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message=f"Synthesizing definition for {word}"
            )

        # Convert dict definitions to Definition objects for the AI method
        definition_objects = []
        for d in clustered_definitions:
            # Create a minimal Definition object for the synthesis
            def_obj = Definition(
                word_id="temp",
                part_of_speech=d.get("part_of_speech", "unknown"),
                text=d["text"],
                frequency_band=None,
            )
            definition_objects.append(def_obj)

        # Use the existing synthesize_definitions method which uses templates
        response = await ai.synthesize_definitions(
            word=word,
            definitions=definition_objects,
            meaning_cluster=None,  # Will synthesize across all
        )

        # Extract the first synthesized definition
        if response.definitions:
            synth_def = response.definitions[0]
            return {
                "definition_text": synth_def.definition,
                "part_of_speech": synth_def.part_of_speech,
                "sources_used": [
                    d.get("provider", "unknown") for d in clustered_definitions
                ],
            }
        else:
            return {
                "definition_text": "",
                "part_of_speech": "",
                "sources_used": [],
            }

    except Exception as e:
        logger.error(f"Failed to synthesize definition: {e}")
        if state_tracker:
            await state_tracker.update_error(f"Definition synthesis failed: {str(e)}")
        return {
            "definition_text": "",
            "part_of_speech": "",
            "sources_used": [],
        }


async def cluster_definitions(
    word: Word,
    definitions: list[Definition],
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[Definition]:
    """Cluster definitions by meaning using AI.

    Args:
        word: Word object being processed
        definitions: List of definitions to cluster
        ai: OpenAI connector instance
        state_tracker: Optional state tracker for progress updates

    Returns:
        The same list of definitions with meaning_cluster attributes set
    """
    if not definitions:
        return definitions

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Clustering {len(definitions)} definitions for '{word.text}'",
            )

        # Prepare definition tuples for clustering
        definition_tuples = []
        for definition in definitions:
            # Get provider name from provider data
            provider_name = "unknown"
            if definition.provider_data_id:
                provider_data = await ProviderData.get(definition.provider_data_id)
                if provider_data:
                    provider_name = provider_data.provider.value

            definition_tuples.append(
                (
                    provider_name,
                    definition.part_of_speech,
                    definition.text,
                )
            )

        # Extract cluster mappings
        cluster_response = await ai.extract_cluster_mapping(
            word.text, definition_tuples
        )

        # Apply cluster assignments
        for cluster_mapping in cluster_response.cluster_mappings:
            # Extract short name from cluster_id (e.g., "bank_finance" -> "finance")
            cluster_name = cluster_mapping.cluster_id.split('_')[-1].title() if '_' in cluster_mapping.cluster_id else cluster_mapping.cluster_id
            
            cluster = MeaningCluster(
                id=cluster_mapping.cluster_id,
                name=cluster_name,  # Short name extracted from ID
                description=cluster_mapping.cluster_description,
                order=int(cluster_mapping.relevancy),
                relevance=cluster_mapping.relevancy,
            )

            for idx in cluster_mapping.definition_indices:
                if 0 <= idx < len(definitions):
                    definitions[idx].meaning_cluster = cluster

        # Log results
        clustered_count = sum(1 for d in definitions if d.meaning_cluster)
        logger.info(
            f"Clustered {clustered_count}/{len(definitions)} definitions "
            f"into {len(cluster_response.cluster_mappings)} clusters"
        )

        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Clustered definitions into {len(cluster_response.cluster_mappings)} meaning groups",
            )

        return definitions

    except Exception as e:
        logger.error(f"Failed to cluster definitions for '{word.text}': {e}")
        if state_tracker:
            await state_tracker.update_error(f"Definition clustering failed: {str(e)}")
        # Return definitions unchanged on error
        return definitions


# Component registry for easy access
SYNTHESIS_COMPONENTS = {
    # Word-level components
    "pronunciation": synthesize_pronunciation,
    "etymology": synthesize_etymology,
    "word_forms": synthesize_word_forms,
    "facts": generate_facts,
    # Definition-level components
    "synonyms": synthesize_synonyms,
    "examples": generate_examples,
    "antonyms": synthesize_antonyms,
    "cefr_level": assess_definition_cefr,
    "frequency_band": assess_definition_frequency,
    "register": classify_definition_register,
    "domain": assess_definition_domain,
    "grammar_patterns": assess_grammar_patterns,
    "collocations": assess_collocations,
    "usage_notes": usage_note_generation,
    "regional_variants": assess_regional_variants,
    # Synthesis utilities
    "definition_text": synthesize_definition_text,
    "cluster_definitions": cluster_definitions,
}


async def enhance_definitions_parallel(
    definitions: list[Definition],
    word: Word,
    ai: OpenAIConnector,
    components: set[str] | None = None,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
) -> None:
    """Enhance definitions with specified components in parallel.

    Args:
        definitions: List of definitions to enhance
        word: The word object
        ai: OpenAI connector instance
        components: Set of components to enhance (None = all definition-level)
        force_refresh: Force regeneration even if data exists
        state_tracker: Optional state tracker
        batch_mode: Use batch processing for AI calls
    """
    # Default to all definition-level components
    if components is None:
        components = SynthesisComponent.default_components()

    # Build tasks for each definition and component
    tasks: list[Coroutine[Any, Any, Any]] = []
    task_info: list[tuple[Definition, str, int]] = []

    for definition in definitions:
        # Synonyms
        if SynthesisComponent.SYNONYMS.value in components and (not definition.synonyms or force_refresh):
            tasks.append(
                synthesize_synonyms(
                    word.text, definition, ai, force_refresh=force_refresh, state_tracker=state_tracker
                )
            )
            task_info.append((definition, SynthesisComponent.SYNONYMS.value, len(tasks) - 1))

        # Examples
        if SynthesisComponent.EXAMPLES.value in components and (not definition.example_ids or force_refresh):
            tasks.append(
                generate_examples(
                    word.text, definition, ai, state_tracker=state_tracker
                )
            )
            task_info.append((definition, SynthesisComponent.EXAMPLES.value, len(tasks) - 1))

        # Antonyms
        if SynthesisComponent.ANTONYMS.value in components and (not definition.antonyms or force_refresh):
            tasks.append(
                synthesize_antonyms(
                    word.text, definition, ai, force_refresh=force_refresh, state_tracker=state_tracker
                )
            )
            task_info.append((definition, SynthesisComponent.ANTONYMS.value, len(tasks) - 1))

        # Word forms
        if SynthesisComponent.WORD_FORMS.value in components and (not definition.word_forms or force_refresh):
            # Use the part of speech from the definition
            tasks.append(
                synthesize_word_forms(
                    word, definition.part_of_speech, ai, state_tracker
                )
            )
            task_info.append((definition, SynthesisComponent.WORD_FORMS.value, len(tasks) - 1))

        # CEFR Level
        if SynthesisComponent.CEFR_LEVEL.value in components and (
            definition.cefr_level is None or force_refresh
        ):
            tasks.append(
                assess_definition_cefr(definition, word.text, ai, state_tracker)
            )
            task_info.append((definition, SynthesisComponent.CEFR_LEVEL.value, len(tasks) - 1))

        # Frequency Band
        if SynthesisComponent.FREQUENCY_BAND.value in components and (
            definition.frequency_band is None or force_refresh
        ):
            tasks.append(
                assess_definition_frequency(definition, word.text, ai, state_tracker)
            )
            task_info.append((definition, SynthesisComponent.FREQUENCY_BAND.value, len(tasks) - 1))

        # Register
        if SynthesisComponent.REGISTER.value in components and (
            not definition.language_register or force_refresh
        ):
            tasks.append(classify_definition_register(definition, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.REGISTER.value, len(tasks) - 1))

        # Domain
        if SynthesisComponent.DOMAIN.value in components and (not definition.domain or force_refresh):
            tasks.append(assess_definition_domain(definition, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.DOMAIN.value, len(tasks) - 1))

        # Grammar Patterns
        if SynthesisComponent.GRAMMAR_PATTERNS.value in components and (
            not definition.grammar_patterns or force_refresh
        ):
            tasks.append(assess_grammar_patterns(definition, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.GRAMMAR_PATTERNS.value, len(tasks) - 1))

        # Collocations
        if SynthesisComponent.COLLOCATIONS.value in components and (
            not definition.collocations or force_refresh
        ):
            tasks.append(
                assess_collocations(definition, word.text, ai, state_tracker)
            )
            task_info.append((definition, SynthesisComponent.COLLOCATIONS.value, len(tasks) - 1))

        # Usage Notes
        if SynthesisComponent.USAGE_NOTES.value in components and (
            not definition.usage_notes or force_refresh
        ):
            tasks.append(usage_note_generation(definition, word.text, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.USAGE_NOTES.value, len(tasks) - 1))

        # Regional Variants
        if SynthesisComponent.REGIONAL_VARIANTS.value in components and (
            not definition.region or force_refresh
        ):
            tasks.append(assess_regional_variants(definition, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.REGIONAL_VARIANTS.value, len(tasks) - 1))

    if not tasks:
        return

    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and update definitions
    successes = 0
    failures = 0

    for definition, component, task_idx in task_info:
        result = results[task_idx]

        if isinstance(result, Exception):
            logger.error(f"Failed to enhance {component} for definition: {result}")
            failures += 1
            continue

        if not result:
            continue

        # Update the definition based on component type
        if component == "synonyms" and isinstance(result, list):
            definition.synonyms = cast(list[str], result)
        elif component == "examples" and isinstance(result, list):
            # Create Example objects and save them
            example_ids = []
            for example_text in cast(list[str], result):
                example = Example(
                    definition_id=str(definition.id),
                    text=example_text,
                    type="generated",
                )
                await example.save()
                example_ids.append(str(example.id))
            definition.example_ids.extend(example_ids)
        elif component == "antonyms" and isinstance(result, list):
            definition.antonyms = cast(list[str], result)
        elif component == "word_forms" and isinstance(result, list):
            definition.word_forms = cast(list[WordForm], result)
        elif component == "cefr_level" and isinstance(result, str):
            definition.cefr_level = result  # type: ignore
        elif component == "frequency_band" and isinstance(result, int):
            definition.frequency_band = result
        elif component == "register" and isinstance(result, str):
            definition.language_register = result  # type: ignore
        elif component == "domain" and isinstance(result, str):
            definition.domain = result
        elif component == "grammar_patterns" and isinstance(result, list):
            definition.grammar_patterns = cast(list[GrammarPattern], result)
        elif component == "collocations" and isinstance(result, list):
            definition.collocations = cast(list[Collocation], result)
        elif component == "usage_notes" and isinstance(result, list):
            definition.usage_notes = cast(list[UsageNote], result)
        elif component == "regional_variants":
            # Regional variants returns a list, take the first
            if isinstance(result, list) and result:
                definition.region = cast(str, result[0])
            elif isinstance(result, str):
                definition.region = result

        successes += 1

    # Save all enhanced definitions
    await asyncio.gather(*[d.save() for d in definitions])

    logger.info(
        f"Enhanced {len(definitions)} definitions: {successes} successes, {failures} failures"
    )

    if state_tracker:
        await state_tracker.update(
            stage=Stages.AI_SYNTHESIS,
            progress=95,
            message=f"Enhanced definitions with {successes} components",
        )


async def enhance_synthesized_entry(
    entry_id: str,
    ai: OpenAIConnector,
    components: set[str] | None = None,
    force: bool = False,
    state_tracker: StateTracker | None = None,
) -> None:
    """Enhance a synthesized entry with arbitrary component synthesis.

    This function supports selective enhancement of any subset of attributes,
    allowing incremental updates to entries without regenerating everything.

    Args:
        entry_id: ID of the SynthesizedDictionaryEntry
        components: Set of components to synthesize (None = all)
        force: Force regeneration even if data exists
        ai: OpenAI connector instance (required)
        state_tracker: Optional state tracker for progress updates
    """
    # Load entry
    entry = await SynthesizedDictionaryEntry.get(entry_id)
    if not entry:
        raise ValueError(f"Entry {entry_id} not found")

    # Load word
    word = await Word.get(entry.word_id)
    if not word:
        raise ValueError(f"Word {entry.word_id} not found")

    # Default to all components
    if components is None:
        components = set(SYNTHESIS_COMPONENTS.keys())

    # Separate word-level and definition-level components
    word_level_components = {"pronunciation", "etymology", "facts"}
    definition_level_components = components - word_level_components

    # Load definitions if we need to enhance them
    definitions = []
    if definition_level_components:
        for def_id in entry.definition_ids:
            definition = await Definition.get(def_id)
            if definition:
                definitions.append(definition)

    # Use the consolidated function for definition enhancements
    if definitions and definition_level_components:
        await enhance_definitions_parallel(
            definitions=definitions,
            word=word,
            ai=ai,
            components=definition_level_components,
            force_refresh=force,
            state_tracker=state_tracker,
        )

    # Handle word-level enhancements separately
    word_tasks: list[Coroutine[Any, Any, Any]] = []
    task_types: list[str] = []  # Track the type of each task

    if "pronunciation" in components and (not entry.pronunciation_id or force):
        # TODO: Load provider data for pronunciation
        pron_provider_data: list[dict[str, Any]] = []
        word_tasks.append(
            synthesize_pronunciation(word, pron_provider_data, ai, state_tracker)
        )
        task_types.append("pronunciation")

    if "etymology" in components and (not entry.etymology or force):
        # TODO: Load provider data for etymology
        etym_provider_data: list[dict[str, Any]] = []
        word_tasks.append(
            synthesize_etymology(word, etym_provider_data, ai, state_tracker)
        )
        task_types.append("etymology")

    if "facts" in components and (not entry.fact_ids or force):
        word_tasks.append(
            generate_facts(word, definitions, ai, state_tracker=state_tracker)
        )
        task_types.append("facts")

    # Execute word-level tasks
    if word_tasks:
        results = await asyncio.gather(*word_tasks, return_exceptions=True)

        # Process results based on task type
        for task_type, result in zip(task_types, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to enhance {task_type}: {result}")
                continue

            if task_type == "pronunciation" and isinstance(result, Pronunciation):
                entry.pronunciation_id = str(result.id)
            elif task_type == "etymology" and isinstance(result, Etymology):
                entry.etymology = result
            elif task_type == "word_forms" and isinstance(result, list):
                entry.word_forms = cast(list[WordForm], result)
            elif task_type == "facts" and isinstance(result, list):
                entry.fact_ids = [str(fact.id) for fact in cast(list[Fact], result)]

        # Save updated entry
        await entry.save()

        # Log results
        successes = sum(1 for r in results if r and not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))
        logger.info(
            f"Enhanced entry {entry_id}: {successes} word-level successes, {failures} failures"
        )

    if state_tracker:
        await state_tracker.update(
            stage=Stages.AI_SYNTHESIS, progress=100, message="Enhancement complete"
        )


async def validate_query(
    query: str,
    ai: OpenAIConnector,
) -> QueryValidationResponse:
    """Validate if a query is seeking word suggestions."""
    return await ai.validate_query(query)


async def suggest_words(
    query: str,
    ai: OpenAIConnector,
    count: int = 10,
) -> WordSuggestionResponse:
    """Generate word suggestions based on descriptive query."""
    return await ai.suggest_words(query, count=count)
