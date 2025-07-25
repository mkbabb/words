"""Modern path constants for Floridify using 2024 best practices."""

from __future__ import annotations

import os
from pathlib import Path


def find_project_root() -> Path:
    """Find project root by looking for both pyproject.toml and auth directory.
    
    Uses modern approach with environment variable override and marker file discovery.
    For this project, we want the root that contains both backend/ and auth/ directories.
    """
    # Environment override (12-factor app principle)
    env_root = os.getenv("FLORIDIFY_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    
    # Check if we're in Docker (auth directory is at /app/auth)
    is_docker = os.path.exists("/.dockerenv")
    if is_docker:
        # In Docker, the backend is mounted at /app and auth at /app/auth
        app_root = Path("/app")
        if (app_root / "auth").exists():
            return app_root
    
    # Search upward from current file location for project root markers
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
        # Also check if we're in backend directory
        if current.name == "backend" and (current.parent / "auth").exists():
            return current.parent
        current = current.parent
    
    return Path.cwd()


def get_config_path() -> Path:
    """Get path to configuration file with environment override."""
    env_path = os.getenv("FLORIDIFY_CONFIG_PATH")
    if env_path:
        return Path(env_path)
    
    # Try standard location
    config_path = PROJECT_ROOT / "auth" / "config.toml"
    if config_path.exists():
        return config_path
    
    # In Docker, auth might be directly in /app/auth
    if os.path.exists("/.dockerenv"):
        docker_config = Path("/app/auth/config.toml")
        if docker_config.exists():
            return docker_config
    
    # Return the standard path even if it doesn't exist
    # (will trigger FileNotFoundError in load_config_dict)
    return config_path


def ensure_directories() -> None:
    """Ensure all required directories exist."""
    for directory in [AUTH_DIR, DATA_DIR, LOGS_DIR, CACHE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# Initialize paths
PROJECT_ROOT = find_project_root()

# Directory constants
AUTH_DIR = PROJECT_ROOT / "auth"
DATA_DIR = PROJECT_ROOT / "backend" / "data"
LOGS_DIR = PROJECT_ROOT / "backend" / "logs"
CACHE_DIR = PROJECT_ROOT / "backend" / ".cache"

# File constants
CONFIG_FILE = get_config_path()