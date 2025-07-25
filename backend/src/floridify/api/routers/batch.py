"""Batch operations for efficient bulk processing."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...core.lookup_pipeline import lookup_word_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


class BatchOperation(BaseModel):
    """Single operation in a batch request."""

    method: Literal["GET", "POST", "PATCH", "DELETE"]
    endpoint: str
    data: dict[str, Any] | None = None
    params: dict[str, Any] | None = None


class BatchRequest(BaseModel):
    """Batch request containing multiple operations."""

    operations: list[BatchOperation] = Field(
        min_length=1, max_length=100, description="List of operations to execute"
    )
    parallel: bool = Field(default=True, description="Execute operations in parallel")
    stop_on_error: bool = Field(default=False, description="Stop execution on first error")


class BatchResult(BaseModel):
    """Result of a batch operation."""

    index: int
    status: int
    data: Any | None = None
    error: str | None = None


class BatchResponse(BaseModel):
    """Response from batch operations."""

    results: list[BatchResult]
    summary: dict[str, int]


class BatchLookupRequest(BaseModel):
    """Batch word lookup request."""

    words: list[str] = Field(min_length=1, max_length=50, description="Words to lookup")
    providers: list[str] | None = None
    languages: list[str] | None = None
    force_refresh: bool = False


class BatchDefinitionUpdate(BaseModel):
    """Batch definition update."""

    word: str
    index: int
    updates: dict[str, Any]


class BatchDefinitionUpdateRequest(BaseModel):
    """Request for batch definition updates."""

    updates: list[BatchDefinitionUpdate] = Field(min_length=1, max_length=100)


@router.post("/lookup")
async def batch_lookup(request: BatchLookupRequest) -> dict[str, Any]:
    """Perform batch word lookup."""
    try:
        results = {}
        errors = {}

        # Process lookups - create actual async tasks for parallel execution
        tasks = []
        for word in request.words:
            task = asyncio.create_task(
                lookup_word_pipeline(
                    word=word,
                    providers=request.providers,
                    languages=request.languages,
                    force_refresh=request.force_refresh,
                )
            )
            tasks.append((word, task))

        # Execute in parallel - await the already created tasks
        for word, task in tasks:
            try:
                result = await task
                results[word] = result
            except Exception as e:
                errors[word] = str(e)
                logger.error(f"Error looking up '{word}': {e}")

        return {
            "results": results,
            "errors": errors,
            "summary": {
                "requested": len(request.words),
                "successful": len(results),
                "failed": len(errors),
            },
        }

    except Exception as e:
        logger.error(f"Batch lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/definitions/update")
async def batch_update_definitions(request: BatchDefinitionUpdateRequest) -> dict[str, Any]:
    """Batch update multiple definitions."""
    try:
        results = []

        for update in request.updates:
            try:
                # Get entry
                from ...storage.mongodb import get_synthesized_entry

                entry = await get_synthesized_entry(update.word)
                if not entry:
                    results.append(
                        {
                            "word": update.word,
                            "index": update.index,
                            "status": "error",
                            "error": "Word not found",
                        }
                    )
                    continue

                # Validate index
                if update.index >= len(entry.definitions):
                    results.append(
                        {
                            "word": update.word,
                            "index": update.index,
                            "status": "error",
                            "error": "Index out of range",
                        }
                    )
                    continue

                # Apply updates
                definition = entry.definitions[update.index]
                for field, value in update.updates.items():
                    if hasattr(definition, field):
                        setattr(definition, field, value)

                # Save
                from ...storage.mongodb import save_synthesized_entry

                await save_synthesized_entry(entry)

                results.append(
                    {
                        "word": update.word,
                        "index": update.index,
                        "status": "success",
                        "updated_fields": list(update.updates.keys()),
                    }
                )

            except Exception as e:
                results.append(
                    {"word": update.word, "index": update.index, "status": "error", "error": str(e)}
                )

        successful = sum(1 for r in results if r["status"] == "success")

        return {
            "results": results,
            "summary": {
                "total": len(request.updates),
                "successful": successful,
                "failed": len(request.updates) - successful,
            },
        }

    except Exception as e:
        logger.error(f"Batch update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_batch(request: BatchRequest) -> BatchResponse:
    """Execute arbitrary batch operations."""
    results = []

    async def execute_operation(index: int, op: BatchOperation) -> BatchResult:
        try:
            # This is a simplified implementation
            # In production, you'd route to actual endpoints
            return BatchResult(
                index=index,
                status=200,
                data={"message": f"Operation {op.method} {op.endpoint} executed"},
            )
        except Exception as e:
            return BatchResult(index=index, status=500, error=str(e))

    if request.parallel:
        # Execute in parallel
        tasks = [execute_operation(i, op) for i, op in enumerate(request.operations)]
        gather_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to results
        results: list[BatchResult] = []
        for i, result in enumerate(gather_results):
            if isinstance(result, Exception):
                results.append(BatchResult(index=i, status=500, error=str(result)))
            else:
                results.append(result)
    else:
        # Execute sequentially
        results = []
        for i, op in enumerate(request.operations):
            result = await execute_operation(i, op)
            results.append(result)

            if request.stop_on_error and result.status >= 400:
                break

    # Summary
    summary = {
        "total": len(results),
        "successful": sum(1 for r in results if 200 <= r.status < 300),
        "failed": sum(1 for r in results if r.status >= 400),
    }

    return BatchResponse(results=results, summary=summary)
