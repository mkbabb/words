"""Generalized Server-Sent Events streaming infrastructure."""

import asyncio
import json
from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any

from fastapi.responses import StreamingResponse

from ..utils.logging import get_logger
from .state_tracker import StateTracker

logger = get_logger(__name__)


def _send_chunked_completion(result_data: dict[str, Any]) -> Generator[str]:
    """Send large completion data in manageable chunks."""
    # Split the result into logical chunks (definitions, examples, etc.)

    # First, send completion start with proper event type
    completion_start = {
        "message": "Sending definition data in chunks",
        "total_definitions": len(result_data.get("definitions", [])),
    }
    yield f"event: completion_start\ndata: {json.dumps(completion_start)}\n\n"

    # Send basic info first (word, id, etymology)
    basic_info = {
        "chunk_type": "basic_info",
        "data": {
            "word": result_data.get("word"),
            "id": result_data.get("id"),
            "last_updated": result_data.get("last_updated"),
            "model_info": result_data.get("model_info"),
            "pronunciation": result_data.get("pronunciation"),
            "etymology": result_data.get("etymology"),
            "images": result_data.get("images", []),
        },
    }
    yield f"event: completion_chunk\ndata: {json.dumps(basic_info)}\n\n"

    # Send definitions in smaller chunks (avoid sending all examples at once)
    definitions = result_data.get("definitions", [])
    for i, definition in enumerate(definitions):
        # Send definition without examples first
        def_chunk = {
            "chunk_type": "definition",
            "definition_index": i,
            "data": {k: v for k, v in definition.items() if k != "examples"},
        }
        yield f"event: completion_chunk\ndata: {json.dumps(def_chunk)}\n\n"

        # Send examples in smaller batches (10 at a time)
        examples = definition.get("examples", [])
        batch_size = 10
        for batch_start in range(0, len(examples), batch_size):
            batch_examples = examples[batch_start : batch_start + batch_size]
            examples_chunk = {
                "chunk_type": "examples",
                "definition_index": i,
                "batch_start": batch_start,
                "data": batch_examples,
            }
            yield f"event: completion_chunk\ndata: {json.dumps(examples_chunk)}\n\n"

    # Send final completion
    final_completion = {"message": "Process completed successfully", "chunked": True}
    yield f"event: complete\ndata: {json.dumps(final_completion)}\n\n"


class SSEEvent:
    """Server-Sent Event data structure."""

    def __init__(self, event_type: str, data: dict[str, Any], event_id: str | None = None):
        self.event_type = event_type
        self.data = data
        self.event_id = event_id

    def format(self) -> str:
        """Format as SSE string (per SSE spec: each event ends with \\n\\n)."""
        lines = []

        if self.event_id:
            lines.append(f"id: {self.event_id}")

        lines.append(f"event: {self.event_type}")
        lines.append(f"data: {json.dumps(self.data)}")

        # SSE spec requires double newline to terminate event
        return "\n".join(lines) + "\n\n"


class StreamingProgressHandler:
    """Handles streaming progress updates for any process."""

    def __init__(self, state_tracker: StateTracker) -> None:
        self.state_tracker = state_tracker
        self.logger = get_logger(f"{__name__}.{state_tracker.category}")

    async def stream_progress(
        self,
        process_func: Callable[[], Any],
        *,
        include_stage_definitions: bool = True,
        include_completion_data: bool = True,
    ) -> AsyncGenerator[str]:
        """Stream progress updates from a StateTracker during process execution.

        Args:
            process_func: Async function that performs the work and updates the state tracker
            include_stage_definitions: Whether to send stage definitions at start
            include_completion_data: Whether to include process result in completion event

        Yields:
            SSE-formatted strings for streaming to client

        """
        try:
            # Send initial configuration if requested
            if include_stage_definitions:
                config_event = SSEEvent(
                    event_type="config",
                    data={
                        "category": self.state_tracker.category,
                        "stages": [
                            stage.model_dump()
                            for stage in self.state_tracker.get_stage_definitions()
                        ],
                    },
                )
                yield config_event.format()

            # Start progress monitoring task
            progress_task = asyncio.create_task(self._monitor_progress())

            # Execute the process
            try:
                result = await process_func()

                # Send completion event
                completion_data = {
                    "type": "complete",
                    "message": "Process completed successfully",
                }

                if include_completion_data and result is not None:
                    completion_data["result"] = result.model_dump(mode="json")

                completion_event = SSEEvent(event_type="complete", data=completion_data)
                yield completion_event.format()

            except Exception as e:
                self.logger.error(f"Process failed: {e}")
                await self.state_tracker.update_error(str(e))

                error_event = SSEEvent(
                    event_type="error",
                    data={
                        "type": "error",
                        "message": str(e),
                        "details": {"exception_type": type(e).__name__},
                    },
                )
                yield error_event.format()

            finally:
                # Cancel progress monitoring
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            error_event = SSEEvent(
                event_type="error",
                data={"type": "error", "message": f"Streaming error: {e!s}"},
            )
            yield error_event.format()

    async def _monitor_progress(self) -> None:
        """Monitor the state tracker and yield progress events."""
        try:
            async with self.state_tracker.subscribe() as queue:
                while True:
                    try:
                        # Wait for state update with timeout
                        state = await asyncio.wait_for(queue.get(), timeout=1.0)

                        # Convert state to SSE event
                        # This would need to be yielded to the outer generator
                        # For now, we'll use a different approach in the main method

                        if state.is_complete or state.error:
                            break

                    except TimeoutError:
                        # No state update in timeout period, continue monitoring
                        continue

        except asyncio.CancelledError:
            self.logger.debug("Progress monitoring cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Progress monitoring error: {e}")


