"""Tests for the prompt template system."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.floridify.prompts import PromptLoader, PromptTemplate
from src.floridify.prompts.formatters import format_provider_context, format_template_variables
from src.floridify.prompts.templates import parse_prompt_markdown
from src.floridify.models import Definition, Examples, GeneratedExample, ProviderData, WordType


class TestPromptTemplate:
    """Test cases for PromptTemplate."""

    def test_prompt_template_creation(self) -> None:
        """Test creating a prompt template."""
        template = PromptTemplate(
            name="test",
            system_message="You are a test assistant.",
            user_template="Define {{word}} please.",
            instructions="Be helpful.",
            output_format="Text format.",
            variables={"word": "The word to define"},
            notes={"temperature": 0.5},
        )
        
        assert template.name == "test"
        assert template.system_message == "You are a test assistant."
        assert "{{word}}" in template.user_template

    def test_template_rendering(self) -> None:
        """Test rendering a template with variables."""
        template = PromptTemplate(
            name="test",
            system_message="You are a test assistant.",
            user_template="Define {{word}} as a {{word_type}}.",
            instructions="",
            output_format="",
            variables={},
            notes={},
        )
        
        system_msg, user_msg = template.render({
            "word": "serendipity",
            "word_type": "noun"
        })
        
        assert system_msg == "You are a test assistant."
        assert user_msg == "Define serendipity as a noun."

    def test_ai_settings_extraction(self) -> None:
        """Test extracting AI settings from notes."""
        template = PromptTemplate(
            name="test",
            system_message="",
            user_template="",
            instructions="",
            output_format="",
            variables={},
            notes={
                "temperature": 0.7,
                "model": "gpt-4",
                "max_tokens": 500,
                "other_setting": "ignored"
            },
        )
        
        settings = template.get_ai_settings()
        
        assert settings["temperature"] == 0.7
        assert settings["model"] == "gpt-4"
        assert settings["max_tokens"] == 500
        assert "other_setting" not in settings


class TestPromptMarkdownParser:
    """Test cases for markdown parsing."""

    def test_parse_basic_template(self) -> None:
        """Test parsing a basic markdown template."""
        markdown_content = """# Test Template

## System Message
You are a helpful assistant.

## User Prompt Template
Please define {{word}} for me.

## Instructions
1. Be clear
2. Be concise

## Output Format
Provide a simple definition.

## Variables
- `{{word}}` - The word to define

## Notes
- Temperature: 0.5
- Model: gpt-4
"""
        
        template = parse_prompt_markdown(markdown_content, "test")
        
        assert template.name == "test"
        assert template.system_message == "You are a helpful assistant."
        assert template.user_template == "Please define {{word}} for me."
        assert "Be clear" in template.instructions
        assert "simple definition" in template.output_format
        assert "word" in template.variables
        assert template.notes["temperature"] == 0.5
        assert template.notes["model"] == "gpt-4"

    def test_parse_empty_sections(self) -> None:
        """Test parsing with some empty sections."""
        markdown_content = """# Minimal Template

## System Message
System message here.

## User Prompt Template
{{prompt}}

## Variables
- `{{prompt}}` - The prompt text
"""
        
        template = parse_prompt_markdown(markdown_content, "minimal")
        
        assert template.name == "minimal"
        assert template.system_message == "System message here."
        assert template.instructions == ""
        assert template.output_format == ""
        assert len(template.variables) == 1


class TestPromptLoader:
    """Test cases for PromptLoader."""

    def test_prompt_loader_initialization(self) -> None:
        """Test prompt loader initialization."""
        # Test with default path
        loader = PromptLoader()
        assert loader.templates_dir.exists()
        
        # Test with custom path
        custom_path = Path(__file__).parent.parent / "src" / "floridify" / "prompts" / "templates"
        loader = PromptLoader(custom_path)
        assert loader.templates_dir == custom_path

    def test_load_synthesis_template(self) -> None:
        """Test loading the synthesis template."""
        loader = PromptLoader()
        
        template = loader.load_template("synthesis")
        
        assert template.name == "synthesis"
        assert "lexicographer" in template.system_message.lower()
        assert "{{word}}" in template.user_template
        assert "{{context}}" in template.user_template
        assert template.get_ai_settings().get("temperature") == 0.3

    def test_load_examples_template(self) -> None:
        """Test loading the examples template."""
        loader = PromptLoader()
        
        template = loader.load_template("examples")
        
        assert template.name == "examples"
        assert "creative" in template.system_message.lower()
        assert "{{word}}" in template.user_template
        assert "{{word_type}}" in template.user_template
        assert "{{definition}}" in template.user_template
        assert template.get_ai_settings().get("temperature") == 0.7

    def test_list_templates(self) -> None:
        """Test listing available templates."""
        loader = PromptLoader()
        
        templates = loader.list_templates()
        
        assert "synthesis" in templates
        assert "examples" in templates
        assert isinstance(templates, list)
        assert all(isinstance(name, str) for name in templates)

    def test_template_caching(self) -> None:
        """Test that templates are cached."""
        loader = PromptLoader()
        
        # Load template twice
        template1 = loader.load_template("synthesis")
        template2 = loader.load_template("synthesis")
        
        # Should be the same object (cached)
        assert template1 is template2
        
        # Clear cache and reload
        loader.clear_cache()
        template3 = loader.load_template("synthesis")
        
        # Should be different object after cache clear
        assert template1 is not template3
        assert template1.name == template3.name  # But same content

    def test_get_template_info(self) -> None:
        """Test getting template information."""
        loader = PromptLoader()
        
        info = loader.get_template_info("synthesis")
        
        assert info["name"] == "synthesis"
        assert "variables" in info
        assert "word" in info["variables"]
        assert "context" in info["variables"]
        assert "ai_settings" in info
        assert info["ai_settings"]["temperature"] == 0.3


class TestFormatters:
    """Test cases for template formatters."""

    def test_format_template_variables(self) -> None:
        """Test formatting template variables."""
        variables = format_template_variables(
            word="test",
            count=5,
            items=["a", "b", "c"],
            none_value=None,
            dict_value={"key": "value"}
        )
        
        assert variables["word"] == "test"
        assert variables["count"] == "5"
        assert variables["items"] == "['a', 'b', 'c']"
        assert variables["none_value"] == ""
        assert "key" in variables["dict_value"]

    def test_format_provider_context(self) -> None:
        """Test formatting provider context."""
        # Create sample provider data
        wiktionary_data = ProviderData(
            provider_name="wiktionary",
            definitions=[
                Definition(
                    word_type=WordType.NOUN,
                    definition="A large body of water",
                    examples=Examples(
                        generated=[
                            GeneratedExample(sentence="The lake was beautiful."),
                            GeneratedExample(sentence="We swam in the lake."),
                        ]
                    ),
                )
            ],
        )
        
        oxford_data = ProviderData(
            provider_name="oxford",
            definitions=[
                Definition(
                    word_type=WordType.NOUN,
                    definition="An expanse of water surrounded by land",
                    examples=Examples(),
                )
            ],
        )
        
        provider_data = {
            "wiktionary": wiktionary_data,
            "oxford": oxford_data,
        }
        
        context = format_provider_context("lake", provider_data)
        
        assert "Word: lake" in context
        assert "WIKTIONARY DEFINITIONS:" in context
        assert "OXFORD DEFINITIONS:" in context
        assert "large body of water" in context
        assert "expanse of water" in context
        assert "The lake was beautiful." in context
        assert "We swam in the lake." in context