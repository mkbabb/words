"""
Protocols for lexicon loading and custom data sources.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from ....caching.decorators import cached_computation_async

# Type alias for clarity
ScraperFunc = Callable[..., Awaitable[str | dict[str, Any]]]


@cached_computation_async(ttl_hours=168.0, key_prefix="http")
async def default_scraper(url: str, timeout: float = 30.0) -> str:
    """Cached HTTP GET downloader returning text content."""
    if not url:
        raise ValueError("URL is required")

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
