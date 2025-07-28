"""Synthesized dictionary entry API endpoints."""

from pathlib import Path
from typing import Any
import tempfile
import os

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from PIL import Image

from ...models import ImageMedia, SynthesizedDictionaryEntry
from ..core import ErrorDetail, ErrorResponse, ResourceResponse

router = APIRouter()


class ImageBindRequest(BaseModel):
    """Request to bind an image to a synth entry."""
    
    image_path: str = Field(..., description="Path to the image file")
    alt_text: str | None = Field(None, description="Alternative text for accessibility")


@router.post("/{entry_id}/images", response_model=ResourceResponse)

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


@router.post("/{entry_id}/images/upload", response_model=ResourceResponse)
async def upload_image_to_synth_entry(
    entry_id: PydanticObjectId,
    file: UploadFile = File(...),
    alt_text: str = Form(None),
) -> ResourceResponse:
    """Upload an image file to a synthesized dictionary entry.
    
    Args:
        entry_id: ID of the synthesized entry
        file: Image file to upload (multipart/form-data)
        alt_text: Optional alternative text for accessibility
    
    Returns:
        Updated synth entry with new image
        
    Raises:
        404: Synthesized entry not found
        400: Invalid image file or upload error
        413: File too large
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
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            400,
            detail=ErrorResponse(
                error="Invalid file type",
                details=[
                    ErrorDetail(
                        field="file",
                        message=f"Expected image file, got {file.content_type}",
                        code="invalid_content_type",
                    )
                ],
            ).model_dump(),
        )
    
    # Check file size (10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            413,
            detail=ErrorResponse(
                error="File too large",
                details=[
                    ErrorDetail(
                        field="file",
                        message=f"File size {len(file_content)} bytes exceeds limit of {max_size} bytes",
                        code="file_too_large",
                    )
                ],
            ).model_dump(),
        )
    
    # Create temporary file to read with PIL
    try:
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(file_content)
            temp_file.flush()
            
            # Get image metadata using PIL
            with Image.open(temp_file.name) as img:
                width, height = img.size
                format_str = img.format.lower() if img.format else file.content_type.split('/')[-1]
                
                # Ensure format is valid
                if format_str not in ['jpeg', 'jpg', 'png', 'webp', 'gif']:
                    raise HTTPException(
                        400,
                        detail=ErrorResponse(
                            error="Unsupported image format",
                            details=[
                                ErrorDetail(
                                    field="file",
                                    message=f"Unsupported format: {format_str}",
                                    code="unsupported_format",
                                )
                            ],
                        ).model_dump(),
                    )
                
                # Normalize format names
                if format_str == 'jpeg':
                    format_str = 'jpg'
                
    except Exception as e:
        raise HTTPException(
            400,
            detail=ErrorResponse(
                error="Invalid image file",
                details=[
                    ErrorDetail(
                        field="file",
                        message=f"Could not process image file: {str(e)}",
                        code="invalid_image",
                    )
                ],
            ).model_dump(),
        )
    
    # Create ImageMedia document with binary data
    image_media = ImageMedia(
        data=file_content,  # Store binary data in MongoDB
        format=format_str,
        size_bytes=len(file_content),
        width=width,
        height=height,
        alt_text=alt_text or file.filename or "Uploaded image",
    )
    await image_media.save()
    
    # Add image ID to synth entry
    if str(image_media.id) not in entry.image_ids:
        entry.image_ids.append(str(image_media.id))
        entry.version += 1
        await entry.save()
    
    return ResourceResponse(
        data={
            "entry": entry.model_dump(),
            "image_id": str(image_media.id),
        },
        metadata={
            "version": entry.version,
            "uploaded_size": len(file_content),
            "image_format": format_str,
            "dimensions": f"{width}x{height}",
        },
        links={
            "self": f"/synth-entries/{entry_id}",
            "word": f"/words/{entry.word_id}",
            "image": f"/images/{image_media.id}",
            "image_content": f"/images/{image_media.id}/content",
        },
    )