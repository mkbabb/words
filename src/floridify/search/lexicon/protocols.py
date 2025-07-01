"""
Protocols for lexicon loading and custom data sources.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import httpx


class CustomDownloader(Protocol):
    """Protocol for downloader functions - can handle URLs or custom scraping."""
    
    async def __call__(self, url: str = "", **kwargs: Any) -> dict[str, Any] | httpx.Response:
        """Download/scrape data from URL or custom logic."""
        ...


# Type alias for clarity
DownloaderFunc = Callable[[str], Awaitable[dict[str, Any] | httpx.Response]]


async def default_downloader(url: str = "", **kwargs: Any) -> httpx.Response:
    """Default HTTP GET downloader."""
    if not url:
        raise ValueError("URL is required for default downloader")
    timeout = kwargs.get('timeout', 30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response