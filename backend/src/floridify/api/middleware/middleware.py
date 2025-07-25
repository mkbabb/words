"""API middleware for logging, error handling, and caching."""

from __future__ import annotations

import hashlib
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...utils.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Log requests and responses with timing."""
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]

        # Start timing
        start_time = time.perf_counter()

        # Log request
        logger.info(
            "API request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate timing
            process_time = time.perf_counter() - start_time
            process_time_ms = int(process_time * 1000)

            # Log response
            logger.info(
                "API request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time_ms": process_time_ms,
                },
            )

            # Add timing header
            response.headers["X-Process-Time"] = str(process_time_ms)
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate timing for errors too
            process_time = time.perf_counter() - start_time
            process_time_ms = int(process_time * 1000)

            # Log error
            logger.error(
                "API request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "process_time_ms": process_time_ms,
                },
            )

            # Re-raise the exception
            raise


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add HTTP cache headers for improved performance."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Add appropriate cache headers based on endpoint."""
        response = await call_next(request)

        # Only add cache headers for successful responses
        if response.status_code == 200:
            path = request.url.path
            query_params = str(request.query_params) if request.query_params else ""

            # Generate ETag based on path and query parameters
            etag_data = f"{path}:{query_params}"
            etag = hashlib.md5(etag_data.encode()).hexdigest()[:16]

            # Check for conditional requests
            if_none_match = request.headers.get("If-None-Match", "").strip('"')
            if if_none_match == etag:
                # Client has current version - return 304 Not Modified
                return Response(status_code=304, headers={"ETag": f'"{etag}"'})

            # Set cache headers based on endpoint type
            if path.startswith("/api/v1/search"):
                # Search results - cache for 1 hour
                response.headers["Cache-Control"] = "public, max-age=3600"
                response.headers["ETag"] = f'"{etag}"'
                response.headers["Vary"] = "Accept-Encoding"

            elif path.startswith("/api/v1/lookup"):
                # Word definitions - cache for 30 minutes
                response.headers["Cache-Control"] = "public, max-age=1800"
                response.headers["ETag"] = f'"{etag}"'
                response.headers["Vary"] = "Accept-Encoding"

            elif path.startswith("/api/v1/suggestions"):
                # Suggestions - cache for 2 hours (more stable)
                response.headers["Cache-Control"] = "public, max-age=7200"
                response.headers["ETag"] = f'"{etag}"'
                response.headers["Vary"] = "Accept-Encoding"

            elif path.startswith("/api/v1/synonyms"):
                # Synonyms - cache for 6 hours (very stable)
                response.headers["Cache-Control"] = "public, max-age=21600"
                response.headers["ETag"] = f'"{etag}"'
                response.headers["Vary"] = "Accept-Encoding"

            elif path.startswith("/api/v1/health"):
                # Health checks - no caching
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"

            else:
                # Default for other endpoints - short cache
                response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes
                response.headers["ETag"] = f'"{etag}"'

        return response
