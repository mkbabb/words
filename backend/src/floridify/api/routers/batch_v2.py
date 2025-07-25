"""Batch operations API v2 - Optimized bulk processing."""

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from ...models import Definition, Example, Fact, Word
from ..core import (
    BulkOperationBuilder,
    handle_api_errors,
)
from ..repositories import (
    DefinitionRepository,
    ExampleRepository,
    WordRepository,
)

router = APIRouter(prefix="/batch/v2", tags=["batch-v2"])


class BulkWordCreate(BaseModel):
    """Bulk word creation request."""

    words: list[dict[str, Any]] = Field(..., min_length=1, max_length=1000)
    skip_existing: bool = Field(True, description="Skip words that already exist")


class BulkDefinitionUpdate(BaseModel):
    """Bulk definition update request."""

    updates: list[dict[str, Any]] = Field(
        ..., min_length=1, max_length=500, description="List of {id, fields} objects"
    )
    validate_versions: bool = Field(False, description="Check version conflicts")


class BulkDeleteRequest(BaseModel):
    """Bulk delete request."""

    model: str = Field(..., pattern="^(word|definition|example|fact)$")
    ids: list[str] = Field(..., min_length=1, max_length=500)
    cascade: bool = Field(False, description="Delete related documents")


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""

    total: int
    successful: int
    failed: int
    errors: list[dict[str, Any]] = Field(default_factory=list)
    results: dict[str, Any] = Field(default_factory=dict)


@router.post("/words/create", response_model=BulkOperationResponse)
@handle_api_errors
async def bulk_create_words(
    request: BulkWordCreate,
    background_tasks: BackgroundTasks,
    repo: WordRepository = Depends(lambda: WordRepository()),
) -> BulkOperationResponse:
    """Bulk create words with optimized performance."""
    bulk = BulkOperationBuilder(Word)
    successful = 0
    failed = 0
    errors = []

    for word_data in request.words:
        try:
            # Check if exists
            if request.skip_existing:
                existing = await repo.find_by_text(
                    word_data["text"], word_data.get("language", "english")
                )
                if existing:
                    failed += 1
                    errors.append(
                        {
                            "word": word_data["text"],
                            "error": "Already exists",
                        }
                    )
                    continue

            # Add to bulk
            bulk.insert_one(word_data)
            successful += 1

        except Exception as e:
            failed += 1
            errors.append(
                {
                    "word": word_data.get("text", "unknown"),
                    "error": str(e),
                }
            )

    # Execute bulk operation
    if successful > 0:
        result = await bulk.execute()
    else:
        result = {"insertedCount": 0}

    return BulkOperationResponse(
        total=len(request.words),
        successful=successful,
        failed=failed,
        errors=errors,
        results=result,
    )


@router.patch("/definitions/update", response_model=BulkOperationResponse)
@handle_api_errors
async def bulk_update_definitions(
    request: BulkDefinitionUpdate,
    repo: DefinitionRepository = Depends(lambda: DefinitionRepository()),
) -> BulkOperationResponse:
    """Bulk update definitions with optimized performance."""
    bulk = BulkOperationBuilder(Definition)
    successful = 0
    failed = 0
    errors = []

    for update in request.updates:
        try:
            definition_id = update.pop("id")

            # Version check if requested
            if request.validate_versions and "version" in update:
                current = await repo.get(PydanticObjectId(definition_id))
                if current.version != update.pop("version"):
                    failed += 1
                    errors.append(
                        {
                            "id": definition_id,
                            "error": "Version conflict",
                        }
                    )
                    continue

            # Add to bulk
            bulk.update_one(
                {"_id": PydanticObjectId(definition_id)},
                {"$set": update, "$inc": {"version": 1}},
            )
            successful += 1

        except Exception as e:
            failed += 1
            errors.append(
                {
                    "id": update.get("id", "unknown"),
                    "error": str(e),
                }
            )

    # Execute bulk operation
    if successful > 0:
        result = await bulk.execute()
    else:
        result = {"modifiedCount": 0}

    return BulkOperationResponse(
        total=len(request.updates),
        successful=successful,
        failed=failed,
        errors=errors,
        results=result,
    )


@router.delete("/delete", response_model=BulkOperationResponse)
@handle_api_errors
async def bulk_delete(
    request: BulkDeleteRequest,
) -> BulkOperationResponse:
    """Bulk delete documents with cascade support."""
    # Map model names to classes
    model_map = {
        "word": Word,
        "definition": Definition,
        "example": Example,
        "fact": Fact,
    }

    model_class = model_map[request.model]
    bulk = BulkOperationBuilder(model_class)

    # Convert IDs
    object_ids = [PydanticObjectId(id) for id in request.ids]

    # Handle cascade for words
    if request.model == "word" and request.cascade:
        # Delete related documents first
        for word_id in object_ids:
            await Definition.find({"word_id": str(word_id)}).delete()
            await Example.find({"word_id": str(word_id)}).delete()
            await Fact.find({"word_id": str(word_id)}).delete()

    # Build bulk delete
    for obj_id in object_ids:
        bulk.delete_one({"_id": obj_id})

    # Execute
    result = await bulk.execute()

    return BulkOperationResponse(
        total=len(request.ids),
        successful=result["deletedCount"],
        failed=len(request.ids) - result["deletedCount"],
        errors=[],
        results=result,
    )


@router.post("/examples/quality-update", response_model=BulkOperationResponse)
@handle_api_errors
async def bulk_update_example_quality(
    scores: dict[str, float] = Field(..., description="Example ID to quality score mapping"),
    repo: ExampleRepository = Depends(lambda: ExampleRepository()),
) -> BulkOperationResponse:
    """Bulk update example quality scores."""
    bulk = BulkOperationBuilder(Example)
    successful = 0

    for example_id, score in scores.items():
        bulk.update_one(
            {"_id": PydanticObjectId(example_id)},
            {"$set": {"quality_score": score}},
        )
        successful += 1

    result = await bulk.execute()

    return BulkOperationResponse(
        total=len(scores),
        successful=result["modifiedCount"],
        failed=len(scores) - result["modifiedCount"],
        errors=[],
        results=result,
    )
