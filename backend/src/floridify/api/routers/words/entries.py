"""
Synthesized Dictionary Entry API Router

Provides comprehensive CRUD operations for SynthesizedDictionaryEntry objects,
including component-level updates and image management.
"""

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...core import (
    FieldSelection,
    NotFoundException,
    ResourceResponse,
    get_fields,
)
from ...repositories.synthesis_repository import SynthesisRepository, SynthesisUpdate

router = APIRouter()

# Request/Response Models
class EntryUpdateRequest(BaseModel):
    """Request model for updating synthesized entry metadata"""
    status: str | None = Field(None, description="Entry status")
    tags: list[str] | None = Field(None, description="Entry tags")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

class ComponentUpdateRequest(BaseModel):
    """Request model for updating entry components"""
    component_type: str = Field(..., description="Component type (definition, image, fact, etc.)")
    component_id: str = Field(..., description="Component ID to update")
    updates: dict[str, Any] = Field(..., description="Update data")

class RegenerateRequest(BaseModel):
    """Request model for re-synthesizing entry components"""
    components: set[str] = Field(default_factory=lambda: {"all"}, description="Components to regenerate")
    force: bool = Field(False, description="Force regeneration even if data exists")

class ImageAddRequest(BaseModel):
    """Request model for adding images to entry"""
    image_ids: list[PydanticObjectId] = Field(..., description="Image IDs to add to entry")

# Repository dependency
def get_synthesis_repo() -> SynthesisRepository:
    return SynthesisRepository()

# Routes

@router.get("/{entry_id}")
async def get_entry(
    entry_id: str,
    field_selection: FieldSelection = Depends(get_fields),
    repo: SynthesisRepository = Depends(get_synthesis_repo)
) -> ResourceResponse:
    """
    Get a synthesized dictionary entry by ID.
    
    Supports field selection for controlling which components are included:
    - expand: Load related components (definitions, images, facts, etc.)
    - include: Only include specified fields
    - exclude: Exclude specified fields
    """
    try:
        entry_dict = await repo.get_with_expansion(
            PydanticObjectId(entry_id),
            expand=field_selection.expand,
            include=field_selection.include,
            exclude=field_selection.exclude
        )
        
        if not entry_dict:
            raise NotFoundException(f"Entry with ID {entry_id} not found")
        
        # Update access tracking
        entry_oid = PydanticObjectId(entry_id)
        await repo.update_access_info(entry_oid)
        
        return ResourceResponse(
            data=entry_dict,
            metadata={
                "id": entry_id,
                "last_updated": entry_dict.get("updated_at"),
                "access_count": entry_dict.get("access_count", 0)
            }
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entry ID format: {entry_id}"
        )

@router.put("/{entry_id}")
async def update_entry(
    entry_id: str,
    request: EntryUpdateRequest,
    repo: SynthesisRepository = Depends(get_synthesis_repo)
) -> ResourceResponse:
    """Update synthesized entry metadata"""
    try:
        entry_oid = PydanticObjectId(entry_id)
        
        # Build update data
        update_data: dict[str, Any] = {}
        if request.status is not None:
            update_data["status"] = request.status
        if request.tags is not None:
            update_data["tags"] = request.tags
        if request.metadata is not None:
            update_data["metadata"] = request.metadata
        
        # Convert to SynthesisUpdate
        update_request = SynthesisUpdate(**update_data)
        updated_entry = await repo.update(entry_oid, update_request)
        
        return ResourceResponse(
            data=updated_entry.model_dump(mode="json"),
            metadata={
                "id": str(updated_entry.id),
                "updated_at": updated_entry.updated_at.isoformat() if updated_entry.updated_at else None
            }
        )
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry with ID {entry_id} not found"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entry ID format: {entry_id}"
        )

@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: str,
    repo: SynthesisRepository = Depends(get_synthesis_repo)
) -> ResourceResponse:
    """Delete a synthesized dictionary entry"""
    try:
        entry_oid = PydanticObjectId(entry_id)
        await repo.delete(entry_oid)
        
        return ResourceResponse(
            data={"deleted": True},
            metadata={"id": entry_id}
        )
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry with ID {entry_id} not found"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entry ID format: {entry_id}"
        )

