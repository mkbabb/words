"""
Protocols for lexicon loading and custom data sources.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from ....caching import get_cached_http_client

# Type alias for clarity
ScraperFunc = Callable[[str], Awaitable[dict[str, Any] | httpx.Response]]


async def default_scraper(url: str = "", **kwargs: Any) -> httpx.Response:
    """Default HTTP GET downloader with caching."""
    if not url:
        raise ValueError("URL is required for default downloader")

    # Get cached HTTP client
    force_refresh = kwargs.get("force_refresh", False)
    ttl_hours = kwargs.get("ttl_hours", 168.0)  # Cache lexicon files for 1 week by default

    http_client = get_cached_http_client(
        force_refresh=force_refresh,
        default_ttl_hours=ttl_hours,
    )

    response = await http_client.get(
        url,
        ttl_hours=ttl_hours,
        force_refresh=force_refresh,
        timeout=kwargs.get("timeout", 30.0),
    )
    response.raise_for_status()
    return response
