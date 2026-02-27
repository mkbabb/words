"""Tests for SSE (Server-Sent Events) streaming infrastructure.

Tests the core streaming module and state tracker independently of the
full lookup pipeline. Mocks external dependencies (OpenAI, MongoDB) to
focus on SSE event generation, heartbeat pings, and timeout behavior.
"""

import asyncio
import json
import time

import pytest

from floridify.core.state_tracker import PipelineState, Stages, StateTracker
from floridify.core.streaming import (
    SSE_HEARTBEAT_INTERVAL,
    SSE_STREAM_TIMEOUT,
    SSEEvent,
    create_streaming_response,
)


class TestSSEEvent:
    """Test SSEEvent formatting."""

    def test_basic_event_format(self):
        """Test that SSEEvent produces valid SSE format."""
        event = SSEEvent(event_type="progress", data={"stage": "START", "progress": 10})
        formatted = event.format()

        assert "event: progress\n" in formatted
        assert "data: " in formatted
        assert formatted.endswith("\n\n")

        # Parse the data line
        for line in formatted.strip().split("\n"):
            if line.startswith("data: "):
                parsed = json.loads(line[6:])
                assert parsed["stage"] == "START"
                assert parsed["progress"] == 10

    def test_event_with_id(self):
        """Test SSEEvent with event ID."""
        event = SSEEvent(
            event_type="config",
            data={"category": "lookup"},
            event_id="evt-001",
        )
        formatted = event.format()

        assert "id: evt-001\n" in formatted
        assert "event: config\n" in formatted

    def test_event_types(self):
        """Test different event types are formatted correctly."""
        for event_type in ["config", "progress", "complete", "error"]:
            event = SSEEvent(event_type=event_type, data={"type": event_type})
            formatted = event.format()
            assert f"event: {event_type}\n" in formatted


