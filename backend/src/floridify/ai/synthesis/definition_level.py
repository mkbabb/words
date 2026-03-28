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
from ..assessment.cefr import assess_cefr_local
from ..assessment.domain import classify_domain_local
from ..assessment.frequency import (
    adjust_band_for_sense,
    assess_frequency_local,
    assess_frequency_score_local,
    assess_sense_frequency,
)
from ..assessment.regional import detect_regional_local
from ..assessment.register import classify_register_local
from ..connector import AIConnector
from ..constants import (
    DEFAULT_ANTONYM_COUNT,
    DEFAULT_EXAMPLE_COUNT,
    DEFAULT_SYNONYM_COUNT,
)
from .hybrid import compute_antonym_delta, compute_synonym_delta

logger = get_logger(__name__)


async def synthesize_synonyms(
    word: str,
    definition: Definition,
    ai: AIConnector,
    count: int = 10,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
    language: str = "en",
) -> list[str]:
    """Synthesize synonyms: Wiktionary + WordNet first, AI for the delta.

    Filters AI response by language — primary-language synonyms go to the
    return list, cross-language cognates are stored on definition.cognates.
    """
    from .language_filter import is_primary_language

    count = count or DEFAULT_SYNONYM_COUNT

    if force_refresh:
        definition.synonyms = []

    # Merge Wiktionary (already on definition) + WordNet synonyms
    merged, ai_needed = await compute_synonym_delta(definition, word, target_count=count)

    # If local sources satisfy the target, skip AI entirely
    if ai_needed <= 0:
        return merged[:count]

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Synthesizing {ai_needed} new synonyms for {word} (have {len(merged)} local)",
            )

        # Map ISO code to display name for prompt
        from ...models.base import Language as LangEnum
        lang_display = {v.value: v.name.title() for v in LangEnum}.get(language, "English")

        response = await ai.synthesize_synonyms(
            word=word,
            definition=definition.text,
            part_of_speech=definition.part_of_speech,
            existing_synonyms=merged,
            count=ai_needed,
            language=lang_display,
        )

        # Filter by language: primary → synonyms, foreign → cognates
        word_lower = word.lower()
        all_synonyms = merged.copy()
        cognates: list[str] = list(definition.cognates or [])

        for candidate in response.synonyms:
            if candidate.word.lower() == word_lower:
                continue
            if candidate.word in all_synonyms:
                continue

            if is_primary_language(candidate.language, language):
                all_synonyms.append(candidate.word)
            else:
                cognates.append(candidate.word)

        # Store cognates on the definition
        seen_cog: set[str] = set()
        definition.cognates = [
            c for c in cognates
            if c.lower() not in seen_cog and not seen_cog.add(c.lower())  # type: ignore[func-returns-value]
        ][:20]

        logger.info(
            f"Synthesized {len(all_synonyms)} synonyms + {len(definition.cognates)} cognates "
            f"for '{word}' (hybrid)"
        )
        return all_synonyms[:count]

    except Exception as e:
        logger.error(f"Failed to synthesize synonyms: {e}")
        if state_tracker:
            await state_tracker.update_error(f"Synonym synthesis failed: {e!s}")
        return merged


async def synthesize_antonyms(
    word: str,
    definition: Definition,
    ai: AIConnector,
    count: int = 5,
    force_refresh: bool = False,
    state_tracker: StateTracker | None = None,
    language: str = "en",
) -> list[str]:
    """Synthesize antonyms: Wiktionary + WordNet first, AI for the delta.

    Filters AI response by language — foreign antonyms are discarded
    (antonyms are less useful cross-linguistically than synonym cognates).
    """
    from .language_filter import is_primary_language

    count = count or DEFAULT_ANTONYM_COUNT

    if force_refresh:
        definition.antonyms = []

    # Merge Wiktionary (already on definition) + WordNet antonyms
    merged, ai_needed = await compute_antonym_delta(definition, word, target_count=count)

    # If local sources satisfy the target, skip AI entirely
    if ai_needed <= 0:
        return merged[:count]

    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Synthesizing {ai_needed} new antonyms for {word} (have {len(merged)} local)",
            )

        from ...models.base import Language as LangEnum
        lang_display = {v.value: v.name.title() for v in LangEnum}.get(language, "English")

        response = await ai.synthesize_antonyms(
            word=word,
            definition=definition.text,
            part_of_speech=definition.part_of_speech,
            existing_antonyms=merged,
            count=ai_needed,
            language=lang_display,
        )

        # Filter: keep only primary-language antonyms (discard foreign ones)
        word_lower = word.lower()
        all_antonyms = merged.copy()
        for candidate in response.antonyms:
            if candidate.word.lower() == word_lower:
                continue
            if candidate.word in all_antonyms:
                continue
            if is_primary_language(candidate.language, language):
                all_antonyms.append(candidate.word)

        return all_antonyms[:count]

    except Exception as e:
        logger.error(f"Failed to synthesize antonyms: {e}")
        return merged  # Return local results even if AI fails


