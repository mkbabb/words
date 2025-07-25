"""Atomic updates API - Safe field-level updates with version control."""

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from floridify.api.core import ErrorResponse, handle_api_errors
from floridify.models.models import Definition, Word

router = APIRouter()


class AtomicFieldUpdate(BaseModel):
    """Request for atomic field update."""
    
    field: str = Field(..., description="Field path to update")
    value: Any = Field(..., description="New value for the field")
    version: int = Field(..., description="Expected version for optimistic locking")


class AtomicUpdateResponse(BaseModel):
    """Response for atomic update operation."""
    
    success: bool
    new_version: int
    updated_field: str
    old_value: Any
    new_value: Any


@router.patch("/word/{word_id}/field", response_model=AtomicUpdateResponse)
@handle_api_errors
async def update_word_field(
    word_id: PydanticObjectId,
    update: AtomicFieldUpdate,
) -> AtomicUpdateResponse:
    """Atomically update a single field on a word."""
    word = await Word.get(word_id)
    if not word:
        raise HTTPException(404, "Word not found")
    
    # Check version
    if word.version != update.version:
        raise HTTPException(
            409,
            detail=ErrorResponse(
                error="Version conflict",
                details=[{
                    "field": "version",
                    "message": f"Expected version {update.version}, got {word.version}",
                    "code": "version_mismatch"
                }]
            ).model_dump()
        )
    
    # Get old value
    old_value = getattr(word, update.field, None)
    
    # Update field
    setattr(word, update.field, update.value)
    word.version += 1
    
    # Save
    await word.save()
    
    return AtomicUpdateResponse(
        success=True,
        new_version=word.version,
        updated_field=update.field,
        old_value=old_value,
        new_value=update.value,
    )


@router.patch("/definition/{definition_id}/field", response_model=AtomicUpdateResponse)
@handle_api_errors
async def update_definition_field(
    definition_id: PydanticObjectId,
    update: AtomicFieldUpdate,
) -> AtomicUpdateResponse:
    """Atomically update a single field on a definition."""
    definition = await Definition.get(definition_id)
    if not definition:
        raise HTTPException(404, "Definition not found")
    
    # Check version
    if definition.version != update.version:
        raise HTTPException(
            409,
            detail=ErrorResponse(
                error="Version conflict",
                details=[{
                    "field": "version",
                    "message": f"Expected version {update.version}, got {definition.version}",
                    "code": "version_mismatch"
                }]
            ).model_dump()
        )
    
    # Get old value
    old_value = getattr(definition, update.field, None)
    
    # Update field
    setattr(definition, update.field, update.value)
    definition.version += 1
    
    # Save
    await definition.save()
    
    return AtomicUpdateResponse(
        success=True,
        new_version=definition.version,
        updated_field=update.field,
        old_value=old_value,
        new_value=update.value,
    )