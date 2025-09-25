"""Default language scraper implementation."""

from __future__ import annotations

from typing import Any

import httpx


async def default_scraper(
    url: str,
    session: httpx.AsyncClient | None = None,
    **kwargs: Any,
) -> str:
    """Default scraper that fetches text content from URL.

    Args:
        url: URL to scrape
        session: Optional HTTP client session to use
        **kwargs: Additional arguments

    Returns:
        Text content from the URL

    """
    if not url:
        raise ValueError("URL is required")

    if session:
        response = await session.get(url)
        response.raise_for_status()
        return response.text
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
