"""Authentication middleware using Clerk JWT validation.

Provides:
- ClerkAuthMiddleware: Starlette middleware that validates JWTs and sets request.state.user_id
- get_current_user: FastAPI dependency for authenticated endpoints
- require_admin: FastAPI dependency for admin-only endpoints
- Endpoint tier classification (public, authenticated, owner, admin)
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from jwt.algorithms import RSAAlgorithm
from starlette.middleware.base import BaseHTTPMiddleware

from ...utils.logging import get_logger

logger = get_logger(__name__)

# Cache JWKS keys in memory
_jwks_cache: dict[str, Any] | None = None
_jwks_cache_time: float = 0

# Endpoint tier classification
# Tier 1: Public (no auth required)
PUBLIC_PREFIXES = frozenset({
    "/api/v1/lookup/",
    "/api/v1/search",
    "/api/v1/suggestions",
    "/api/v1/health",
    "/api/v1/config",
    "/api",
})
PUBLIC_EXACT = frozenset({
    "/api/v1/health",
    "/api/v1/config",
    "/api",
})

# Tier 4: Admin-only endpoints
ADMIN_PREFIXES = frozenset({
    "/api/v1/cache/clear",
    "/api/v1/cache/prune",
    "/api/v1/corpus/rebuild",
    "/api/v1/database/cleanup",
    "/api/v1/database/stats",
    "/api/v1/providers/circuit-status",
    "/api/v1/metrics",
})


def _is_public_endpoint(path: str, method: str) -> bool:
    """Check if endpoint is Tier 1 (public, no auth required)."""
    # Health check at root
    if path in ("/health", "/api"):
        return True

    # All GET requests to lookup, search, suggestions, health, config are public
    if method == "GET":
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True
        if path in PUBLIC_EXACT:
            return True

    return False


def _is_admin_endpoint(path: str) -> bool:
    """Check if endpoint is Tier 4 (admin-only)."""
    for prefix in ADMIN_PREFIXES:
        if path.startswith(prefix):
            return True
    # Config with show_keys is admin
    if path.startswith("/api/v1/config") and "show_keys" in path:
        return True
    return False


async def _get_jwks(clerk_domain: str) -> dict[str, Any]:
    """Fetch and cache Clerk's JWKS (JSON Web Key Set)."""
    import time

    global _jwks_cache, _jwks_cache_time

    # Cache for 1 hour
    now = time.time()
    if _jwks_cache is not None and (now - _jwks_cache_time) < 3600:
        return _jwks_cache

    jwks_url = f"https://{clerk_domain}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = now
        return _jwks_cache


def _get_signing_key(jwks: dict[str, Any], token: str) -> str:
    """Extract the correct signing key from JWKS for the given token."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return RSAAlgorithm.from_jwk(key_data)

    raise jwt.InvalidTokenError(f"No matching key found for kid: {kid}")


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates Clerk JWTs and populates request.state.user_id.

    - Tier 1 (public) endpoints bypass auth entirely
    - Other endpoints require a valid Bearer token
    - Sets request.state.user_id and request.state.user_role on success
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        method = request.method

        # OPTIONS requests always pass through (CORS preflight)
        if method == "OPTIONS":
            return await call_next(request)

        # Tier 1: Public endpoints - no auth required
        if _is_public_endpoint(path, method):
            return await call_next(request)

        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response(
                content='{"detail":"Authentication required"}',
                status_code=401,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header[7:]  # Strip "Bearer "

        clerk_domain = os.getenv("CLERK_DOMAIN", "")
        if not clerk_domain:
            # Auth not configured - pass through with warning
            logger.warning("CLERK_DOMAIN not set - auth middleware disabled")
            return await call_next(request)

        try:
            jwks = await _get_jwks(clerk_domain)
            signing_key = _get_signing_key(jwks, token)

            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                issuer=f"https://{clerk_domain}",
                options={"verify_aud": False},  # Clerk doesn't always set aud
            )

            request.state.user_id = payload.get("sub", "")
            request.state.user_role = payload.get("metadata", {}).get("role", "user")

        except jwt.ExpiredSignatureError:
            return Response(
                content='{"detail":"Token expired"}',
                status_code=401,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT: {e}")
            return Response(
                content='{"detail":"Invalid authentication token"}',
                status_code=401,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            return Response(
                content='{"detail":"Authentication service unavailable"}',
                status_code=503,
                media_type="application/json",
            )

        # Tier 4: Admin check
        if _is_admin_endpoint(path):
            if request.state.user_role != "admin":
                return Response(
                    content='{"detail":"Admin access required"}',
                    status_code=403,
                    media_type="application/json",
                )

        return await call_next(request)


async def get_current_user(request: Request) -> str:
    """FastAPI dependency: returns the authenticated user_id.

    Use as Depends(get_current_user) on endpoints that require auth.
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def require_admin(request: Request) -> str:
    """FastAPI dependency: requires admin role.

    Use as Depends(require_admin) on admin-only endpoints.
    """
    user_id = await get_current_user(request)
    role = getattr(request.state, "user_role", "user")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user_id


def get_optional_user(request: Request) -> str | None:
    """FastAPI dependency: returns user_id if authenticated, None otherwise.

    Use for endpoints that work with or without auth (e.g., personalized results).
    """
    return getattr(request.state, "user_id", None)
