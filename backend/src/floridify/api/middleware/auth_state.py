"""Typed authentication state for request middleware.

Replaces untyped request.state attributes with a structured model.
"""

from pydantic import BaseModel

from ...models.user import User, UserRole


class AuthState(BaseModel):
    """Typed authentication state attached to request.state.auth."""

    user_id: str | None = None
    user_role: UserRole | None = None
    user: User | None = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None

    @property
    def is_admin(self) -> bool:
        return self.user_role == UserRole.ADMIN

    @property
    def is_premium_or_admin(self) -> bool:
        return self.user_role in (UserRole.PREMIUM, UserRole.ADMIN)


class DevAuthState(AuthState):
    """Dev-mode auth state with admin access."""

    user_id: str = "dev_user"
    user_role: UserRole = UserRole.ADMIN
