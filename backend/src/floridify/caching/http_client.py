"""HTTP client with modern caching using hishel."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional
import time

import hishel
import httpx

from ..utils.logging import get_logger

logger = get_logger(__name__)


class CachedHTTPClient:
    """HTTP client with filesystem caching and TTL support."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        default_ttl_hours: float = 24.0,
        force_refresh: bool = False,
    ) -> None:
        """Initialize cached HTTP client.
        
        Args:
            cache_dir: Directory for HTTP cache
            default_ttl_hours: Default TTL for HTTP responses
            force_refresh: If True, bypass cache for all requests
        """
        # Setup cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "floridify" / "http"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_dir = cache_dir
        self.default_ttl_hours = default_ttl_hours
        self.force_refresh = force_refresh
        
        # Configure cache storage
        storage = hishel.FileStorage(
            base_path=cache_dir,
            check_ttl_every=300,  # Check TTL every 5 minutes
        )
        
        # Create cached client with proper configuration
        self._client = hishel.CacheClient(
            storage=storage,
        )
        
        logger.info(f"🌐 HTTP cache initialized: {cache_dir}, TTL={default_ttl_hours}h")

    async def get(
        self,
        url: str,
        ttl_hours: float | None = None,
        force_refresh: bool | None = None,
        progress_callback: Optional[Callable[[str, dict[str, Any]], None]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Cached GET request.
        
        Args:
            url: URL to request
            ttl_hours: TTL for this request (overrides default)
            force_refresh: Force refresh for this request
            **kwargs: Additional httpx arguments
            
        Returns:
            HTTP response
        """
        # Determine if we should force refresh
        should_force = force_refresh if force_refresh is not None else self.force_refresh
        
        # Set TTL
        ttl_hours = ttl_hours or self.default_ttl_hours
        
        # Configure cache headers
        if should_force:
            # Force fresh request
            kwargs.setdefault("headers", {})["Cache-Control"] = "no-cache"
            logger.debug(f"🔄 Force refresh: {url}")
        else:
            # Set max-age for TTL
            max_age = int(ttl_hours * 3600)
            kwargs.setdefault("headers", {})["Cache-Control"] = f"max-age={max_age}"
        
        # Track timing
        start_time = time.time()
        
        # Report connection start
        if progress_callback:
            progress_callback('connecting', {
                'url': url,
                'method': 'GET',
                'cache_enabled': not should_force
            })
        
        # Make request
        logger.debug(f"🌐 HTTP GET: {url} (TTL: {ttl_hours}h)")
        connection_time = time.time()
        
        response = self._client.get(url, **kwargs)
        if hasattr(response, '__await__'):
            response = await response
        
        download_time = time.time()
        
        # Report download complete
        if progress_callback:
            response_size = len(response.content) if hasattr(response, 'content') else 0
            progress_callback('downloaded', {
                'url': url,
                'status_code': response.status_code,
                'response_size_bytes': response_size,
                'connection_time_ms': (connection_time - start_time) * 1000,
                'download_time_ms': (download_time - connection_time) * 1000,
                'total_time_ms': (download_time - start_time) * 1000
            })
        
        # Log cache status if available
        try:
            if hasattr(response, "extensions") and response.extensions and "cache" in response.extensions:
                cache_status = response.extensions["cache"].get("status", "unknown")
                logger.debug(f"📡 {cache_status.upper()}: {url}")
        except Exception:
            # Ignore cache status logging errors
            pass
        
        return response

    async def post(
        self,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Non-cached POST request.
        
        Args:
            url: URL to request
            **kwargs: Additional httpx arguments
            
        Returns:
            HTTP response
        """
        logger.debug(f"🌐 HTTP POST: {url}")
        response = self._client.post(url, **kwargs)
        if hasattr(response, '__await__'):
            response = await response
        return response

    async def download_file(
        self,
        url: str,
        file_path: Path,
        ttl_hours: float | None = None,
        force_refresh: bool | None = None,
        **kwargs: Any,
    ) -> bool:
        """Download file with caching.
        
        Args:
            url: URL to download
            file_path: Local path to save file
            ttl_hours: TTL for cached download
            force_refresh: Force fresh download
            **kwargs: Additional httpx arguments
            
        Returns:
            True if file was downloaded/cached successfully
        """
        try:
            # Check if file exists and is fresh (unless forcing refresh)
            should_force = force_refresh if force_refresh is not None else self.force_refresh
            
            if not should_force and file_path.exists():
                # Check file age
                file_age_hours = (
                    (file_path.stat().st_mtime - file_path.stat().st_ctime) / 3600
                )
                ttl_hours = ttl_hours or self.default_ttl_hours
                
                if file_age_hours < ttl_hours:
                    logger.debug(f"📁 Using cached file: {file_path}")
                    return True
            
            # Download file with progress tracking
            def file_progress_callback(stage: str, metadata: dict[str, Any]):
                logger.debug(f"📥 File download {stage}: {metadata}")
            
            response = await self.get(
                url, 
                ttl_hours=ttl_hours, 
                force_refresh=should_force,
                progress_callback=file_progress_callback,
                **kwargs
            )
            response.raise_for_status()
            
            # Save to file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(response.content)
            
            logger.info(f"💾 Downloaded: {url} -> {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Download failed: {url} -> {file_path}: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear HTTP cache."""
        try:
            # Remove all cache files
            cache_files = list(self.cache_dir.rglob("*"))
            for cache_file in cache_files:
                if cache_file.is_file():
                    cache_file.unlink()
            
            # Remove empty directories
            for cache_dir in sorted(self.cache_dir.rglob("*"), reverse=True):
                if cache_dir.is_dir() and not any(cache_dir.iterdir()):
                    cache_dir.rmdir()
            
            logger.info(f"🧹 Cleared HTTP cache: {len(cache_files)} files")
            
        except Exception as e:
            logger.warning(f"Failed to clear HTTP cache: {e}")

    async def close(self) -> None:
        """Close HTTP client."""
        try:
            if hasattr(self._client, 'aclose'):
                await self._client.aclose()
            elif hasattr(self._client, 'close'):
                self._client.close()
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {e}")


# Global HTTP client instance
_http_client: CachedHTTPClient | None = None


def get_cached_http_client(
    force_refresh: bool = False,
    default_ttl_hours: float = 24.0,
) -> CachedHTTPClient:
    """Get the global cached HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = CachedHTTPClient(
            force_refresh=force_refresh,
            default_ttl_hours=default_ttl_hours,
        )
    return _http_client


async def close_http_client() -> None:
    """Close the global HTTP client."""
    global _http_client
    if _http_client is not None:
        await _http_client.close()
        _http_client = None