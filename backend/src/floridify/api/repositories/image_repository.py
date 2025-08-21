"""Repository for image operations."""

from __future__ import annotations

import builtins
from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from beanie.odm.enums import SortDirection
from pydantic import BaseModel, Field

from ...models.base import ImageMedia
from ..core import BaseRepository, PaginationParams, SortParams


class ImageFilter(BaseModel):
    """Filter parameters for image queries."""

    format: str | None = Field(None, description="Image format (png, jpg, webp)")
    min_width: int | None = Field(None, description="Minimum width in pixels")
    max_width: int | None = Field(None, description="Maximum width in pixels")
    min_height: int | None = Field(None, description="Minimum height in pixels")
    max_height: int | None = Field(None, description="Maximum height in pixels")
    has_alt_text: bool | None = Field(None, description="Has alt text")
    created_after: datetime | None = Field(None, description="Created after date")
    created_before: datetime | None = Field(None, description="Created before date")

    def to_query(self) -> dict[str, Any]:
        """Convert to MongoDB query."""
        query: dict[str, Any] = {}

        if self.format:
            query["format"] = self.format
        if self.min_width:
            query["width"] = {"$gte": self.min_width}
        if self.max_width:
            query.setdefault("width", {})["$lte"] = self.max_width
        if self.min_height:
            query["height"] = {"$gte": self.min_height}
        if self.max_height:
            query.setdefault("height", {})["$lte"] = self.max_height
        if self.has_alt_text is not None:
            if self.has_alt_text:
                query["alt_text"] = {"$ne": None}
            else:
                query["alt_text"] = None
        if self.created_after:
            query["created_at"] = {"$gte": self.created_after}
        if self.created_before:
            query.setdefault("created_at", {})["$lte"] = self.created_before

        return query


class ImageCreate(BaseModel):
    """Schema for creating an image."""

    data: bytes = Field(..., description="Binary image data")
    format: str = Field(..., description="Image format")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    width: int = Field(..., gt=0, description="Width in pixels")
    height: int = Field(..., gt=0, description="Height in pixels")
    alt_text: str | None = Field(None, description="Alternative text")
    description: str | None = Field(None, description="Image description")
    url: str | None = Field(None, description="External URL if applicable")


class ImageUpdate(BaseModel):
    """Schema for updating image metadata."""

    alt_text: str | None = Field(None, description="Alternative text")
    description: str | None = Field(None, description="Image description")
    url: str | None = Field(None, description="External URL")


class ImageRepository(BaseRepository[ImageMedia, ImageCreate, ImageUpdate]):
    """Repository for image operations."""

    def __init__(self) -> None:
        """Initialize image repository."""
        super().__init__(ImageMedia)

    async def list(
        self,
        filter_dict: dict[str, Any] | None = None,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> tuple[builtins.list[ImageMedia], int]:
        """List images with filtering and pagination."""
        query = self.model.find(filter_dict or {})

        # Get total count
        total = await query.count()

        # Apply sorting
        if sort and sort.sort_by:
            sort_criteria = sort.get_sort_criteria()
            if sort_criteria:
                for field, direction in sort_criteria:
                    query = query.sort((field, direction))
        else:
            # Default sort by created_at desc
            query = query.sort(("created_at", SortDirection.DESCENDING))

        # Apply pagination
        if pagination:
            query = query.skip(pagination.skip).limit(pagination.limit)

        items = await query.to_list()
        return items, total

    async def create(self, data: ImageCreate) -> ImageMedia:
        """Create new image."""
        image = ImageMedia(
            data=data.data,
            format=data.format,
            size_bytes=data.size_bytes,
            width=data.width,
            height=data.height,
            alt_text=data.alt_text,
            description=data.description,
            url=data.url,
        )
        await image.save()
        return image

    async def update(
        self,
        item_id: PydanticObjectId,
        data: ImageUpdate,
        version: int | None = None,
    ) -> ImageMedia:
        """Update image metadata."""
        image = await self.get(item_id, raise_on_missing=True)
        assert image is not None

        # Version check
        if version is not None and image.version != version:
            raise ValueError(f"Version mismatch: expected {version}, got {image.version}")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(image, field, value)

        image.version += 1
        await image.save()

        return image

    async def delete(self, item_id: PydanticObjectId, cascade: bool = True) -> bool:
        """Delete image with automatic reference cleanup."""
        doc = await self.get(item_id, raise_on_missing=True)
        assert doc is not None

        if cascade:
            from ..services.cleanup_service import CleanupService

            await CleanupService.cleanup_image_references(item_id)

        # Use Beanie's basic delete method
        await doc.delete()
        return True

    async def get_by_format(self, format: str) -> builtins.list[ImageMedia]:
        """Get all images by format."""
        return await self.model.find(ImageMedia.format == format).to_list()

    async def get_orphaned_images(self) -> builtins.list[ImageMedia]:
        """Get images not referenced by any definitions."""
        # This would require checking against Definition.image_ids
        # For now, return empty list - can be implemented later
        return []

    async def _cascade_delete(self, doc: ImageMedia) -> None:
        """Handle cascade deletion - implemented via CleanupService in delete method."""
        # This method is required by BaseRepository but we handle cascading
        # in the delete method using CleanupService for better separation of concerns
