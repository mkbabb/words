"""Typed models for golden fixture data.

Mirrors the relevant fields from the production models (Definition, Etymology, etc.)
but as plain Pydantic models without Beanie Document behavior. Used for strict
type-safe quality validation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FixtureExample(BaseModel):
    """Example sentence from a definition."""

    text: str
    type: Literal["generated", "literature"]


class FixtureMeaningCluster(BaseModel):
    """Meaning cluster assignment for a definition."""

    id: str
    name: str
    description: str
    order: int = 0
    relevance: float = 1.0


class FixtureDefinition(BaseModel):
    """Definition with all synthesis fields."""

    part_of_speech: str
    text: str
    meaning_cluster: FixtureMeaningCluster | None = None
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    examples: list[FixtureExample] = Field(default_factory=list)
    cefr_level: Literal["A1", "A2", "B1", "B2", "C1", "C2"] | None = None
    frequency_band: int | None = Field(default=None, ge=1, le=5)
    language_register: Literal["formal", "informal", "neutral", "slang", "technical"] | None = None
    domain: str | None = None
    providers: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class FixturePronunciation(BaseModel):
    """Pronunciation data."""

    phonetic: str = ""
    ipa: str | None = None

    model_config = {"extra": "allow"}


class FixtureEtymology(BaseModel):
    """Etymology data."""

    text: str
    origin_language: str | None = None
    root_words: list[str] = Field(default_factory=list)
    first_known_use: str | None = None

    model_config = {"extra": "allow"}


class GoldenFixture(BaseModel):
    """Top-level golden fixture model."""

    word: str
    language: str
    definitions: list[FixtureDefinition]
    pronunciation: FixturePronunciation | None = None
    etymology: FixtureEtymology | None = None
    facts: list[str] | None = None
