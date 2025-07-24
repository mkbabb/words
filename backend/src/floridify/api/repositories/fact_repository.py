"""Repository for Fact model operations."""

from typing import Any

from pydantic import BaseModel, Field

from floridify.api.core.base import BaseRepository
from floridify.models.models import Fact


class FactCreate(BaseModel):
    """Schema for creating a fact."""
    
    word_id: str
    text: str = Field(..., min_length=1)
    category: str | None = Field(None, description="Fact category (etymology, cultural, etc.)")
    source: str | None = None
    confidence_score: float | None = Field(None, ge=0, le=1)


class FactUpdate(BaseModel):
    """Schema for updating a fact."""
    
    text: str | None = Field(None, min_length=1)
    category: str | None = None
    source: str | None = None
    confidence_score: float | None = Field(None, ge=0, le=1)


class FactFilter(BaseModel):
    """Filter parameters for fact queries."""
    
    word_id: str | None = None
    category: str | None = None
    has_source: bool | None = None
    confidence_score_min: float | None = None
    
    def to_query(self) -> dict[str, Any]:
        """Convert to MongoDB query."""
        query = {}
        
        if self.word_id:
            query["word_id"] = self.word_id
        
        if self.category:
            query["category"] = self.category
        
        if self.has_source is not None:
            if self.has_source:
                query["source"] = {"$ne": None}
            else:
                query["source"] = None
        
        if self.confidence_score_min is not None:
            query["confidence_score"] = {"$gte": self.confidence_score_min}
        
        return query


class FactRepository(BaseRepository[Fact, FactCreate, FactUpdate]):
    """Repository for Fact CRUD operations."""
    
    def __init__(self):
        super().__init__(Fact)
    
    async def find_by_word(
        self,
        word_id: str,
        category: str | None = None
    ) -> list[Fact]:
        """Find facts for a word."""
        query = {"word_id": word_id}
        if category:
            query["category"] = category
        
        return await Fact.find(query).to_list()
    
    async def find_by_category(
        self,
        category: str,
        limit: int = 100
    ) -> list[Fact]:
        """Find facts by category."""
        return await Fact.find({"category": category}).limit(limit).to_list()
    
    async def _cascade_delete(self, fact: Fact) -> None:
        """No cascade needed for facts."""
        pass