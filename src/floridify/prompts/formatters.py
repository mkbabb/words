"""Formatters for preparing complex template variables."""

from __future__ import annotations

from typing import Any

from ..models import ProviderData


def format_provider_context(word: str, provider_definitions: dict[str, ProviderData]) -> str:
    """Format provider definitions into context string for synthesis.
    
    Args:
        word: The word being defined
        provider_definitions: Dictionary of provider data
        
    Returns:
        Formatted context string
    """
    context_parts = [f"Word: {word}\n"]
    
    for provider_name, provider_data in provider_definitions.items():
        if not provider_data.definitions:
            continue
            
        context_parts.append(f"\n{provider_name.upper()} DEFINITIONS:")
        
        for i, definition in enumerate(provider_data.definitions, 1):
            context_parts.append(
                f"{i}. [{definition.word_type.value}] {definition.definition}"
            )
            
            # Add examples if available
            if definition.examples.generated:
                context_parts.append("   Examples:")
                for example in definition.examples.generated[:2]:  # Limit examples
                    context_parts.append(f"   - {example.sentence}")
    
    return "\n".join(context_parts)


def format_template_variables(**kwargs: Any) -> dict[str, Any]:
    """Format and validate template variables.
    
    Args:
        **kwargs: Raw template variables
        
    Returns:
        Formatted template variables
    """
    formatted = {}
    
    for key, value in kwargs.items():
        if value is None:
            formatted[key] = ""
        elif isinstance(value, (list, dict)):
            # Convert complex types to string representation
            formatted[key] = str(value)
        else:
            formatted[key] = str(value)
    
    return formatted