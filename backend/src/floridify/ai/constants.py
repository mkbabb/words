"""AI synthesis constants and defaults."""

from enum import Enum


class SynthesisComponent(Enum):
    """Components available for synthesis and enhancement."""
    
    # Word-level components
    PRONUNCIATION = "pronunciation"
    ETYMOLOGY = "etymology"
    WORD_FORMS = "word_forms"
    FACTS = "facts"
    
    # Definition-level components (default set)
    SYNONYMS = "synonyms"
    EXAMPLES = "examples"
    ANTONYMS = "antonyms"
    CEFR_LEVEL = "cefr_level"
    FREQUENCY_BAND = "frequency_band"
    REGISTER = "register"
    DOMAIN = "domain"
    GRAMMAR_PATTERNS = "grammar_patterns"
    COLLOCATIONS = "collocations"
    USAGE_NOTES = "usage_notes"
    REGIONAL_VARIANTS = "regional_variants"
    
    # Synthesis utilities
    DEFINITION_TEXT = "definition_text"
    CLUSTER_DEFINITIONS = "cluster_definitions"
    
    @classmethod
    def default_components(cls) -> set["SynthesisComponent"]:
        """Return default components for definition enhancement."""
        return {
            cls.SYNONYMS,
            cls.EXAMPLES,
            cls.ANTONYMS,
            cls.USAGE_NOTES,
            cls.REGIONAL_VARIANTS,
        }
    
    @classmethod
    def word_level_components(cls) -> set["SynthesisComponent"]:
        """Return components that apply to the entire word."""
        return {
            cls.PRONUNCIATION,
            cls.ETYMOLOGY,
            cls.WORD_FORMS,
            cls.FACTS,
        }
    
    @classmethod
    def definition_level_components(cls) -> set["SynthesisComponent"]:
        """Return components that apply to individual definitions."""
        return {
            cls.SYNONYMS,
            cls.EXAMPLES,
            cls.ANTONYMS,
            cls.CEFR_LEVEL,
            cls.FREQUENCY_BAND,
            cls.REGISTER,
            cls.DOMAIN,
            cls.GRAMMAR_PATTERNS,
            cls.COLLOCATIONS,
            cls.USAGE_NOTES,
            cls.REGIONAL_VARIANTS,
        }


# Default counts for AI generation functions
DEFAULT_SYNONYM_COUNT = 10
DEFAULT_ANTONYM_COUNT = 5
DEFAULT_FACT_COUNT = 3
DEFAULT_EXAMPLE_COUNT = 3
DEFAULT_SUGGESTION_COUNT = 10
DEFAULT_USAGE_NOTE_COUNT = 3

# Parameter ordering standard
# Functions should follow this parameter order:
# 1. word: str (the word being processed)
# 2. definition: Definition (when working with a specific definition)  
# 3. ai: OpenAIConnector (AI connector instance)
# 4. count: int = DEFAULT_X_COUNT (for generation functions)
# 5. state_tracker: StateTracker | None = None (optional state tracking)

# Function type categories
SYNTHESIZE_FUNCTIONS = {
    "pronunciation",
    "synonyms", 
    "antonyms",
    "etymology",
    "definition_text",
    "cluster_definitions",
}

GENERATE_FUNCTIONS = {
    "facts",
    "examples", 
    "word_forms",
    "usage_notes",
}

ASSESS_FUNCTIONS = {
    "cefr_level",
    "frequency_band",
    "register",
    "domain", 
    "grammar_patterns",
    "collocations",
    "regional_variants",
}