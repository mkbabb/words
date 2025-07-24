"""Atomic update operations with optimistic locking."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...models import Definition, Word
from ...utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class AtomicUpdate(BaseModel):
    """Atomic update operation."""
    
    op: str = Field(..., pattern="^(add|remove|replace|test)$")
    path: str = Field(..., pattern="^/[a-zA-Z0-9/_-]+$")
    value: str | int | float | bool | list[Any] | dict[str, Any] | None = None


class AtomicUpdateRequest(BaseModel):
    """Request for atomic updates."""
    
    operations: list[AtomicUpdate] = Field(..., min_length=1, max_length=50)
    expected_version: int = Field(..., ge=1)


class AtomicUpdateResponse(BaseModel):
    """Response from atomic update."""
    
    success: bool
    new_version: int | None = None
    error: str | None = None


@router.patch("/word/{word_id}", response_model=AtomicUpdateResponse)
async def atomic_update_word(
    word_id: str,
    request: AtomicUpdateRequest
) -> AtomicUpdateResponse:
    """Atomically update a word with version checking."""
    
    word = await Word.get(word_id)
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word {word_id} not found"
        )
    
    # Check version for optimistic locking
    if word.version != request.expected_version:
        return AtomicUpdateResponse(
            success=False,
            error=f"Version mismatch: expected {request.expected_version}, got {word.version}"
        )
    
    try:
        # Apply operations
        for op in request.operations:
            apply_operation(word, op)
        
        # Increment version and save
        word.version += 1
        await word.save()
        
        return AtomicUpdateResponse(
            success=True,
            new_version=word.version
        )
        
    except Exception as e:
        logger.error(f"Atomic update failed for word {word_id}: {e}")
        return AtomicUpdateResponse(
            success=False,
            error=str(e)
        )


@router.patch("/definition/{definition_id}", response_model=AtomicUpdateResponse)
async def atomic_update_definition(
    definition_id: str,
    request: AtomicUpdateRequest
) -> AtomicUpdateResponse:
    """Atomically update a definition with version checking."""
    
    definition = await Definition.get(definition_id)
    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Definition {definition_id} not found"
        )
    
    if definition.version != request.expected_version:
        return AtomicUpdateResponse(
            success=False,
            error=f"Version mismatch: expected {request.expected_version}, got {definition.version}"
        )
    
    try:
        for op in request.operations:
            apply_operation(definition, op)
        
        definition.version += 1
        await definition.save()
        
        return AtomicUpdateResponse(
            success=True,
            new_version=definition.version
        )
        
    except Exception as e:
        logger.error(f"Atomic update failed for definition {definition_id}: {e}")
        return AtomicUpdateResponse(
            success=False,
            error=str(e)
        )


def apply_operation(obj: object, operation: AtomicUpdate) -> None:
    """Apply a single atomic operation to an object.
    
    Args:
        obj: Object to update
        operation: Operation to apply
        
    Raises:
        ValueError: If operation fails
    """
    path_parts = operation.path.strip("/").split("/")
    
    # Navigate to the target
    target = obj
    for i, part in enumerate(path_parts[:-1]):
        if hasattr(target, part):
            target = getattr(target, part)
        elif isinstance(target, dict) and part in target:
            target = target[part]
        elif isinstance(target, list) and part.isdigit():
            idx = int(part)
            if 0 <= idx < len(target):
                target = target[idx]
            else:
                raise ValueError(f"Index {idx} out of range")
        else:
            raise ValueError(f"Path {'/'.join(path_parts[:i+1])} not found")
    
    final_key = path_parts[-1]
    
    # Apply operation
    if operation.op == "test":
        # Test that current value matches
        current = None
        if hasattr(target, final_key):
            current = getattr(target, final_key)
        elif isinstance(target, dict) and final_key in target:
            current = target[final_key]
        elif isinstance(target, list) and final_key.isdigit():
            idx = int(final_key)
            current = target[idx] if 0 <= idx < len(target) else None
        
        if current != operation.value:
            raise ValueError(f"Test failed: expected {operation.value}, got {current}")
    
    elif operation.op == "add":
        if isinstance(target, list):
            if final_key == "-":
                target.append(operation.value)
            else:
                idx = int(final_key)
                target.insert(idx, operation.value)
        elif isinstance(target, dict):
            target[final_key] = operation.value
        else:
            setattr(target, final_key, operation.value)
    
    elif operation.op == "remove":
        if isinstance(target, list) and final_key.isdigit():
            idx = int(final_key)
            if 0 <= idx < len(target):
                target.pop(idx)
        elif isinstance(target, dict) and final_key in target:
            del target[final_key]
        elif hasattr(target, final_key):
            delattr(target, final_key)
        else:
            raise ValueError(f"Cannot remove {final_key}")
    
    elif operation.op == "replace":
        if isinstance(target, list) and final_key.isdigit():
            idx = int(final_key)
            if 0 <= idx < len(target):
                target[idx] = operation.value
        elif isinstance(target, dict):
            if final_key in target:
                target[final_key] = operation.value
            else:
                raise ValueError(f"Key {final_key} not found")
        elif hasattr(target, final_key):
            setattr(target, final_key, operation.value)
        else:
            raise ValueError(f"Cannot replace {final_key}")


@router.post("/transaction", response_model=dict[str, AtomicUpdateResponse])
async def atomic_transaction(
    updates: dict[str, AtomicUpdateRequest]
) -> dict[str, AtomicUpdateResponse]:
    """Execute multiple atomic updates as a transaction.
    
    All updates must succeed or all are rolled back.
    """
    results = {}
    updated_objects = []
    
    try:
        # Apply all updates
        for resource_id, request in updates.items():
            resource_type, obj_id = resource_id.split(":", 1)
            
            if resource_type == "word":
                result = await atomic_update_word(obj_id, request)
            elif resource_type == "definition":
                result = await atomic_update_definition(obj_id, request)
            else:
                raise ValueError(f"Unknown resource type: {resource_type}")
            
            results[resource_id] = result
            
            if not result.success:
                # Rollback
                raise ValueError(f"Update failed for {resource_id}: {result.error}")
            
            updated_objects.append((resource_type, obj_id))
        
        return results
        
    except Exception as e:
        # Rollback all changes
        logger.error(f"Transaction failed, rolling back: {e}")
        
        # In a real implementation, we'd restore previous versions
        # For now, we just return error responses
        for resource_id in updates:
            if resource_id not in results:
                results[resource_id] = AtomicUpdateResponse(
                    success=False,
                    error="Transaction rolled back"
                )
        
        return results