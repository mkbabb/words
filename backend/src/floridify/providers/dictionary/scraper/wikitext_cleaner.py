"""Unified wikitext cleaning using wikitextparser.

Provides the ``WikitextCleaner`` class with 25+ template handlers for converting
raw wikitext markup into clean plain text.
"""

from __future__ import annotations

import html
import re

import wikitextparser as wtp  # type: ignore[import-untyped]


class WikitextCleaner:
    """Unified wikitext cleaning using wikitextparser."""

    @staticmethod
    def clean_text(text: str, preserve_structure: bool = False) -> str:
        """Clean wikitext using wikitextparser and targeted regex."""
        if not text:
            return ""

        try:
            # Parse with wikitextparser for proper handling
            parsed = wtp.parse(text)

            # Handle templates with specialized logic
            for template in parsed.templates:
                template_name = template.name.strip().lower()

                # Handle templates with general approach
                if template_name.startswith("quote-") or template_name in ["quote", "quotation"]:
                    # Quote templates should be completely removed from definitions
                    # They will be handled separately as examples
                    template.string = ""

                elif template_name in ["term", "mention", "lang", "l", "link"]:
                    # Keep the main content, remove the template wrapper
                    if template.arguments:
                        # Usually the last argument is the display text, or second for {{l|lang|word}}
                        if len(template.arguments) >= 2:
                            content = str(template.arguments[1].value).strip()
                        else:
                            content = str(template.arguments[-1].value).strip()
                        template.string = content
                    else:
                        template.string = ""

                elif template_name in ["gloss", "gl"]:
                    # Gloss templates: {{gloss|meaning}} -> "(meaning)"
                    if template.arguments:
                        gloss_text = str(template.arguments[0].value).strip()
                        template.string = f"({gloss_text})"
                    else:
                        template.string = ""

                elif template_name in ["lb", "label", "qualifier", "q"]:
                    # Label/qualifier templates: {{lb|en|informal}} -> "(informal)"
                    labels = []
                    for arg in template.arguments:
                        arg_val = str(arg.value).strip()
                        if arg_val and arg_val not in ["en", "eng"]:  # Skip language codes
                            labels.append(arg_val)
                    if labels:
                        template.string = f"({', '.join(labels)})"
                    else:
                        template.string = ""

                # For other templates, try to extract meaningful content from arguments
                # This handles templates like {{synonym of|en|word}}, {{form of|...}}, etc.
                elif template.arguments:
                    # Skip language codes and template metadata, look for actual content
                    content_args = []
                    for arg in template.arguments:
                        arg_val = str(arg.value).strip()
                        # Skip language codes and common metadata
                        if (
                            arg_val
                            and len(arg_val) > 1
                            and arg_val not in ["en", "eng", "1", "2", "3"]
                            and not arg_val.startswith("http")
                        ):
                            content_args.append(arg_val)

                    if content_args:
                        # Use the first meaningful content argument
                        template.string = content_args[0]
                    else:
                        template.string = ""
                else:
                    template.string = ""

            # Convert wikilinks to plain text
            for wikilink in parsed.wikilinks:
                # Use display text if available, otherwise use target
                display_text = wikilink.text or wikilink.target
                wikilink.string = display_text or ""

            # Get the cleaned text
            cleaned = str(parsed)

        except Exception:
            # Fallback to regex cleaning if wtp fails
            cleaned = text

        # Final cleanup with regex for any remaining templates
        cleaned = re.sub(r"<[^>]+>", "", cleaned)  # Remove HTML tags
        cleaned = re.sub(r"\{\{[^}]*\}\}", "", cleaned)  # Remove remaining templates
        cleaned = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", cleaned)  # Clean links
        cleaned = re.sub(r"<ref[^>]*>.*?</ref>", "", cleaned, flags=re.DOTALL)  # Remove refs

        # Decode HTML entities
        cleaned = html.unescape(cleaned)

        # Remove any remaining wikitext artifacts
        cleaned = re.sub(r"'''(.+?)'''", r"\1", cleaned)  # Bold text
        cleaned = re.sub(r"''(.+?)''", r"\1", cleaned)  # Italic text
        cleaned = re.sub(r"\[\.\.\.\.?\]", "...", cleaned)  # [...] to ...
        cleaned = re.sub(r"&[a-zA-Z]+;", "", cleaned)  # Remove any remaining entities

        # Clean up extra whitespace and punctuation
        cleaned = re.sub(r"\s*\.\s*$", "", cleaned)  # Remove trailing period
        cleaned = re.sub(r"^\s*[.,;:]\s*", "", cleaned)  # Remove leading punctuation

        if not preserve_structure:
            cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace

        return cleaned.strip()
