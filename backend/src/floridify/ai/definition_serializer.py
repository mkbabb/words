"""Optimized definition serialization for AI prompts."""

from typing import Any

from ..models import Definition


def serialize_definition_for_ai(definition: Definition, include_examples: bool = False) -> dict[str, Any]:
    """Serialize Definition object for AI prompts with minimal tokens.
    
    Args:
        definition: Definition object to serialize
        include_examples: Whether to include example data (adds significant tokens)
        
    Returns:
        Minimal dict with just essential fields for AI processing
    """
    serialized = {
        "definition": definition.text,  # Map text -> definition for template compatibility
        "part_of_speech": definition.part_of_speech,
    }
    
    # Only include synonyms if present and limit to first 5
    if definition.synonyms:
        serialized["synonyms"] = ", ".join(definition.synonyms[:5])
    
    # Only include examples if specifically requested
    if include_examples and definition.example_ids:
        # This would need to load examples - for now just indicate presence
        serialized["has_examples"] = "true"
        
    return serialized


def prepare_definitions_for_synthesis(definitions: list[Definition], max_definitions: int = 10) -> list[dict[str, Any]]:
    """Prepare definitions for synthesis with token optimization.
    
    Args:
        definitions: List of Definition objects
        max_definitions: Maximum definitions to include per cluster
        
    Returns:
        List of serialized definitions optimized for token usage
    """
    # Limit definitions to prevent excessive tokens
    limited_defs = definitions[:max_definitions]
    
    # Serialize without examples for synthesis
    return [serialize_definition_for_ai(d, include_examples=False) for d in limited_defs]