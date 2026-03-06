"""Authentication middleware using Clerk JWT validation.

Provides:
- ClerkAuthMiddleware: Starlette middleware that validates JWTs and sets request.state.user_id
- get_current_user: FastAPI dependency for authenticated endpoints
- get_current_user_object: FastAPI dependency returning full User document
- require_admin: FastAPI dependency for admin-only endpoints
- require_premium: FastAPI dependency for premium-or-admin endpoints
- get_optional_user: FastAPI dependency for optional auth
- Endpoint tier classification (public, authenticated, premium, admin)
"""

from __future__ import annotations

import os
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, Request, Response, status
from jwt.algorithms import RSAAlgorithm
from starlette.middleware.base import BaseHTTPMiddleware

from ...models.user import User, UserRole
from ...utils.logging import get_logger

logger = get_logger(__name__)

# Cache JWKS keys in memory
_jwks_cache: dict[str, Any] | None = None
_jwks_cache_time: float = 0

# Super admin emails (auto-promoted to admin on first login)
_super_admins: frozenset[str] | None = None


def _get_super_admins() -> frozenset[str]:
    """Get super admin emails from environment."""
    global _super_admins
    if _super_admins is None:
        raw = os.getenv("CLERK_SUPER_ADMINS", "")
        _super_admins = frozenset(
            email.strip().lower() for email in raw.split(",") if email.strip()
        )
    return _super_admins


# Endpoint tier classification
# Tier 1: Public (no auth required)
PUBLIC_PREFIXES = frozenset(
    {
        "/api/v1/lookup/",
        "/api/v1/search",
        "/api/v1/suggestions",
        "/api/v1/health",
        "/api",
    }
)
PUBLIC_EXACT = frozenset(
    {
        "/api/v1/health",
        "/api",
    }
)

# Tier 3: Premium endpoints (require premium or admin role)
PREMIUM_PREFIXES = frozenset(
    {
        "/api/v1/ai/",
    }
)
# Pattern-matched premium endpoints
PREMIUM_PATTERNS = [
    re.compile(r"^/api/v1/definitions/[^/]+/regenerate$"),
    re.compile(r"^/api/v1/examples/[^/]+/generate$"),
    re.compile(r"^/api/v1/audio/tts/generate$"),
]

# Tier 4: Admin-only endpoints
ADMIN_PREFIXES = frozenset(
    {
        "/api/v1/cache/",
        "/api/v1/config",
        "/api/v1/corpus/rebuild",
        "/api/v1/database/",
        "/api/v1/providers/",
        "/api/v1/metrics",
    }
)


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

    # Users/me is authenticated but should pass through middleware for token extraction
    # Audio cache serving is public (GET)
    if method == "GET" and path.startswith("/api/v1/audio/cache/"):
        return True

    return False


def _is_premium_endpoint(path: str) -> bool:
    """Check if endpoint is Tier 3 (premium or admin required)."""
    for prefix in PREMIUM_PREFIXES:
        if path.startswith(prefix):
            return True
    for pattern in PREMIUM_PATTERNS:
        if pattern.match(path):
            return True
    return False


def _is_admin_endpoint(path: str) -> bool:
    """Check if endpoint is Tier 4 (admin-only)."""
    for prefix in ADMIN_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


async def _get_jwks(clerk_domain: str) -> dict[str, Any]:
    """Fetch and cache Clerk's JWKS (JSON Web Key Set)."""
    # TODO[HIGH]: Hoist nested import to module scope unless this is an intentional lazy-init boundary (e.g., CLI or heavyweight model init); document rationale when kept nested.
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


