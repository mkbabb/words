"""Atomic updates API - Safe field-level updates with version control."""

from typing import Any, Literal

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from pymongo import ReturnDocument
from datetime import datetime

from ..core import ErrorResponse, handle_api_errors
from ...models import Definition, Word
from ...utils.sanitization import sanitize_field_name

router = APIRouter()


# Define allowed fields for atomic updates
WORD_UPDATABLE_FIELDS = {
    "offensive_flag",
    "first_known_use", 
    "homograph_number",
    "language",
    "tags",
}

DEFINITION_UPDATABLE_FIELDS = {
    "definition",
    "word_type",
    "confidence_score",
    "offensive_flag",
    "tags",
    "meaning_cluster",
}


class AtomicFieldUpdate(BaseModel):
    """Request for atomic field update."""
    
    field: str = Field(..., description="Field path to update")
    value: Any = Field(..., description="New value for the field")
    version: int = Field(..., ge=1, description="Expected version for optimistic locking")
    
    @validator("field")
    def validate_field_name(cls, v):
        """Ensure field name is safe."""
        return sanitize_field_name(v)


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
    """Atomically update a single field on a word using MongoDB atomic operations."""
    
    # Validate field is updatable
    if update.field not in WORD_UPDATABLE_FIELDS:
        raise HTTPException(
            400,
            f"Field '{update.field}' cannot be updated. Allowed fields: {', '.join(sorted(WORD_UPDATABLE_FIELDS))}"
        )
    
    # Validate field type
    if update.field in Word.__fields__:
        field_info = Word.__fields__[update.field]
        # Basic type validation - could be expanded
        if update.field == "offensive_flag" and not isinstance(update.value, bool):
            raise HTTPException(400, "offensive_flag must be a boolean")
        elif update.field == "homograph_number" and update.value is not None:
            if not isinstance(update.value, int) or update.value < 0:
                raise HTTPException(400, "homograph_number must be a non-negative integer or null")
    
    # Perform atomic update with version check
    result = await Word.get_motor_collection().find_one_and_update(
        {
            "_id": word_id,
            "version": update.version
        },
        {
            "$set": {
                update.field: update.value,
                "updated_at": datetime.utcnow()
            },
            "$inc": {"version": 1}
        },
        return_document=ReturnDocument.BEFORE
    )
    
    if not result:
        # Check if it's a version mismatch or not found
        existing = await Word.get(word_id)
        if not existing:
            raise HTTPException(404, "Word not found")
        else:
            raise HTTPException(
                409,
                detail=ErrorResponse(
                    error="Version conflict",
                    details=[{
                        "field": "version",
                        "message": f"Expected version {update.version}, got {existing.version}",
                        "code": "version_mismatch"
                    }]
                ).model_dump()
            )
    
    return AtomicUpdateResponse(
        success=True,
        new_version=update.version + 1,
        updated_field=update.field,
        old_value=result.get(update.field),
        new_value=update.value,
    )


@router.patch("/definition/{definition_id}/field", response_model=AtomicUpdateResponse)
@handle_api_errors
async def update_definition_field(
    definition_id: PydanticObjectId,
    update: AtomicFieldUpdate,
) -> AtomicUpdateResponse:
    """Atomically update a single field on a definition using MongoDB atomic operations."""
    
    # Validate field is updatable
    if update.field not in DEFINITION_UPDATABLE_FIELDS:
        raise HTTPException(
            400,
            f"Field '{update.field}' cannot be updated. Allowed fields: {', '.join(sorted(DEFINITION_UPDATABLE_FIELDS))}"
        )
    
    # Validate field type
    if update.field in Definition.__fields__:
        if update.field == "offensive_flag" and not isinstance(update.value, bool):
            raise HTTPException(400, "offensive_flag must be a boolean")
        elif update.field == "confidence_score":
            if not isinstance(update.value, (int, float)) or not 0 <= update.value <= 1:
                raise HTTPException(400, "confidence_score must be between 0 and 1")
    
    # Perform atomic update with version check
    result = await Definition.get_motor_collection().find_one_and_update(
        {
            "_id": definition_id,
            "version": update.version
        },
        {
            "$set": {
                update.field: update.value,
                "updated_at": datetime.utcnow()
            },
            "$inc": {"version": 1}
        },
        return_document=ReturnDocument.BEFORE
    )
    
    if not result:
        # Check if it's a version mismatch or not found
        existing = await Definition.get(definition_id)
        if not existing:
            raise HTTPException(404, "Definition not found")
        else:
            raise HTTPException(
                409,
                detail=ErrorResponse(
                    error="Version conflict",
                    details=[{
                        "field": "version",
                        "message": f"Expected version {update.version}, got {existing.version}",
                        "code": "version_mismatch"
                    }]
                ).model_dump()
            )
    
    return AtomicUpdateResponse(
        success=True,
        new_version=update.version + 1,
        updated_field=update.field,
        old_value=result.get(update.field),
        new_value=update.value,
    )


class BatchAtomicUpdate(BaseModel):
    """Request for batch atomic updates."""
    
    updates: list[dict[str, Any]] = Field(
        ...,
        description="List of atomic updates to perform",
        max_items=100
    )


@router.post("/batch/atomic-updates", response_model=dict[str, Any])
@handle_api_errors
async def batch_atomic_updates(
    request: BatchAtomicUpdate,
) -> dict[str, Any]:
    """Perform multiple atomic updates in a single request."""
    from pymongo import UpdateOne
    
    word_operations = []
    definition_operations = []
    
    for update in request.updates:
        if "word_id" in update:
            # Validate word field
            if update["field"] not in WORD_UPDATABLE_FIELDS:
                continue
                
            word_operations.append(
                UpdateOne(
                    {
                        "_id": PydanticObjectId(update["word_id"]),
                        "version": update["version"]
                    },
                    {
                        "$set": {
                            update["field"]: update["value"],
                            "updated_at": datetime.utcnow()
                        },
                        "$inc": {"version": 1}
                    }
                )
            )
        elif "definition_id" in update:
            # Validate definition field
            if update["field"] not in DEFINITION_UPDATABLE_FIELDS:
                continue
                
            definition_operations.append(
                UpdateOne(
                    {
                        "_id": PydanticObjectId(update["definition_id"]),
                        "version": update["version"]
                    },
                    {
                        "$set": {
                            update["field"]: update["value"],
                            "updated_at": datetime.utcnow()
                        },
                        "$inc": {"version": 1}
                    }
                )
            )
    
    results = {
        "words": {"matched": 0, "modified": 0, "errors": []},
        "definitions": {"matched": 0, "modified": 0, "errors": []}
    }
    
    # Execute word updates
    if word_operations:
        word_result = await Word.get_motor_collection().bulk_write(
            word_operations, 
            ordered=False
        )
        results["words"]["matched"] = word_result.matched_count
        results["words"]["modified"] = word_result.modified_count
        if hasattr(word_result, "bulk_api_result"):
            results["words"]["errors"] = word_result.bulk_api_result.get("writeErrors", [])
    
    # Execute definition updates
    if definition_operations:
        def_result = await Definition.get_motor_collection().bulk_write(
            definition_operations,
            ordered=False
        )
        results["definitions"]["matched"] = def_result.matched_count
        results["definitions"]["modified"] = def_result.modified_count
        if hasattr(def_result, "bulk_api_result"):
            results["definitions"]["errors"] = def_result.bulk_api_result.get("writeErrors", [])
    
    return results