"""Utilities for respectful web scraping and API usage."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx
from httpx import Response

from ..utils.logging import get_logger

logger = get_logger(__name__)


class RespectfulScrapingHeaders:
    """Generate respectful headers for web scraping."""
    
    # Rotate between realistic user agents to avoid detection
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    @classmethod
    def get_headers(cls, custom_user_agent: str | None = None) -> dict[str, str]:
        """Get respectful scraping headers.
        
        Args:
            custom_user_agent: Optional custom user agent to use
            
        Returns:
            Dictionary of headers for respectful scraping
        """
        return {
            "User-Agent": custom_user_agent or random.choice(cls.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",  # Do Not Track
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on server responses."""
    
    def __init__(self, base_rate: float, max_rate: float = None, min_rate: float = 0.1):
        """Initialize adaptive rate limiter.
        
        Args:
            base_rate: Base requests per second
            max_rate: Maximum requests per second (defaults to base_rate * 2)
            min_rate: Minimum requests per second when backing off
        """
        self.base_rate = base_rate
        self.max_rate = max_rate or base_rate * 2
        self.min_rate = min_rate
        self.current_rate = base_rate
        self.last_request_time = 0.0
        self.consecutive_errors = 0
        self.consecutive_successes = 0
        self._lock = asyncio.Lock()
    
    async def wait(self) -> None:
        """Wait according to current rate limit with automatic respectful delay."""
        async with self._lock:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time
            min_interval = 1.0 / self.current_rate
            
            # Add base respectful delay (1-3 seconds) for web scraping
            base_delay = random.uniform(1.0, 3.0)
            
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                # Combine rate limiting with respectful delay
                total_wait = max(wait_time, base_delay)
                # Add small random jitter to avoid thundering herd
                jitter = random.uniform(0.0, min(0.2, total_wait * 0.1))
                total_wait += jitter
                
                logger.debug(f"Rate limiting + respectful delay: waiting {total_wait:.2f}s (rate: {self.current_rate:.2f} req/s)")
                await asyncio.sleep(total_wait)
            else:
                # Even if not rate limited, add respectful delay for scraping
                jitter = random.uniform(0.0, 0.2)
                total_delay = base_delay + jitter
                logger.debug(f"Respectful delay: waiting {total_delay:.2f}s")
                await asyncio.sleep(total_delay)
            
            self.last_request_time = asyncio.get_event_loop().time()
    
    def record_success(self) -> None:
        """Record a successful request."""
        self.consecutive_errors = 0
        self.consecutive_successes += 1
        
        # Gradually increase rate after sustained success
        if self.consecutive_successes >= 10 and self.current_rate < self.max_rate:
            self.current_rate = min(self.max_rate, self.current_rate * 1.1)
            self.consecutive_successes = 0
            logger.debug(f"Increased rate limit to {self.current_rate:.2f} req/s")
    
    def record_error(self, status_code: int | None = None) -> None:
        """Record an error response.
        
        Args:
            status_code: HTTP status code if applicable
        """
        self.consecutive_successes = 0
        self.consecutive_errors += 1
        
        # Back off more aggressively for rate limiting errors
        if status_code in (429, 503, 520, 521, 522, 524):
            # Server is overloaded or rate limiting
            self.current_rate = max(self.min_rate, self.current_rate * 0.5)
            logger.warning(f"Server overload (HTTP {status_code}), reduced rate to {self.current_rate:.2f} req/s")
        elif self.consecutive_errors >= 3:
            # General error backoff
            self.current_rate = max(self.min_rate, self.current_rate * 0.8)
            logger.warning(f"Multiple errors, reduced rate to {self.current_rate:.2f} req/s")


class RespectfulHttpClient:
    """HTTP client with built-in respectful scraping practices."""
    
    def __init__(
        self,
        base_url: str | None = None,
        rate_limit: float = 2.0,
        custom_headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ):
        """Initialize respectful HTTP client.
        
        Args:
            base_url: Base URL for requests
            rate_limit: Base rate limit in requests per second
            custom_headers: Custom headers to include
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.rate_limiter = AdaptiveRateLimiter(rate_limit)
        self.custom_headers = custom_headers or {}
        
        # Create session with respectful defaults
        headers = RespectfulScrapingHeaders.get_headers()
        headers.update(self.custom_headers)
        
        self.session = httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
        )
    
    async def get(self, url: str, **kwargs: Any) -> Response:
        """Make a GET request with respectful practices.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for httpx.get
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPStatusError: For HTTP errors
            httpx.RequestError: For request errors
        """
        # Apply rate limiting
        await self.rate_limiter.wait()
        
        # Make full URL if base_url provided
        if self.base_url and not url.startswith(('http://', 'https://')):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        try:
            response = await self.session.get(url, **kwargs)
            
            # Check for rate limiting response
            if response.status_code == 429:
                # Honor Retry-After header if present
                retry_after = response.headers.get('retry-after')
                if retry_after:
                    try:
                        wait_time = int(retry_after)
                        logger.warning(f"Rate limited, waiting {wait_time}s as requested by server")
                        await asyncio.sleep(wait_time)
                    except ValueError:
                        pass
            
            # Record response for rate limiting adaptation
            if response.status_code < 400:
                self.rate_limiter.record_success()
            else:
                self.rate_limiter.record_error(response.status_code)
            
            response.raise_for_status()
            return response
            
        except httpx.HTTPStatusError as e:
            self.rate_limiter.record_error(e.response.status_code)
            logger.error(f"HTTP error {e.response.status_code} for {url}")
            raise
        except httpx.RequestError as e:
            self.rate_limiter.record_error()
            logger.error(f"Request error for {url}: {e}")
            raise
    
    async def close(self) -> None:
        """Close the HTTP session."""
        await self.session.aclose()
    
    async def __aenter__(self) -> RespectfulHttpClient:
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()


