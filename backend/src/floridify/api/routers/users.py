"""User management endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...models.user import User, UserHistory, UserRole
from ..core import AdminDep, CurrentUserDep, CurrentUserObjectDep

router = APIRouter(prefix="/users", tags=["users"])


# --- Request/Response Models ---


class UserProfileResponse(BaseModel):
    """Public user profile."""

    clerk_id: str
    email: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    role: UserRole
    preferences: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    last_login: datetime


class UpdateProfileRequest(BaseModel):
    """Fields that can be updated on a user profile."""

    username: str | None = None
    avatar_url: str | None = None


class UpdatePreferencesRequest(BaseModel):
    """Full replacement of user preferences."""

    preferences: dict[str, Any]


class SyncHistoryRequest(BaseModel):
    """Merge history from frontend."""

    search_history: list[dict[str, Any]] = Field(default_factory=list)
    lookup_history: list[dict[str, Any]] = Field(default_factory=list)


class HistoryResponse(BaseModel):
    """User history."""

    search_history: list[dict[str, Any]] = Field(default_factory=list)
    lookup_history: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: datetime | None = None


class UpdateRoleRequest(BaseModel):
    """Admin request to change a user's role."""

    role: UserRole


class UserListItem(BaseModel):
    """User summary for admin list."""

    clerk_id: str
    email: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    role: UserRole
    created_at: datetime
    last_login: datetime


# --- Endpoints ---


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(user: CurrentUserObjectDep):
    """Get the current user's profile."""
    return UserProfileResponse(
        clerk_id=user.clerk_id,
        email=user.email,
        username=user.username,
        avatar_url=user.avatar_url,
        role=user.role,
        preferences=user.preferences,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    body: UpdateProfileRequest,
    user: CurrentUserObjectDep,
):
    """Update the current user's profile fields."""
    if body.username is not None:
        user.username = body.username
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    await user.save()

    return UserProfileResponse(
        clerk_id=user.clerk_id,
        email=user.email,
        username=user.username,
        avatar_url=user.avatar_url,
        role=user.role,
        preferences=user.preferences,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.get("/me/preferences")
async def get_my_preferences(
    user: CurrentUserObjectDep,
) -> dict[str, Any]:
    """Get the current user's preferences."""
    return user.preferences


@router.put("/me/preferences")
async def set_my_preferences(
    body: UpdatePreferencesRequest,
    user: CurrentUserObjectDep,
) -> dict[str, Any]:
    """Set the current user's preferences (full replacement)."""
    user.preferences = body.preferences
    await user.save()
    return user.preferences


@router.get("/me/history", response_model=HistoryResponse)
async def get_my_history(user_id: CurrentUserDep):
    """Get the current user's search and lookup history."""
    history = await UserHistory.find_one(UserHistory.clerk_id == user_id)
    if not history:
        return HistoryResponse()
    return HistoryResponse(
        search_history=history.search_history,
        lookup_history=history.lookup_history,
        updated_at=history.updated_at,
    )


@router.post("/me/history/sync", response_model=HistoryResponse)
async def sync_my_history(
    body: SyncHistoryRequest,
    user_id: CurrentUserDep,
):
    """Merge history from frontend with backend storage.

    Deduplicates by timestamp and keeps the most recent 100 entries per category.
    """
    history = await UserHistory.find_one(UserHistory.clerk_id == user_id)
    if not history:
        history = UserHistory(
            clerk_id=user_id,
            search_history=[],
            lookup_history=[],
        )

    # Merge search history (deduplicate by timestamp)
    existing_search_ts = {
        entry.get("timestamp") for entry in history.search_history if "timestamp" in entry
    }
    for entry in body.search_history:
        if entry.get("timestamp") not in existing_search_ts:
            history.search_history.append(entry)

    # Merge lookup history (deduplicate by timestamp)
    existing_lookup_ts = {
        entry.get("timestamp") for entry in history.lookup_history if "timestamp" in entry
    }
    for entry in body.lookup_history:
        if entry.get("timestamp") not in existing_lookup_ts:
            history.lookup_history.append(entry)

    # Sort by timestamp descending and cap at 100 entries
    history.search_history.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    history.lookup_history.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    history.search_history = history.search_history[:100]
    history.lookup_history = history.lookup_history[:100]

    history.updated_at = datetime.now(UTC)
    await history.save()

    return HistoryResponse(
        search_history=history.search_history,
        lookup_history=history.lookup_history,
        updated_at=history.updated_at,
    )


# --- Admin Endpoints ---


@router.get("", response_model=list[UserListItem])
async def list_users(
    _admin_id: AdminDep,
    skip: int = 0,
    limit: int = 50,
):
    """List all users (admin only)."""
    users = await User.find_all().skip(skip).limit(limit).to_list()
    return [
        UserListItem(
            clerk_id=u.clerk_id,
            email=u.email,
            username=u.username,
            avatar_url=u.avatar_url,
            role=u.role,
            created_at=u.created_at,
            last_login=u.last_login,
        )
        for u in users
    ]


@router.patch("/{clerk_id}/role", response_model=UserListItem)
async def update_user_role(
    clerk_id: str,
    body: UpdateRoleRequest,
    _admin_id: AdminDep,
):
    """Change a user's role (admin only)."""
    user = await User.find_one(User.clerk_id == clerk_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {clerk_id} not found",
        )

    user.role = body.role
    await user.save()

    return UserListItem(
        clerk_id=user.clerk_id,
        email=user.email,
        username=user.username,
        avatar_url=user.avatar_url,
        role=user.role,
        created_at=user.created_at,
        last_login=user.last_login,
    )
