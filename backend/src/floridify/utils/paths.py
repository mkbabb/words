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


def ensure_directories() -> None:
    """Ensure all required directories exist."""
    for directory in [AUTH_DIR, DATA_DIR, LOGS_DIR, CACHE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)