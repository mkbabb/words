"""AI integration module for Floridify dictionary synthesis and generation."""

from .connector import OpenAIConnector
from .factory import (
    create_ai_system,
    get_definition_synthesizer,
    get_openai_connector,
    reset_ai_singletons,
)
from .models import (
    AIGeneratedProviderData,
    SynthesisResponse,
)
from .synthesizer import DefinitionSynthesizer

__all__ = [
    "AIGeneratedProviderData",
    "DefinitionSynthesizer",
    "OpenAIConnector",
    "SynthesisResponse",
    "create_ai_system",
    "get_definition_synthesizer",
    "get_openai_connector",
    "reset_ai_singletons",
]
