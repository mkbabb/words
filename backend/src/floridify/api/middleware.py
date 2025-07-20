"""API middleware for logging and error handling."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.logging import get_logger

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
