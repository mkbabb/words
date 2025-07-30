"""Audio API - Full CRUD operations for audio management."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ....models import AudioMedia
from ....utils.paths import get_project_root
from ...core import (
    ErrorDetail,
    ErrorResponse,
    ListResponse,
    PaginationParams,
    ResourceResponse,
    SortParams,
    get_pagination,
    get_sort,
)
from ...repositories import (
    AudioCreate,
    AudioFilter,
    AudioRepository,
    AudioUpdate,
)

router = APIRouter(prefix="/audio", tags=["audio"])


def get_audio_repo() -> AudioRepository:
    """Dependency to get audio repository."""
    return AudioRepository()


class AudioQueryParams(BaseModel):
    """Query parameters for listing audio files."""
    
    format: str | None = Field(None, description="Filter by format (mp3, wav, ogg)")
    accent: str | None = Field(None, description="Filter by accent (us, uk, au)")
    quality: Literal["low", "standard", "high"] | None = Field(None, description="Filter by quality")
    min_duration_ms: int | None = Field(None, description="Minimum duration in milliseconds")
    max_duration_ms: int | None = Field(None, description="Maximum duration in milliseconds")


@router.get("", response_model=ListResponse[dict[str, Any]])
async def list_audio_files(
    repo: AudioRepository = Depends(get_audio_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    params: AudioQueryParams = Depends(),
) -> ListResponse[dict[str, Any]]:
    """List audio files with filtering and pagination.
    
    Query Parameters:
        - format: Filter by audio format
        - accent: Filter by accent
        - quality: Filter by quality level
        - min/max_duration_ms: Duration range filter
        - Standard pagination params
    
    Returns:
        Paginated list of audio metadata.
    """
    # Build filter
    filter_params = AudioFilter(
        format=params.format,
        accent=params.accent,
        quality=params.quality,
        min_duration_ms=params.min_duration_ms,
        max_duration_ms=params.max_duration_ms,
    )
    
    # Get data
    audio_files, total = await repo.list(
        filter_dict=filter_params.to_query(),
        pagination=pagination,
        sort=sort,
    )
    
    # Convert to response format
    items = []
    for audio in audio_files:
        items.append({
            "id": str(audio.id),
            "url": audio.url,
            "format": audio.format,
            "size_bytes": audio.size_bytes,
            "duration_ms": audio.duration_ms,
            "accent": audio.accent,
            "quality": audio.quality,
            "content_url": f"/api/v1/audio/{audio.id}/content",
            "created_at": audio.created_at.isoformat() if audio.created_at else None,
        })
    
    return ListResponse(
        items=items,
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.post("", response_model=ResourceResponse, status_code=201)
async def upload_audio(
    file: UploadFile = File(...),
    accent: str | None = Query(None, description="Accent (us, uk, au)"),
    quality: Literal["low", "standard", "high"] = Query("standard", description="Audio quality"),
    repo: AudioRepository = Depends(get_audio_repo),
) -> ResourceResponse:
    """Upload a new audio file.
    
    Body:
        - file: Audio file (multipart/form-data)
    
    Query Parameters:
        - accent: Audio accent
        - quality: Audio quality level
    
    Returns:
        Created audio metadata with resource links.
    
    Errors:
        400: Invalid audio file
        413: File too large (max 50MB)
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(
            400,
            detail=ErrorResponse(
                error="Invalid file type",
                details=[
                    ErrorDetail(
                        field="file",
                        message=f"File must be audio, got {file.content_type}",
                        code="invalid_type",
                    )
                ],
            ).model_dump(),
        )
    
    # Read file data
    data = await file.read()
    
    # Check file size (max 50MB for audio)
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(
            413,
            detail=ErrorResponse(
                error="File too large",
                details=[
                    ErrorDetail(
                        field="file",
                        message="File size must be less than 50MB",
                        code="file_too_large",
                    )
                ],
            ).model_dump(),
        )
    
    # Save file to disk
    # Create audio cache directory if not exists
    cache_dir = get_project_root() / "data" / "audio_cache" / "uploads"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    import uuid
    file_ext = file.filename.split('.')[-1] if file.filename else 'mp3'
    filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = cache_dir / filename
    
    # Write file
    with open(file_path, 'wb') as f:
        f.write(data)
    
    # Get audio duration (simplified - in real app use audio library)
    # For now, estimate based on file size and format
    duration_ms = len(data) // 100  # Very rough estimate
    
    # Create audio entry
    audio_data = AudioCreate(
        url=str(file_path),
        format=file_ext,
        size_bytes=len(data),
        duration_ms=duration_ms,
        accent=accent,
        quality=quality,
    )
    
    audio = await repo.create(audio_data)
    
    return ResourceResponse(
        data={
            "id": str(audio.id),
            "url": audio.url,
            "format": audio.format,
            "size_bytes": audio.size_bytes,
            "duration_ms": audio.duration_ms,
            "accent": audio.accent,
            "quality": audio.quality,
            "content_url": f"/api/v1/audio/{audio.id}/content",
        },
        links={
            "self": f"/audio/{audio.id}",
            "content": f"/audio/{audio.id}/content",
        },
    )


