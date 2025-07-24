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
    
    # Search upward from current file location for project root markers
    current = Path(__file__).resolve().parent
    while current != current.parent:
        # Look for the root that has both backend and auth directories
        if (current / "backend").exists() and (current / "auth").exists():
            return current
        current = current.parent
    
    # Fallback to current working directory search  
    current = Path.cwd()
    while current != current.parent:
        if (current / "backend").exists() and (current / "auth").exists():
            return current
        current = current.parent
    
    return Path.cwd()


def get_config_path() -> Path:
    """Get path to configuration file with environment override."""
    env_path = os.getenv("FLORIDIFY_CONFIG_PATH")
    if env_path:
        return Path(env_path)
    return PROJECT_ROOT / "auth" / "config.toml"


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