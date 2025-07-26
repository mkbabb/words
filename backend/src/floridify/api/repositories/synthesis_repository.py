"""Repository for SynthesizedDictionaryEntry model operations."""

from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from ...models import Etymology, ModelInfo, SynthesizedDictionaryEntry
from ..core.base import BaseRepository


class SynthesisCreate(BaseModel):
    """Schema for creating a synthesized entry."""

    word_id: str
    pronunciation_id: str | None = None
    definition_ids: list[str] = Field(default_factory=list)
    etymology: Etymology | None = None
    fact_ids: list[str] = Field(default_factory=list)
    model_info: ModelInfo
    source_provider_data_ids: list[str] = Field(default_factory=list)


class SynthesisUpdate(BaseModel):
    """Schema for updating a synthesized entry."""

    pronunciation_id: str | None = None
    definition_ids: list[str] | None = None
    etymology: Etymology | None = None
    fact_ids: list[str] | None = None
    model_info: ModelInfo | None = None


class SynthesisFilter(BaseModel):
    """Filter parameters for synthesis queries."""

    word_id: str | None = None
    has_pronunciation: bool | None = None
    has_etymology: bool | None = None
    has_facts: bool | None = None
    accessed_after: datetime | None = None
    min_access_count: int | None = None

    def to_query(self) -> dict[str, Any]:
        """Convert to MongoDB query."""
        query: dict[str, Any] = {}

        if self.word_id:
            query["word_id"] = self.word_id

        if self.has_pronunciation is not None:
            if self.has_pronunciation:
                query["pronunciation_id"] = {"$ne": None}
            else:
                query["pronunciation_id"] = None

        if self.has_etymology is not None:
            if self.has_etymology:
                query["etymology"] = {"$ne": None}
            else:
                query["etymology"] = None

        if self.has_facts is not None:
            if self.has_facts:
                query["fact_ids"] = {"$ne": []}
            else:
                query["fact_ids"] = []

        if self.accessed_after:
            query["accessed_at"] = {"$gte": self.accessed_after}

        if self.min_access_count is not None:
            query["access_count"] = {"$gte": self.min_access_count}

        return query


class ComponentStatus(BaseModel):
    """Status of synthesized entry components."""

    word_id: str
    has_pronunciation: bool
    has_etymology: bool
    has_facts: bool
    definition_count: int
    fact_count: int
    completeness_score: float
    last_updated: datetime | None
    model_version: str | None


class SynthesisRepository(
    BaseRepository[SynthesizedDictionaryEntry, SynthesisCreate, SynthesisUpdate]
):
    """Repository for SynthesizedDictionaryEntry CRUD operations."""

    def __init__(self) -> None:
        super().__init__(SynthesizedDictionaryEntry)

    async def find_by_word(self, word_id: str) -> SynthesizedDictionaryEntry | None:
        """Find synthesized entry for a word."""
        return await SynthesizedDictionaryEntry.find_one({"word_id": word_id})

    async def get_component_status(self, entry_id: PydanticObjectId) -> ComponentStatus:
        """Get detailed component status for an entry."""
        entry = await self.get(entry_id, raise_on_missing=True)
        if entry is None:
            raise ValueError(f"Entry with id {entry_id} not found")

        # Calculate completeness
        components = [
            entry.pronunciation_id is not None,
            entry.etymology is not None,
            bool(entry.fact_ids),
            bool(entry.definition_ids),
        ]
        completeness = sum(components) / len(components)

        return ComponentStatus(
            word_id=entry.word_id,
            has_pronunciation=entry.pronunciation_id is not None,
            has_etymology=entry.etymology is not None,
            has_facts=bool(entry.fact_ids),
            definition_count=len(entry.definition_ids),
            fact_count=len(entry.fact_ids),
            completeness_score=completeness,
            last_updated=entry.updated_at,
            model_version=getattr(entry.model_info, 'model', None) if entry.model_info else None,
        )

    async def find_incomplete(self, limit: int = 100) -> list[SynthesizedDictionaryEntry]:
        """Find entries missing components."""
        return (
            await SynthesizedDictionaryEntry.find(
                {
                    "$or": [
                        {"pronunciation_id": None},
                        {"etymology": None},
                        {"fact_ids": []},
                        {"definition_ids": []},
                    ]
                }
            )
            .limit(limit)
            .to_list()
        )

    async def update_access_info(self, entry_id: PydanticObjectId) -> None:
        """Update access timestamp and count."""
        entry = await self.get(entry_id, raise_on_missing=True)
        if entry is None:
            raise ValueError(f"Entry with id {entry_id} not found")
        entry.accessed_at = datetime.utcnow()
        entry.access_count += 1
        await entry.save()

    async def _cascade_delete(self, entry: SynthesizedDictionaryEntry) -> None:
        """Delete is handled at word level, no cascade needed here."""
        pass
