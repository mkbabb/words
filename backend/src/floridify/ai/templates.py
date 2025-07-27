"""Template management for AI prompts using Jinja2."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import BaseLoader, Environment, TemplateNotFound

if TYPE_CHECKING:
    from ..models import Definition


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

        return (
            source,
            str(template_path),
            lambda: mtime == os.path.getmtime(template_path),
        )


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
        self,
        word: str,
        definitions: list[Definition],
        meaning_cluster: str | None = None,
        optimized: bool = True,
    ) -> str:
        """Generate synthesis prompt for definition aggregation using full Definition objects."""
        template_name = "synthesize/definitions_optimized" if optimized else "synthesize/definitions"
        
        # If using optimized template, prepare definitions with minimal data
        if optimized:
            from .definition_serializer import prepare_definitions_for_synthesis
            definitions = prepare_definitions_for_synthesis(definitions)
            
        return self.render_template(
            template_name,
            word=word,
            definitions=definitions,
            meaning_cluster=meaning_cluster,
        )

    def get_generate_examples_prompt(
        self,
        word: str,
        part_of_speech: str,
        definition: str,
        count: int = 1,
        optimized: bool = True,
    ) -> str:
        """Generate example generation prompt."""
        template_name = "generate/examples_optimized" if optimized else "generate/examples"
        return self.render_template(
            template_name,
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            count=count,
        )

    def get_pronunciation_prompt(self, word: str) -> str:
        """Generate pronunciation prompt."""
        return self.render_template("synthesize/pronunciation", word=word)

    def get_lookup_prompt(self, word: str) -> str:
        """Generate lookup fallback prompt."""
        return self.render_template("misc/lookup", word=word)

    def get_meaning_extraction_prompt(
        self, word: str, definitions: list[tuple[str, str, str]], optimized: bool = True
    ) -> str:
        """Generate meaning extraction prompt with cluster mapping."""
        template_name = "misc/meaning_extraction_optimized" if optimized else "misc/meaning_extraction"
        return self.render_template(
            template_name,
            word=word,
            definitions=definitions,
        )

    def get_meaning_cluster_single_prompt(
        self, word: str, definition: str, part_of_speech: str
    ) -> str:
        """Generate meaning cluster for a single definition."""
        return self.render_template(
            "meaning_cluster_single",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
        )

    def get_synthesize_synonyms_prompt(
        self, word: str, definition: str, part_of_speech: str, existing_synonyms: list[str], count: int = 10, optimized: bool = True
    ) -> str:
        """Generate prompt for synonym synthesis with existing items."""
        template_name = "synthesize/synonyms_optimized" if optimized else "synthesize/synonyms"
        return self.render_template(
            template_name,
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            existing_synonyms=existing_synonyms,
            count=count,
        )

    def get_suggestions_prompt(self, input_words: list[str] | None, count: int = 10) -> str:
        """Generate prompt for word suggestions based on input words."""
        return self.render_template(
            "misc/suggestions",
            input_words=input_words,
            count=count,
        )

    def get_fact_generation_prompt(
        self, word: str, definition: str, count: int = 5, previous_words: list[str] | None = None
    ) -> str:
        """Generate prompt for interesting facts about a word."""
        return self.render_template(
            "generate/facts",
            word=word,
            definition=definition,
            count=count,
            previous_words=previous_words or [],
        )

    def get_synthesize_antonyms_prompt(self, word: str, definition: str, part_of_speech: str, existing_antonyms: list[str], count: int = 5) -> str:
        """Generate prompt for antonym synthesis."""
        return self.render_template(
            "synthesize/antonyms",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            existing_antonyms=existing_antonyms,
            count=count,
        )

    def get_etymology_prompt(self, word: str, provider_data: list[dict[str, Any]]) -> str:
        """Generate prompt for etymology extraction."""
        return self.render_template(
            "synthesize/etymology",
            word=word,
            provider_data=provider_data,
        )

    def get_word_forms_prompt(self, word: str, part_of_speech: str, optimized: bool = True) -> str:
        """Generate prompt for word form generation."""
        template_name = "generate/word_forms_optimized" if optimized else "generate/word_forms"
        return self.render_template(
            template_name,
            word=word,
            part_of_speech=part_of_speech,
        )

    def get_frequency_prompt(self, word: str, definition: str, optimized: bool = True) -> str:
        """Generate prompt for frequency band assessment."""
        template_name = "assess/frequency_optimized" if optimized else "assess/frequency"
        return self.render_template(
            template_name,
            word=word,
            definition=definition,
        )

    def get_register_prompt(self, definition: str) -> str:
        """Generate prompt for register classification."""
        return self.render_template(
            "assess/register",
            definition=definition,
        )

    def get_domain_prompt(self, definition: str) -> str:
        """Generate prompt for domain identification."""
        return self.render_template(
            "assess/domain",
            definition=definition,
        )

    def get_cefr_prompt(self, word: str, definition: str) -> str:
        """Generate prompt for CEFR level assessment."""
        return self.render_template(
            "assess/cefr",
            word=word,
            definition=definition,
        )

    def get_grammar_patterns_prompt(self, definition: str, part_of_speech: str) -> str:
        """Generate prompt for grammar pattern extraction."""
        return self.render_template(
            "assess/grammar_patterns",
            definition=definition,
            part_of_speech=part_of_speech,
        )

    def get_collocations_prompt(self, word: str, definition: str, part_of_speech: str) -> str:
        """Generate prompt for collocation identification."""
        return self.render_template(
            "assess/collocations",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
        )

    def get_usage_notes_prompt(self, word: str, definition: str, optimized: bool = True) -> str:
        """Generate prompt for usage note generation."""
        template_name = "misc/usage_note_generation_optimized" if optimized else "misc/usage_note_generation"
        return self.render_template(
            template_name,
            word=word,
            definition=definition,
        )

    def get_regional_variants_prompt(self, definition: str) -> str:
        """Generate prompt for regional variant detection."""
        return self.render_template(
            "assess/regional_variants",
            definition=definition,
        )

    def get_query_validation_prompt(self, query: str) -> str:
        """Generate prompt for query validation."""
        return self.render_template(
            "misc/query_validation",
            query=query,
        )

    def get_word_suggestion_prompt(self, query: str, count: int = 10) -> str:
        """Generate prompt for word suggestions."""
        return self.render_template(
            "misc/word_suggestion",
            query=query,
            count=count,
        )
