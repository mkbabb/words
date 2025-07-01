"""Factory for creating AI components with configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import toml

from .connector import OpenAIConnector
from .synthesizer import DefinitionSynthesizer


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from TOML file."""
    if config_path is None:
        # Default to auth/config.toml relative to project root
        current_dir = Path(__file__).parent.parent.parent.parent
        config_path = current_dir / "auth" / "config.toml"
    
    with open(config_path, encoding="utf-8") as f:
        return toml.load(f)


def create_openai_connector(config_path: str | Path | None = None) -> OpenAIConnector:
    """Create OpenAI connector from configuration."""
    config = load_config(config_path)
    
    api_key = config["openai"]["api_key"]
    model_name = config["models"]["openai_model"]
    
    # Only set temperature for non-reasoning models
    temperature = None
    if not model_name.startswith(("o1", "o3")):
        temperature = 0.7  # Default temperature for non-reasoning models
    
    return OpenAIConnector(
        api_key=api_key,
        model_name=model_name,
        temperature=temperature,
    )


def create_definition_synthesizer(config_path: str | Path | None = None) -> DefinitionSynthesizer:
    """Create definition synthesizer with OpenAI connector."""
    connector = create_openai_connector(config_path)
    return DefinitionSynthesizer(connector)


def create_ai_system(config_path: str | Path | None = None) -> tuple[OpenAIConnector, DefinitionSynthesizer]:
    """Create complete AI system from configuration."""
    connector = create_openai_connector(config_path)
    synthesizer = DefinitionSynthesizer(connector)
    return connector, synthesizer