"""Batch processing support for OpenAI API integration."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class BatchPromise(Generic[T]):
    """Promise for a batch request result that will be resolved later."""
    
    def __init__(self, request_id: str, response_model: type[T]):
        self.request_id = request_id
        self.response_model = response_model
        self._future: asyncio.Future[T] = asyncio.Future()
        self._resolved = False
    
    def resolve(self, result: Any) -> None:
        """Resolve the promise with a result."""
        if self._resolved:
            return
            
        self._resolved = True
        
        if isinstance(result, Exception):
            self._future.set_exception(result)
        elif result is None:
            self._future.set_exception(ValueError(f"No result found for {self.request_id}"))
        else:
            try:
                # Handle different result formats
                if isinstance(result, dict) and "choices" in result:
                    # Standard OpenAI response format
                    content = result["choices"][0]["message"]["content"]
                    if isinstance(content, str):
                        # Parse JSON string to dict first
                        content = json.loads(content)
                    parsed = self.response_model.model_validate(content)
                elif isinstance(result, self.response_model):
                    # Already parsed
                    parsed = result
                else:
                    # Direct validation
                    parsed = self.response_model.model_validate(result)
                    
                self._future.set_result(parsed)
            except Exception as e:
                logger.error(f"Failed to parse result for {self.request_id}: {e}")
                self._future.set_exception(e)
    
    def __await__(self) -> Any:
        return self._future.__await__()
    
    @property
    def done(self) -> bool:
        """Check if the promise has been resolved."""
        return self._future.done()


@dataclass
class BatchRequest:
    """Represents a single request in a batch."""
    
    request_id: str
    custom_id: str
    prompt: str
    response_model: type[BaseModel]
    model: str
    temperature: float | None = None
    max_tokens: int = 1000
    kwargs: dict[str, Any] = field(default_factory=dict)
    
    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI batch request format."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": self.prompt}
        ]
        
        body = {
            "model": self.model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": self.response_model.__name__.lower(),
                    "schema": self.response_model.model_json_schema(),
                    "strict": True
                }
            },
            "max_tokens": self.max_tokens,
        }
        
        if self.temperature is not None:
            body["temperature"] = self.temperature
            
        # Add any additional kwargs
        body.update(self.kwargs)
        
        return {
            "custom_id": self.custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": body
        }


class BatchAccumulator:
    """Accumulates requests for batch processing."""
    
    def __init__(self, batch_name: str = "synthesis_batch"):
        self.batch_name = batch_name
        self.requests: list[BatchRequest] = []
        self.promises: dict[str, BatchPromise[Any]] = {}
        self.request_map: dict[str, int] = {}
        self._request_counter = 0
    
    def add_request(
        self,
        prompt: str,
        response_model: type[T],
        model: str,
        temperature: float | None = None,
        max_tokens: int = 1000,
        **kwargs: Any
    ) -> BatchPromise[T]:
        """Add a request and return a promise for the future result."""
        # Generate unique request ID
        request_id = self._generate_request_id(prompt, response_model, kwargs)
        custom_id = f"{self.batch_name}_{self._request_counter:06d}"
        self._request_counter += 1
        
        # Create batch request
        batch_request = BatchRequest(
            request_id=request_id,
            custom_id=custom_id,
            prompt=prompt,
            response_model=response_model,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            kwargs=kwargs
        )
        
        # Store request and create promise
        self.requests.append(batch_request)
        self.request_map[custom_id] = len(self.requests) - 1
        
        promise = BatchPromise(custom_id, response_model)
        self.promises[custom_id] = promise
        
        logger.debug(f"Added batch request {custom_id} for {response_model.__name__}")
        
        return promise
    
    def _generate_request_id(
        self, 
        prompt: str, 
        response_model: type[BaseModel], 
        kwargs: dict[str, Any]
    ) -> str:
        """Generate a unique ID for the request."""
        # Create a hash of the key components
        key_parts = [
            prompt[:100],  # First 100 chars of prompt
            response_model.__name__,
            str(sorted(kwargs.items()))
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    def create_batch_file(self, output_dir: Path) -> Path:
        """Create a JSONL batch file for OpenAI."""
        if not self.requests:
            raise ValueError("No requests to batch")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_file = output_dir / f"{self.batch_name}_{timestamp}.jsonl"
        
        # Ensure directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write requests in JSONL format
        with open(batch_file, "w", encoding="utf-8") as f:
            for request in self.requests:
                openai_request = request.to_openai_format()
                f.write(json.dumps(openai_request) + "\n")
        
        logger.info(f"Created batch file with {len(self.requests)} requests: {batch_file}")
        return batch_file
    
    def resolve_results(self, results_file: Path) -> int:
        """Resolve promises with results from OpenAI batch file."""
        resolved_count = 0
        
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                        
                    result = json.loads(line)
                    custom_id = result.get("custom_id")
                    
                    if custom_id not in self.promises:
                        logger.warning(f"Unknown custom_id in results: {custom_id}")
                        continue
                    
                    promise = self.promises[custom_id]
                    
                    # Check for errors
                    if "error" in result:
                        error_msg = result["error"].get("message", "Unknown error")
                        promise.resolve(Exception(f"OpenAI error: {error_msg}"))
                    else:
                        # Extract response
                        response_body = result.get("response", {}).get("body", {})
                        promise.resolve(response_body)
                    
                    resolved_count += 1
            
            # Resolve any remaining promises with errors
            for custom_id, promise in self.promises.items():
                if not promise.done:
                    promise.resolve(Exception("No result found in batch response"))
                    
        except Exception as e:
            logger.error(f"Error resolving batch results: {e}")
            # Resolve all promises with error
            for promise in self.promises.values():
                if not promise.done:
                    promise.resolve(e)
        
        logger.info(f"Resolved {resolved_count}/{len(self.promises)} promises")
        return resolved_count
    
    def clear(self) -> None:
        """Clear all accumulated requests and promises."""
        self.requests.clear()
        self.promises.clear()
        self.request_map.clear()
        self._request_counter = 0
    
    @property
    def size(self) -> int:
        """Get the number of accumulated requests."""
        return len(self.requests)
    
    @property
    def is_empty(self) -> bool:
        """Check if accumulator is empty."""
        return len(self.requests) == 0


class BatchExecutor:
    """Executes accumulated batch requests using OpenAI Batch API."""
    
    def __init__(self, client: AsyncOpenAI, output_dir: Path | None = None):
        self.client = client
        self.output_dir = output_dir or Path("/tmp/floridify_batches")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def execute_batch(
        self, 
        accumulator: BatchAccumulator,
        wait_for_completion: bool = True,
        timeout_minutes: int = 30
    ) -> dict[str, Any]:
        """Execute a batch and optionally wait for completion."""
        if accumulator.is_empty:
            return {"status": "empty", "message": "No requests to process"}
        
        try:
            # Create batch file
            batch_file = accumulator.create_batch_file(self.output_dir)
            
            # Upload to OpenAI
            with open(batch_file, "rb") as f:
                file_response = await self.client.files.create(
                    file=f,
                    purpose="batch"
                )
            
            logger.info(f"Uploaded batch file: {file_response.id}")
            
            # Create batch job
            batch = await self.client.batches.create(
                input_file_id=file_response.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
                metadata={
                    "name": accumulator.batch_name,
                    "requests": str(accumulator.size),
                    "created_at": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Created batch job: {batch.id}")
            
            if not wait_for_completion:
                return {
                    "status": "submitted",
                    "batch_id": batch.id,
                    "file_id": file_response.id,
                    "requests": accumulator.size
                }
            
            # Wait for completion
            result = await self._wait_for_batch(batch.id, timeout_minutes)
            
            if result["status"] == "completed":
                # Download and process results
                output_file = await self._download_results(
                    result["output_file_id"],
                    batch.id
                )
                
                # Resolve promises
                resolved = accumulator.resolve_results(output_file)
                
                return {
                    "status": "completed",
                    "batch_id": batch.id,
                    "requests": accumulator.size,
                    "resolved": resolved,
                    "output_file": str(output_file)
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            
            # Resolve all promises with error
            for promise in accumulator.promises.values():
                if not promise.done:
                    promise.resolve(e)
            
            return {
                "status": "failed",
                "error": str(e),
                "requests": accumulator.size
            }
    
    async def _wait_for_batch(
        self, 
        batch_id: str, 
        timeout_minutes: int
    ) -> dict[str, Any]:
        """Wait for batch to complete with timeout."""
        start_time = datetime.now()
        check_interval = 30  # seconds
        
        while True:
            # Check batch status
            batch = await self.client.batches.retrieve(batch_id)
            
            if batch.status == "completed":
                return {
                    "status": "completed",
                    "output_file_id": batch.output_file_id,
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                }
            elif batch.status in ["failed", "expired", "cancelled"]:
                return {
                    "status": batch.status,
                    "error": f"Batch {batch.status}",
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                }
            
            # Check timeout
            elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
            if elapsed_minutes > timeout_minutes:
                return {
                    "status": "timeout",
                    "error": f"Batch did not complete within {timeout_minutes} minutes",
                    "batch_status": batch.status
                }
            
            # Log progress if available
            if hasattr(batch, "request_counts") and batch.request_counts:
                counts = batch.request_counts
                total = getattr(counts, "total", 0)
                completed = getattr(counts, "completed", 0)
                if total > 0:
                    progress = (completed / total) * 100
                    logger.info(f"Batch progress: {completed}/{total} ({progress:.1f}%)")
            
            # Wait before next check
            await asyncio.sleep(check_interval)
    
    async def _download_results(self, file_id: str, batch_id: str) -> Path:
        """Download batch results file."""
        response = await self.client.files.content(file_id)
        
        output_file = self.output_dir / f"results_{batch_id}.jsonl"
        with open(output_file, "wb") as f:
            f.write(response.content)
        
        logger.info(f"Downloaded results to: {output_file}")
        return output_file