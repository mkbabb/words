"""Base classes and utilities for API operations."""

from __future__ import annotations

import builtins
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar

from beanie import Document, PydanticObjectId
from beanie.odm.enums import SortDirection
from beanie.operators import In
from fastapi import Request, Response
from pydantic import BaseModel, ConfigDict, Field
from pydantic.generics import GenericModel

from .exceptions import ErrorResponse, NotFoundException, VersionConflictException
from .protocols import (
    HasId,
    TypedFieldUpdater,
    VersionedDocument,
    format_datetime,
    serialize_for_response,
)


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
        direction = (
            SortDirection.ASCENDING if self.sort_order == "asc" else SortDirection.DESCENDING
        )
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
        if self.exclude:
            return {k: v for k, v in data.items() if k not in self.exclude}
        return data


T = TypeVar("T", bound=Document)
CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)
ListT = TypeVar("ListT")


class ListResponse(GenericModel, Generic[ListT]):  # noqa: UP046
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


class BaseRepository(ABC, Generic[T, CreateSchema, UpdateSchema]):  # noqa: UP046
    """Base repository for CRUD operations."""

    def __init__(self, model: type[T]):
        self.model = model

    async def get(self, id: PydanticObjectId, raise_on_missing: bool = True) -> T | None:
        """Get a single document by ID."""
        doc = await self.model.get(id)
        if not doc and raise_on_missing:
            raise NotFoundException(
                resource=self.model.__name__,
                identifier=str(id),
            )
        return doc

    # Placeholder for duplicate methods - real implementations below

    async def create(self, data: CreateSchema) -> T:
        """Create a new document."""
        doc = self.model(**data.model_dump())
        await doc.create()
        return doc

    async def update(
        self,
        id: PydanticObjectId,
        data: UpdateSchema,
        version: int | None = None,
    ) -> T:
        """Update a document with optional optimistic locking."""
        doc = await self.get(id, raise_on_missing=True)
        if doc is None:
            raise NotFoundException(
                resource=self.model.__name__,
                identifier=str(id),
            )

        # Check version for optimistic locking
        if version is not None and isinstance(doc, VersionedDocument):
            if doc.version != version:
                raise VersionConflictException(
                    expected=version,
                    actual=doc.version,
                    resource=self.model.__name__,
                )

        # Update fields with type-safe field updater
        update_data = data.model_dump(exclude_unset=True)
        TypedFieldUpdater.update_fields(doc, update_data)

        # Increment version if applicable
        if isinstance(doc, VersionedDocument):
            doc.version += 1

        await doc.save()
        return doc

    async def delete(self, id: PydanticObjectId, cascade: bool = False) -> bool:
        """Delete a document, optionally with cascade."""
        doc = await self.get(id, raise_on_missing=True)
        if doc is None:
            raise NotFoundException(
                resource=self.model.__name__,
                identifier=str(id),
            )

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
        self,
        updates: builtins.list[tuple[PydanticObjectId, UpdateSchema]],
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
        self,
        filter_dict: dict[str, Any] | None = None,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> tuple[list[T], int]:
        """List documents with filtering, pagination, and sorting."""
        filter_dict = filter_dict or {}
        pagination = pagination or PaginationParams(offset=0, limit=20)

        # Build query
        query = self.model.find(filter_dict)

        # Apply sorting
        if sort and sort.sort_by:
            sort_direction = (
                SortDirection.ASCENDING if sort.sort_order == "asc" else SortDirection.DESCENDING
            )
            query = query.sort([(sort.sort_by, sort_direction)])

        # Get total count
        total = await query.count()

        # Apply pagination
        documents = await query.skip(pagination.offset).limit(pagination.limit).to_list()

        return documents, total

    @abstractmethod
    async def _cascade_delete(self, doc: T) -> None:
        """Handle cascade deletion of related documents."""


def get_etag(data: Any) -> str:
    """Generate ETag for response data."""
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(content.encode()).hexdigest()


def check_etag(request: Request, etag: str) -> bool:
    """Check if client ETag matches."""
    client_etag = request.headers.get("If-None-Match")
    return client_etag == etag


# Response building utilities
class ResponseBuilder:
    """Utility class for building consistent API responses."""

    @staticmethod
    def build_resource_response(
        data: Any,
        resource_type: str,
        resource_id: str | None = None,
        version: int | None = None,
        updated_at: datetime | None = None,
        additional_links: dict[str, str] | None = None,
        additional_metadata: dict[str, Any] | None = None,
    ) -> ResourceResponse:
        """Build a standardized resource response."""
        # Extract ID if not provided
        if resource_id is None:
            if isinstance(data, HasId):
                resource_id = str(data.id)
            elif isinstance(data, dict) and "id" in data:
                resource_id = str(data["id"])

        # Build links
        links = {
            "self": f"/{resource_type}s/{resource_id}" if resource_id else f"/{resource_type}s",
        }
        if additional_links:
            links.update(additional_links)

        # Build metadata
        metadata: dict[str, Any] = {}
        if version is not None:
            metadata["version"] = version
        if updated_at is not None:
            metadata["last_modified"] = format_datetime(updated_at)
        if additional_metadata:
            metadata.update(additional_metadata)

        # Convert data to dict if it's a Pydantic model
        response_data = serialize_for_response(data)

        return ResourceResponse(
            data=response_data,
            metadata=metadata if metadata else None,
            links=links,
        )

    @staticmethod
    def build_list_response(
        items: list[Any],
        total: int,
        pagination: PaginationParams,
        resource_type: str | None = None,
        additional_metadata: dict[str, Any] | None = None,
    ) -> ListResponse[dict[str, Any]]:
        """Build a standardized list response."""
        # Convert items to dicts if they're Pydantic models
        serialized_items = [serialize_for_response(item) for item in items]

        response: ListResponse[dict[str, Any]] = ListResponse(
            items=serialized_items,
            total=total,
            offset=pagination.offset,
            limit=pagination.limit,
        )

        # Add resource type to metadata if provided
        if resource_type and additional_metadata:
            additional_metadata["resource_type"] = resource_type
        elif resource_type:
            additional_metadata = {"resource_type": resource_type}

        return response

    @staticmethod
    def apply_etag(
        response: Response,
        data: Any,
        request: Request,
    ) -> bool:
        """Apply ETag to response and check for Not Modified.

        Returns:
            True if the client has the latest version (304 Not Modified should be sent)
            False if the response should be sent normally

        """
        etag = get_etag(data)
        response.headers["ETag"] = etag

        return check_etag(request, etag)


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