class TestStateTracker:
    """Test StateTracker event generation for SSE."""

    @pytest.mark.asyncio
    async def test_state_tracker_produces_events(self):
        """Test that StateTracker produces PipelineState events on update."""
        tracker = StateTracker(category="lookup")

        async with tracker.subscribe() as queue:
            await tracker.update_stage(Stages.START)
            await tracker.update_stage(Stages.SEARCH_START)

            # Drain the events
            events = []
            while not queue.empty():
                events.append(queue.get_nowait())

            assert len(events) >= 2
            assert events[0].stage == Stages.START
            assert events[0].progress == 5  # from PROGRESS_MAP
            assert events[1].stage == Stages.SEARCH_START
            assert events[1].progress == 10

    @pytest.mark.asyncio
    async def test_state_tracker_complete_event(self):
        """Test that update_complete sets is_complete flag."""
        tracker = StateTracker(category="lookup")

        async with tracker.subscribe() as queue:
            await tracker.update_complete(message="Done!")

            event = queue.get_nowait()
            assert event.is_complete is True
            assert event.progress == 100
            assert event.stage == "COMPLETE"

    @pytest.mark.asyncio
    async def test_state_tracker_error_event(self):
        """Test that update_error sets error field."""
        tracker = StateTracker(category="lookup")

        async with tracker.subscribe() as queue:
            await tracker.update_error("Something went wrong")

            event = queue.get_nowait()
            assert event.error == "Something went wrong"
            assert event.is_complete is True

    @pytest.mark.asyncio
    async def test_state_tracker_reset(self):
        """Test that reset clears state and queue."""
        tracker = StateTracker(category="lookup")

        await tracker.update_stage(Stages.START)
        await tracker.update_stage(Stages.SEARCH_START)

        tracker.reset()

        assert tracker.get_current_state() is None

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test that multiple subscribers each receive all events."""
        tracker = StateTracker(category="lookup")

        async with tracker.subscribe() as q1, tracker.subscribe() as q2:
            await tracker.update_stage(Stages.START)

            e1 = q1.get_nowait()
            e2 = q2.get_nowait()

            assert e1.stage == Stages.START
            assert e2.stage == Stages.START

    @pytest.mark.asyncio
    async def test_subscriber_cleanup(self):
        """Test that subscribers are removed on context exit."""
        tracker = StateTracker(category="lookup")

        async with tracker.subscribe():
            assert len(tracker._subscribers) == 1

        # After context exit, subscriber should be removed
        assert len(tracker._subscribers) == 0


class TestStreamingResponse:
    """Test create_streaming_response for config, progress, and complete events."""

    @pytest.mark.asyncio
    async def test_stream_produces_config_progress_complete(self):
        """Test that stream emits config, progress, and complete events in order."""
        tracker = StateTracker(category="lookup")

        async def mock_process():
            await tracker.update_stage(Stages.START)
            await tracker.update_stage(Stages.SEARCH_START)
            await tracker.update_complete(message="All done")

            # Return a mock result with model_dump
            class MockResult:
                def model_dump(self, mode=None):
                    return {"word": "test", "definitions": []}

            return MockResult()

        response = await create_streaming_response(
            state_tracker=tracker,
            process_func=mock_process,
            include_stage_definitions=True,
            include_completion_data=True,
        )

        # Collect all SSE events from the stream
        events = []
        event_types = []
        async for chunk in response.body_iterator:
            text = chunk if isinstance(chunk, str) else chunk.decode()
            # Parse SSE events (separated by double newline)
            for raw_event in text.split("\n\n"):
                raw_event = raw_event.strip()
                if not raw_event:
                    continue
                event_type = None
                event_data = None
                for line in raw_event.split("\n"):
                    if line.startswith("event: "):
                        event_type = line[7:]
                    elif line.startswith("data: "):
                        try:
                            event_data = json.loads(line[6:])
                        except json.JSONDecodeError:
                            event_data = line[6:]
                if event_type and event_data is not None:
                    events.append({"type": event_type, "data": event_data})
                    event_types.append(event_type)

        # Must have config event first
        assert "config" in event_types, f"Expected config event, got: {event_types}"
        assert event_types[0] == "config"

        # Config event should have stages and category
        config_data = events[0]["data"]
        assert "stages" in config_data
        assert "category" in config_data

        # Must have at least one progress event
        assert "progress" in event_types, f"Expected progress event, got: {event_types}"

        # Must have a complete event
        assert "complete" in event_types, f"Expected complete event, got: {event_types}"

        # Complete should be last
        assert event_types[-1] == "complete"

    @pytest.mark.asyncio
    async def test_stream_without_stage_definitions(self):
        """Test stream can skip the initial config event."""
        tracker = StateTracker(category="lookup")

        async def mock_process():
            await tracker.update_complete(message="Quick finish")

            class MockResult:
                def model_dump(self, mode=None):
                    return {"result": "ok"}

            return MockResult()

        response = await create_streaming_response(
            state_tracker=tracker,
            process_func=mock_process,
            include_stage_definitions=False,
            include_completion_data=True,
        )

        event_types = []
        async for chunk in response.body_iterator:
            text = chunk if isinstance(chunk, str) else chunk.decode()
            for raw_event in text.split("\n\n"):
                raw_event = raw_event.strip()
                if not raw_event:
                    continue
                for line in raw_event.split("\n"):
                    if line.startswith("event: "):
                        event_types.append(line[7:])

        # Should NOT have config when include_stage_definitions=False
        assert "config" not in event_types

    @pytest.mark.asyncio
    async def test_stream_error_propagation(self):
        """Test that process errors are sent as SSE error events."""
        tracker = StateTracker(category="lookup")

        async def failing_process():
            await tracker.update_stage(Stages.START)
            raise ValueError("Provider fetch failed")

        response = await create_streaming_response(
            state_tracker=tracker,
            process_func=failing_process,
            include_stage_definitions=True,
            include_completion_data=True,
        )

        events = []
        async for chunk in response.body_iterator:
            text = chunk if isinstance(chunk, str) else chunk.decode()
            for raw_event in text.split("\n\n"):
                raw_event = raw_event.strip()
                if not raw_event:
                    continue
                event_type = None
                event_data = None
                for line in raw_event.split("\n"):
                    if line.startswith("event: "):
                        event_type = line[7:]
                    elif line.startswith("data: "):
                        try:
                            event_data = json.loads(line[6:])
                        except json.JSONDecodeError:
                            pass
                if event_type:
                    events.append({"type": event_type, "data": event_data})

        # Should have an error event
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) >= 1, f"Expected error event, got types: {[e['type'] for e in events]}"

        error_data = error_events[0]["data"]
        assert "message" in error_data
        assert "Provider fetch failed" in error_data["message"]


class TestStreamTimeout:
    """Test SSE stream timeout behavior."""

    @pytest.mark.asyncio
    async def test_stream_timeout_sends_error(self):
        """Test that exceeding SSE_STREAM_TIMEOUT produces a timeout error event."""
        tracker = StateTracker(category="lookup")

        # Create a process that would take forever
        async def slow_process():
            # This will be cancelled by the timeout mechanism
            await asyncio.sleep(600)
            return None

        # Monkey-patch the timeout to a very short value for testing
        import floridify.core.streaming as streaming_mod

        original_timeout = streaming_mod.SSE_STREAM_TIMEOUT
        streaming_mod.SSE_STREAM_TIMEOUT = 0.3  # 300ms for testing

        try:
            response = await create_streaming_response(
                state_tracker=tracker,
                process_func=slow_process,
                include_stage_definitions=True,
                include_completion_data=False,
            )

            events = []
            async for chunk in response.body_iterator:
                text = chunk if isinstance(chunk, str) else chunk.decode()
                for raw_event in text.split("\n\n"):
                    raw_event = raw_event.strip()
                    if not raw_event:
                        continue
                    event_type = None
                    event_data = None
                    for line in raw_event.split("\n"):
                        if line.startswith("event: "):
                            event_type = line[7:]
                        elif line.startswith("data: "):
                            try:
                                event_data = json.loads(line[6:])
                            except json.JSONDecodeError:
                                pass
                    if event_type:
                        events.append({"type": event_type, "data": event_data})

            # Should have a timeout error event
            error_events = [e for e in events if e["type"] == "error"]
            assert len(error_events) >= 1, (
                f"Expected timeout error event, got types: {[e['type'] for e in events]}"
            )
            assert "timeout" in error_events[0]["data"]["message"].lower()

        finally:
            streaming_mod.SSE_STREAM_TIMEOUT = original_timeout


class TestHeartbeat:
    """Test SSE heartbeat ping generation."""

    @pytest.mark.asyncio
    async def test_heartbeat_ping_sent_on_idle(self):
        """Test that heartbeat pings are generated when no events arrive for a while."""
        tracker = StateTracker(category="lookup")

        # Monkey-patch heartbeat interval to a short value for testing
        import floridify.core.streaming as streaming_mod

        original_interval = streaming_mod.SSE_HEARTBEAT_INTERVAL
        streaming_mod.SSE_HEARTBEAT_INTERVAL = 0.3  # 300ms

        try:

            async def slow_process():
                # Wait long enough for at least one heartbeat to fire,
                # then complete
                await asyncio.sleep(0.8)
                await tracker.update_complete(message="Done after idle")

                class MockResult:
                    def model_dump(self, mode=None):
                        return {"result": "ok"}

                return MockResult()

            response = await create_streaming_response(
                state_tracker=tracker,
                process_func=slow_process,
                include_stage_definitions=False,
                include_completion_data=True,
            )

            raw_chunks = []
            async for chunk in response.body_iterator:
                text = chunk if isinstance(chunk, str) else chunk.decode()
                raw_chunks.append(text)

            full_text = "".join(raw_chunks)

            # Should contain at least one heartbeat ping comment
            assert ": ping\n\n" in full_text, (
                f"Expected heartbeat ping in output. Full output:\n{full_text[:500]}"
            )

        finally:
            streaming_mod.SSE_HEARTBEAT_INTERVAL = original_interval


class TestPipelineStateOptimized:
    """Test PipelineState.model_dump_optimized for SSE payload reduction."""

    def test_optimized_dump_minimal(self):
        """Test that optimized dump only includes essential fields."""
        state = PipelineState(
            stage="SEARCH_START",
            progress=10,
            message="search start",  # Same as stage name -> excluded
        )
        dumped = state.model_dump_optimized()

        assert "stage" in dumped
        assert "progress" in dumped
        # Message matches stage (case-insensitive, underscores replaced) -> excluded
        assert "message" not in dumped
        # No details, not complete, no error
        assert "details" not in dumped
        assert "is_complete" not in dumped
        assert "error" not in dumped

    def test_optimized_dump_with_details(self):
        """Test that details are included when present."""
        state = PipelineState(
            stage="PROVIDER_FETCH_START",
            progress=25,
            message="Fetching from 3 providers",
            details={"providers": ["wiktionary", "free_dictionary", "oxford"]},
        )
        dumped = state.model_dump_optimized()

        assert dumped["message"] == "Fetching from 3 providers"
        assert "providers" in dumped["details"]

    def test_optimized_dump_complete(self):
        """Test that is_complete is included when True."""
        state = PipelineState(
            stage="COMPLETE",
            progress=100,
            is_complete=True,
        )
        dumped = state.model_dump_optimized()

        assert dumped["is_complete"] is True

    def test_optimized_dump_error(self):
        """Test that error field is included when present."""
        state = PipelineState(
            stage="ERROR",
            progress=50,
            error="Network timeout",
        )
        dumped = state.model_dump_optimized()

        assert dumped["error"] == "Network timeout"
