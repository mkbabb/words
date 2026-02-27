"""Generalized Server-Sent Events streaming infrastructure."""

import asyncio
import json
import time
from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any

from fastapi.responses import StreamingResponse

from ..utils.logging import get_logger
from .state_tracker import StateTracker

logger = get_logger(__name__)

# SSE configuration
SSE_HEARTBEAT_INTERVAL = 30  # seconds between heartbeat pings
SSE_STREAM_TIMEOUT = 300  # 5 minute overall stream timeout


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
        """Generate SSE events by running process in background and streaming progress.

        Features:
        - Heartbeat pings every 30s to keep proxies alive
        - 5-minute overall stream timeout
        - Cancels background process when client disconnects (generator closes)
        """
        process_task: asyncio.Task | None = None
        stream_start = time.monotonic()

        try:
            # Send initial configuration
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

            # Reset state tracker
            state_tracker.reset()

            # Subscribe to state updates before starting the process
            # so we don't miss early events
            async with state_tracker.subscribe() as queue:
                # Run the process in a background task
                process_result: Any = None
                process_error: Exception | None = None

                async def run_process() -> None:
                    nonlocal process_result, process_error
                    try:
                        process_result = await process_func()
                    except asyncio.CancelledError:
                        logger.info("Process task cancelled (client disconnected)")
                        raise
                    except Exception as e:
                        process_error = e

                process_task = asyncio.create_task(run_process())
                last_heartbeat = time.monotonic()

                # Stream progress events until the process completes
                while not process_task.done():
                    # Check overall stream timeout
                    elapsed = time.monotonic() - stream_start
                    if elapsed > SSE_STREAM_TIMEOUT:
                        logger.warning(f"SSE stream timed out after {elapsed:.0f}s")
                        process_task.cancel()
                        try:
                            await process_task
                        except asyncio.CancelledError:
                            pass
                        error_event = SSEEvent(
                            event_type="error",
                            data={"type": "error", "message": "Stream timeout exceeded"},
                        )
                        yield error_event.format()
                        return

                    try:
                        state = await asyncio.wait_for(queue.get(), timeout=0.2)
                        progress_event = SSEEvent(
                            event_type="progress",
                            data=state.model_dump_optimized(),
                        )
                        yield progress_event.format()
                        last_heartbeat = time.monotonic()

                        if state.is_complete or state.error:
                            break
                    except TimeoutError:
                        # Send heartbeat ping if no events for 30s
                        now = time.monotonic()
                        if now - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                            yield ": ping\n\n"
                            last_heartbeat = now
                        continue

                # Process finished — drain any remaining queued events
                while not queue.empty():
                    try:
                        state = queue.get_nowait()
                        progress_event = SSEEvent(
                            event_type="progress",
                            data=state.model_dump_optimized(),
                        )
                        yield progress_event.format()
                    except asyncio.QueueEmpty:
                        break

                # Ensure the task is awaited (propagates cancellation cleanly)
                if not process_task.done():
                    await process_task

                # Send completion or error
                if process_error is not None:
                    logger.error(f"Process failed: {process_error}")
                    await state_tracker.update_error(str(process_error))
                    error_event = SSEEvent(
                        event_type="error",
                        data={
                            "type": "error",
                            "message": str(process_error),
                        },
                    )
                    yield error_event.format()
                else:
                    completion_data = {
                        "type": "complete",
                        "message": "Process completed successfully",
                    }
                    if include_completion_data and process_result is not None:
                        completion_data["result"] = process_result.model_dump(mode="json")

                    completion_event = SSEEvent(event_type="complete", data=completion_data)
                    yield completion_event.format()

        except GeneratorExit:
            # Client disconnected - cancel background process
            logger.info("SSE client disconnected, cancelling background process")
            if process_task and not process_task.done():
                process_task.cancel()
                try:
                    await process_task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.error(f"Streaming generator error: {e}")
            error_event = SSEEvent(
                event_type="error",
                data={"type": "error", "message": f"Streaming error: {e!s}"},
            )
            yield error_event.format()
        finally:
            # Ensure process task is cleaned up
            if process_task and not process_task.done():
                process_task.cancel()
                try:
                    await process_task
                except (asyncio.CancelledError, Exception):
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
