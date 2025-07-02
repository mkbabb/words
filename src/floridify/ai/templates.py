"""Template management for AI prompts using Jinja2."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateNotFound


class PromptTemplateLoader(BaseLoader):
    """Custom Jinja2 loader for prompt templates."""

    def __init__(self, template_dir: str | Path) -> None:
        self.template_dir = Path(template_dir)

    def get_source(self, environment: Environment, template: str) -> tuple[str, str, Any]:
        """Load template source from file."""
        template_path = self.template_dir / f"{template}.md"
        
        if not template_path.exists():
            raise TemplateNotFound(template)
        
        mtime = os.path.getmtime(template_path)
        
        with open(template_path, encoding="utf-8") as f:
            source = f.read()
        
        return source, str(template_path), lambda: mtime == os.path.getmtime(template_path)


class PromptTemplateManager:
    """Manages prompt templates with Jinja2."""

    def __init__(self, template_dir: str | Path | None = None) -> None:
        if template_dir is None:
            # Default to prompts directory relative to this file
            current_dir = Path(__file__).parent
            template_dir = current_dir / "prompts"
        
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=PromptTemplateLoader(self.template_dir),
            autoescape=False,  # We don't want HTML escaping for prompts
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_template(self, template_name: str, **kwargs: Any) -> str:
        """Render a template with the given context."""
        template = self.env.get_template(template_name)
        return template.render(**kwargs)

    def get_synthesis_prompt(
        self, word: str, word_type: str, provider_definitions: list[tuple[str, str]]
    ) -> str:
        """Generate synthesis prompt for definition aggregation."""
        return self.render_template(
            "synthesis",
            word=word,
            word_type=word_type,
            provider_definitions=provider_definitions,
        )

    def get_example_prompt(self, word: str, definition: str, word_type: str) -> str:
        """Generate example generation prompt."""
        return self.render_template(
            "example_generation",
            word=word,
            definition=definition,
            word_type=word_type,
        )

    def get_pronunciation_prompt(self, word: str) -> str:
        """Generate pronunciation prompt."""
        return self.render_template("pronunciation", word=word)

    def get_fallback_prompt(self, word: str) -> str:
        """Generate fallback provider prompt."""
        return self.render_template("fallback_provider", word=word)

    def get_meaning_extraction_prompt(
        self, word: str, all_provider_definitions: list[tuple[str, str, str]]
    ) -> str:
        """Generate meaning extraction prompt."""
        return self.render_template(
            "meaning_extraction",
            word=word,
            all_provider_definitions=all_provider_definitions,
        )