"""Repository for Example model operations."""

from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from ...models import Example, LiteratureSource
from ..core.base import BaseRepository


class ExampleCreate(BaseModel):
    """Schema for creating an example."""

    word_id: str
    definition_id: str
    text: str = Field(..., min_length=1)
    translation: str | None = None
    literature_source: LiteratureSource | None = None
    is_ai_generated: bool = True
    can_regenerate: bool = True
    quality_score: float | None = Field(None, ge=0, le=1)


class ExampleUpdate(BaseModel):
    """Schema for updating an example."""

    text: str | None = Field(None, min_length=1)
    translation: str | None = None
    literature_source: LiteratureSource | None = None
    quality_score: float | None = Field(None, ge=0, le=1)


class ExampleFilter(BaseModel):
    """Filter parameters for example queries."""

    word_id: str | None = None
    definition_id: str | None = None
    is_ai_generated: bool | None = None
    can_regenerate: bool | None = None
    has_literature_source: bool | None = None
    quality_score_min: float | None = None

    def to_query(self) -> dict[str, Any]:
        """Convert to MongoDB query."""
        query = {}

        if self.word_id:
            query["word_id"] = self.word_id

        if self.definition_id:
            query["definition_id"] = self.definition_id

        if self.is_ai_generated is not None:
            query["is_ai_generated"] = self.is_ai_generated

        if self.can_regenerate is not None:
            query["can_regenerate"] = self.can_regenerate

        if self.has_literature_source is not None:
            if self.has_literature_source:
                query["literature_source"] = {"$ne": None}
            else:
                query["literature_source"] = None

        if self.quality_score_min is not None:
            query["quality_score"] = {"$gte": self.quality_score_min}

        return query


class ExampleRepository(BaseRepository[Example, ExampleCreate, ExampleUpdate]):
    """Repository for Example CRUD operations."""

    def __init__(self):
        super().__init__(Example)

    async def find_by_definition(
        self, definition_id: str, limit: int | None = None
    ) -> list[Example]:
        """Find examples for a definition."""
        query = Example.find({"definition_id": definition_id})
        if limit:
            query = query.limit(limit)
        return await query.to_list()

    async def find_by_word(self, word_id: str, limit: int | None = None) -> list[Example]:
        """Find all examples for a word."""
        query = Example.find({"word_id": word_id})
        if limit:
            query = query.limit(limit)
        return await query.to_list()

    async def find_regeneratable(self, definition_id: str | None = None) -> list[Example]:
        """Find examples that can be regenerated."""
        query = {"can_regenerate": True}
        if definition_id:
            query["definition_id"] = definition_id

        return await Example.find(query).to_list()

    async def update_quality_scores(self, scores: list[tuple[PydanticObjectId, float]]) -> int:
        """Batch update quality scores."""
        updated = 0
        for example_id, score in scores:
            example = await self.get(example_id, raise_on_missing=False)
            if example:
                example.quality_score = score
                await example.save()
                updated += 1
        return updated

    async def _cascade_delete(self, example: Example) -> None:
        """No cascade needed for examples."""
        pass
