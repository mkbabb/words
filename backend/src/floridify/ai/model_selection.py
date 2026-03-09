"""Model selection and complexity management for AI operations."""

from enum import Enum


class ModelComplexity(Enum):
    """Categorization of task complexity for model selection."""

    HIGH = "high"  # Complex reasoning, synthesis, clustering
    MEDIUM = "medium"  # Creative generation, pedagogical tasks
    LOW = "low"  # Simple classification, validation


class ModelTier(Enum):
    """Available OpenAI models mapped to capability tiers.

    GPT-5 series uses reasoning.effort to control depth:
    - effort=none: fastest, no reasoning tokens, supports temperature
    - effort=low/medium/high/xhigh: progressively deeper reasoning
    Temperature is ONLY supported when effort=none.
    All GPT-5 models use max_completion_tokens (not max_tokens).
    All GPT-5 models use "developer" role (not "system").
    """

    # GPT-5 series (current generation, March 2026)
    GPT_5_4 = "gpt-5.4"  # Frontier: complex professional work
    GPT_5_MINI = "gpt-5-mini"  # Cost-optimized reasoning and chat
    GPT_5_NANO = "gpt-5-nano"  # High-throughput, instruction-following

    # Reasoning models (o-series, legacy)
    O3_MINI = "o3-mini"

    # GPT-4 series (legacy)
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"

    # Capability-level aliases
    HIGH = "gpt-5.4"
    MEDIUM = "gpt-5-mini"
    LOW = "gpt-5-nano"

    @property
    def is_gpt5(self) -> bool:
        """Check if this is a GPT-5 series model."""
        return self.value.startswith("gpt-5")

    @property
    def is_o_series(self) -> bool:
        """Check if this is an o-series reasoning model."""
        return self.value.startswith(("o1", "o3"))

    @property
    def uses_developer_role(self) -> bool:
        """GPT-5 and o-series use 'developer' role instead of 'system'."""
        return self.is_gpt5 or self.is_o_series

    @property
    def uses_completion_tokens(self) -> bool:
        """GPT-5 and o-series use max_completion_tokens."""
        return self.is_gpt5 or self.is_o_series


# Task-to-complexity mapping based on prompt analysis
TASK_COMPLEXITY_MAP: dict[str, ModelComplexity] = {
    # High complexity — reasoning, synthesis, clustering, synthetic data generation
    "synthesize_definitions": ModelComplexity.HIGH,
    "suggest_words": ModelComplexity.HIGH,
    "extract_cluster_mapping": ModelComplexity.HIGH,
    "generate_synthetic_corpus": ModelComplexity.HIGH,
    "literature_analysis": ModelComplexity.HIGH,
    # Medium complexity — creative generation, pedagogical tasks
    "generate_synonyms": ModelComplexity.MEDIUM,
    "generate_facts": ModelComplexity.MEDIUM,
    "generate_examples": ModelComplexity.MEDIUM,
    "generate_anki_best_describes": ModelComplexity.MEDIUM,
    "generate_anki_fill_blank": ModelComplexity.MEDIUM,
    "synthesize_etymology": ModelComplexity.MEDIUM,
    "generate_collocations": ModelComplexity.MEDIUM,
    "generate_word_forms": ModelComplexity.MEDIUM,
    "generate_antonyms": ModelComplexity.MEDIUM,
    "generate_suggestions": ModelComplexity.MEDIUM,
    "lookup_word": ModelComplexity.MEDIUM,
    "deduplicate_definitions": ModelComplexity.MEDIUM,
    "literature_augmentation": ModelComplexity.MEDIUM,
    "text_generation": ModelComplexity.MEDIUM,
    # Low complexity — simple classification, basic generation
    "assess_frequency": ModelComplexity.LOW,
    "assess_cefr_level": ModelComplexity.LOW,
    "classify_domain": ModelComplexity.LOW,
    "classify_register": ModelComplexity.LOW,
    "generate_pronunciation": ModelComplexity.LOW,
    "generate_usage_notes": ModelComplexity.LOW,
    "validate_query": ModelComplexity.LOW,
    "identify_grammar_patterns": ModelComplexity.LOW,
    "identify_regional_variants": ModelComplexity.LOW,
    "rank_candidates": ModelComplexity.LOW,
}


# Default model selection based on complexity
COMPLEXITY_TO_MODEL: dict[ModelComplexity, ModelTier] = {
    ModelComplexity.HIGH: ModelTier.HIGH,  # gpt-5.4
    ModelComplexity.MEDIUM: ModelTier.MEDIUM,  # gpt-5-mini
    ModelComplexity.LOW: ModelTier.LOW,  # gpt-5-nano
}


def get_model_for_task(task_name: str, override: ModelTier | None = None) -> ModelTier:
    """Get the appropriate model for a given task."""
    if override:
        return override
    complexity = TASK_COMPLEXITY_MAP.get(task_name, ModelComplexity.MEDIUM)
    return COMPLEXITY_TO_MODEL[complexity]


def get_temperature_for_model(model: ModelTier, task_name: str | None = None) -> float | None:
    """Get appropriate temperature for a model and task.

    GPT-5 models only support temperature when reasoning.effort=none.
    Since we use effort=none by default for structured outputs (no reasoning
    needed), temperature IS supported in our usage pattern.
    """
    # o-series reasoning models never support temperature
    if model.is_o_series:
        return None

    # Task-specific temperatures
    if task_name:
        creative_tasks = {
            "generate_facts",
            "generate_examples",
            "suggest_words",
            "generate_suggestions",
            "generate_anki_best_describes",
            "generate_anki_fill_blank",
        }
        if task_name in creative_tasks:
            return 0.8

        classification_tasks = {
            "assess_frequency",
            "assess_cefr_level",
            "classify_domain",
            "classify_register",
            "validate_query",
        }
        if task_name in classification_tasks:
            return 0.3

    return 0.7
