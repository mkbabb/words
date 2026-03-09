"""Miscellaneous response models — colocated with misc prompt templates."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ....models.base import AIResponseBase


class CandidateRanking(BaseModel):
    """A single candidate's ranking in a tournament."""

    index: int = Field(ge=0, description="Index of the candidate being ranked")
    score: float = Field(ge=0.0, le=10.0, description="Quality score (0-10)")
    reasoning: str = Field(description="Brief explanation of the ranking")


class RankingResponse(AIResponseBase):
    """Response from candidate ranking in tournament selection."""

    rankings: list[CandidateRanking] = Field(
        description="Rankings for each candidate with scores and reasoning"
    )


class ClusterMapping(AIResponseBase):
    """A single cluster mapping entry."""

    cluster_slug: str = Field(
        description="Unique cluster slug (e.g., 'bank_financial') - always in the form {word}_{pos}_{meaning_cluster}.",
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
        max_length=10,
        description="List of cluster mappings with their descriptions and indices",
    )


class MeaningClusterResponse(AIResponseBase):
    """Response for single definition meaning cluster generation."""

    cluster_slug: str = Field(description="Semantic cluster slug for this definition")
    cluster_description: str = Field(description="Human-readable cluster description")


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
