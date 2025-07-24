"""Functional synthesis components for AI pipeline."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from ..core.state_tracker import StateTracker

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

logger = get_logger(__name__)

# Type alias for synthesis functions
SynthesisFunc = Callable[..., Any]


async def synthesize_pronunciation(
    word: Word,
    providers_data: list[dict[str, Any]] | list[ProviderData],
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> Pronunciation | None:
    """Synthesize pronunciation from provider data or generate if missing."""

    # Check if any provider has pronunciation
    for provider in providers_data:
        if isinstance(provider, ProviderData):
            # ProviderData format
            if provider.pronunciation_id:
                pronunciation = await Pronunciation.get(provider.pronunciation_id)
                if pronunciation:
                    return pronunciation
        else:
            # Dict format
            if provider.get("pronunciation"):
                # TODO: Merge pronunciations from multiple sources
                return cast(Pronunciation, provider["pronunciation"])

    # Generate pronunciation if none found
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Generating pronunciation for {word.text}",
            )
        response = await ai.pronunciation(word.text)
        pronunciation = Pronunciation(
            word_id=str(word.id),
            phonetic=response.phonetic,
            ipa_american=response.ipa,
            syllables=[],  # TODO: Extract syllables
            stress_pattern=None,
        )
        await pronunciation.save()
        return pronunciation
    except Exception as e:
        logger.error(f"Failed to synthesize pronunciation for {word.text}: {e}")
        return None


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
                form_type=form["form_type"],  # type: ignore[arg-type]
                text=str(form["text"]),
            )
            for form in response.forms
        ]
    except Exception as e:
        logger.error(f"Failed to synthesize word forms for {word.text}: {e}")
        return []


async def synthesize_antonyms(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[str]:
    """Generate antonyms for a definition."""

    if definition.antonyms:  # Already has antonyms
        return definition.antonyms

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message=f"Generating antonyms for {word}"
            )
        response = await ai.generate_antonyms(
            word=word,
            definition=definition.text,
            part_of_speech=definition.part_of_speech,
        )
        return response.antonyms
    except Exception as e:
        logger.error(f"Failed to generate antonyms: {e}")
        return []


async def assess_definition_cefr(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> str | None:
    """Assess CEFR level for a definition."""

    if definition.cefr_level:
        return definition.cefr_level

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

    if definition.frequency_band:
        return definition.frequency_band

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

    if definition.language_register:
        return definition.language_register

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message="Classifying register for definition"
            )
        response = await ai.classify_register(definition.text)
        return response.register
    except Exception as e:
        logger.error(f"Failed to classify register: {e}")
        return None


async def identify_definition_domain(
    definition: Definition,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> str | None:
    """Identify domain for a definition."""

    if definition.domain:
        return definition.domain

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message="Identifying domain for definition"
            )
        response = await ai.identify_domain(definition.text)
        return response.domain
    except Exception as e:
        logger.error(f"Failed to identify domain: {e}")
        return None


async def extract_grammar_patterns(
    definition: Definition,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[GrammarPattern]:
    """Extract grammar patterns for a definition."""

    if definition.grammar_patterns:
        return definition.grammar_patterns

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message="Extracting grammar patterns"
            )
        response = await ai.extract_grammar_patterns(
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


async def identify_collocations(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[Collocation]:
    """Identify collocations for a definition."""

    if definition.collocations:
        return definition.collocations

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Identifying collocations for {word}",
            )
        response = await ai.identify_collocations(
            word=word,
            definition=definition.text,
            part_of_speech=definition.part_of_speech,
        )
        return [
            Collocation(
                text=str(coll["text"]),
                type=coll["type"],  # type: ignore[arg-type]
                frequency=(
                    float(coll["frequency"])
                    if coll.get("frequency") is not None
                    else 0.0
                ),
            )
            for coll in response.collocations
        ]
    except Exception as e:
        logger.error(f"Failed to identify collocations: {e}")
        return []


async def generate_usage_notes(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[UsageNote]:
    """Generate usage notes for a definition."""

    if definition.usage_notes:
        return definition.usage_notes

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message=f"Generating usage notes for {word}"
            )
        response = await ai.generate_usage_notes(word, definition.text)
        return [
            UsageNote(
                type=note["type"],  # type: ignore[arg-type]
                text=str(note["text"]),
            )
            for note in response.notes
        ]
    except Exception as e:
        logger.error(f"Failed to generate usage notes: {e}")
        return []


async def detect_regional_variants(
    definition: Definition,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[str]:
    """Detect regional variants for a definition."""

    if definition.region:
        return [definition.region]

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message="Detecting regional variants"
            )
        response = await ai.detect_regional_variants(definition.text)
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

            # Ensure category is valid
            valid_categories = ["general", "technical", "cultural", "scientific"]
            if category not in valid_categories:
                category = "general"

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
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[str]:
    """Generate synonyms for a definition with efflorescence ranking."""
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message=f"Generating synonyms for {word}"
            )

        # Use the existing generate_synonyms method which uses templates
        response = await ai.generate_synonyms(
            word=word,
            definition=definition.text,
            part_of_speech=definition.part_of_speech,
            count=10,
        )

        # Extract just the words from the structured response
        synonyms = [candidate.word for candidate in response.synonyms]

        logger.info(f"Generated {len(synonyms)} synonyms for '{word}'")
        return synonyms

    except Exception as e:
        logger.error(f"Failed to generate synonyms: {e}")
        if state_tracker:
            await state_tracker.update_error(f"Synonym generation failed: {str(e)}")
        return []


async def synthesize_examples(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> list[str]:
    """Generate contextual example sentences for a definition."""
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS, message=f"Generating examples for {word}"
            )

        # Use the existing generate_examples method which uses templates
        response = await ai.generate_examples(
            word=word,
            part_of_speech=definition.part_of_speech,
            definition=definition.text,
            count=3,
        )

        # Extract the example sentences
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
            cluster = MeaningCluster(
                id=cluster_mapping.cluster_id,
                name=cluster_mapping.cluster_description,
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
    "examples": synthesize_examples,
    "antonyms": synthesize_antonyms,
    "cefr_level": assess_definition_cefr,
    "frequency_band": assess_definition_frequency,
    "register": classify_definition_register,
    "domain": identify_definition_domain,
    "grammar_patterns": extract_grammar_patterns,
    "collocations": identify_collocations,
    "usage_notes": generate_usage_notes,
    "regional_variants": detect_regional_variants,
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
        force: Force regeneration even if data exists
        state_tracker: Optional state tracker
    """
    # Default to all definition-level components
    if components is None:
        components = {
            "synonyms",
            "examples",
            "antonyms",
            "word_forms",
            "cefr_level",
            "frequency_band",
            "register",
            "domain",
            "grammar_patterns",
            "collocations",
            "usage_notes",
            "regional_variants",
        }

    # Build tasks for each definition and component
    tasks: list[Coroutine[Any, Any, Any]] = []
    task_info: list[tuple[Definition, str, int]] = []

    for definition in definitions:
        # Synonyms
        if "synonyms" in components and (not definition.synonyms or force_refresh):
            tasks.append(synthesize_synonyms(definition, word.text, ai, state_tracker))
            task_info.append((definition, "synonyms", len(tasks) - 1))

        # Examples
        if "examples" in components and (not definition.example_ids or force_refresh):
            tasks.append(synthesize_examples(definition, word.text, ai, state_tracker))
            task_info.append((definition, "examples", len(tasks) - 1))

        # Antonyms
        if "antonyms" in components and (not definition.antonyms or force_refresh):
            tasks.append(synthesize_antonyms(definition, word.text, ai, state_tracker))
            task_info.append((definition, "antonyms", len(tasks) - 1))

        # Word forms
        if "word_forms" in components and (not definition.word_forms or force_refresh):
            # Use the part of speech from the definition
            tasks.append(
                synthesize_word_forms(
                    definition.word, definition.part_of_speech, ai, state_tracker
                )
            )
            task_info.append((definition, "word_forms", len(tasks) - 1))

        # CEFR Level
        if "cefr_level" in components and (
            definition.cefr_level is None or force_refresh
        ):
            tasks.append(
                assess_definition_cefr(definition, word.text, ai, state_tracker)
            )
            task_info.append((definition, "cefr_level", len(tasks) - 1))

        # Frequency Band
        if "frequency_band" in components and (
            definition.frequency_band is None or force_refresh
        ):
            tasks.append(
                assess_definition_frequency(definition, word.text, ai, state_tracker)
            )
            task_info.append((definition, "frequency_band", len(tasks) - 1))

        # Register
        if "register" in components and (
            not definition.language_register or force_refresh
        ):
            tasks.append(classify_definition_register(definition, ai, state_tracker))
            task_info.append((definition, "register", len(tasks) - 1))

        # Domain
        if "domain" in components and (not definition.domain or force_refresh):
            tasks.append(identify_definition_domain(definition, ai, state_tracker))
            task_info.append((definition, "domain", len(tasks) - 1))

        # Grammar Patterns
        if "grammar_patterns" in components and (
            not definition.grammar_patterns or force_refresh
        ):
            tasks.append(extract_grammar_patterns(definition, ai, state_tracker))
            task_info.append((definition, "grammar_patterns", len(tasks) - 1))

        # Collocations
        if "collocations" in components and (
            not definition.collocations or force_refresh
        ):
            tasks.append(
                identify_collocations(definition, word.text, ai, state_tracker)
            )
            task_info.append((definition, "collocations", len(tasks) - 1))

        # Usage Notes
        if "usage_notes" in components and (
            not definition.usage_notes or force_refresh
        ):
            tasks.append(generate_usage_notes(definition, word.text, ai, state_tracker))
            task_info.append((definition, "usage_notes", len(tasks) - 1))

        # Regional Variants
        if "regional_variants" in components and (
            not definition.region or force_refresh
        ):
            tasks.append(detect_regional_variants(definition, ai, state_tracker))
            task_info.append((definition, "regional_variants", len(tasks) - 1))

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
