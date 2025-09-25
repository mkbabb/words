"""Batch processing for OpenAI API calls with 50% cost reduction.

This module provides a context manager approach to batch multiple OpenAI API calls
into a single batch request, maintaining compatibility with existing code.
"""

import asyncio
import json
import tempfile
import time
import types
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar
from uuid import uuid4

from openai import AsyncOpenAI
from pydantic import BaseModel

from ..utils.logging import get_logger
from .connector import OpenAIConnector

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class AIBatchRequest:
    """Represents a single request in an AI batch with its associated future."""

    custom_id: str
    prompt: str
    response_model: type[BaseModel]
    kwargs: dict[str, Any]
    future: asyncio.Future[Any] = field(default_factory=asyncio.Future)


class BatchCollector:
    """Collects OpenAI API requests for batch processing."""

    def __init__(self) -> None:
        self.requests: list[AIBatchRequest] = []
        self._id_counter = 0

    def add_request(
        self,
        prompt: str,
        response_model: type[BaseModel],
        **kwargs: Any,
    ) -> asyncio.Future[Any]:
        """Add a request to the batch and return a future for the result."""
        self._id_counter += 1
        custom_id = f"req-{self._id_counter}-{uuid4().hex[:8]}"

        request = AIBatchRequest(
            custom_id=custom_id,
            prompt=prompt,
            response_model=response_model,
            kwargs=kwargs,
        )
        self.requests.append(request)

        return request.future

    def prepare_batch_file(self) -> Path | None:
        """Prepare JSONL file for OpenAI Batch API."""
        if not self.requests:
            return None

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for req in self.requests:
                # Build messages
                messages = [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": req.prompt},
                ]

                # Build batch request
                batch_entry: dict[str, Any] = {
                    "custom_id": req.custom_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": req.kwargs.get("model", "gpt-4o-mini"),
                        "messages": messages,
                        "max_tokens": req.kwargs.get("max_tokens", 500),
                        "temperature": req.kwargs.get("temperature", 0.7),
                    },
                }

                # Add response format if using structured output
                if hasattr(req.response_model, "model_json_schema"):
                    batch_entry["body"]["response_format"] = {
                        "type": "json_schema",
                        "json_schema": {
                            "name": req.response_model.__name__,
                            "schema": req.response_model.model_json_schema(),
                        },
                    }

                f.write(json.dumps(batch_entry) + "\n")

            return Path(f.name)

    def clear(self) -> None:
        """Clear all collected requests."""
        self.requests.clear()
        self._id_counter = 0


