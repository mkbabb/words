"""Images API - Full CRUD operations for image management."""

import io
from datetime import datetime
from pathlib import Path
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from PIL import Image as PILImage
from pydantic import BaseModel, Field

from ....core.state_tracker import Stages, StateTracker
from ....core.streaming import create_streaming_response
from ....models import ImageMedia
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
    ImageCreate,
    ImageFilter,
    ImageRepository,
    ImageUpdate,
)

router = APIRouter()


def get_image_repo() -> ImageRepository:
    """Dependency to get image repository."""
    return ImageRepository()


class ImageQueryParams(BaseModel):
    """Query parameters for listing images."""

    format: str | None = Field(None, description="Filter by format (png, jpg, webp)")
    min_width: int | None = Field(None, description="Minimum width")
    max_width: int | None = Field(None, description="Maximum width")
    min_height: int | None = Field(None, description="Minimum height")
    max_height: int | None = Field(None, description="Maximum height")
    has_alt_text: bool | None = Field(None, description="Has alt text")
    created_after: datetime | None = Field(None, description="Created after date")
    created_before: datetime | None = Field(None, description="Created before date")


class ImageUploadResponse(BaseModel):
    """Response for image upload."""

    id: str = Field(..., description="Image ID")
    format: str = Field(..., description="Image format")
    size_bytes: int = Field(..., description="File size")
    width: int = Field(..., description="Width in pixels")
    height: int = Field(..., description="Height in pixels")
    url: str = Field(..., description="Image URL")


