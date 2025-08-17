"""
Streamlined prompt template manager for AI operations.
"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class PromptManager:
    """Lightweight prompt template manager using Jinja2."""

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

    def render(self, name: str, **context: Any) -> str:
        """Render a template with the given context.

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

        # Load and render template
        template = self.env.get_template(str(relative_path))
        return template.render(**context).strip()

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
                    elif not ext and not path.suffix:
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
