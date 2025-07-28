"""Synthesized dictionary entry API endpoints."""

from pathlib import Path
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ...models import ImageMedia, SynthesizedDictionaryEntry
from ..core import ErrorDetail, ErrorResponse, ResourceResponse, handle_api_errors

router = APIRouter()


class ImageBindRequest(BaseModel):
    """Request to bind an image to a synth entry."""
    
    image_path: str = Field(..., description="Path to the image file")
    alt_text: str | None = Field(None, description="Alternative text for accessibility")


@router.post("/{entry_id}/images", response_model=ResourceResponse)
@handle_api_errors
async def bind_image_to_synth_entry(
    entry_id: PydanticObjectId,
    request: ImageBindRequest,
) -> ResourceResponse:
    """Bind an image to a synthesized dictionary entry.
    
    Args:
        entry_id: ID of the synthesized entry
        request: Image binding request with path and optional alt text
    
    Returns:
        Updated synth entry with image
        
    Raises:
        404: Synthesized entry not found
        400: Invalid image path
    """
    # Get the synth entry
    entry = await SynthesizedDictionaryEntry.get(entry_id)
    if not entry:
        raise HTTPException(
            404,
            detail=ErrorResponse(
                error="Synthesized entry not found",
                details=[
                    ErrorDetail(
                        field="entry_id",
                        message=f"Synthesized entry with ID {entry_id} not found",
                        code="not_found",
                    )
                ],
            ).model_dump(),
        )
    
    # Validate image path exists
    image_path = Path(request.image_path)
    if not image_path.exists():
        raise HTTPException(
            400,
            detail=ErrorResponse(
                error="Invalid image path",
                details=[
                    ErrorDetail(
                        field="image_path",
                        message=f"Image file not found: {request.image_path}",
                        code="file_not_found",
                    )
                ],
            ).model_dump(),
        )
    
    # Get image metadata
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            width, height = img.size
            format = img.format.lower() if img.format else image_path.suffix[1:].lower()
    except Exception as e:
        raise HTTPException(
            400,
            detail=ErrorResponse(
                error="Invalid image file",
                details=[
                    ErrorDetail(
                        field="image_path",
                        message=f"Could not open image file: {str(e)}",
                        code="invalid_image",
                    )
                ],
            ).model_dump(),
        )
    
    # Create ImageMedia document
    image_media = ImageMedia(
        url=str(image_path),  # Store as file path for now
        format=format,
        size_bytes=image_path.stat().st_size,
        width=width,
        height=height,
        alt_text=request.alt_text,
    )
    await image_media.save()
    
    # Add image ID to synth entry
    if str(image_media.id) not in entry.image_ids:
        entry.image_ids.append(str(image_media.id))
        entry.version += 1
        await entry.save()
    
    return ResourceResponse(
        data=entry.model_dump(),
        metadata={
            "image_id": str(image_media.id),
            "version": entry.version,
        },
        links={
            "self": f"/synth-entries/{entry_id}",
            "word": f"/words/{entry.word_id}",
            "image": f"/images/{image_media.id}",
        },
    )