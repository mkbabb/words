"""Async concurrency utilities."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


async def gather_bounded(
    *coros: Coroutine[Any, Any, Any],
    limit: int = 5,
    return_exceptions: bool = False,
) -> list[Any]:
    """Like asyncio.gather but with a concurrency semaphore.

    Args:
        *coros: Coroutines to run concurrently.
        limit: Maximum number of coroutines running at the same time.
        return_exceptions: If True, exceptions are returned as results
            instead of being raised.

    Returns:
        Results in the same order as the input coroutines.

    """
    sem = asyncio.Semaphore(limit)

    async def _bounded(coro: Coroutine[Any, Any, Any]) -> Any:
        async with sem:
            return await coro

    return await asyncio.gather(
        *(_bounded(c) for c in coros),
        return_exceptions=return_exceptions,
    )
