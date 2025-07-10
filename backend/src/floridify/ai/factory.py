"""Factory for creating AI components with configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import toml

from ..utils.logging import get_logger
from .connector import OpenAIConnector
from .synthesizer import DefinitionSynthesizer

logger = get_logger(__name__)

# Global singleton instances
_openai_connector: OpenAIConnector | None = None
_definition_synthesizer: DefinitionSynthesizer | None = None


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from TOML file."""
    if config_path is None:
        # Default to auth/config.toml relative to project root
        current_dir = Path(__file__).parent.parent.parent.parent
        config_path = current_dir / "auth" / "config.toml"
    
    with open(config_path, encoding="utf-8") as f:
        return toml.load(f)


def get_openai_connector(
    config_path: str | Path | None = None,
    force_recreate: bool = False,
) -> OpenAIConnector:
    """Get or create the global OpenAI connector singleton.
    
    Args:
        config_path: Path to configuration file (defaults to auth/config.toml)
        force_recreate: Force recreation of the connector
        
    Returns:
        Initialized OpenAI connector instance
    """
    global _openai_connector
    
    if _openai_connector is None or force_recreate:
        logger.info("Initializing OpenAI connector singleton")
        config = load_config(config_path)
        
        api_key = config["openai"]["api_key"]
        model_name = config["models"]["openai_model"]
        
        # Only set temperature for non-reasoning models
        temperature = None
        if not model_name.startswith(("o1", "o3")):
            temperature = 0.7  # Default temperature for non-reasoning models
        
        _openai_connector = OpenAIConnector(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
        )
        logger.success("OpenAI connector singleton initialized")
    
    return _openai_connector


def create_openai_connector(config_path: str | Path | None = None) -> OpenAIConnector:
    """Create OpenAI connector from configuration.
    
    DEPRECATED: Use get_openai_connector() for singleton behavior.
    This function is kept for backward compatibility.
    """
    return get_openai_connector(config_path)


def get_definition_synthesizer(
    config_path: str | Path | None = None, 
    examples_count: int = 2,
    force_recreate: bool = False,
) -> DefinitionSynthesizer:
    """Get or create the global definition synthesizer singleton.
    
    Args:
        config_path: Path to configuration file
        examples_count: Number of examples to generate
        force_recreate: Force recreation of the synthesizer
        
    Returns:
        Initialized definition synthesizer instance
    """
    global _definition_synthesizer
    
    if _definition_synthesizer is None or force_recreate:
        logger.info("Initializing definition synthesizer singleton")
        connector = get_openai_connector(config_path, force_recreate)
        _definition_synthesizer = DefinitionSynthesizer(connector, examples_count=examples_count)
        logger.success("Definition synthesizer singleton initialized")
    
    return _definition_synthesizer


def create_definition_synthesizer(
    config_path: str | Path | None = None, 
    examples_count: int = 2
) -> DefinitionSynthesizer:
    """Create definition synthesizer with OpenAI connector.
    
    DEPRECATED: Use get_definition_synthesizer() for singleton behavior.
    This function is kept for backward compatibility.
    """
    return get_definition_synthesizer(config_path, examples_count)


def create_ai_system(
    config_path: str | Path | None = None,
    examples_count: int = 2,
) -> tuple[OpenAIConnector, DefinitionSynthesizer]:
    """Create complete AI system from configuration.
    
    Returns singleton instances for optimal resource usage.
    """
    connector = get_openai_connector(config_path)
    synthesizer = get_definition_synthesizer(config_path, examples_count)
    return connector, synthesizer


def reset_ai_singletons() -> None:
    """Reset all AI singletons (for testing/cleanup)."""
    global _openai_connector, _definition_synthesizer
    _openai_connector = None
    _definition_synthesizer = None
    logger.info("AI singletons reset")