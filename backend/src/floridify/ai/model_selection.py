"""Model selection and complexity management for AI operations."""

from enum import Enum


class ModelComplexity(Enum):
    """Categorization of task complexity for model selection."""

    HIGH = "high"  # Complex reasoning, synthesis, clustering
    MEDIUM = "medium"  # Creative generation, pedagogical tasks
    LOW = "low"  # Simple classification, validation


class ModelTier(Enum):
    """Available OpenAI models with their capabilities."""

    # Reasoning models (o-series)
    O3_MINI = "o3-mini"
    O1_MINI = "o1-mini"

    # GPT-4 series
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"

    @property
    def supports_vision(self) -> bool:
        """Check if model supports vision/multimodal inputs."""
        return self in {ModelTier.GPT_4O, ModelTier.GPT_4O_MINI}

    @property
    def is_reasoning_model(self) -> bool:
        """Check if this is a reasoning model (o-series)."""
        return self.value.startswith(("o1", "o3"))


# Task-to-complexity mapping based on prompt analysis
TASK_COMPLEXITY_MAP: dict[str, ModelComplexity] = {
    # High complexity - reasoning, synthesis, clustering
    "synthesize_definitions": ModelComplexity.HIGH,
    "suggest_words": ModelComplexity.HIGH,
    "extract_cluster_mapping": ModelComplexity.HIGH,
    # Medium complexity - creative generation, pedagogical tasks
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
    # Low complexity - simple classification, basic generation
    "assess_frequency": ModelComplexity.LOW,
    "assess_cefr_level": ModelComplexity.LOW,
    "classify_domain": ModelComplexity.LOW,
    "classify_register": ModelComplexity.LOW,
    "generate_pronunciation": ModelComplexity.LOW,
    "generate_usage_notes": ModelComplexity.LOW,
    "validate_query": ModelComplexity.LOW,
    "identify_grammar_patterns": ModelComplexity.LOW,
    "identify_regional_variants": ModelComplexity.LOW,
}


# Default model selection based on complexity
COMPLEXITY_TO_MODEL: dict[ModelComplexity, ModelTier] = {
    ModelComplexity.HIGH: ModelTier.O3_MINI,
    ModelComplexity.MEDIUM: ModelTier.GPT_4O,
    ModelComplexity.LOW: ModelTier.GPT_4O_MINI,
}


def get_model_for_task(task_name: str, override: ModelTier | None = None) -> ModelTier:
    """
    Get the appropriate model for a given task.

    Args:
        task_name: Name of the task/method being called
        override: Optional model override

    Returns:
        The selected model tier
    """
    if override:
        return override

    complexity = TASK_COMPLEXITY_MAP.get(task_name, ModelComplexity.MEDIUM)

    return COMPLEXITY_TO_MODEL[complexity]


def get_temperature_for_model(
    model: ModelTier, task_name: str | None = None
) -> float | None:
    """
    Get appropriate temperature for a model and task.

    Args:
        model: The model tier
        task_name: Optional task name for task-specific temperature

    Returns:
        Temperature value or None for reasoning models
    """
    # Reasoning models don't use temperature
    if model.is_reasoning_model:
        return None

    # Task-specific temperatures
    if task_name:
        # Creative tasks benefit from higher temperature
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

        # Classification tasks need lower temperature
        classification_tasks = {
            "assess_frequency",
            "assess_cefr_level",
            "classify_domain",
            "classify_register",
            "validate_query",
        }
        if task_name in classification_tasks:
            return 0.3

    # Default temperature
    return 0.7
