"""Batch collection for OpenAI API calls during synthesis.

This module provides a clean way to collect multiple AI calls and execute them
as a batch, without changing existing function signatures or return types.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

import openai
from pydantic import BaseModel

from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class CollectedRequest:
    """A collected request waiting to be batched."""
    
    id: str
    method_name: str
    prompt: str
    response_model: type[BaseModel]
    future: asyncio.Future[Any]
    kwargs: dict[str, Any] = field(default_factory=dict)


class BatchCollector:
    """Collects OpenAI API calls for batch execution.
    
    This acts as a proxy for the OpenAI connector, intercepting calls
    and collecting them for batch execution rather than executing immediately.
    """
    
    def __init__(self, openai_connector: Any, api_key: str):
        self.connector = openai_connector
        self.api_key = api_key
        self.collected_requests: list[CollectedRequest] = []
        self.client = openai.AsyncOpenAI(api_key=api_key)
        
    def collect(
        self,
        method_name: str,
        prompt: str,
        response_model: type[T],
        **kwargs: Any
    ) -> asyncio.Future[T]:
        """Collect a request and return a future for its result."""
        request_id = f"{method_name}_{uuid.uuid4().hex[:8]}"
        future: asyncio.Future[T] = asyncio.Future()
        
        request = CollectedRequest(
            id=request_id,
            method_name=method_name,
            prompt=prompt,
            response_model=response_model,
            future=future,
            kwargs=kwargs
        )
        
        self.collected_requests.append(request)
        logger.debug(f"Collected request {request_id} for {method_name}")
        
        return future
    
    def _create_batch_request(self, request: CollectedRequest, index: int) -> dict[str, Any]:
        """Convert a collected request to OpenAI batch format."""
        return {
            "custom_id": f"{request.id}_{index}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.connector.model_name,
                "messages": [{"role": "user", "content": request.prompt}],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": request.response_model.__name__.lower(),
                        "schema": request.response_model.model_json_schema(),
                        "strict": True
                    }
                },
                "temperature": self.connector.temperature,
                "max_tokens": self.connector.max_tokens,
                **request.kwargs
            }
        }
    
    async def execute_batch(self, timeout_minutes: int = 30) -> dict[str, Any]:
        """Execute all collected requests as a batch."""
        if not self.collected_requests:
            return {"status": "empty", "requests": 0}
        
        logger.info(f"Executing batch with {len(self.collected_requests)} requests")
        
        try:
            # Create batch file
            batch_file = self._create_batch_file()
            
            # Upload to OpenAI
            with open(batch_file, "rb") as f:
                file_response = await self.client.files.create(
                    file=f,
                    purpose="batch"
                )
            
            # Create batch job
            batch = await self.client.batches.create(
                input_file_id=file_response.id,
                endpoint="/v1/chat/completions",
                completion_window="24h"
            )
            
            logger.info(f"Created batch job: {batch.id}")
            
            # Wait for completion
            completed_batch = await self._wait_for_completion(batch.id, timeout_minutes)
            
            if completed_batch.status != "completed":
                raise Exception(f"Batch failed with status: {completed_batch.status}")
            
            # Process results
            if completed_batch.output_file_id:
                await self._process_results(completed_batch.output_file_id)
            
            return {
                "status": "completed",
                "batch_id": batch.id,
                "requests": len(self.collected_requests),
                "duration_seconds": getattr(completed_batch, "processing_time", 0)
            }
            
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            # Reject all futures with the error
            for request in self.collected_requests:
                if not request.future.done():
                    request.future.set_exception(e)
            
            return {
                "status": "failed",
                "error": str(e),
                "requests": len(self.collected_requests)
            }
    
    def _create_batch_file(self) -> Path:
        """Create JSONL batch file for OpenAI."""
        batch_dir = Path("/tmp/floridify_batches")
        batch_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_file = batch_dir / f"batch_{timestamp}.jsonl"
        
        with open(batch_file, "w") as f:
            for i, request in enumerate(self.collected_requests):
                batch_request = self._create_batch_request(request, i)
                f.write(json.dumps(batch_request) + "\n")
        
        logger.info(f"Created batch file: {batch_file}")
        return batch_file
    
    async def _wait_for_completion(
        self, 
        batch_id: str, 
        timeout_minutes: int
    ) -> Any:
        """Wait for batch to complete."""
        start_time = datetime.now()
        
        while True:
            batch = await self.client.batches.retrieve(batch_id)
            
            if batch.status in ["completed", "failed", "expired", "cancelled"]:
                return batch
            
            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            if elapsed > timeout_minutes:
                raise TimeoutError(f"Batch did not complete within {timeout_minutes} minutes")
            
            # Log progress
            if hasattr(batch, "request_counts") and batch.request_counts:
                total = getattr(batch.request_counts, "total", 0)
                completed = getattr(batch.request_counts, "completed", 0)
                if total > 0:
                    logger.info(f"Batch progress: {completed}/{total} ({completed/total*100:.0f}%)")
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def _process_results(self, output_file_id: str) -> None:
        """Process batch results and resolve futures."""
        # Download results
        response = await self.client.files.content(output_file_id)
        
        # Create lookup map
        request_map = {req.id: req for req in self.collected_requests}
        
        # Process each result
        for line in response.content.decode().strip().split("\n"):
            if not line:
                continue
                
            result = json.loads(line)
            custom_id = result.get("custom_id", "")
            
            # Extract original request ID
            request_id = "_".join(custom_id.split("_")[:-1])
            
            if request_id not in request_map:
                logger.warning(f"Unknown request ID in results: {request_id}")
                continue
            
            request = request_map[request_id]
            
            try:
                if "error" in result:
                    # Set exception on future
                    error_msg = result["error"].get("message", "Unknown error")
                    request.future.set_exception(Exception(f"OpenAI error: {error_msg}"))
                else:
                    # Parse and set result
                    response_body = result["response"]["body"]
                    content = response_body["choices"][0]["message"]["content"]
                    
                    # Parse JSON content to model
                    parsed = request.response_model.model_validate_json(content)
                    request.future.set_result(parsed)
                    
            except Exception as e:
                logger.error(f"Failed to process result for {request_id}: {e}")
                request.future.set_exception(e)
        
        # Set exception for any unresolved futures
        for request in self.collected_requests:
            if not request.future.done():
                request.future.set_exception(
                    Exception("No result found in batch response")
                )
    
    def __getattr__(self, name: str) -> Any:
        """Proxy method calls to create collected requests.
        
        This allows the BatchCollector to be used as a drop-in replacement
        for the OpenAI connector, intercepting method calls.
        """
        # Get the original method from the connector
        original_method = getattr(self.connector, name)
        
        # If it's not a synthesis method, just pass through
        if not asyncio.iscoroutinefunction(original_method):
            return original_method
        
        # For synthesis methods, return a wrapper that collects requests
        async def collecting_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract prompt and response model from the call
            # This is a bit hacky but works for our synthesis methods
            if "_make_structured_request" in str(original_method):
                # Direct call to _make_structured_request
                prompt = args[0] if args else kwargs.get("prompt", "")
                response_model = args[1] if len(args) > 1 else kwargs.get("response_model")
            else:
                # For higher-level methods, we need to intercept differently
                # Just execute normally for now
                return await original_method(*args, **kwargs)
            
            if prompt and response_model:
                # Collect the request and return a future
                return self.collect(name, prompt, response_model, **kwargs)
            else:
                # Fall back to normal execution
                return await original_method(*args, **kwargs)
        
        return collecting_wrapper


class BatchContext:
    """Context manager for batch collection during synthesis."""
    
    def __init__(self, openai_connector: Any, enabled: bool = True):
        self.original_connector = openai_connector
        self.enabled = enabled
        self.collector: BatchCollector | None = None
        
    def __enter__(self) -> BatchCollector | Any:
        """Enter batch collection context."""
        if self.enabled:
            # Create collector with the same API key
            self.collector = BatchCollector(
                self.original_connector,
                self.original_connector.api_key
            )
            return self.collector
        else:
            # Return original connector if batching disabled
            return self.original_connector
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit batch collection context."""
        # Nothing to clean up
        pass
    
    async def __aenter__(self) -> BatchCollector | Any:
        """Async enter."""
        return self.__enter__()
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async exit."""
        self.__exit__(exc_type, exc_val, exc_tb)