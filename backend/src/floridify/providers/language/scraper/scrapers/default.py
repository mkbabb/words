"""Default language scraper implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .....utils.logging import get_logger

logger = get_logger(__name__)


async def default_scraper(
    url: str,
    session: httpx.AsyncClient | None = None,
    local_path: str | None = None,
    **kwargs: Any,
) -> str:
    """Default scraper that fetches text content from URL with local file fallback.

    Args:
        url: URL to scrape
        session: Optional HTTP client session to use
        local_path: Optional local file path to use as fallback if URL fails
        **kwargs: Additional arguments

    Returns:
        Text content from the URL or local file

    """
    if url:
        try:
            if session:
                response = await session.get(url)
                response.raise_for_status()
                return response.text
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            if local_path:
                logger.warning(
                    f"URL fetch failed ({e}), falling back to bundled file: {local_path}"
                )
            else:
                raise

    if local_path:
        resolved = Path(local_path)
        if not resolved.is_absolute():
            # Resolve relative to the backend data directory
            # Lazy: heavyweight module
            from .....utils.paths import get_data_dir

            resolved = get_data_dir() / local_path
        if resolved.exists():
            logger.info(f"Loading from bundled file: {resolved}")
            return resolved.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Bundled file not found: {resolved}")

    raise ValueError("Either URL or local_path is required")