@router.get("/{audio_id}", response_model=ResourceResponse)
async def get_audio_metadata(
    audio_id: PydanticObjectId,
    repo: AudioRepository = Depends(get_audio_repo),
) -> ResourceResponse:
    """Get audio metadata.
    
    Path Parameters:
        - audio_id: ID of the audio file
    
    Returns:
        Audio metadata with resource links.
    
    Errors:
        404: Audio not found
    """
    audio = await repo.get(audio_id, raise_on_missing=True)
    assert audio is not None
    
    return ResourceResponse(
        data={
            "id": str(audio.id),
            "url": audio.url,
            "format": audio.format,
            "size_bytes": audio.size_bytes,
            "duration_ms": audio.duration_ms,
            "accent": audio.accent,
            "quality": audio.quality,
            "created_at": audio.created_at.isoformat() if audio.created_at else None,
            "updated_at": audio.updated_at.isoformat() if audio.updated_at else None,
            "version": audio.version,
        },
        metadata={
            "version": audio.version,
        },
        links={
            "self": f"/audio/{audio_id}",
            "content": f"/audio/{audio_id}/content",
        },
    )


@router.get("/{audio_id}/content")
async def get_audio_content(audio_id: str) -> FileResponse:
    """Get audio file content.

    Args:
        audio_id: The audio media document ID

    Returns:
        The audio file

    Raises:
        404: Audio file not found
    """
    # Get the audio media document
    audio = await AudioMedia.get(audio_id)
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Get the file path
    file_path = Path(audio.url)

    # Check if it's an absolute path or relative to project root
    if not file_path.is_absolute():
        file_path = get_project_root() / file_path

    # Verify the file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    # Return the file
    return FileResponse(
        path=file_path,
        media_type=f"audio/{audio.format}",
        filename=f"audio_{audio_id}.{audio.format}",
    )


@router.put("/{audio_id}", response_model=ResourceResponse)
async def update_audio(
    audio_id: PydanticObjectId,
    update: AudioUpdate,
    version: int | None = Query(None, description="Version for optimistic locking"),
    repo: AudioRepository = Depends(get_audio_repo),
) -> ResourceResponse:
    """Update audio metadata.
    
    Path Parameters:
        - audio_id: ID of the audio to update
    
    Query Parameters:
        - version: Version for optimistic locking
    
    Body:
        - accent: Audio accent
        - quality: Audio quality level
    
    Returns:
        Updated audio metadata.
    
    Errors:
        404: Audio not found
        409: Version conflict
    """
    try:
        audio = await repo.update(audio_id, update, version)
        
        return ResourceResponse(
            data={
                "id": str(audio.id),
                "url": audio.url,
                "format": audio.format,
                "size_bytes": audio.size_bytes,
                "duration_ms": audio.duration_ms,
                "accent": audio.accent,
                "quality": audio.quality,
                "version": audio.version,
            },
            metadata={
                "version": audio.version,
                "updated_at": audio.updated_at.isoformat() if audio.updated_at else None,
            },
            links={
                "self": f"/audio/{audio_id}",
                "content": f"/audio/{audio_id}/content",
            },
        )
    except ValueError as e:
        if "Version mismatch" in str(e):
            raise HTTPException(
                409,
                detail=ErrorResponse(
                    error="Version conflict",
                    details=[
                        ErrorDetail(
                            field="version",
                            message=str(e),
                            code="version_conflict",
                        )
                    ],
                ).model_dump(),
            )
        raise


@router.delete("/{audio_id}", status_code=204, response_model=None)
async def delete_audio(
    audio_id: PydanticObjectId,
    repo: AudioRepository = Depends(get_audio_repo),
) -> None:
    """Delete an audio file.
    
    Path Parameters:
        - audio_id: ID of the audio to delete
    
    Errors:
        404: Audio not found
    """
    # Get audio to check file path
    audio = await repo.get(audio_id, raise_on_missing=True)
    assert audio is not None
    
    # Delete from database
    await repo.delete(audio_id)
    
    # Try to delete file from disk if it's in uploads
    if "/uploads/" in audio.url:
        try:
            file_path = Path(audio.url)
            if file_path.exists():
                os.remove(file_path)
        except Exception:
            # Log but don't fail if file deletion fails
            pass


# Keep legacy endpoints for backward compatibility
@router.get("/files/{audio_id}")
async def get_audio_file_legacy(audio_id: str) -> FileResponse:
    """[DEPRECATED] Use GET /audio/{audio_id}/content instead."""
    return await get_audio_content(audio_id)


@router.get("/cache/{subdir}/{filename}")
async def get_cached_audio(subdir: str, filename: str) -> FileResponse:
    """Get a cached audio file by path.

    This endpoint serves files from the audio cache directory.

    Args:
        subdir: The cache subdirectory (first 2 chars of hash)
        filename: The audio filename

    Returns:
        The audio file

    Raises:
        404: Audio file not found
    """
    # Construct the file path
    cache_dir = get_project_root() / "data" / "audio_cache"
    file_path = cache_dir / subdir / filename

    # Security check - ensure we're not accessing files outside cache
    try:
        file_path = file_path.resolve()
        cache_dir = cache_dir.resolve()
        if not str(file_path).startswith(str(cache_dir)):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid file path")

    # Verify the file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Determine format from extension
    format = file_path.suffix.lstrip(".")
    if format not in ["mp3", "wav", "ogg"]:
        raise HTTPException(status_code=400, detail="Invalid audio format")

    # Return the file
    return FileResponse(
        path=file_path,
        media_type=f"audio/{format}",
        filename=filename,
    )