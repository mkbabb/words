"""Repository for Word model operations."""

from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from beanie.operators import RegEx
from pydantic import BaseModel, Field

from ...constants import Language
from ...models import Word
from ..core.base import BaseRepository


class WordCreate(BaseModel):
    """Schema for creating a word."""

    text: str = Field(..., min_length=1, max_length=100)
    language: Language = Language.ENGLISH
    homograph_number: int | None = None
    offensive_flag: bool = False
    first_known_use: str | None = None


class WordUpdate(BaseModel):
    """Schema for updating a word."""

    text: str | None = Field(None, min_length=1, max_length=100)
    language: Language | None = None
    homograph_number: int | None = None
    offensive_flag: bool | None = None
    first_known_use: str | None = None


class WordFilter(BaseModel):
    """Filter parameters for word queries."""

    text: str | None = None
    text_pattern: str | None = None
    language: Language | None = None
    offensive_flag: bool | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None

    def to_query(self) -> dict[str, Any]:
        """Convert to MongoDB query."""
        query: dict[str, Any] = {}

        if self.text:
            query["text"] = self.text
        elif self.text_pattern:
            query["text"] = RegEx(self.text_pattern, "i")

        if self.language:
            query["language"] = self.language.value  # Use enum value

        if self.offensive_flag is not None:
            query["offensive_flag"] = self.offensive_flag

        if self.created_after or self.created_before:
            created_query: dict[str, datetime] = {}
            if self.created_after:
                created_query["$gte"] = self.created_after
            if self.created_before:
                created_query["$lte"] = self.created_before
            query["created_at"] = created_query

        return query


class WordRepository(BaseRepository[Word, WordCreate, WordUpdate]):
    """Repository for Word CRUD operations."""

    def __init__(self) -> None:
        super().__init__(Word)

    async def find_by_text(self, text: str, language: Language = Language.ENGLISH) -> Word | None:
        """Find word by text and language."""
        return await Word.find_one({"text": text, "language": language})

    async def find_by_normalized(
        self, normalized: str, language: Language = Language.ENGLISH
    ) -> list[Word]:
        """Find words by normalized form."""
        return await Word.find({"normalized": normalized, "language": language.value}).to_list()

    async def search(
        self, query: str, language: Language | None = None, limit: int = 10
    ) -> list[Word]:
        """Search words by text pattern."""
        filter_dict: dict[str, Any] = {"text": RegEx(f"^{query}", "i")}
        if language:
            filter_dict["language"] = language.value

        return await Word.find(filter_dict).limit(limit).to_list()

    async def _cascade_delete(self, word: Word) -> None:
        """Delete related documents when deleting a word."""
        from ...models import (
            Definition,
            Example,
            Fact,
            Pronunciation,
            ProviderData,
            SynthesizedDictionaryEntry,
        )

        # Delete all related documents
        await Definition.find({"word_id": str(word.id)}).delete()
        await Example.find({"word_id": str(word.id)}).delete()
        await Fact.find({"word_id": str(word.id)}).delete()
        await Pronunciation.find({"word_id": str(word.id)}).delete()
        await ProviderData.find({"word_id": str(word.id)}).delete()
        await SynthesizedDictionaryEntry.find({"word_id": str(word.id)}).delete()

    async def get_with_counts(self, id: PydanticObjectId) -> dict[str, Any]:
        """Get word with related document counts."""
        from ...models import Definition, Example, Fact

        word = await self.get(id, raise_on_missing=True)
        if word is None:
            raise ValueError(f"Word with id {id} not found")
        word_dict = word.model_dump()

        # Add counts
        word_dict["counts"] = {
            "definitions": await Definition.find({"word_id": str(id)}).count(),
            "examples": await Example.find({"word_id": str(id)}).count(),
            "facts": await Fact.find({"word_id": str(id)}).count(),
        }

        return word_dict
