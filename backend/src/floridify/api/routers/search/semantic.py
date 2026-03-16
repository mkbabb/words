"""Semantic search status and SSE stream endpoints."""

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ....core.search_pipeline import get_search_engine_manager
from ....utils.logging import get_logger
from .models import HotReloadStatusResponse, SemanticStatusResponse

logger = get_logger(__name__)
router = APIRouter()

# SSE constants
_SSE_HEARTBEAT_INTERVAL = 30.0
_SSE_MAX_DURATION = 300.0  # 5 minutes max lifetime


def _build_semantic_status() -> dict[str, Any]:
    """Build the semantic status dict from current SearchEngineManager state.

    Shared by both the GET and SSE endpoints.
    """
    manager = get_search_engine_manager()

    if manager._engine is None:
        if manager._initializing:
            message = "Search engine initializing in background..."
        elif manager._init_error:
            message = f"Search engine initialization failed: {manager._init_error}"
        else:
            message = "Search engine not yet initialized"

        return {
            "enabled": manager._semantic,
            "ready": False,
            "building": manager._initializing,
            "languages": [lang.value for lang in (manager._languages or [])],
            "model_name": None,
            "vocabulary_size": 0,
            "message": message,
        }

    stats = manager._engine.get_stats()
    enabled = stats.get("semantic_enabled", False)
    ready = manager._engine.is_semantic_ready()
    building = manager._engine.is_semantic_building()

    if not enabled:
        message = "Semantic search is disabled"
    elif ready:
        message = "Semantic search is ready"
    elif building:
        message = "Semantic search is building in background (search still works with exact/fuzzy)"
    else:
        message = "Semantic search is not initialized"

    return {
        "enabled": enabled,
        "ready": ready,
        "building": building,
        "languages": [lang.value for lang in (manager._languages or [])],
        "model_name": stats.get("semantic_model"),
        "vocabulary_size": stats.get("vocabulary_size", 0),
        "message": message,
    }


@router.get("/search/semantic/status", response_model=SemanticStatusResponse)
async def get_semantic_status() -> SemanticStatusResponse:
    """Get status of semantic search initialization.

    This endpoint allows clients to check if semantic search is ready to use,
    or if it's still building in the background. Useful for showing loading
    states in the UI. Non-blocking — does not trigger initialization.
    """
    try:
        return SemanticStatusResponse(**_build_semantic_status())
    except Exception as e:
        logger.error(f"Failed to get semantic status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get semantic status")


@router.get("/search/semantic/status/stream")
async def stream_semantic_status(request: Request) -> StreamingResponse:
    """Stream semantic search status changes via Server-Sent Events.

    Pushes a ``status`` event whenever the semantic search state changes
    (initializing, building, ready, error).  The stream auto-closes once
    a terminal state is reached (``ready`` or ``!enabled``).

    Heartbeat pings are sent every 30 s to keep proxies alive.
    """

    async def _event_generator():
        last_snapshot: dict[str, Any] | None = None
        poll_interval = 1.0
        start_time = time.monotonic()
        last_heartbeat = start_time

        while True:
            # Client gone?
            if await request.is_disconnected():
                break

            # Max lifetime guard
            if time.monotonic() - start_time >= _SSE_MAX_DURATION:
                yield f"event: timeout\ndata: {json.dumps({'message': 'Stream max duration reached'})}\n\n"
                break

            try:
                current = _build_semantic_status()
            except Exception as exc:
                logger.error(f"Semantic status stream error: {exc}")
                yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
                break

            # Only emit when something changed
            if current != last_snapshot:
                yield f"event: status\ndata: {json.dumps(current)}\n\n"
                last_snapshot = current
                last_heartbeat = time.monotonic()

                # Terminal state — close the stream
                if current.get("ready") or not current.get("enabled"):
                    break

            # Heartbeat
            now = time.monotonic()
            if now - last_heartbeat >= _SSE_HEARTBEAT_INTERVAL:
                yield ": ping\n\n"
                last_heartbeat = now

            await asyncio.sleep(poll_interval)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/search/hot-reload/status", response_model=HotReloadStatusResponse)
async def get_hot_reload_status() -> HotReloadStatusResponse:
    """Get the status of the search engine hot-reload mechanism.

    Shows when the last corpus change check occurred, the check interval,
    and the current corpus fingerprint used for change detection.
    """
    manager = get_search_engine_manager()
    status = manager.get_status()
    return HotReloadStatusResponse(**status)