# Image Management Routes (Primary Focus)

@router.post("/{entry_id}/images")
async def add_images_to_entry(
    entry_id: str,
    request: ImageAddRequest,
    repo: SynthesisRepository = Depends(get_synthesis_repo)
) -> ResourceResponse:
    """
    Add images to a synthesized dictionary entry.
    
    This is the primary endpoint for associating uploaded images with entries.
    """
    try:
        entry_oid = PydanticObjectId(entry_id)
        
        # Image IDs are already PydanticObjectIds
        image_oids = request.image_ids
        
        # Get current entry
        entry = await repo.get(entry_oid)
        if not entry:
            raise NotFoundException(f"Entry with ID {entry_id} not found")
        
        # Add images to entry (avoid duplicates)
        current_image_ids = set(entry.image_ids or [])
        new_image_ids = current_image_ids.union(set(image_oids))
        
        # Update entry with new images
        update_request = SynthesisUpdate(image_ids=list(new_image_ids))
        updated_entry = await repo.update(entry_oid, update_request)
        
        return ResourceResponse(
            data={
                "entry_id": entry_id,
                "image_ids": [str(img_id) for img_id in updated_entry.image_ids],
                "images_added": len(image_oids),
                "total_images": len(updated_entry.image_ids)
            },
            metadata={
                "updated_at": updated_entry.updated_at.isoformat() if updated_entry.updated_at else None
            }
        )
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry with ID {entry_id} not found"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ID format: {str(e)}"
        )

@router.delete("/{entry_id}/images/{image_id}")
async def remove_image_from_entry(
    entry_id: str,
    image_id: str,
    repo: SynthesisRepository = Depends(get_synthesis_repo)
) -> ResourceResponse:
    """Remove an image from a synthesized dictionary entry"""
    try:
        entry_oid = PydanticObjectId(entry_id)
        image_oid = PydanticObjectId(image_id)
        
        # Get current entry
        entry = await repo.get(entry_oid)
        if not entry:
            raise NotFoundException(f"Entry with ID {entry_id} not found")
        
        # Remove image from entry
        current_image_ids = entry.image_ids or []
        updated_image_ids = [img_id for img_id in current_image_ids if img_id != image_oid]
        
        # Update entry
        update_request = SynthesisUpdate(image_ids=updated_image_ids)
        updated_entry = await repo.update(entry_oid, update_request)
        
        return ResourceResponse(
            data={
                "entry_id": entry_id,
                "image_id": image_id,
                "removed": True,
                "remaining_images": len(updated_entry.image_ids)
            },
            metadata={
                "updated_at": updated_entry.updated_at.isoformat() if updated_entry.updated_at else None
            }
        )
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry with ID {entry_id} not found"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ID format: {str(e)}"
        )

@router.post("/{entry_id}/regenerate")
async def regenerate_entry_components(
    entry_id: str,
    request: RegenerateRequest,
    repo: SynthesisRepository = Depends(get_synthesis_repo)
) -> ResourceResponse:
    """
    Re-synthesize components of a dictionary entry.
    
    This endpoint triggers AI regeneration of specific components
    or the entire entry if requested.
    """
    try:
        entry_oid = PydanticObjectId(entry_id)
        
        # Get current entry
        entry = await repo.get(entry_oid)
        if not entry:
            raise NotFoundException(f"Entry with ID {entry_id} not found")
        
        # TODO: Implement actual regeneration logic
        # This would involve calling the synthesis system to regenerate  
        # the requested components using the synthesizer's regenerate_entry_components method
        
        return ResourceResponse(
            data={
                "entry_id": entry_id,
                "components": list(request.components),
                "regeneration_requested": True,
                "status": "pending"
            },
            metadata={
                "requested_at": "2025-01-31T00:00:00Z"  # TODO: Use actual timestamp
            }
        )
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry with ID {entry_id} not found"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entry ID format: {entry_id}"
        )