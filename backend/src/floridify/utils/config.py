"""Centralized configuration loading with environment variable support."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import toml

from ..config import Config
from .paths import get_config_path, PROJECT_ROOT


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
    
    try:
        with open(config_path, encoding="utf-8") as f:
            return toml.load(f)
    except Exception as e:
        raise


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
    """Get database configuration with automatic environment detection.
    
    Detects environment based on:
    - Running in Docker container (production/staging)
    - Running on EC2 instance (production)
    - Running locally (development with SSH tunnel)
    
    Returns:
        Tuple of (mongodb_url, database_name)
    """
    try:
        config_dict = load_config_dict()
        if config_dict is None:
            raise ValueError("load_config_dict returned None")
        db_config = config_dict.get("database", {})
        
        # Detect environment
        is_docker = os.path.exists("/.dockerenv")
        is_ec2 = os.path.exists("/var/lib/cloud")
        is_production = is_ec2 or os.getenv("ENVIRONMENT") == "production"
        
        # Get the base URL from config
        mongodb_url = db_config.get("url")
        database_name = db_config.get("name", "floridify")
        
        # Log environment detection
        from ..utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info(f"Environment detection: docker={is_docker}, ec2={is_ec2}, production={is_production}")
        
        # Modify URL based on environment
        if mongodb_url:
            # For local development, we need to use SSH tunnel
            if not is_production:
                # Replace production DocumentDB with localhost SSH tunnel
                if "docdb" in mongodb_url and "amazonaws.com" in mongodb_url:
                    # Extract username and password from URL
                    import re
                    match = re.search(r'mongodb://([^:]+):([^@]+)@', mongodb_url)
                    if match:
                        username = match.group(1)
                        password = match.group(2)
                        # Build local development URL with SSH tunnel
                        # For SSH tunnel, we need to disable hostname verification since cert is for DocumentDB not localhost
                        if is_docker:
                            # Docker uses host.docker.internal to reach host's localhost
                            mongodb_url = f"mongodb://{username}:{password}@host.docker.internal:27018/floridify?tls=true&tlsCAFile=/app/auth/rds-ca-2019-root.pem&retryWrites=false&directConnection=true&tlsAllowInvalidHostnames=true"
                            logger.info("Using Docker development connection via host.docker.internal SSH tunnel on port 27018")
                        else:
                            # Native local development
                            mongodb_url = f"mongodb://{username}:{password}@localhost:27018/floridify?tls=true&tlsCAFile={PROJECT_ROOT}/auth/rds-ca-2019-root.pem&retryWrites=false&directConnection=true&tlsAllowInvalidHostnames=true"
                            logger.info("Using local development connection via SSH tunnel on port 27018")
            else:
                logger.info("Using production database configuration")
        
        if not mongodb_url:
            raise ValueError(f"No MongoDB URL found for environment (docker={is_docker}, ec2={is_ec2}, production={is_production})")
        
        return mongodb_url, database_name
        
    except Exception as e:
        # More detailed error logging
        from ..utils.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"Failed to load database config: {type(e).__name__}: {e}")
        logger.error("Stack trace:", exc_info=True)
        
        # Only use fallback for local development
        if not os.path.exists("/.dockerenv") and not os.path.exists("/var/lib/cloud"):
            logger.warning("Using localhost fallback for local development")
            return "mongodb://localhost:27017", "floridify"
        else:
            # In Docker/production, we should fail fast
            raise


def update_tls_path_in_url(url: str, new_path: str) -> str:
    """Update the tlsCAFile path in a MongoDB URL."""
    import re
    return re.sub(r'tlsCAFile=[^&]+', f'tlsCAFile={new_path}', url)