"""Centralized configuration loading with environment variable support."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import toml

from ..config import Config
from .paths import get_config_path


def load_config_dict(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from TOML file as dictionary.
    
    Args:
        config_path: Path to configuration file (defaults to auth/config.toml)
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
    """
    if config_path is None:
        config_path = get_config_path()
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, encoding="utf-8") as f:
        return toml.load(f)


def load_config(config_path: str | Path | None = None) -> Config:
    """Load structured configuration object.
    
    Args:
        config_path: Path to configuration file (defaults to auth/config.toml)
        
    Returns:
        Structured Config object
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
    """
    return Config.from_file(config_path)


def get_database_config() -> tuple[str, str]:
    """Get database configuration from config file with optional environment override.
    
    Priority order:
    1. Environment variables (for local development override)
    2. Configuration file values (production default)
    3. Built-in defaults (fallback)
    
    Returns:
        Tuple of (mongodb_url, database_name)
    """
    # Allow environment variable override (mainly for local development)
    mongodb_url = os.getenv("MONGODB_URL")
    database_name = os.getenv("MONGODB_DATABASE")
    
    # Load from config file if not overridden
    if mongodb_url is None or database_name is None:
        try:
            config = load_config()
            if mongodb_url is None:
                mongodb_url = config.database.url
            if database_name is None:
                database_name = config.database.name
        except (FileNotFoundError, AttributeError):
            # Final fallbacks
            if mongodb_url is None:
                mongodb_url = "mongodb://localhost:27017"
            if database_name is None:
                database_name = "floridify"
    
    return mongodb_url, database_name