async def create_streaming_response(
    state_tracker: StateTracker,
    process_func: Callable[[], Any],
    *,
    include_stage_definitions: bool = True,
    include_completion_data: bool = True,
) -> StreamingResponse:
    """Create a StreamingResponse for any process with progress tracking.

    This is the main entry point for creating streaming responses.

    Args:
        state_tracker: StateTracker instance for the process
        process_func: Async function that performs the work
        include_stage_definitions: Whether to send stage definitions at start
        include_completion_data: Whether to include result data in completion

    Returns:
        StreamingResponse with SSE content

    """

    async def event_generator() -> AsyncGenerator[str]:
        """Generate SSE events by monitoring state tracker and running process."""
        try:
            # Send initial configuration if requested
            if include_stage_definitions:
                config_event = SSEEvent(
                    event_type="config",
                    data={
                        "category": state_tracker.category,
                        "stages": [
                            stage.model_dump() for stage in state_tracker.get_stage_definitions()
                        ],
                    },
                )
                yield config_event.format()
                await asyncio.sleep(0)  # Yield control to event loop

            # Reset state tracker
            state_tracker.reset()

            # Start progress monitoring and process execution concurrently
            async def monitor_and_yield() -> AsyncGenerator[str]:
                """Monitor state tracker and yield progress events."""
                async with state_tracker.subscribe() as queue:
                    while True:
                        try:
                            state = await asyncio.wait_for(queue.get(), timeout=0.1)

                            progress_event = SSEEvent(
                                event_type="progress",
                                data=state.model_dump_optimized(),
                            )
                            yield progress_event.format()

                            if state.is_complete or state.error:
                                break

                        except TimeoutError:
                            continue

            # Start monitoring task
            monitor_task = asyncio.create_task(monitor_and_yield().__anext__())

            try:
                # Execute process and monitor concurrently
                result = await process_func()

                # Yield any remaining progress events
                try:
                    while True:
                        event = await asyncio.wait_for(monitor_task, timeout=0.5)
                        yield event
                        monitor_task = asyncio.create_task(monitor_and_yield().__anext__())
                except TimeoutError:
                    pass

                # Send completion event
                completion_data = {
                    "type": "complete",
                    "message": "Process completed successfully",
                }

                if include_completion_data and result is not None:
                    completion_data["result"] = result.model_dump(mode="json")

                completion_event = SSEEvent(event_type="complete", data=completion_data)
                yield completion_event.format()

            except Exception as e:
                logger.error(f"Process failed: {e}")
                await state_tracker.update_error(str(e))

                error_event = SSEEvent(
                    event_type="error",
                    data={
                        "type": "error",
                        "message": str(e),
                    },
                )
                yield error_event.format()

            finally:
                # Cancel monitoring task
                if not monitor_task.done():
                    monitor_task.cancel()
                    try:
                        await monitor_task
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            logger.error(f"Streaming generator error: {e}")
            error_event = SSEEvent(
                event_type="error",
                data={"type": "error", "message": f"Streaming error: {e!s}"},
            )
            yield error_event.format()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