async def generate_examples(
    word: str,
    definition: Definition,
    ai: AIConnector,
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
    ai: AIConnector,
    state_tracker: StateTracker | None = None,
) -> str | None:
    """Assess CEFR level for a definition. Local-first with AI fallback.

    Uses sense-level frequency when definition context is available,
    so rare senses of common words get higher CEFR levels.
    """
    local_result = await assess_cefr_local(
        word,
        definition_text=definition.text,
        part_of_speech=definition.part_of_speech,
    )
    if local_result is not None:
        logger.debug(f"CEFR for '{word}' ({definition.part_of_speech}): {local_result} (local, sense-adjusted)")
        return local_result

    # Fall back to AI
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
    ai: AIConnector,
    state_tracker: StateTracker | None = None,
) -> int | None:
    """Assess frequency band for a definition. Local-first with AI fallback.

    Also sets definition.frequency_score as a side effect when using local assessment.
    """
    # Try local assessment first (corpus-derived, deterministic, free)
    local_band = assess_frequency_local(word)
    if local_band is not None:
        # Adjust for sense-level prominence
        sense_freq = await assess_sense_frequency(word, definition.part_of_speech, definition.text)
        adjusted_band = adjust_band_for_sense(local_band, sense_freq)

        # Also set the continuous frequency score for temperature visualization
        local_score = assess_frequency_score_local(word)
        if local_score is not None:
            # Adjust score proportionally to sense frequency
            if sense_freq is not None:
                local_score = local_score * (0.5 + 0.5 * sense_freq)
            definition.frequency_score = local_score

        sense_str = f"{sense_freq:.2f}" if sense_freq is not None else "N/A"
        logger.debug(
            f"Frequency for '{word}' ({definition.part_of_speech}): "
            f"word_band={local_band}, sense_freq={sense_str}, "
            f"adjusted_band={adjusted_band} (local)"
        )
        return adjusted_band

    # Fall back to AI
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
    ai: AIConnector,
    state_tracker: StateTracker | None = None,
) -> str | None:
    """Classify register for a definition. Local-first with AI fallback."""
    local_result = classify_register_local(definition.text)
    if local_result is not None:
        logger.debug(f"Register: {local_result} (local)")
        return local_result

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
    ai: AIConnector,
    state_tracker: StateTracker | None = None,
    word: str = "",
) -> str | None:
    """Identify domain for a definition. Local-first via WordNet taxonomy, AI fallback."""
    local_result = await classify_domain_local(definition.text, word=word, part_of_speech=definition.part_of_speech)
    if local_result is not None:
        logger.debug(f"Domain: {local_result} (local)")
        return local_result

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
    ai: AIConnector,
    count: int = 3,
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
            count=count,
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
    ai: AIConnector,
    count: int = 5,
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
            count=count,
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
    ai: AIConnector,
    count: int = 3,
    state_tracker: StateTracker | None = None,
) -> list[UsageNote]:
    """Generate usage notes for a definition."""
    try:
        if state_tracker:
            await state_tracker.update(
                stage=Stages.AI_SYNTHESIS,
                message=f"Generating usage notes for {word}",
            )
        response = await ai.usage_note_generation(word, definition.text, count=count)
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
    ai: AIConnector,
    state_tracker: StateTracker | None = None,
) -> list[str]:
    """Detect regional variants for a definition. Local-first with AI fallback."""
    local_result = detect_regional_local(definition.text)
    if local_result is not None:
        logger.debug(f"Regional: {local_result} (local)")
        return [local_result]

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
    ai: AIConnector,
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
