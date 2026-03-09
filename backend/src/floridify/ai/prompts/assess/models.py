"""Assessment response models — colocated with assessment prompt templates."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ....models.base import AIResponseBase


class CEFRLevelResponse(AIResponseBase):
    """Response for CEFR level assessment."""

    level: str = Field(description="CEFR level (A1-C2)")
    reasoning: str = Field(description="Explanation for the level assignment")


class FrequencyBandResponse(AIResponseBase):
    """Response for frequency band assessment."""

    band: int = Field(ge=1, le=5, description="Frequency band: 1 (most common) to 5 (least common)")
    reasoning: str = Field(description="Explanation for assessment")


class RegisterClassificationResponse(AIResponseBase):
    """Response for register classification."""

    model_config = ConfigDict(populate_by_field_name=True)

    language_register: str = Field(
        alias="register",
        description="Register level: formal, informal, neutral, slang, technical",
    )
    reasoning: str = Field(description="Explanation for classification")


class DomainIdentificationResponse(AIResponseBase):
    """Response for domain identification."""

    domain: str | None = Field(None, description="Domain/field: medical, legal, computing, etc.")
    reasoning: str = Field(description="Explanation for identification")


class GrammarPatternResponse(AIResponseBase):
    """Response for grammar pattern extraction."""

    patterns: list[str] = Field(
        max_length=10,
        description="Common grammatical constructions (e.g., [Tn], sb/sth)",
    )
    descriptions: list[str] = Field(
        max_length=10,
        description="Human-readable descriptions of patterns",
    )


class Collocation(BaseModel):
    """A single collocation entry."""

    type: str = Field(description="Type of collocation (e.g., verb+noun, adjective+noun)")
    phrase: str = Field(description="The collocation phrase")
    frequency: float = Field(ge=0.0, le=1.0, description="Frequency score")


class CollocationResponse(AIResponseBase):
    """Response for collocation generation."""

    collocations: list[Collocation] = Field(
        max_length=10,
        description="Common word combinations with type and frequency",
    )


class RegionalVariantResponse(AIResponseBase):
    """Response for regional variant detection."""

    regions: list[str] = Field(
        max_length=10,
        description="Regions where this usage is common (US, UK, AU, etc.)",
    )


class UsageNote(BaseModel):
    """A single usage note."""

    type: str = Field(description="Type of usage note (e.g., register, formality, context)")
    text: str = Field(description="The usage guidance text")


class UsageNoteResponse(AIResponseBase):
    """Response for usage note generation."""

    notes: list[UsageNote] = Field(
        max_length=5,
        description="Usage guidance with type and text",
    )
