"""Configuration classes for connectors."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VersionConfig(BaseModel):
    """Configuration for versioned fetching behavior."""
    
    force_api: bool = Field(default=False, description="Force API call even if versioned data exists")
    version: str | None = Field(default=None, description="Fetch specific version from storage")
    save_versioned: bool = Field(default=True, description="Save API results to versioned storage")
    increment_version: bool = Field(default=True, description="Auto-increment version when saving")
    
    class Config:
        """Pydantic configuration."""
        frozen = True  # Make immutable