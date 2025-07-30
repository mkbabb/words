"""Repository for audio operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from beanie import PydanticObjectId
from beanie.odm.enums import SortDirection
from pydantic import BaseModel, Field

from ...models import AudioMedia
from ..core import BaseRepository, PaginationParams, SortParams


class AudioFilter(BaseModel):
    """Filter parameters for audio queries."""
    
    format: str | None = Field(None, description="Audio format (mp3, wav, ogg)")
    accent: str | None = Field(None, description="Accent (us, uk, au)")
    quality: Literal["low", "standard", "high"] | None = Field(None, description="Audio quality")
    min_duration_ms: int | None = Field(None, description="Minimum duration in milliseconds")
    max_duration_ms: int | None = Field(None, description="Maximum duration in milliseconds")
    created_after: datetime | None = Field(None, description="Created after date")
    created_before: datetime | None = Field(None, description="Created before date")
    
    def to_query(self) -> dict[str, Any]:
        """Convert to MongoDB query."""
        query: dict[str, Any] = {}
        
        if self.format:
            query["format"] = self.format
        if self.accent:
            query["accent"] = self.accent
        if self.quality:
            query["quality"] = self.quality
        if self.min_duration_ms:
            query["duration_ms"] = {"$gte": self.min_duration_ms}
        if self.max_duration_ms:
            query.setdefault("duration_ms", {})["$lte"] = self.max_duration_ms
        if self.created_after:
            query["created_at"] = {"$gte": self.created_after}
        if self.created_before:
            query.setdefault("created_at", {})["$lte"] = self.created_before
            
        return query


class AudioCreate(BaseModel):
    """Schema for creating audio."""
    
    url: str = Field(..., description="Audio file URL or path")
    format: str = Field(..., description="Audio format (mp3, wav, ogg)")
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    duration_ms: int = Field(..., gt=0, description="Duration in milliseconds")
    accent: str | None = Field(None, description="Accent (us, uk, au)")
    quality: Literal["low", "standard", "high"] = Field("standard", description="Audio quality")


class AudioUpdate(BaseModel):
    """Schema for updating audio metadata."""
    
    accent: str | None = Field(None, description="Accent (us, uk, au)")
    quality: Literal["low", "standard", "high"] | None = Field(None, description="Audio quality")


class AudioRepository(BaseRepository[AudioMedia, AudioCreate, AudioUpdate]):
    """Repository for audio operations."""
    
    model = AudioMedia
    
    async def list(
        self,
        filter_dict: dict[str, Any] | None = None,
        pagination: PaginationParams | None = None,
        sort: SortParams | None = None,
    ) -> tuple[list[AudioMedia], int]:
        """List audio files with filtering and pagination."""
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
    
    async def create(self, data: AudioCreate) -> AudioMedia:
        """Create new audio entry."""
        audio = AudioMedia(
            url=data.url,
            format=data.format,
            size_bytes=data.size_bytes,
            duration_ms=data.duration_ms,
            accent=data.accent,
            quality=data.quality,
        )
        await audio.save()
        return audio
    
    async def update(
        self,
        item_id: PydanticObjectId,
        data: AudioUpdate,
        version: int | None = None,
    ) -> AudioMedia:
        """Update audio metadata."""
        audio = await self.get(item_id, raise_on_missing=True)
        assert audio is not None
        
        # Version check
        if version is not None and audio.version != version:
            raise ValueError(f"Version mismatch: expected {version}, got {audio.version}")
        
        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(audio, field, value)
        
        audio.version += 1
        await audio.save()
        
        return audio
    
    async def delete(self, item_id: PydanticObjectId, cascade: bool = False) -> None:
        """Delete audio entry."""
        audio = await self.get(item_id, raise_on_missing=True)
        assert audio is not None
        
        # Note: cascade not applicable for audio, but keeping for consistency
        await audio.delete()
    
    async def get_by_format(self, format: str) -> list[AudioMedia]:
        """Get all audio files by format."""
        return await self.model.find(AudioMedia.format == format).to_list()
    
    async def get_by_accent(self, accent: str) -> list[AudioMedia]:
        """Get all audio files by accent."""
        return await self.model.find(AudioMedia.accent == accent).to_list()