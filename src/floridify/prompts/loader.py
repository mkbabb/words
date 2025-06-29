"""Prompt loader for managing template files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from .templates import PromptTemplate, parse_prompt_markdown


class PromptLoader:
    """Loads and manages prompt templates from markdown files."""
    
    def __init__(self, templates_dir: str | Path | None = None) -> None:
        """Initialize the prompt loader.
        
        Args:
            templates_dir: Directory containing template files. 
                          Defaults to templates/ subdirectory relative to this file.
        """
        if templates_dir is None:
            # Default to templates directory relative to this file
            templates_dir = Path(__file__).parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        self._cache: Dict[str, PromptTemplate] = {}
        
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_dir}")
    
    def load_template(self, template_name: str) -> PromptTemplate:
        """Load a prompt template by name.
        
        Args:
            template_name: Name of the template (without .md extension)
            
        Returns:
            Loaded PromptTemplate object
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If template file is malformed
        """
        # Check cache first
        if template_name in self._cache:
            return self._cache[template_name]
        
        # Load from file
        template_path = self.templates_dir / f"{template_name}.md"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            template = parse_prompt_markdown(content, template_name)
            
            # Cache the template
            self._cache[template_name] = template
            
            return template
            
        except Exception as e:
            raise ValueError(f"Error parsing template '{template_name}': {e}") from e
    
    def list_templates(self) -> list[str]:
        """List all available template names.
        
        Returns:
            List of template names (without .md extension)
        """
        templates = []
        for file_path in self.templates_dir.glob("*.md"):
            templates.append(file_path.stem)
        return sorted(templates)
    
    def reload_template(self, template_name: str) -> PromptTemplate:
        """Force reload a template from disk.
        
        Args:
            template_name: Name of the template to reload
            
        Returns:
            Reloaded PromptTemplate object
        """
        # Clear from cache
        if template_name in self._cache:
            del self._cache[template_name]
        
        # Load fresh copy
        return self.load_template(template_name)
    
    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()
    
    def get_template_info(self, template_name: str) -> dict[str, Any]:
        """Get information about a template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Dictionary with template metadata
        """
        template = self.load_template(template_name)
        
        return {
            "name": template.name,
            "variables": list(template.variables.keys()),
            "system_message_preview": template.system_message[:100] + "..." if len(template.system_message) > 100 else template.system_message,
            "ai_settings": template.get_ai_settings(),
        }