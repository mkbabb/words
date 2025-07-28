"""Image serving API endpoints."""

from pathlib import Path
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from ...models import ImageMedia
from ..core import ErrorDetail, ErrorResponse

router = APIRouter()


@router.get("/{image_id}", response_model=None)
async def get_image(request: Request, image_id: str) -> Response | dict[str, Any]:
    """Get image metadata or content based on Accept header.

    Args:
        request: FastAPI request object
        image_id: ID of the image

    Returns:
        Image metadata (JSON) or image content (binary) based on Accept header

    Raises:
        404: Image not found
    """
    image = await ImageMedia.get(image_id)

    if not image:
        raise HTTPException(
            404,
            detail=ErrorResponse(
                error="Image not found",
                details=[
                    ErrorDetail(
                        field="image_id",
                        message=f"Image with ID {image_id} not found",
                        code="not_found",
                    )
                ],
            ).model_dump(),
        )

    # Check if client accepts image content (browser requesting image)
    accept_header = request.headers.get("accept", "")
    if "image/" in accept_header or "text/html" in accept_header:
        # Serve image content for browsers
        if image.data:
            media_type = f"image/{image.format}"
            if image.format == "jpg":
                media_type = "image/jpeg"
            
            return Response(
                content=image.data,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'inline; filename="{image_id}.{image.format}"'
                }
            )
        
        # Fallback to file path if available
        elif image.url and image.url.startswith("/"):
            image_path = Path(image.url)
            if image_path.exists():
                media_type = f"image/{image.format}"
                if image.format == "jpg":
                    media_type = "image/jpeg"

                return FileResponse(
                    path=image_path,
                    media_type=media_type,
                    filename=f"{image_id}.{image.format}",
                )
        
        # No data available
        raise HTTPException(
            404,
            detail=ErrorResponse(
                error="Image data not found",
                details=[
                    ErrorDetail(
                        field="data",
                        message="No image data or valid file path available",
                        code="no_data",
                    )
                ],
            ).model_dump(),
        )
    
    # Return metadata for API clients
    return {
        "id": str(image.id),
        "format": image.format,
        "size_bytes": image.size_bytes,
        "width": image.width,
        "height": image.height,
        "alt_text": image.alt_text,
        "description": image.description,
        "url": image.url,
        "content_url": f"/api/v1/images/{image_id}/content",
    }


@router.get("/{image_id}/content", response_model=None)
async def get_image_content(image_id: str) -> Response:
    """Serve image content.

    Args:
        image_id: ID of the image

    Returns:
        Image file content

    Raises:
        404: Image not found or no data available
    """
    # Get image metadata
    image = await ImageMedia.get(image_id)

    if not image:
        raise HTTPException(
            404,
            detail=ErrorResponse(
                error="Image not found",
                details=[
                    ErrorDetail(
                        field="image_id",
                        message=f"Image with ID {image_id} not found",
                        code="not_found",
                    )
                ],
            ).model_dump(),
        )

    # Check if we have binary data
    if image.data:
        # Serve from MongoDB
        media_type = f"image/{image.format}"
        if image.format == "jpg":
            media_type = "image/jpeg"
        
        return Response(
            content=image.data,
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{image_id}.{image.format}"'
            }
        )
    
    # Fallback to file path if available
    elif image.url and image.url.startswith("/"):
        image_path = Path(image.url)
        if image_path.exists():
            # Determine media type
            media_type = f"image/{image.format}"
            if image.format == "jpg":
                media_type = "image/jpeg"

            return FileResponse(
                path=image_path,
                media_type=media_type,
                filename=f"{image_id}.{image.format}",
            )
    
    # No data available
    raise HTTPException(
        404,
        detail=ErrorResponse(
            error="Image data not found",
            details=[
                ErrorDetail(
                    field="data",
                    message="No image data or valid file path available",
                    code="no_data",
                )
            ],
        ).model_dump(),
    )
