"""Image serving API endpoints."""

from pathlib import Path

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from ...models import ImageMedia
from ..core import ErrorDetail, ErrorResponse

router = APIRouter()


@router.get("/{image_id}/content")
async def get_image_content(image_id: str):
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
