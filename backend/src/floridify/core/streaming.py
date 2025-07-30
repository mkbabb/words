"""Generalized Server-Sent Events streaming infrastructure."""

import asyncio
import json
from collections.abc import AsyncGenerator, Callable
from typing import Any

from beanie import PydanticObjectId
from bson import ObjectId
from fastapi.responses import StreamingResponse

from ..utils.logging import get_logger
from .state_tracker import StateTracker

logger = get_logger(__name__)


class SSEEvent:
    """Server-Sent Event data structure."""

    def __init__(self, event_type: str, data: dict[str, Any], event_id: str | None = None):
        self.event_type = event_type
        self.data = data
        self.event_id = event_id
    
    @staticmethod
    def _json_serializer(obj: Any) -> str:
        """Custom JSON serializer for ObjectId types."""
        if isinstance(obj, (ObjectId, PydanticObjectId)):
            return str(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def format(self) -> str:
        """Format as SSE string."""
        lines = []

        if self.event_id:
            lines.append(f"id: {self.event_id}")

        lines.append(f"event: {self.event_type}")
        lines.append(f"data: {json.dumps(self.data, default=self._json_serializer)}")
        lines.append("")  # Empty line to end event

        return "\n".join(lines)


class StreamingProgressHandler:
    """Handles streaming progress updates for any process."""

    def __init__(self, state_tracker: StateTracker):
        self.state_tracker = state_tracker
        self.logger = get_logger(f"{__name__}.{state_tracker.category}")

    async def stream_progress(
        self,
        process_func: Callable[[], Any],
        *,
        include_stage_definitions: bool = True,
        include_completion_data: bool = True,
    ) -> AsyncGenerator[str, None]:
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
                    completion_data["result"] = result

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
                event_type="error", data={"type": "error", "message": f"Streaming error: {str(e)}"}
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

    async def event_generator() -> AsyncGenerator[str, None]:
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

            # Reset state tracker
            state_tracker.reset()

            # Start progress monitoring and process execution concurrently
            async def monitor_and_yield() -> AsyncGenerator[str, None]:
                """Monitor state tracker and yield progress events."""
                async with state_tracker.subscribe() as queue:
                    while True:
                        try:
                            state = await asyncio.wait_for(queue.get(), timeout=0.1)

                            progress_event = SSEEvent(
                                event_type="progress", data=state.model_dump_optimized()
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
                        event = await asyncio.wait_for(monitor_task, timeout=0.1)
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
                    completion_data["result"] = result

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
                event_type="error", data={"type": "error", "message": f"Streaming error: {str(e)}"}
            )
            yield error_event.format()

    # Simplified event generator that works with the existing pattern
    async def simple_generator() -> AsyncGenerator[str, None]:
        """Simplified generator that follows the existing SSE pattern."""
        try:
            # Send initial stage configuration
            if include_stage_definitions:
                stages_data = [
                    {
                        "progress": stage.progress,
                        "label": stage.label,
                        "description": stage.description,
                    }
                    for stage in state_tracker.get_stage_definitions()
                ]
                config_data = {
                    "type": "config",
                    "category": state_tracker.category,
                    "stages": stages_data,
                }
                yield f"data: {json.dumps(config_data, default=SSEEvent._json_serializer)}\n\n"

            # Reset state tracker
            state_tracker.reset()

            # Start process and monitor states
            process_task = asyncio.create_task(process_func())

            try:
                # Monitor state updates
                async with state_tracker.subscribe() as queue:
                    while True:
                        try:
                            # Check if process is done
                            if process_task.done():
                                result = await process_task

                                # Send final completion
                                completion_data = {
                                    "type": "complete",
                                    "message": "Process completed successfully",
                                }
                                if include_completion_data and result is not None:
                                    completion_data["result"] = result

                                yield f"data: {json.dumps(completion_data, default=SSEEvent._json_serializer)}\n\n"
                                break

                            # Wait for state update with short timeout
                            state = await asyncio.wait_for(queue.get(), timeout=0.1)

                            # Send progress update
                            progress_data = {"type": "progress", **state.model_dump_optimized()}
                            yield f"data: {json.dumps(progress_data, default=SSEEvent._json_serializer)}\n\n"

                            if state.is_complete or state.error:
                                if state.error:
                                    # Process had an error
                                    error_data = {
                                        "type": "error",
                                        "message": state.error,
                                    }
                                    yield f"data: {json.dumps(error_data, default=SSEEvent._json_serializer)}\n\n"
                                break

                        except TimeoutError:
                            # No state update, continue monitoring
                            continue

            except Exception as e:
                logger.error(f"Process execution error: {e}")
                process_task.cancel()

                error_data = {
                    "type": "error",
                    "message": str(e),
                }
                yield f"data: {json.dumps(error_data, default=SSEEvent._json_serializer)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_data = {"type": "error", "message": f"Streaming error: {str(e)}"}
            yield f"data: {json.dumps(error_data, default=SSEEvent._json_serializer)}\n\n"

    return StreamingResponse(
        simple_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
