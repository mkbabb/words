"""Word-of-the-Day response models — colocated with WOTD prompt templates."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ....models.base import AIResponseBase


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
        default_factory=dict,
        description="Thematic word clusters",
    )


class LiteratureQualityMetrics(BaseModel):
    """Quality assessment metrics for literature corpus."""

    coverage_score: float = Field(ge=0.0, le=1.0, description="Coverage of author's vocabulary")
    distinctiveness_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Uniqueness compared to general English",
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
