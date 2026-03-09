"""Generation response models — colocated with generation prompt templates."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ....models.base import AIResponseBase


class ExampleGenerationResponse(AIResponseBase):
    """Response from example generation."""

    example_sentences: list[str] = Field(
        max_length=5,
        description="List of high-quality example sentences.",
    )


class FactGenerationResponse(AIResponseBase):
    """Response from AI fact generation about a word."""

    facts: list[str] = Field(
        max_length=5,
        description="List of interesting, educational facts about the word",
    )
    categories: list[str] = Field(
        max_length=5,
        description="Categories of facts generated (etymology, usage, cultural, etc.)",
    )


class WordForm(BaseModel):
    """A single word form."""

    type: str = Field(description="Type of form (e.g., plural, past_tense, gerund)")
    text: str = Field(description="The word form text")


class WordFormResponse(AIResponseBase):
    """Response for word form generation."""

    forms: list[WordForm] = Field(description="List of word forms with type and text")


class ExampleSynthesisResponse(AIResponseBase):
    """Response for example sentence synthesis."""

    examples: list[str] = Field(description="List of natural, contextual example sentences")
