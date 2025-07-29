"""Base classes and utilities for API operations."""

from __future__ import annotations

import builtins
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from typing import Any, Generic, TypeVar

from beanie import Document, PydanticObjectId
from beanie.odm.enums import SortDirection
from beanie.operators import In
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T", bound=Document)
CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)
ResponseT = TypeVar("ResponseT")
ListT = TypeVar("ListT")  # Generic type for list responses


class ErrorDetail(BaseModel):
    """Standard error detail."""

    field: str | None = None
    message: str
    code: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    details: list[ErrorDetail] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str | None = None


class PaginationParams(BaseModel):
    """Pagination parameters."""

    offset: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(20, ge=1, le=100, description="Number of items to return")

    @property
    def skip(self) -> int:
        return self.offset


class SortParams(BaseModel):
    """Sorting parameters."""

    sort_by: str | None = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")

    def get_sort_criteria(self) -> list[tuple[str, SortDirection]] | None:
        if not self.sort_by:
            return None
        direction = SortDirection.ASCENDING if self.sort_order == "asc" else SortDirection.DESCENDING
        return [(self.sort_by, direction)]


class FieldSelection(BaseModel):
    """Field selection parameters."""

    include: set[str] | None = Field(None, description="Fields to include")
    exclude: set[str] | None = Field(None, description="Fields to exclude")
    expand: set[str] | None = Field(None, description="Related resources to expand")

    def apply_to_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply field selection to a dictionary."""
        if self.include:
            return {k: v for k, v in data.items() if k in self.include}
        elif self.exclude:
            return {k: v for k, v in data.items() if k not in self.exclude}
        return data


class ListResponse(BaseModel, Generic[ListT]):
    """Standard list response with pagination metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[ListT]
    total: int
    offset: int
    limit: int
    has_more: bool = Field(default=False)

    def __init__(self, **data: Any) -> None:
        data["has_more"] = data["offset"] + len(data["items"]) < data["total"]
        super().__init__(**data)


class ResourceResponse(BaseModel):
    """Standard resource response wrapper."""

    data: Any
    metadata: dict[str, Any] | None = None
    links: dict[str, str] | None = None


class BatchRequest(BaseModel):
    """Batch operation request."""

    operations: list[dict[str, Any]]
    parallel: bool = Field(True, description="Execute operations in parallel")
    stop_on_error: bool = Field(False, description="Stop on first error")


class BatchResponse(BaseModel):
    """Batch operation response."""

    results: list[dict[str, Any]]
    errors: list[ErrorResponse | None]
    successful: int
    failed: int


class BaseRepository(ABC, Generic[T, CreateSchema, UpdateSchema]):
    """Base repository for CRUD operations."""

    def __init__(self, model: type[T]):
        self.model = model

    async def get(self, id: PydanticObjectId, raise_on_missing: bool = True) -> T | None:
        """Get a single document by ID."""
        doc = await self.model.get(id)
        if not doc and raise_on_missing:
            raise HTTPException(404, f"{self.model.__name__} not found")
        return doc

    # Placeholder for duplicate methods - real implementations below

    async def create(self, data: CreateSchema) -> T:
        """Create a new document."""
        doc = self.model(**data.model_dump())
        await doc.create()
        return doc

    async def update(
        self, id: PydanticObjectId, data: UpdateSchema, version: int | None = None
    ) -> T:
        """Update a document with optional optimistic locking."""
        doc = await self.get(id, raise_on_missing=True)
        if doc is None:
            raise HTTPException(404, "Document not found")

        # Check version for optimistic locking
        if version is not None and hasattr(doc, "version"):
            if doc.version != version:
                raise HTTPException(409, "Version conflict")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(doc, field, value)

        # Increment version if applicable
        if hasattr(doc, "version"):
            doc.version += 1

        await doc.save()
        return doc

    async def delete(self, id: PydanticObjectId, cascade: bool = False) -> bool:
        """Delete a document, optionally with cascade."""
        doc = await self.get(id, raise_on_missing=True)
        if doc is None:
            raise HTTPException(404, "Document not found")

        if cascade:
            await self._cascade_delete(doc)

        await doc.delete()
        return True

    async def get_many(self, ids: builtins.list[PydanticObjectId | str]) -> builtins.list[T]:
        """Get multiple documents by IDs efficiently."""
        # Convert string IDs to ObjectId
        object_ids = [PydanticObjectId(id) if isinstance(id, str) else id for id in ids]

        # Fetch all documents in one query
        docs = await self.model.find(In(self.model.id, object_ids)).to_list()

        # Create a mapping for easy access
        doc_map = {str(doc.id): doc for doc in docs}

        # Return in the same order as requested (filter out None values)
        return [doc_map[str(id)] for id in ids if str(id) in doc_map]

    async def batch_create(self, items: builtins.list[CreateSchema]) -> builtins.list[T]:
        """Create multiple documents."""
        docs = [self.model(**item.model_dump()) for item in items]
        await self.model.insert_many(docs)
        return docs

    async def batch_update(
        self, updates: builtins.list[tuple[PydanticObjectId, UpdateSchema]]
    ) -> builtins.list[T]:
        """Update multiple documents."""
        results = []
        for id, data in updates:
            doc = await self.update(id, data)
            results.append(doc)
        return results

    async def batch_delete(self, ids: builtins.list[PydanticObjectId]) -> int:
        """Delete multiple documents."""
        result = await self.model.find(In(self.model.id, ids)).delete()
        return result.deleted_count if result else 0

    async def list(
        self, filter_dict: dict[str, Any] | None = None, 
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None
    ) -> tuple[list[T], int]:
        """List documents with filtering, pagination, and sorting."""
        filter_dict = filter_dict or {}
        pagination = pagination or PaginationParams(offset=0, limit=20)
        
        # Build query
        query = self.model.find(filter_dict)
        
        # Apply sorting
        if sort and sort.sort_by:
            sort_direction = SortDirection.ASCENDING if sort.sort_order == "asc" else SortDirection.DESCENDING
            query = query.sort([(sort.sort_by, sort_direction)])
        
        # Get total count
        total = await query.count()
        
        # Apply pagination
        documents = await query.skip(pagination.offset).limit(pagination.limit).to_list()
        
        return documents, total

    @abstractmethod
    async def _cascade_delete(self, doc: T) -> None:
        """Handle cascade deletion of related documents."""
        pass




def get_etag(data: Any) -> str:
    """Generate ETag for response data."""
    import hashlib
    import json

    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(content.encode()).hexdigest()


def check_etag(request: Request, etag: str) -> bool:
    """Check if client ETag matches."""
    client_etag = request.headers.get("If-None-Match")
    return client_etag == etag


# Dependency injection helpers for FastAPI
def get_pagination() -> PaginationParams:
    """Get pagination parameters from query params."""
    return PaginationParams(offset=0, limit=20)

def get_sort() -> SortParams:
    """Get sort parameters from query params."""
    return SortParams(sort_by=None, sort_order="asc")

def get_fields() -> FieldSelection:
    """Get field selection from query params."""
    return FieldSelection(include=None, exclude=None, expand=None)
