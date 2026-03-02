"""Definition-level synthesis functions: synonyms, antonyms, examples, assessments."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId

from ...core.state_tracker import Stages, StateTracker
from ...models.dictionary import (
    Definition,
    Word,
)
from ...models.relationships import (
    Collocation,
    GrammarPattern,
    UsageNote,
)
from ...utils.logging import get_logger
from ..connector import OpenAIConnector
from ..constants import (
    DEFAULT_ANTONYM_COUNT,
    DEFAULT_EXAMPLE_COUNT,
    DEFAULT_SYNONYM_COUNT,
)

logger = get_logger(__name__)


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
                message=f"Synthesizing {needed_count} new synonyms for {word} (total: {count})",
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
            await state_tracker.update_error(f"Synonym synthesis failed: {e!s}")
        return existing_synonyms


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
                message=f"Synthesizing {needed_count} new antonyms for {word} (total: {count})",
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
        for candidate in response.antonyms:
            if candidate.word not in all_antonyms:
                all_antonyms.append(candidate.word)

        return all_antonyms[:count]

    except Exception as e:
        logger.error(f"Failed to synthesize antonyms: {e}")
        return existing_antonyms


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
            await state_tracker.update_error(f"Example generation failed: {e!s}")
        return []


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
                stage=Stages.AI_SYNTHESIS,
                message=f"Assessing CEFR level for {word}",
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
                stage=Stages.AI_SYNTHESIS,
                message="Classifying register for definition",
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
                stage=Stages.AI_SYNTHESIS,
                message="Identifying domain for definition",
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
                stage=Stages.AI_SYNTHESIS,
                message="Extracting grammar patterns",
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
            for pattern, desc in zip(response.patterns, response.descriptions, strict=False)
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
                stage=Stages.AI_SYNTHESIS,
                message=f"Generating usage notes for {word}",
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
                stage=Stages.AI_SYNTHESIS,
                message="Detecting regional variants",
            )
        response = await ai.assess_regional_variants(definition.text)
        return response.regions
    except Exception as e:
        logger.error(f"Failed to detect regional variants: {e}")
        return []


async def synthesize_definition_text(
    clustered_definitions: list[dict[str, Any]],
    word: Word,
    ai: OpenAIConnector,
    state_tracker: StateTracker | None = None,
) -> dict[str, Any]:
    """Synthesize definition text from clustered meanings."""
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Synthesizing definition for {word.text}",
            )

        # Convert dict definitions to Definition objects for the AI method
        definition_objects = []
        for d in clustered_definitions:
            # Create a minimal Definition object for the synthesis
            def_obj = Definition(
                word_id=word.id if word.id else PydanticObjectId(),
                part_of_speech=d.get("part_of_speech", "unknown"),
                text=d["text"],
                frequency_band=None,
            )
            definition_objects.append(def_obj)

        # Use the existing synthesize_definitions method which uses templates
        response = await ai.synthesize_definitions(
            word=word.text,
            definitions=definition_objects,
            meaning_cluster=None,  # Will synthesize across all
        )

        # Extract the first synthesized definition
        if response.definitions:
            synth_def = response.definitions[0]
            return {
                "definition_text": synth_def.definition,
                "part_of_speech": synth_def.part_of_speech,
                "sources_used": [d.get("provider", "unknown") for d in clustered_definitions],
            }
        return {
            "definition_text": "",
            "part_of_speech": "",
            "sources_used": [],
        }

    except Exception as e:
        logger.error(f"Failed to synthesize definition: {e}")
        if state_tracker:
            await state_tracker.update_error(f"Definition synthesis failed: {e!s}")
        return {
            "definition_text": "",
            "part_of_speech": "",
            "sources_used": [],
        }
