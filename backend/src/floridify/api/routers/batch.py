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


class BatchOperationResponse(BaseModel):
    """Response for batch operations with per-item results."""
    
    results: list[dict[str, Any]] = Field(..., description="Individual operation results")
    summary: dict[str, int] = Field(..., description="Operation summary statistics")
    errors: list[dict[str, Any]] = Field(default_factory=list, description="List of errors")
    
    @property
    def successful_count(self) -> int:
        """Count of successful operations."""
        return self.summary.get("successful", 0)
    
    @property
    def failed_count(self) -> int:
        """Count of failed operations."""
        return self.summary.get("failed", 0)
    
    @property
    def total_count(self) -> int:
        """Total number of operations."""
        return self.summary.get("total", len(self.results))


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


class BatchResponse(BatchOperationResponse):
    """Response from batch operations with detailed results."""
    pass  # Use all fields from BatchOperationResponse


class BatchLookupRequest(BaseModel):
    """Batch word lookup request."""

    words: list[str] = Field(min_length=1, max_length=50, description="Words to lookup")
    providers: list[str] | None = None
    languages: list[str] | None = None
    force_refresh: bool = False




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
        batch_results: list[BatchResult] = []
        for i, result in enumerate(gather_results):
            if isinstance(result, Exception):
                batch_results.append(BatchResult(index=i, status=500, error=str(result)))
            elif isinstance(result, BatchResult):
                batch_results.append(result)
        results = batch_results
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

    # Convert BatchResult to dict format for BatchOperationResponse
    result_dicts = [
        {
            "index": r.index,
            "status": r.status,
            "data": r.data,
            "error": r.error,
        }
        for r in results
    ]
    
    # Include errors in the response
    errors = [
        {"index": r.index, "error": r.error}
        for r in results
        if r.error
    ]
    
    return BatchResponse(
        results=result_dicts,
        summary=summary,
        errors=errors,
    )
