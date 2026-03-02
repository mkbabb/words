"""Synthesis sub-package: functional synthesis components for AI pipeline."""

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
from .orchestration import (
    SYNTHESIS_COMPONENTS,
    SynthesisFunc,
    cluster_definitions,
    enhance_definitions_parallel,
    enhance_synthesized_entry,
    suggest_words,
    validate_query,
)
from .word_level import (
    generate_facts,
    synthesize_etymology,
    synthesize_pronunciation,
    synthesize_word_forms,
)

__all__ = [
    "SYNTHESIS_COMPONENTS",
    "SynthesisFunc",
    "assess_collocations",
    "assess_definition_cefr",
    "assess_definition_domain",
    "assess_definition_frequency",
    "assess_grammar_patterns",
    "assess_regional_variants",
    "classify_definition_register",
    "cluster_definitions",
    "enhance_definitions_parallel",
    "enhance_synthesized_entry",
    "generate_examples",
    "generate_facts",
    "suggest_words",
    "synthesize_antonyms",
    "synthesize_definition_text",
    "synthesize_etymology",
    "synthesize_pronunciation",
    "synthesize_synonyms",
    "synthesize_word_forms",
    "usage_note_generation",
    "validate_query",
]