@router.get("", response_model=ListResponse[dict[str, Any]])
async def list_images(
    repo: ImageRepository = Depends(get_image_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    params: ImageQueryParams = Depends(),
) -> ListResponse[dict[str, Any]]:
    """List images with filtering and pagination.

    Query Parameters:
        - format: Filter by image format
        - min/max_width: Width range filter
        - min/max_height: Height range filter
        - has_alt_text: Filter by alt text presence
        - Standard pagination params

    Returns:
        Paginated list of image metadata.
    """
    # Build filter
    filter_params = ImageFilter(
        format=params.format,
        min_width=params.min_width,
        max_width=params.max_width,
        min_height=params.min_height,
        max_height=params.max_height,
        has_alt_text=params.has_alt_text,
        created_after=params.created_after,
        created_before=params.created_before,
    )

    # Get data
    images, total = await repo.list(
        filter_dict=filter_params.to_query(),
        pagination=pagination,
        sort=sort,
    )

    # Convert to response format
    items = []
    for image in images:
        items.append(
            {
                "id": str(image.id),
                "format": image.format,
                "size_bytes": image.size_bytes,
                "width": image.width,
                "height": image.height,
                "alt_text": image.alt_text,
                "description": image.description,
                "url": f"/api/v1/images/{image.id}",
                "content_url": f"/api/v1/images/{image.id}/content",
                "created_at": image.created_at.isoformat() if image.created_at else None,
            }
        )

    return ListResponse(
        items=items,
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.post("", response_model=ResourceResponse, status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    alt_text: str | None = Query(None, description="Alternative text"),
    description: str | None = Query(None, description="Image description"),
    repo: ImageRepository = Depends(get_image_repo),
) -> ResourceResponse:
    """Upload a new image.

    Body:
        - file: Image file (multipart/form-data)

    Query Parameters:
        - alt_text: Alternative text for accessibility
        - description: Image description

    Returns:
        Created image metadata with resource links.

    Errors:
        400: Invalid image file
        413: File too large (max 10MB)
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            400,
            detail=ErrorResponse(
                error="Invalid file type",
                details=[
                    ErrorDetail(
                        field="file",
                        message=f"File must be an image, got {file.content_type}",
                        code="invalid_type",
                    )
                ],
            ).model_dump(),
        )

    # Read file data
    data = await file.read()

    # Check file size (max 10MB)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(
            413,
            detail=ErrorResponse(
                error="File too large",
                details=[
                    ErrorDetail(
                        field="file",
                        message="File size must be less than 10MB",
                        code="file_too_large",
                    )
                ],
            ).model_dump(),
        )

    # Get image metadata
    try:
        img = PILImage.open(io.BytesIO(data))
        width, height = img.size
        format = img.format.lower() if img.format else "unknown"
    except Exception as e:
        raise HTTPException(
            400,
            detail=ErrorResponse(
                error="Invalid image file",
                details=[
                    ErrorDetail(
                        field="file",
                        message=f"Could not parse image: {str(e)}",
                        code="invalid_image",
                    )
                ],
            ).model_dump(),
        )

    # Create image
    image_data = ImageCreate(
        data=data,
        format=format,
        size_bytes=len(data),
        width=width,
        height=height,
        alt_text=alt_text,
        description=description,
        url=None,
    )

    image = await repo.create(image_data)

    return ResourceResponse(
        data={
            "id": str(image.id),
            "format": image.format,
            "size_bytes": image.size_bytes,
            "width": image.width,
            "height": image.height,
            "alt_text": image.alt_text,
            "description": image.description,
            "url": f"/api/v1/images/{image.id}",
            "content_url": f"/api/v1/images/{image.id}/content",
        },
        links={
            "self": f"/images/{image.id}",
            "content": f"/images/{image.id}/content",
        },
    )


@router.post("/upload/stream", response_model=ResourceResponse, status_code=201)
async def upload_image_stream(
    file: UploadFile = File(...),
    alt_text: str | None = Query(None, description="Alternative text"),
    description: str | None = Query(None, description="Image description"),
    repo: ImageRepository = Depends(get_image_repo),
) -> StreamingResponse:
    """Upload an image with streaming progress updates.

    Returns Server-Sent Events (SSE) with progress updates.

    Form Data:
        - file: Image file (multipart/form-data)

    Query Parameters:
        - alt_text: Alternative text for accessibility
        - description: Image description

    Event Types:
        - config: Stage definitions for progress visualization
        - progress: Update on current operation with stage and progress
        - complete: Final result with image info
        - error: Error details if something goes wrong
    """
    # Read file content
    data = await file.read()

    # Create state tracker for image upload process
    state_tracker = StateTracker(category="image")

    async def upload_process() -> dict[str, Any]:
        """Perform the image upload process while updating state tracker."""
        try:
            # Start upload
            await state_tracker.update_stage(Stages.IMAGE_UPLOAD_START)
            await state_tracker.update(
                stage=Stages.IMAGE_UPLOAD_START, message="Starting image upload..."
            )

            # Validate file type
            await state_tracker.update_stage(Stages.IMAGE_UPLOAD_VALIDATING)
            await state_tracker.update(
                stage=Stages.IMAGE_UPLOAD_VALIDATING, message="Validating file type..."
            )

            if not file.content_type or not file.content_type.startswith("image/"):
                raise ValueError(f"File must be an image, got {file.content_type}")

            # Check file size (max 10MB)
            if len(data) > 10 * 1024 * 1024:
                raise ValueError("File size must be less than 10MB")

            await state_tracker.update(
                stage=Stages.IMAGE_UPLOAD_VALIDATING,
                progress=40,
                message=f"Validated {file.content_type} file ({len(data)} bytes)",
            )

            # Process image metadata
            await state_tracker.update_stage(Stages.IMAGE_UPLOAD_PROCESSING)
            await state_tracker.update(
                stage=Stages.IMAGE_UPLOAD_PROCESSING, message="Processing image metadata..."
            )

            try:
                img = PILImage.open(io.BytesIO(data))
                width, height = img.size
                format = img.format.lower() if img.format else "unknown"
            except Exception as e:
                raise ValueError(f"Could not parse image: {str(e)}")

            await state_tracker.update(
                stage=Stages.IMAGE_UPLOAD_PROCESSING,
                progress=70,
                message=f"Processed {width}x{height} {format} image",
            )

            # Store image
            await state_tracker.update_stage(Stages.IMAGE_UPLOAD_STORING)
            await state_tracker.update(
                stage=Stages.IMAGE_UPLOAD_STORING, message="Storing image data..."
            )

            # Create image
            image_data = ImageCreate(
                data=data,
                format=format,
                size_bytes=len(data),
                width=width,
                height=height,
                alt_text=alt_text,
                description=description,
                url=None,
            )

            image = await repo.create(image_data)

            # Complete successfully
            await state_tracker.update_complete(message="Image uploaded successfully!")

            # Return result data
            return {
                "id": str(image.id),
                "format": image.format,
                "size_bytes": image.size_bytes,
                "width": image.width,
                "height": image.height,
                "alt_text": image.alt_text,
                "description": image.description,
                "url": f"/api/v1/images/{image.id}",
                "content_url": f"/api/v1/images/{image.id}/content",
            }

        except Exception as e:
            await state_tracker.update_error(f"Failed to upload image: {str(e)}")
            raise

    # Use the generalized streaming system
    return await create_streaming_response(
        state_tracker=state_tracker,
        process_func=upload_process,
        include_stage_definitions=True,
        include_completion_data=True,
    )


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
                headers={"Content-Disposition": f'inline; filename="{image_id}.{image.format}"'},
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
        "created_at": image.created_at.isoformat() if image.created_at else None,
        "updated_at": image.updated_at.isoformat() if image.updated_at else None,
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
            headers={"Content-Disposition": f'inline; filename="{image_id}.{image.format}"'},
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


@router.put("/{image_id}", response_model=ResourceResponse)
async def update_image(
    image_id: PydanticObjectId,
    update: ImageUpdate,
    version: int | None = Query(None, description="Version for optimistic locking"),
    repo: ImageRepository = Depends(get_image_repo),
) -> ResourceResponse:
    """Update image metadata.

    Path Parameters:
        - image_id: ID of the image to update

    Query Parameters:
        - version: Version for optimistic locking

    Body:
        - alt_text: Alternative text
        - description: Image description
        - url: External URL

    Returns:
        Updated image metadata.

    Errors:
        404: Image not found
        409: Version conflict
    """
    try:
        image = await repo.update(image_id, update, version)

        return ResourceResponse(
            data={
                "id": str(image.id),
                "format": image.format,
                "size_bytes": image.size_bytes,
                "width": image.width,
                "height": image.height,
                "alt_text": image.alt_text,
                "description": image.description,
                "url": f"/api/v1/images/{image.id}",
                "content_url": f"/api/v1/images/{image.id}/content",
                "version": image.version,
            },
            metadata={
                "version": image.version,
                "updated_at": image.updated_at.isoformat() if image.updated_at else None,
            },
            links={
                "self": f"/images/{image_id}",
                "content": f"/images/{image_id}/content",
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


@router.delete("/{image_id}", status_code=204, response_model=None)
async def delete_image(
    image_id: PydanticObjectId,
    repo: ImageRepository = Depends(get_image_repo),
) -> None:
    """Delete an image.

    Path Parameters:
        - image_id: ID of the image to delete

    Errors:
        404: Image not found
    """
    await repo.delete(image_id)
