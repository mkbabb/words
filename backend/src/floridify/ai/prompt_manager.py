"""Streamlined prompt template manager for AI operations."""

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup


def _sanitize_user_input(value: str) -> str:
    """Sanitize user-provided text before injecting into prompts.

    Strips control characters and common prompt injection patterns
    while preserving legitimate content.
    """
    if not isinstance(value, str):
        return str(value)

    # Strip control characters (except newlines and tabs)
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

    # Neutralize common prompt injection delimiters
    # Replace triple backticks and system-like prefixes
    value = value.replace('```', '`​`​`')  # Insert zero-width spaces
    value = re.sub(
        r'(?i)(system\s*:|assistant\s*:|user\s*:|<\|im_start\|>|<\|im_end\|>)',
        lambda m: m.group(0).replace(':', ':\u200B'),  # Zero-width space after colon
        value,
    )

    return value


class PromptManager:
    """Lightweight prompt template manager using Jinja2.

    All user-provided variables are automatically sanitized to prevent
    prompt injection attacks.
    """

    DEFAULT_EXTENSIONS = [".md", ".txt", ""]

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize the prompt manager.

        Args:
            prompts_dir: Directory containing prompt templates.
                        Defaults to ai/prompts relative to this file.

        """
        self.prompts_dir = prompts_dir or Path(__file__).parent / "prompts"

        # Setup Jinja2 environment with filesystem loader
        self.env = Environment(
            loader=FileSystemLoader(self.prompts_dir),
            autoescape=select_autoescape(enabled_extensions=()),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom filter for explicit sanitization in templates
        self.env.filters["sanitize"] = _sanitize_user_input

    def _find_template_path(self, name: str) -> Path:
        """Find template file with flexible extension handling.

        Args:
            name: Template name (can include subdirectory path)

        Returns:
            Path to the template file

        Raises:
            FileNotFoundError: If template not found

        """
        # Support nested paths (e.g., "assess/cefr" or "synthesize/definitions")
        base_path = self.prompts_dir / name

        # Try each extension
        for ext in self.DEFAULT_EXTENSIONS:
            template_path = Path(str(base_path) + ext)
            if template_path.exists():
                return template_path

        # If not found, raise error
        raise FileNotFoundError(f"Template not found: {name}")

    def get_template(self, name: str) -> str:
        """Get raw template content without rendering.

        Args:
            name: Template name/path

        Returns:
            Raw template content

        """
        path = self._find_template_path(name)
        content = path.read_text(encoding="utf-8")
        return content.strip()

    def _sanitize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Sanitize all user-provided string values in the context.

        This prevents prompt injection by stripping control characters
        and neutralizing injection patterns in all string values.
        """
        sanitized = {}
        for key, value in context.items():
            if isinstance(value, str):
                sanitized[key] = _sanitize_user_input(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    _sanitize_user_input(item) if isinstance(item, str) else item
                    for item in value
                ]
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_context(value)
            else:
                sanitized[key] = value
        return sanitized

    def render(self, name: str, **context: Any) -> str:
        """Render a template with the given context.

        All string values in context are automatically sanitized to
        prevent prompt injection attacks.

        Args:
            name: Template name/path (e.g., "synthesize/definitions")
            **context: Variables to pass to the template

        Returns:
            Rendered template string

        """
        # Find the template file
        path = self._find_template_path(name)

        # Get relative path for Jinja2 (from prompts_dir)
        relative_path = path.relative_to(self.prompts_dir)

        # Sanitize all user-provided values before rendering
        sanitized_context = self._sanitize_context(context)

        # Load and render template
        template = self.env.get_template(str(relative_path))
        return template.render(**sanitized_context).strip()

    def list_templates(self) -> list[str]:
        """List all available templates.

        Returns:
            List of template names (without extensions)

        """
        templates = []

        # Walk through prompts directory
        for path in self.prompts_dir.rglob("*"):
            if path.is_file():
                # Check if file has valid extension
                for ext in self.DEFAULT_EXTENSIONS:
                    if ext and path.suffix == ext:
                        # Get relative path without extension
                        rel_path = path.relative_to(self.prompts_dir)
                        template_name = str(rel_path.with_suffix(""))
                        templates.append(template_name)
                        break
                    if not ext and not path.suffix:
                        # Handle files without extension
                        rel_path = path.relative_to(self.prompts_dir)
                        templates.append(str(rel_path))
                        break

        return sorted(templates)

    def template_exists(self, name: str) -> bool:
        """Check if a template exists.

        Args:
            name: Template name/path

        Returns:
            True if template exists

        """
        try:
            self._find_template_path(name)
            return True
        except FileNotFoundError:
            return False