class BatchExecutor:
    """Executes batch requests using OpenAI Batch API."""

    def __init__(self, client: AsyncOpenAI) -> None:
        self.client = client

    async def execute_batch(self, batch_file: Path, check_interval: int = 1) -> dict[str, Any]:
        """Upload and execute a batch file, returning results mapped by custom_id."""
        try:
            # Upload file
            logger.info(f"📎 Uploading batch file: {batch_file}")
            with open(batch_file, "rb") as f:
                uploaded_file = await self.client.files.create(file=f, purpose="batch")
            logger.info(f"✅ File uploaded: {uploaded_file.id}")

            # Create batch job
            logger.info("🔨 Creating batch job")
            batch_job = await self.client.batches.create(
                input_file_id=uploaded_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h",
            )

            # Wait for completion
            logger.info(f"🎫 Batch job created: {batch_job.id}")
            logger.info(f"⏳ Waiting for batch completion (checking every {check_interval}s)")
            completed_job = await self._wait_for_completion(batch_job.id, check_interval)
            logger.info("✅ Batch completed successfully")

            # Download and parse results
            if completed_job.output_file_id:
                results = await self._download_results(completed_job.output_file_id)
                return self._map_results_by_id(results)
            logger.error(f"Batch job {batch_job.id} completed without output file")
            return {}

        finally:
            # Clean up temp file
            if batch_file.exists():
                batch_file.unlink()

    async def _wait_for_completion(self, batch_id: str, check_interval: int) -> Any:
        """Wait for batch job to complete."""
        start_time = time.time()
        check_count = 0

        while True:
            check_count += 1
            batch_job = await self.client.batches.retrieve(batch_id)
            elapsed = time.time() - start_time
            logger.info(
                f"🔄 Check #{check_count} - Batch {batch_id} status: {batch_job.status} (elapsed: {elapsed:.1f}s)",
            )

            if batch_job.status == "completed":
                return batch_job
            if batch_job.status in ["failed", "expired", "cancelled"]:
                raise Exception(f"Batch job failed: {batch_job.status}")

            await asyncio.sleep(check_interval)

    async def _download_results(self, file_id: str) -> list[dict[str, Any]]:
        """Download and parse batch results."""
        content = await self.client.files.content(file_id)

        results = []
        for line in content.content.decode("utf-8").strip().split("\n"):
            if line:
                results.append(json.loads(line))

        return results

    def _map_results_by_id(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Map results by custom_id for easy lookup."""
        mapped = {}

        for result in results:
            custom_id = result.get("custom_id")
            if custom_id:
                mapped[custom_id] = result

        return mapped


class BatchContext:
    """Context manager for batch processing OpenAI requests."""

    def __init__(self, connector: OpenAIConnector) -> None:
        self.connector = connector
        self.collector = BatchCollector()
        self.executor = BatchExecutor(connector.client)
        self._original_method: Callable[..., Awaitable[Any]] | None = None

    async def __aenter__(self) -> "BatchContext":
        """Enter batch mode by patching the connector."""
        logger.info("🚀 Entering batch synthesis context")
        self._original_method = self.connector._make_structured_request

        # Store reference to self for the wrapper
        batch_context = self

        # Create wrapper that collects requests
        async def batch_wrapper(
            connector: OpenAIConnector,
            prompt: str,
            response_model: type[BaseModel],
            **kwargs: Any,
        ) -> Any:
            # Add to batch and return future
            future = batch_context.collector.add_request(prompt, response_model, **kwargs)
            logger.debug(
                f"📥 Collected request #{len(batch_context.collector.requests)}: {response_model.__name__}",
            )
            return await batch_context._await_future(future)

        # Patch the method
        self.connector._make_structured_request = types.MethodType(batch_wrapper, self.connector)
        logger.info("✅ Batch mode activated - collecting API requests")
        return self

    async def _await_future(self, future: asyncio.Future[Any]) -> Any:
        """Helper to await a future."""
        return await future

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit batch mode and execute collected requests."""
        logger.info(f"🏁 Exiting batch context with {len(self.collector.requests)} requests")

        # Restore original method
        if self._original_method:
            self.connector._make_structured_request = self._original_method
            logger.debug("🔄 Restored original API method")

        # Execute batch if no exception
        if exc_type is None:
            await self.execute()
        else:
            logger.error(f"❌ Batch context exited with error: {exc_type.__name__}: {exc_val}")

    async def execute(self) -> None:
        """Execute all collected requests as a batch."""
        if not self.collector.requests:
            logger.info("📭 No requests to batch")
            return

        logger.info(f"🎯 Executing batch with {len(self.collector.requests)} requests")

        # Log request types
        request_types: dict[str, int] = {}
        for req in self.collector.requests:
            model_name = req.response_model.__name__
            request_types[model_name] = request_types.get(model_name, 0) + 1
        logger.info(f"📊 Request breakdown: {request_types}")

        # Prepare batch file
        batch_file = self.collector.prepare_batch_file()
        if not batch_file:
            logger.error("❌ Failed to prepare batch file")
            return

        try:
            # Execute batch
            logger.info("📤 Submitting batch to OpenAI API")
            results = await self.executor.execute_batch(batch_file)
            logger.info(f"📥 Received {len(results)} results from batch")

            # Resolve futures with results
            for request in self.collector.requests:
                result = results.get(request.custom_id)

                if result and result.get("response", {}).get("status_code") == 200:
                    try:
                        # Extract content from response
                        content = result["response"]["body"]["choices"][0]["message"]["content"]

                        # Parse JSON if using structured output
                        if hasattr(request.response_model, "model_validate_json"):
                            parsed = request.response_model.model_validate_json(content)
                            request.future.set_result(parsed)
                        else:
                            request.future.set_result(content)
                    except Exception as e:
                        logger.error(f"Failed to parse result for {request.custom_id}: {e}")
                        request.future.set_exception(e)
                else:
                    error = (
                        result.get("response", {}).get("error", "Unknown error")
                        if result
                        else "No result found"
                    )
                    logger.error(f"Request {request.custom_id} failed: {error}")
                    request.future.set_exception(Exception(f"Batch request failed: {error}"))

        except Exception as e:
            # Set exception on all futures
            logger.error(f"Batch execution failed: {e}")
            for request in self.collector.requests:
                if not request.future.done():
                    request.future.set_exception(e)

        finally:
            # Clear collector
            self.collector.clear()


@asynccontextmanager
async def batch_synthesis(connector: OpenAIConnector) -> AsyncIterator[BatchContext]:
    """Context manager for batch synthesis operations.

    Usage:
        async with batch_synthesis(ai_connector) as batch:
            # All OpenAI calls within this block will be batched
            await enhance_definitions_parallel(definitions, word, ai_connector)
            # Batch execution happens automatically on exit
    """
    context = BatchContext(connector)
    async with context:
        yield context
