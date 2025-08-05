"""Path utilities and constants for Floridify."""

from __future__ import annotations

import os
from pathlib import Path


def get_project_root() -> Path:
    """Find project root by looking for both backend/ and auth/ directories.

    Uses modern approach with environment variable override and marker file discovery.
    """
    # Environment override (12-factor app principle)
    env_root = os.getenv("FLORIDIFY_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()

    # Check if we're in Docker
    is_docker = os.path.exists("/.dockerenv")
    if is_docker:
        # In Docker, the backend is mounted at /app
        app_root = Path("/app")
        if (app_root / "auth").exists():
            return app_root

    # Search upward from current file location
    current = Path(__file__).resolve().parent
    while current != current.parent:
        # Look for the root that has both backend and auth directories
        if (current / "backend").exists() and (current / "auth").exists():
            return current
        # Also check if we're inside backend and auth is a sibling
        if current.name == "backend" and (current.parent / "auth").exists():
            return current.parent
        current = current.parent

    # Fallback to current working directory search
    current = Path.cwd()
    while current != current.parent:
        if (current / "backend").exists() and (current / "auth").exists():
            return current
        if current.name == "backend" and (current.parent / "auth").exists():
            return current.parent
        current = current.parent

    return Path.cwd()


# Get project root
PROJECT_ROOT = get_project_root()

# Directory constants
AUTH_DIR = PROJECT_ROOT / "auth"
DATA_DIR = PROJECT_ROOT / "backend" / "data"
LOGS_DIR = PROJECT_ROOT / "backend" / "logs"
CACHE_DIR = PROJECT_ROOT / "backend" / ".cache"


def get_cache_directory(cache_type: str = "") -> Path:
    """
    Get unified cache directory for different cache types.
    
    Handles Docker, production, and development environments consistently.
    
    Args:
        cache_type: Optional cache type subdirectory (e.g., 'semantic', 'vocabulary', 'trie')
    
    Returns:
        Path to cache directory, created if it doesn't exist
    """
    # Check for environment variable override first (12-factor)
    env_cache_dir = os.getenv("FLORIDIFY_CACHE_DIR")
    if env_cache_dir:
        base_cache = Path(env_cache_dir)
    else:
        # Docker detection and path resolution
        is_docker = os.path.exists("/.dockerenv")
        if is_docker:
            # In Docker, use /app/cache (mounted volume)
            base_cache = Path("/app/cache")
        else:
            # Native development: use project cache or system cache
            project_cache = PROJECT_ROOT / "cache"
            if project_cache.exists():
                base_cache = project_cache
            else:
                # Fallback to user cache directory
                base_cache = Path.home() / ".cache"
    
    # Add floridify namespace and cache type
    cache_dir = base_cache / "floridify"
    if cache_type:
        cache_dir = cache_dir / cache_type
    
    # Ensure directory exists
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def ensure_directories() -> None:
    """Ensure all required directories exist."""
    for directory in [AUTH_DIR, DATA_DIR, LOGS_DIR, CACHE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
