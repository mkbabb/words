"""Orchestration functions: parallel enhancement, entry enhancement, clustering, validation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, cast

from beanie import PydanticObjectId

from ...core.state_tracker import Stages, StateTracker
from ...models import Etymology, ModelInfo
from ...models.dictionary import (
    Definition,
    DictionaryEntry,
    Example,
    Fact,
    Pronunciation,
    Word,
)
from ...models.relationships import (
    Collocation,
    GrammarPattern,
    MeaningCluster,
    UsageNote,
    WordForm,
)
from ...utils.logging import get_logger
from ..batch_processor import batch_synthesis
from ..connector import OpenAIConnector
from ..constants import SynthesisComponent
from ..models import QueryValidationResponse, WordSuggestionResponse
from .definition_level import (
    assess_collocations,
    assess_definition_cefr,
    assess_definition_domain,
    assess_definition_frequency,
    assess_grammar_patterns,
    assess_regional_variants,
    classify_definition_register,
    generate_examples,
    synthesize_antonyms,
    synthesize_definition_text,
    synthesize_synonyms,
    usage_note_generation,
)
from .word_level import (
    generate_facts,
    synthesize_etymology,
    synthesize_pronunciation,
    synthesize_word_forms,
)

logger = get_logger(__name__)

# Type alias for synthesis functions
SynthesisFunc = Callable[..., Any]


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
                provider_data = await DictionaryEntry.get(definition.dictionary_entry_id)

                if provider_data:
                    # Convert enum to string for display
                    provider_name = provider_data.provider.value

            definition_tuples.append(
                (
                    provider_name,
                    definition.part_of_speech,
                    definition.text,
                ),
            )

        # Extract cluster mappings
        cluster_response = await ai.extract_cluster_mapping(word.text, definition_tuples)

        # Apply cluster assignments
        for cluster_mapping in cluster_response.cluster_mappings:
            # Extract short name from cluster_id (e.g., "bank_finance" -> "finance")
            cluster_name = (
                cluster_mapping.cluster_id.split("_")[-1].title()
                if "_" in cluster_mapping.cluster_id
                else cluster_mapping.cluster_id
            )

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
            f"into {len(cluster_response.cluster_mappings)} clusters",
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
            await state_tracker.update_error(f"Definition clustering failed: {e!s}")
        # Return definitions unchanged on error
        return definitions


async def enhance_definitions_parallel(
    definitions: list[Definition],
    word: Word,
    ai: OpenAIConnector,
    components: set[SynthesisComponent] | None = None,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
    batch_mode: bool = False,
) -> None:
    """Enhance definitions with specified components in parallel.

    Args:
        definitions: List of definitions to enhance
        word: The word object
        ai: OpenAI connector instance
        components: Set of components to enhance (None = all definition-level)
        force_refresh: Force regeneration even if data exists
        state_tracker: Optional state tracker
        batch_mode: Use batch processing for 50% cost reduction (for bulk operations)

    """
    # Default to all definition-level components
    if components is None:
        components = SynthesisComponent.default_components()

    # Build tasks for each definition and component
    tasks: list[Coroutine[Any, Any, Any]] = []
    task_info: list[tuple[Definition, SynthesisComponent, int]] = []

    for definition in definitions:
        # Synonyms
        if SynthesisComponent.SYNONYMS in components and (not definition.synonyms or force_refresh):
            tasks.append(
                synthesize_synonyms(
                    word.text,
                    definition,
                    ai,
                    force_refresh=force_refresh,
                    state_tracker=state_tracker,
                ),
            )
            task_info.append((definition, SynthesisComponent.SYNONYMS, len(tasks) - 1))

        # Examples
        if SynthesisComponent.EXAMPLES in components and (
            not definition.example_ids or force_refresh
        ):
            tasks.append(generate_examples(word.text, definition, ai, state_tracker=state_tracker))
            task_info.append((definition, SynthesisComponent.EXAMPLES, len(tasks) - 1))

        # Antonyms
        if SynthesisComponent.ANTONYMS in components and (not definition.antonyms or force_refresh):
            tasks.append(
                synthesize_antonyms(
                    word.text,
                    definition,
                    ai,
                    force_refresh=force_refresh,
                    state_tracker=state_tracker,
                ),
            )
            task_info.append((definition, SynthesisComponent.ANTONYMS, len(tasks) - 1))

        # Word forms
        if SynthesisComponent.WORD_FORMS in components and (
            not definition.word_forms or force_refresh
        ):
            # Use the part of speech from the definition
            tasks.append(synthesize_word_forms(word, definition.part_of_speech, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.WORD_FORMS, len(tasks) - 1))

        # CEFR Level
        if SynthesisComponent.CEFR_LEVEL in components and (
            definition.cefr_level is None or force_refresh
        ):
            tasks.append(assess_definition_cefr(definition, word.text, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.CEFR_LEVEL, len(tasks) - 1))

        # Frequency Band
        if SynthesisComponent.FREQUENCY_BAND in components and (
            definition.frequency_band is None or force_refresh
        ):
            tasks.append(assess_definition_frequency(definition, word.text, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.FREQUENCY_BAND, len(tasks) - 1))

        # Register
        if SynthesisComponent.REGISTER in components and (
            not definition.language_register or force_refresh
        ):
            tasks.append(classify_definition_register(definition, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.REGISTER, len(tasks) - 1))

        # Domain
        if SynthesisComponent.DOMAIN in components and (not definition.domain or force_refresh):
            tasks.append(assess_definition_domain(definition, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.DOMAIN, len(tasks) - 1))

        # Grammar Patterns
        if SynthesisComponent.GRAMMAR_PATTERNS in components and (
            not definition.grammar_patterns or force_refresh
        ):
            tasks.append(assess_grammar_patterns(definition, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.GRAMMAR_PATTERNS, len(tasks) - 1))

        # Collocations
        if SynthesisComponent.COLLOCATIONS in components and (
            not definition.collocations or force_refresh
        ):
            tasks.append(assess_collocations(definition, word.text, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.COLLOCATIONS, len(tasks) - 1))

        # Usage Notes
        if SynthesisComponent.USAGE_NOTES in components and (
            not definition.usage_notes or force_refresh
        ):
            tasks.append(usage_note_generation(definition, word.text, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.USAGE_NOTES, len(tasks) - 1))

        # Regional Variants
        if SynthesisComponent.REGIONAL_VARIANTS in components and (
            not definition.region or force_refresh
        ):
            tasks.append(assess_regional_variants(definition, ai, state_tracker))
            task_info.append((definition, SynthesisComponent.REGIONAL_VARIANTS, len(tasks) - 1))

    if not tasks:
        return

    # Execute tasks based on mode
    if batch_mode:
        # batch_synthesis patches connector._make_structured_request to collect
        # requests into a batch; the gather triggers collection, not execution.
        # Actual batch execution happens on context manager __aexit__.
        async with batch_synthesis(ai):
            results = await asyncio.gather(*tasks, return_exceptions=True)
    else:
        # Execute all tasks in parallel (immediate mode)
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
        if component == SynthesisComponent.SYNONYMS and isinstance(result, list):
            definition.synonyms = cast("list[str]", result)
        elif component == SynthesisComponent.EXAMPLES and isinstance(result, list):
            # Create Example objects and save them
            example_ids: list[PydanticObjectId] = []
            assert definition.id is not None  # Definition should have been saved
            for example_text in cast("list[str]", result):
                example = Example(
                    definition_id=definition.id,
                    text=example_text,
                    type="generated",
                    model_info=ModelInfo(
                        name=ai.last_model_info.name
                        if ai.last_model_info
                        else "unknown",  # Track the model used
                        confidence=1.0,  # Examples don't have confidence in response
                        generation_count=1,
                    ),
                )
                await example.save()
                assert example.id is not None  # After save(), id is guaranteed to be not None
                example_ids.append(example.id)
            definition.example_ids.extend(example_ids)
        elif component == SynthesisComponent.ANTONYMS and isinstance(result, list):
            definition.antonyms = cast("list[str]", result)
        elif component == SynthesisComponent.WORD_FORMS and isinstance(result, list):
            definition.word_forms = cast("list[WordForm]", result)
        elif component == SynthesisComponent.CEFR_LEVEL and isinstance(result, str):
            definition.cefr_level = result  # type: ignore
        elif component == SynthesisComponent.FREQUENCY_BAND and isinstance(result, int):
            definition.frequency_band = result
        elif component == SynthesisComponent.REGISTER and isinstance(result, str):
            definition.language_register = result  # type: ignore
        elif component == SynthesisComponent.DOMAIN and isinstance(result, str):
            definition.domain = result
        elif component == SynthesisComponent.GRAMMAR_PATTERNS and isinstance(result, list):
            definition.grammar_patterns = cast("list[GrammarPattern]", result)
        elif component == SynthesisComponent.COLLOCATIONS and isinstance(result, list):
            definition.collocations = cast("list[Collocation]", result)
        elif component == SynthesisComponent.USAGE_NOTES and isinstance(result, list):
            definition.usage_notes = cast("list[UsageNote]", result)
        elif component == SynthesisComponent.REGIONAL_VARIANTS:
            # Regional variants returns a list, take the first
            if isinstance(result, list) and result:
                definition.region = cast("str", result[0])
            elif isinstance(result, str):
                definition.region = result

        successes += 1

    # Save all enhanced definitions
    await asyncio.gather(*[d.save() for d in definitions])

    logger.info(
        f"Enhanced {len(definitions)} definitions: {successes} successes, {failures} failures",
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
    components: set[SynthesisComponent] | None = None,
    force: bool = False,
    state_tracker: StateTracker | None = None,
) -> None:
    """Enhance a synthesized entry with arbitrary component synthesis.

    This function supports selective enhancement of any subset of attributes,
    allowing incremental updates to entries without regenerating everything.

    Args:
        entry_id: ID of the DictionaryEntry
        components: Set of components to synthesize (None = all)
        force: Force regeneration even if data exists
        ai: OpenAI connector instance (required)
        state_tracker: Optional state tracker for progress updates

    """
    # Load entry
    entry = await DictionaryEntry.get(entry_id)
    if not entry:
        raise ValueError(f"Entry {entry_id} not found")

    # Load word
    word = await Word.get(entry.word_id)
    if not word:
        raise ValueError(f"Word {entry.word_id} not found")

    # Default to all components
    if components is None:
        components = (
            SynthesisComponent.word_level_components()
            | SynthesisComponent.definition_level_components()
        )

    # Separate word-level and definition-level components
    definition_level_components = components & SynthesisComponent.definition_level_components()

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
    task_types: list[SynthesisComponent] = []  # Track the type of each task

    if SynthesisComponent.PRONUNCIATION in components and (not entry.pronunciation_id or force):
        # Use the entry itself as provider data (it's a DictionaryEntry)
        word_tasks.append(synthesize_pronunciation(word.text, [entry], ai, state_tracker))
        task_types.append(SynthesisComponent.PRONUNCIATION)

    if SynthesisComponent.ETYMOLOGY in components and (not entry.etymology or force):
        # Use the entry itself as provider data (it's a DictionaryEntry)
        word_tasks.append(synthesize_etymology(word, [entry], ai, state_tracker))
        task_types.append(SynthesisComponent.ETYMOLOGY)

    if SynthesisComponent.FACTS in components and (not entry.fact_ids or force):
        word_tasks.append(generate_facts(word, definitions, ai, state_tracker=state_tracker))
        task_types.append(SynthesisComponent.FACTS)

    # Execute word-level tasks
    if word_tasks:
        # Note: batch_mode would be passed from enhance_synthesized_entry if needed
        # For now, word-level tasks run in immediate mode
        results = await asyncio.gather(*word_tasks, return_exceptions=True)

        # Process results based on task type
        for task_type, result in zip(task_types, results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"Failed to enhance {task_type}: {result}")
                continue

            if task_type == SynthesisComponent.PRONUNCIATION and isinstance(result, Pronunciation):
                assert result.id is not None  # Pronunciation should have been saved
                entry.pronunciation_id = result.id
            elif task_type == SynthesisComponent.ETYMOLOGY and isinstance(result, Etymology):
                entry.etymology = result
            elif task_type == SynthesisComponent.WORD_FORMS and isinstance(result, list):
                entry.word_forms = cast("list[WordForm]", result)
            elif task_type == SynthesisComponent.FACTS and isinstance(result, list):
                entry.fact_ids = [
                    fact.id for fact in cast("list[Fact]", result) if fact.id is not None
                ]

        # Save updated entry
        await entry.save()

        # Log results
        successes = sum(1 for r in results if r and not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))
        logger.info(
            f"Enhanced entry {entry_id}: {successes} word-level successes, {failures} failures",
        )

    if state_tracker:
        await state_tracker.update(
            stage=Stages.AI_SYNTHESIS,
            progress=100,
            message="Enhancement complete",
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
