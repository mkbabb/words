"""Global exception handlers for the FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ...utils.logging import get_logger

_logger = get_logger(__name__)

# Maximum request body sizes by endpoint pattern
MAX_BODY_SIZE_DEFAULT = 1 * 1024 * 1024  # 1MB
MAX_BODY_SIZE_UPLOAD = 10 * 1024 * 1024  # 10MB for uploads


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        """Handle ValueError as 400 Bad Request."""
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions as 500 Internal Server Error."""
        _logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {exc}"
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.middleware("http")
    async def request_size_limit_middleware(request: Request, call_next):
        """Enforce request body size limits to prevent abuse."""
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length:
                size = int(content_length)
                path = request.url.path

                # Upload endpoints get higher limits
                max_size = MAX_BODY_SIZE_DEFAULT
                if "/upload" in path or "/images" in path:
                    max_size = MAX_BODY_SIZE_UPLOAD

                if size > max_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request body too large: {size} bytes "
                            f"(max: {max_size} bytes)"
                        },
                    )

        return await call_next(request)