async def _upsert_user(
    clerk_id: str, email: str | None, username: str | None, avatar_url: str | None
) -> User:
    """Find or create a User document after JWT validation."""
    user = await User.find_one(User.clerk_id == clerk_id)

    if user is None:
        # Determine role: auto-promote super admins
        role = UserRole.USER
        if email and email.lower() in _get_super_admins():
            role = UserRole.ADMIN
            logger.info(f"Auto-promoting super admin: {email}")

        user = User(
            clerk_id=clerk_id,
            email=email,
            username=username,
            avatar_url=avatar_url,
            role=role,
        )
        await user.insert()
        logger.info(f"Created new user: {clerk_id} ({email}) with role {role}")
    else:
        # Update last_login and any changed profile fields
        user.last_login = datetime.now(UTC)
        if email and user.email != email:
            user.email = email
        if username and user.username != username:
            user.username = username
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
        await user.save()

    return user


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates Clerk JWTs and populates request.state.

    - Tier 1 (public) endpoints bypass auth entirely
    - Other endpoints require a valid Bearer token
    - Sets request.state.user_id, request.state.user_role, request.state.user on success
    - In development without CLERK_DOMAIN, grants admin access for all requests
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
            # Still try to extract user if token is present (for optional auth)
            await self._try_extract_user(request)
            return await call_next(request)

        # Dev passthrough: when CLERK_DOMAIN not set in development, grant admin access
        clerk_domain = os.getenv("CLERK_DOMAIN", "")
        environment = os.getenv("ENVIRONMENT", "development")
        if not clerk_domain and environment == "development":
            # TODO[CRITICAL]: Keep dev path, but centralize it as an explicit DevAuthPolicy
            # (single gate, audited logs, and shared behavior across middleware/dependencies).
            request.state.user_id = "dev_user"
            request.state.user_role = UserRole.ADMIN
            request.state.user = None  # No DB user in dev passthrough
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

        if not clerk_domain:
            # Fail-closed: deny access when auth is not configured
            logger.error("CLERK_DOMAIN not set - denying access to protected endpoint")
            return Response(
                content='{"detail":"Authentication service not configured"}',
                status_code=503,
                media_type="application/json",
            )

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

            clerk_id = payload.get("sub", "")
            # Extract profile info from Clerk JWT claims
            email = payload.get("email")
            username = payload.get("username") or payload.get("name")
            avatar_url = payload.get("image_url") or payload.get("profile_image_url")

            # Upsert user in database
            try:
                user = await _upsert_user(clerk_id, email, username, avatar_url)
                request.state.user_id = clerk_id
                request.state.user_role = user.role
                request.state.user = user
            except Exception as e:
                # TODO[HIGH]: Eliminate JWT-claim fallback; reject request when user persistence fails.
                # If DB upsert fails, still allow request with JWT claims
                logger.warning(f"User upsert failed, using JWT claims: {e}")
                request.state.user_id = clerk_id
                request.state.user_role = UserRole(
                    payload.get("metadata", {}).get("role", "user")
                )
                request.state.user = None

        except jwt.ExpiredSignatureError:
            return Response(
                content='{"detail":"Token expired"}',
                status_code=401,
                media_type="application/json",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT: {e}")
            return Response(
                content='{"detail":"Invalid authentication token"}',
                status_code=401,
                media_type="application/json",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
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
            if request.state.user_role != UserRole.ADMIN:
                return Response(
                    content='{"detail":"Admin access required"}',
                    status_code=403,
                    media_type="application/json",
                )

        # Tier 3: Premium check
        if _is_premium_endpoint(path):
            if request.state.user_role not in (UserRole.PREMIUM, UserRole.ADMIN):
                return Response(
                    content='{"detail":"Premium access required"}',
                    status_code=403,
                    media_type="application/json",
                )

        return await call_next(request)

    async def _try_extract_user(self, request: Request) -> None:
        """Try to extract user from Bearer token on public endpoints (optional auth)."""
        # Dev passthrough: grant admin access when CLERK_DOMAIN not set in development
        clerk_domain = os.getenv("CLERK_DOMAIN", "")
        environment = os.getenv("ENVIRONMENT", "development")
        if not clerk_domain and environment == "development":
            # TODO[CRITICAL]: Keep optional-auth dev path, but route through the same explicit
            # DevAuthPolicy used by protected endpoints to avoid split behavior.
            request.state.user_id = "dev_user"
            request.state.user_role = UserRole.ADMIN
            request.state.user = None
            return

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            request.state.user_id = None
            request.state.user_role = None
            request.state.user = None
            return

        token = auth_header[7:]

        if not clerk_domain:
            request.state.user_id = None
            request.state.user_role = None
            request.state.user = None
            return

        try:
            jwks = await _get_jwks(clerk_domain)
            signing_key = _get_signing_key(jwks, token)
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                issuer=f"https://{clerk_domain}",
                options={"verify_aud": False},
            )

            clerk_id = payload.get("sub", "")
            email = payload.get("email")
            username = payload.get("username") or payload.get("name")
            avatar_url = payload.get("image_url") or payload.get("profile_image_url")

            try:
                user = await _upsert_user(clerk_id, email, username, avatar_url)
                request.state.user_id = clerk_id
                request.state.user_role = user.role
                request.state.user = user
            except Exception:
                # TODO[HIGH]: Stop masking persistence failures as USER role; surface explicit auth-state error.
                request.state.user_id = clerk_id
                request.state.user_role = UserRole.USER
                request.state.user = None
        except Exception:
            # TODO[HIGH]: Replace silent optional-auth failure with explicit telemetry + typed failure path.
            # Silent failure on public endpoints — user just won't be authenticated
            request.state.user_id = None
            request.state.user_role = None
            request.state.user = None


async def get_current_user(request: Request) -> str:
    """FastAPI dependency: returns the authenticated user_id.

    Use as Depends(get_current_user) on endpoints that require auth.
    """
    # TODO[CRITICAL]: Remove getattr fallback; require middleware to set typed auth state fields.
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def get_current_user_object(request: Request) -> User:
    """FastAPI dependency: returns the full User document.

    Use as Depends(get_current_user_object) on endpoints that need user details.
    """
    # TODO[CRITICAL]: Remove dynamic request.state access; enforce explicit state contract.
    user = getattr(request.state, "user", None)
    if user is not None:
        return user

    # TODO[HIGH]: Revisit this fallback DB lookup; dependency should not recover missing middleware state.
    # Fallback: look up by user_id
    user_id = await get_current_user(request)
    user = await User.find_one(User.clerk_id == user_id)
    if not user:
        # TODO[HIGH]: Keep dev principal support, but move synthetic user creation to a
        # dedicated factory so this dependency does not embed environment-specific branching.
        # Dev passthrough: create a synthetic admin user
        if user_id == "dev_user":
            return User(
                clerk_id="dev_user",
                email="dev@localhost",
                username="dev_admin",
                role=UserRole.ADMIN,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def require_admin(request: Request) -> str:
    """FastAPI dependency: requires admin role.

    Use as Depends(require_admin) on admin-only endpoints.
    """
    user_id = await get_current_user(request)
    # TODO[CRITICAL]: Remove getattr default role; explicit auth state must be mandatory.
    role = getattr(request.state, "user_role", UserRole.USER)
    if role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user_id


async def require_premium(request: Request) -> str:
    """FastAPI dependency: requires premium or admin role.

    Use as Depends(require_premium) on premium endpoints.
    """
    user_id = await get_current_user(request)
    # TODO[CRITICAL]: Remove getattr default role; explicit auth state must be mandatory.
    role = getattr(request.state, "user_role", UserRole.USER)
    if role not in (UserRole.PREMIUM, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium access required",
        )
    return user_id


def get_optional_user(request: Request) -> str | None:
    """FastAPI dependency: returns user_id if authenticated, None otherwise.

    Use for endpoints that work with or without auth (e.g., personalized results).
    """
    # TODO[HIGH]: Remove dynamic optional auth lookup and return from a typed auth context object.
    return getattr(request.state, "user_id", None)


def get_optional_user_role(request: Request) -> UserRole | None:
    """FastAPI dependency: returns user role if authenticated, None otherwise."""
    # TODO[HIGH]: Remove dynamic optional auth lookup and return from a typed auth context object.
    return getattr(request.state, "user_role", None)
