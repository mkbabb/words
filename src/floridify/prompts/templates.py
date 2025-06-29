"""Prompt template data structures and parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class PromptTemplate:
    """Represents a prompt template with metadata."""
    
    name: str
    system_message: str
    user_template: str
    instructions: str
    output_format: str
    variables: dict[str, str]
    notes: dict[str, Any]
    
    def render(self, variables: dict[str, Any]) -> tuple[str, str]:
        """Render the template with provided variables.
        
        Args:
            variables: Dictionary of variable values
            
        Returns:
            Tuple of (system_message, rendered_user_prompt)
        """
        # Simple variable substitution using {{variable}} syntax
        rendered_user = self.user_template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            rendered_user = rendered_user.replace(placeholder, str(value))
        
        return self.system_message, rendered_user
    
    def get_ai_settings(self) -> dict[str, Any]:
        """Extract AI model settings from notes.
        
        Returns:
            Dictionary with model settings
        """
        settings = {}
        
        # Extract temperature
        if "temperature" in self.notes:
            try:
                settings["temperature"] = float(self.notes["temperature"])
            except (ValueError, TypeError):
                pass
        
        # Extract model
        if "model" in self.notes:
            settings["model"] = self.notes["model"]
            
        # Extract max_tokens
        if "max_tokens" in self.notes and self.notes["max_tokens"] != "auto":
            try:
                settings["max_tokens"] = int(self.notes["max_tokens"])
            except (ValueError, TypeError):
                pass
        
        return settings


def parse_prompt_markdown(content: str, template_name: str) -> PromptTemplate:
    """Parse a markdown prompt template file.
    
    Args:
        content: Raw markdown content
        template_name: Name of the template
        
    Returns:
        Parsed PromptTemplate object
    """
    sections = {}
    current_section = None
    current_content: list[str] = []
    
    lines = content.split('\n')
    
    for line in lines:
        # Check for section headers
        if line.startswith('## '):
            # Save previous section
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = line[3:].strip()
            current_content = []
        elif current_section:
            current_content.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    # Extract required sections
    system_message = sections.get('System Message', '')
    user_template = sections.get('User Prompt Template', '')
    instructions = sections.get('Instructions', '')
    output_format = sections.get('Output Format', '')
    
    # Parse variables section
    variables = {}
    variables_section = sections.get('Variables', '')
    if variables_section:
        for line in variables_section.split('\n'):
            if line.strip().startswith('- `{{'):
                # Parse format: - `{{variable}}` - Description
                match = re.search(r'`\{\{(\w+)\}\}` - (.+)', line)
                if match:
                    var_name, description = match.groups()
                    variables[var_name] = description.strip()
    
    # Parse notes section
    notes = {}
    notes_section = sections.get('Notes', '')
    if notes_section:
        for line in notes_section.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                # Parse format: - Key: value
                if line.startswith('- '):
                    line = line[2:]
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                # Extract numeric value before any parentheses or other text
                # Example: "0.3 (lower for consistency)" -> "0.3"
                if '(' in value:
                    value = value.split('(')[0].strip()
                
                # Convert some common values to appropriate types for notes dict
                parsed_value: Any = value
                if value.lower() in ('true', 'false'):
                    parsed_value = value.lower() == 'true'
                elif value.replace('.', '').isdigit():
                    parsed_value = float(value) if '.' in value else int(value)
                else:
                    parsed_value = value
                
                notes[key] = parsed_value
    
    return PromptTemplate(
        name=template_name,
        system_message=system_message,
        user_template=user_template,
        instructions=instructions,
        output_format=output_format,
        variables=variables,
        notes=notes,
    )