"""Functional synthesis components for AI pipeline."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, cast

from ..models import (
    Collocation,
    Definition,
    Etymology,
    Fact,
    GrammarPattern,
    ModelInfo,
    Pronunciation,
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
    providers_data: list[dict[str, Any]],
    ai: OpenAIConnector,
) -> Pronunciation | None:
    """Synthesize pronunciation from provider data or generate if missing."""
    
    # Check if any provider has pronunciation
    for provider in providers_data:
        if provider.get("pronunciation"):
            # TODO: Merge pronunciations from multiple sources
            return cast(Pronunciation, provider["pronunciation"])
    
    # Generate pronunciation if none found
    try:
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
    providers_data: list[dict[str, Any]],
    ai: OpenAIConnector,
) -> Etymology | None:
    """Extract and synthesize etymology from provider data."""
    
    # Collect etymology data from providers
    etymology_data = []
    for provider in providers_data:
        if provider.get("etymology"):
            etymology_data.append({
                "name": provider["name"],
                "etymology_text": provider["etymology"],
            })
    
    if not etymology_data:
        return None
    
    try:
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
    ai: OpenAIConnector,
) -> list[WordForm]:
    """Generate word forms for a word."""
    
    # Determine primary word type from definitions
    # TODO: Get word type from most common definition
    word_type = "noun"  # Default
    
    try:
        response = await ai.identify_word_forms(word.text, word_type)
        return [
            WordForm(
                form_type=str(form["form_type"]),
                text=str(form["text"]),
            )
            for form in response.forms
        ]
    except Exception as e:
        logger.error(f"Failed to synthesize word forms for {word.text}: {e}")
        return []


async def enhance_definition_antonyms(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
) -> list[str]:
    """Generate antonyms for a definition."""
    
    if definition.antonyms:  # Already has antonyms
        return definition.antonyms
    
    try:
        response = await ai.generate_antonyms(
            word=word,
            definition=definition.text,
            word_type=definition.part_of_speech,
        )
        return response.antonyms
    except Exception as e:
        logger.error(f"Failed to generate antonyms: {e}")
        return []


async def assess_definition_cefr(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
) -> str | None:
    """Assess CEFR level for a definition."""
    
    if definition.cefr_level:
        return definition.cefr_level
    
    try:
        response = await ai.assess_cefr_level(word, definition.text)
        return response.level
    except Exception as e:
        logger.error(f"Failed to assess CEFR level: {e}")
        return None


async def assess_definition_frequency(
    definition: Definition,
    word: str,
    ai: OpenAIConnector,
) -> int | None:
    """Assess frequency band for a definition."""
    
    if definition.frequency_band:
        return definition.frequency_band
    
    try:
        response = await ai.assess_frequency_band(word, definition.text)
        return response.band
    except Exception as e:
        logger.error(f"Failed to assess frequency band: {e}")
        return None


async def classify_definition_register(
    definition: Definition,
    ai: OpenAIConnector,
) -> str | None:
    """Classify register for a definition."""
    
    if definition.language_register:
        return definition.language_register
    
    try:
        response = await ai.classify_register(definition.text)
        return response.register
    except Exception as e:
        logger.error(f"Failed to classify register: {e}")
        return None


async def identify_definition_domain(
    definition: Definition,
    ai: OpenAIConnector,
) -> str | None:
    """Identify domain for a definition."""
    
    if definition.domain:
        return definition.domain
    
    try:
        response = await ai.identify_domain(definition.text)
        return response.domain
    except Exception as e:
        logger.error(f"Failed to identify domain: {e}")
        return None


async def extract_grammar_patterns(
    definition: Definition,
    ai: OpenAIConnector,
) -> list[GrammarPattern]:
    """Extract grammar patterns for a definition."""
    
    if definition.grammar_patterns:
        return definition.grammar_patterns
    
    try:
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
) -> list[Collocation]:
    """Identify collocations for a definition."""
    
    if definition.collocations:
        return definition.collocations
    
    try:
        response = await ai.identify_collocations(
            word=word,
            definition=definition.text,
            word_type=definition.part_of_speech,
        )
        return [
            Collocation(
                text=str(coll["text"]),
                type=str(coll["type"]),
                frequency=float(coll["frequency"]) if coll.get("frequency") is not None else None,
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
) -> list[UsageNote]:
    """Generate usage notes for a definition."""
    
    if definition.usage_notes:
        return definition.usage_notes
    
    try:
        response = await ai.generate_usage_notes(word, definition.text)
        return [
            UsageNote(
                type=str(note["type"]),
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
) -> list[str]:
    """Detect regional variants for a definition."""
    
    if definition.region:
        return [definition.region]
    
    try:
        response = await ai.detect_regional_variants(definition.text)
        return response.regions
    except Exception as e:
        logger.error(f"Failed to detect regional variants: {e}")
        return []


async def synthesize_facts(
    word: Word,
    definitions: list[Definition],
    ai: OpenAIConnector,
    count: int = 3,
) -> list[Fact]:
    """Generate interesting facts about a word."""
    
    # Use primary definition for context
    primary_def = definitions[0].text if definitions else ""
    
    try:
        response = await ai.generate_facts(
            word=word.text,
            definition=primary_def,
            count=count,
        )
        
        facts = []
        for idx, fact_text in enumerate(response.facts):
            # Determine category from response
            category = response.categories[idx] if idx < len(response.categories) else "general"
            
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


# Component registry for easy access
SYNTHESIS_COMPONENTS = {
    # Word-level components
    "pronunciation": synthesize_pronunciation,
    "etymology": synthesize_etymology,
    "word_forms": synthesize_word_forms,
    "facts": synthesize_facts,
    
    # Definition-level components
    "antonyms": enhance_definition_antonyms,
    "cefr_level": assess_definition_cefr,
    "frequency_band": assess_definition_frequency,
    "register": classify_definition_register,
    "domain": identify_definition_domain,
    "grammar_patterns": extract_grammar_patterns,
    "collocations": identify_collocations,
    "usage_notes": generate_usage_notes,
    "regional_variants": detect_regional_variants,
}


async def enhance_synthesized_entry(
    entry_id: str,
    components: set[str] | None = None,
    force: bool = False,
    ai: OpenAIConnector | None = None,
) -> None:
    """Enhance a synthesized entry with parallel component synthesis.
    
    Args:
        entry_id: ID of the SynthesizedDictionaryEntry
        components: Set of components to synthesize (None = all)
        force: Force regeneration even if data exists
        ai: OpenAI connector instance
    """
    from ..models import SynthesizedDictionaryEntry
    
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
    
    # Initialize AI if not provided
    if ai is None:
        # TODO: Get from config
        ai = OpenAIConnector(api_key="", model_name="gpt-4")
    
    tasks = []
    
    # Word-level enhancements
    if "etymology" in components and (not entry.etymology or force):
        # TODO: Load provider data
        provider_data: list[dict[str, Any]] = []
        tasks.append(synthesize_etymology(word, provider_data, ai))
    
    if "word_forms" in components and (not word.word_forms or force):
        tasks.append(synthesize_word_forms(word, ai))
    
    # Definition-level enhancements
    definition_ids = entry.definition_ids
    definitions = []
    for def_id in definition_ids:
        definition = await Definition.get(def_id)
        if definition:
            definitions.append(definition)
            
            # Add tasks for each component
            if "antonyms" in components and (not definition.antonyms or force):
                tasks.append(enhance_definition_antonyms(definition, word.text, ai))
            
            if "cefr_level" in components and (definition.cefr_level is None or force):
                tasks.append(assess_definition_cefr(definition, word.text, ai))
            
            # ... add other components
    
    # Facts generation
    if "facts" in components and (not entry.fact_ids or force):
        tasks.append(synthesize_facts(word, definitions, ai))
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results and update entry
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Enhancement task failed: {result}")
        # TODO: Update entry with results
    
    # Save updated entry
    await entry.save()
    logger.info(f"Enhanced entry {entry_id} with {len(tasks)} components")