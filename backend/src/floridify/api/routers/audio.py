"""Audio file serving endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ...models import AudioMedia
from ...utils.paths import get_project_root

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/files/{audio_id}")
async def get_audio_file(audio_id: str) -> FileResponse:
    """Get an audio file by ID.

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
        filename=f"pronunciation_{audio_id}.{audio.format}",
    )


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
