"""AI-specific data models for Floridify."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..models.base import AIResponseBase
from ..models.dictionary import DictionaryProvider


class ExampleGenerationResponse(AIResponseBase):
    """Response from example generation."""

    example_sentences: list[str] = Field(
        description="List of high-quality example sentences.",
    )


class PronunciationResponse(AIResponseBase):
    """Response from pronunciation generation."""

    phonetic: str
    ipa: str


class DefinitionResponse(AIResponseBase):
    """Clean definition model for AI responses without numpy arrays."""

    part_of_speech: str = Field(
        description="Part of speech of the word (noun, verb, etc.).",
    )

    definition: str = Field(
        description="Definition of the word type.",
    )

    relevancy: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relevancy score for this definition within its meaning cluster (0.0-1.0, where 1.0 is most commonly used).",
    )

    source_providers: list[DictionaryProvider] = Field(
        default_factory=list,
        description="List of providers that contributed to this definition.",
    )


class DictionaryEntryResponse(AIResponseBase):
    """Response from AI dictionary synthesis."""

    definitions: list[DefinitionResponse] = Field(
        description="Comprehensive list of synthesized definitions with provider attribution.",
    )


class ClusterMapping(AIResponseBase):
    """A single cluster mapping entry."""

    cluster_id: str = Field(
        description="Unique cluster identifier (e.g., 'bank_financial') - always in the form {word}_{meaning_cluster}.",
    )
    cluster_description: str = Field(description="Human-readable description of this cluster")
    definition_indices: list[int] = Field(
        description="List of definition indices (0-based) in this cluster",
    )
    relevancy: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="How relevant this cluster is to common usage (0.0-1.0, where 1.0 is most commonly used meaning)",
    )


class ClusterMappingResponse(AIResponseBase):
    """Response containing numerical mapping of clusters to definition IDs."""

    word: str = Field(description="The word being analyzed")

    cluster_mappings: list[ClusterMapping] = Field(
        description="List of cluster mappings with their descriptions and indices",
    )


class TextGenerationRequest(BaseModel):
    """Request for text generation."""

    prompt: str = Field(description="The prompt for text generation")
    max_tokens: int = Field(default=500, description="Maximum tokens to generate")
    temperature: float = Field(default=0.7, description="Temperature for generation")


class TextGenerationResponse(AIResponseBase):
    """Response from text generation."""

    text: str = Field(description="Generated text content")


class LiteratureAugmentationRequest(BaseModel):
    """Request for literature augmentation."""

    author: str = Field(description="Author name for context")
    sample_words: list[str] = Field(description="Sample words from the author")
    transformation_prompt: str = Field(description="How to transform the words")
    target_count: int = Field(default=50, description="Number of words to generate")


class LiteratureAugmentationResponse(AIResponseBase):
    """Response from literature augmentation."""

    words: list[str] = Field(description="Generated augmented words")
    transformation_applied: str = Field(description="Description of transformation applied")


class SemanticID(BaseModel):
    """4D semantic identifier for literature analysis."""

    style: int = Field(ge=0, le=7, description="Style dimension (0-7)")
    complexity: int = Field(ge=0, le=7, description="Complexity dimension (0-7)")
    era: int = Field(ge=0, le=7, description="Era dimension (0-7)")
    variation: int = Field(ge=0, le=4, description="Variation dimension (0-4)")


class LiteratureAnalysis(BaseModel):
    """Detailed analysis of literature characteristics."""

    style_description: str = Field(description="Detailed explanation of style classification")
    complexity_description: str = Field(description="Explanation of complexity assessment")
    era_description: str = Field(description="Historical/temporal context")
    variation_description: str = Field(description="Uniqueness and variation factors")


class LiteratureCharacteristics(BaseModel):
    """Characteristic features of the literature corpus."""

    dominant_themes: list[str] = Field(description="Main thematic elements")
    linguistic_features: list[str] = Field(description="Key linguistic features")
    stylistic_markers: list[str] = Field(description="Stylistic markers")
    semantic_domains: list[str] = Field(description="Semantic domains covered")


class LiteratureAugmentation(BaseModel):
    """Augmentation suggestions for literature corpus."""

    suggested_additions: list[str] = Field(description="Words to add")
    suggested_removals: list[str] = Field(description="Words to remove")
    thematic_clusters: dict[str, list[str]] = Field(
        default_factory=dict, description="Thematic word clusters"
    )


class LiteratureQualityMetrics(BaseModel):
    """Quality assessment metrics for literature corpus."""

    coverage_score: float = Field(ge=0.0, le=1.0, description="Coverage of author's vocabulary")
    distinctiveness_score: float = Field(
        ge=0.0, le=1.0, description="Uniqueness compared to general English"
    )
    coherence_score: float = Field(ge=0.0, le=1.0, description="Internal consistency")
    balance_score: float = Field(ge=0.0, le=1.0, description="Distribution across categories")
    overall_quality: float = Field(ge=0.0, le=1.0, description="Overall quality assessment")


class LiteratureMetadata(BaseModel):
    """Metadata about the analyzed literature."""

    author: str = Field(description="Author name")
    period: str = Field(description="Literary period")
    genre: str = Field(description="Primary genre")
    word_count: int = Field(description="Number of words analyzed")
    unique_features: list[str] = Field(description="Unique features identified")


class LiteratureAnalysisResponse(AIResponseBase):
    """Complete response from literature corpus analysis."""

    semantic_id: SemanticID = Field(description="4D semantic identifier")
    style_description: str = Field(description="Detailed explanation of style classification")
    complexity_description: str = Field(description="Explanation of complexity assessment")
    era_description: str = Field(description="Historical/temporal context")
    dominant_themes: list[str] = Field(description="Main thematic elements")
    quality_score: float = Field(ge=0.0, le=1.0, description="Overall quality assessment")
    author: str = Field(description="Author name")
    word_count: int = Field(description="Number of words analyzed")


class SynthesisResponse(AIResponseBase):
    """Response from definition synthesis."""

    definitions: list[DefinitionResponse] = Field(
        description="Comprehensive list of definitions for this word across all word types, each with their source providers.",
    )
    sources_used: list[str] = Field(
        description="List of all unique provider names used in the synthesis.",
    )


class SynonymCandidate(BaseModel):
    """A single synonym candidate with relevance and efflorescence rating."""

    word: str = Field(description="The synonym word or phrase")
    language: str = Field(description="Language of origin (e.g., English, Latin, French)")
    relevance: float = Field(description="Relevance score (0.0 to 1.0)")
    efflorescence: float = Field(description="Beauty and expressive power score (0.0 to 1.0)")
    explanation: str = Field(
        description="Brief explanation of the relationship and why it's beautiful",
    )


class SynonymGenerationResponse(AIResponseBase):
    """Response for synonym generation with efflorescence ranking."""

    synonyms: list[SynonymCandidate] = Field(
        description="List of synonyms ordered by relevance and efflorescence",
    )


class Suggestion(BaseModel):
    """A single word suggestion."""

    word: str = Field(description="The suggested word")
    reasoning: str = Field(description="Brief explanation of why this word is a good suggestion")
    difficulty_level: int = Field(
        ge=1,
        le=5,
        description="Difficulty level from 1 (basic) to 5 (advanced)",
    )
    semantic_category: str = Field(description="Semantic category or theme")


class SuggestionsResponse(AIResponseBase):
    """Response for word suggestions based on input words."""

    suggestions: list[Suggestion] = Field(description="List of word suggestions with explanations")
    input_analysis: str = Field(
        description="Brief analysis of the input words and suggestion rationale",
    )


class FactGenerationResponse(AIResponseBase):
    """Response from AI fact generation about a word."""

    facts: list[str] = Field(description="List of interesting, educational facts about the word")
    categories: list[str] = Field(
        description="Categories of facts generated (etymology, usage, cultural, etc.)",
    )


class Collocation(BaseModel):
    """A single collocation entry."""

    type: str = Field(description="Type of collocation (e.g., verb+noun, adjective+noun)")
    phrase: str = Field(description="The collocation phrase")
    frequency: float = Field(ge=0.0, le=1.0, description="Frequency score")


class CollocationResponse(AIResponseBase):
    """Response for collocation generation."""

    collocations: list[Collocation] = Field(
        description="Common word combinations with type and frequency",
    )


class WordSuggestion(BaseModel):
    """A word suggestion based on descriptive query."""

    word: str = Field(description="The suggested word")
    confidence: float = Field(ge=0.0, le=1.0, description="Semantic match confidence")
    efflorescence: float = Field(ge=0.0, le=1.0, description="Beauty and memorability score")
    reasoning: str = Field(description="Why this word fits the query")
    example_usage: str | None = Field(None, description="Example sentence with word in context")


class WordSuggestionResponse(AIResponseBase):
    """Response for AI word suggestions from descriptive queries."""

    suggestions: list[WordSuggestion] = Field(
        description="Words matching the description, ranked by confidence then efflorescence",
    )
    query_type: str = Field(
        description="Type of query (descriptive, fill-in-blank, characteristic-based)",
    )
    original_query: str = Field(description="The original user query")


class QueryValidationResponse(AIResponseBase):
    """Response for query validation."""

    is_valid: bool = Field(description="Whether query seeks word suggestions")
    reason: str = Field(description="Explanation of validation decision")


class GrammarPatternResponse(AIResponseBase):
    """Response for grammar pattern extraction."""

    patterns: list[str] = Field(description="Common grammatical constructions (e.g., [Tn], sb/sth)")
    descriptions: list[str] = Field(description="Human-readable descriptions of patterns")


class CEFRLevelResponse(AIResponseBase):
    """Response for CEFR level assessment."""

    level: str = Field(description="CEFR level (A1-C2)")
    reasoning: str = Field(description="Explanation for the level assignment")


class UsageNote(BaseModel):
    """A single usage note."""

    type: str = Field(description="Type of usage note (e.g., register, formality, context)")
    text: str = Field(description="The usage guidance text")


class UsageNoteResponse(AIResponseBase):
    """Response for usage note generation."""

    notes: list[UsageNote] = Field(description="Usage guidance with type and text")


class AIGeneratedProviderData(BaseModel):
    """AI fallback provider data with quality indicators."""

    word: str
    provider: DictionaryProvider = DictionaryProvider.AI_FALLBACK
    definitions: list[dict[str, Any]] = Field(default_factory=list)
    confidence_score: float
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    model_used: str


class AntonymCandidate(BaseModel):
    """A single antonym candidate with relevance and efflorescence rating."""

    word: str = Field(description="The antonym word or phrase")
    language: str = Field(description="Language of origin (e.g., English, Latin, French)")
    relevance: float = Field(description="Relevance score (0.0 to 1.0)")
    efflorescence: float = Field(description="Beauty and expressive power score (0.0 to 1.0)")
    explanation: str = Field(
        description="Brief explanation of the semantic inversion",
    )


class AntonymResponse(AIResponseBase):
    """Response for antonym generation with efflorescence ranking."""

    antonyms: list[AntonymCandidate] = Field(
        description="List of antonyms ordered by relevance and efflorescence",
    )


class EtymologyResponse(AIResponseBase):
    """Response for etymology extraction."""

    text: str = Field(description="Etymology text explaining word origin")
    origin_language: str | None = Field(None, description="Language of origin")
    root_words: list[str] = Field(description="Root words or morphemes")
    first_known_use: str | None = Field(None, description="Date or period of first use")


class WordForm(BaseModel):
    """A single word form."""

    type: str = Field(description="Type of form (e.g., plural, past_tense, gerund)")
    text: str = Field(description="The word form text")


class WordFormResponse(AIResponseBase):
    """Response for word form generation."""

    forms: list[WordForm] = Field(description="List of word forms with type and text")


class RegisterClassificationResponse(AIResponseBase):
    """Response for register classification."""

    model_config = {"populate_by_name": True}  # Accept both field name and alias

    language_register: str = Field(
        alias="register",
        description="Register level: formal, informal, neutral, slang, technical",
    )
    reasoning: str = Field(description="Explanation for classification")


class DomainIdentificationResponse(AIResponseBase):
    """Response for domain identification."""

    domain: str | None = Field(None, description="Domain/field: medical, legal, computing, etc.")
    reasoning: str = Field(description="Explanation for identification")


class FrequencyBandResponse(AIResponseBase):
    """Response for frequency band assessment."""

    band: int = Field(ge=1, le=5, description="Frequency band: 1 (most common) to 5 (least common)")
    reasoning: str = Field(description="Explanation for assessment")


class RegionalVariantResponse(AIResponseBase):
    """Response for regional variant detection."""

    regions: list[str] = Field(description="Regions where this usage is common (US, UK, AU, etc.)")


class EnhancedDefinitionResponse(AIResponseBase):
    """Complete enhanced definition with all fields."""

    model_config = {"populate_by_name": True}  # Accept both field name and alias

    definition: DefinitionResponse
    antonyms: list[str]
    language_register: str | None = Field(alias="register")
    domain: str | None
    regions: list[str]
    cefr_level: str | None
    frequency_band: int | None
    grammar_patterns: list[dict[str, str]]
    collocations: list[dict[str, str | float]]
    usage_notes: list[dict[str, str]]


class ComprehensiveSynthesisResponse(AIResponseBase):
    """Complete synthesis response with all components."""

    pronunciation: PronunciationResponse | None
    etymology: EtymologyResponse | None
    word_forms: list[dict[str, str]]
    definitions: list[EnhancedDefinitionResponse]
    facts: list[str]
    overall_confidence: float = Field(ge=0.0, le=1.0)
    model_info: dict[str, Any]


class ExampleSynthesisResponse(AIResponseBase):
    """Response for example sentence synthesis."""

    examples: list[str] = Field(description="List of natural, contextual example sentences")


class DefinitionSynthesisResponse(AIResponseBase):
    """Response for definition text synthesis from clusters."""

    definition_text: str = Field(
        description="Synthesized definition text combining clustered meanings",
    )
    part_of_speech: str = Field(description="Part of speech for this definition cluster")
    sources_used: list[str] = Field(description="Provider sources used in synthesis")


class MeaningClusterResponse(AIResponseBase):
    """Response for single definition meaning cluster generation."""

    cluster_id: str = Field(description="Semantic cluster identifier for this definition")
    cluster_description: str = Field(description="Human-readable cluster description")


# Anki Models


class AnkiFillBlankResponse(AIResponseBase):
    """Response for fill-in-the-blank flashcard generation."""

    sentence: str = Field(description="Sentence with _____ where the word belongs")
    choice_a: str = Field(description="First answer choice")
    choice_b: str = Field(description="Second answer choice")
    choice_c: str = Field(description="Third answer choice")
    choice_d: str = Field(description="Fourth answer choice")
    correct_choice: str = Field(description="Letter of correct answer (A, B, C, or D)")


class AnkiMultipleChoiceResponse(AIResponseBase):
    """Response for multiple choice flashcard generation."""

    choice_a: str = Field(description="First answer choice")
    choice_b: str = Field(description="Second answer choice")
    choice_c: str = Field(description="Third answer choice")
    choice_d: str = Field(description="Fourth answer choice")
    correct_choice: str = Field(description="Letter of correct answer (A, B, C, or D)")


class DeduplicatedDefinition(BaseModel):
    """A deduplicated definition with quality assessment."""

    part_of_speech: str = Field(description="Part of speech")
    definition: str = Field(description="The highest quality definition text")
    source_indices: list[int] = Field(description="Indices of merged definitions (0-based)")
    quality_score: float = Field(description="Quality score (0.0-1.0)")
    reasoning: str = Field(description="Brief explanation (max 10 words)")


class DeduplicationResponse(AIResponseBase):
    """Response from definition deduplication."""

    deduplicated_definitions: list[DeduplicatedDefinition] = Field(
        description="Deduplicated definitions preserving highest quality",
    )
    removed_count: int = Field(description="Number of duplicate definitions removed")


class WordOfTheDayResponse(AIResponseBase):
    """Response for Word of the Day generation."""

    word: str = Field(description="The selected word")
    definition: str = Field(description="Clear, concise definition")
    etymology: str = Field(description="Brief origin and historical development")
    example_usage: str = Field(description="Natural sentence demonstrating proper usage")
    fascinating_fact: str = Field(
        description="Interesting linguistic, cultural, or historical insight",
    )
    difficulty_level: str = Field(description="Difficulty level: intermediate or advanced")
    memorable_aspect: str = Field(description="What makes this word particularly worth learning")


class SyntheticWordEntry(BaseModel):
    """AI-generated word entry for training data."""

    word: str = Field(description="The generated word")
    definition: str = Field(description="Word definition")
    part_of_speech: str = Field(description="Grammatical category")
    etymology: str = Field(description="Word origin and development")
    example_sentence: str = Field(description="Natural usage example")
    semantic_justification: str = Field(description="Why this word fits the requested category")
    difficulty_level: str = Field(description="Assessed difficulty level")


class SyntheticCorpusResponse(AIResponseBase):
    """Response from synthetic corpus generation."""

    generated_words: list[SyntheticWordEntry] = Field(description="Generated word entries")
    total_generated: int = Field(description="Number of words successfully generated")
    quality_score: float = Field(ge=0.0, le=1.0, description="Overall quality assessment")


# Rebuild models with forward references
SynthesisResponse.model_rebuild()
EnhancedDefinitionResponse.model_rebuild()
