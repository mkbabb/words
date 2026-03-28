"""Wiktionary wikitext parsing functions.

Free functions for extracting definitions, examples, etymology, pronunciation,
synonyms, antonyms, derived terms, related terms, hypernyms, hyponyms,
collocations, and usage notes from parsed wikitext sections.
"""

from __future__ import annotations

import html
import re
from typing import Literal

import wikitextparser as wtp  # type: ignore[import-untyped]
from beanie import PydanticObjectId

from ....models.dictionary import (
    Definition,
    Example,
    Pronunciation,
)
from ....models.relationships import (
    Collocation,
    UsageNote,
)
from ....storage.dictionary import _resolve_word_text, save_definition_versioned
from ....utils.logging import get_logger
from .wikitext_cleaner import WikitextCleaner

logger = get_logger(__name__)

# Module-level cleaner instance (stateless, safe to share)
_cleaner = WikitextCleaner()

# Word type mappings
POS_MAPPINGS = {
    # Core POS
    "noun": "noun",
    "proper noun": "noun",
    "verb": "verb",
    "participle": "verb",
    "adjective": "adjective",
    "adverb": "adverb",
    "pronoun": "pronoun",
    "preposition": "preposition",
    "conjunction": "conjunction",
    "interjection": "interjection",
    # Mapped POS
    "determiner": "adjective",
    "article": "adjective",
    "numeral": "adjective",
    # Phrase-level POS (common in multi-language entries)
    "prepositional phrase": "preposition",
    "phrase": "noun",
    "proverb": "noun",
    "idiom": "noun",
    # Morphological POS
    "suffix": "noun",
    "prefix": "noun",
    "affix": "noun",
    "contraction": "pronoun",
    # Abbreviation POS
    "initialism": "noun",
    "abbreviation": "noun",
    "acronym": "noun",
}


def find_language_section(parsed: wtp.WikiList, language: str) -> wtp.Section | None:
    """Find the specific language section using wtp.Section hierarchy."""
    for section in parsed.sections:
        if (
            section.title
            and section.title.strip().lower() == language.lower()
            and section.level == 2
        ):  # Language sections are level 2 (==)
            return section
    return None


def find_all_language_sections(parsed: wtp.WikiList) -> list[tuple[str, wtp.Section]]:
    """Discover all language sections in a Wiktionary entry.

    Returns:
        List of (language_name, section) tuples. E.g., [("French", <Section>)]
        for an entry like 'en coulisse' that only has a ==French== section.
    """
    results: list[tuple[str, wtp.Section]] = []
    for section in parsed.sections:
        if section.title and section.level == 2:
            results.append((section.title.strip(), section))
    return results


async def extract_definitions(
    section: wtp.Section,
    word_id: PydanticObjectId,
    section_synonyms: list[str] | None = None,
    section_antonyms: list[str] | None = None,
) -> list[Definition]:
    """Extract definitions using new model structure."""
    definitions = []
    word_text = await _resolve_word_text(word_id)

    for subsection in section.sections:
        if not subsection.title:
            continue

        section_title = subsection.title.strip().lower()

        # Find matching part of speech
        part_of_speech = None
        for pos_name, pos_enum in POS_MAPPINGS.items():
            if pos_name in section_title:
                part_of_speech = pos_enum
                break

        if not part_of_speech:
            continue

        # Use wtp.WikiList to extract numbered definitions
        definition_texts = extract_wikilist_items(str(subsection))

        # Store the full subsection text for example extraction
        subsection_text = str(subsection)

        for idx, def_text in enumerate(definition_texts):
            if not def_text or len(def_text.strip()) < 5:
                continue

            # Extract components from definition
            clean_def = _cleaner.clean_text(def_text)
            if not clean_def:
                continue

            # Extract inline synonyms and merge with section-level synonyms
            synonyms = extract_inline_synonyms(def_text)
            if section_synonyms:
                synonyms = list(set(synonyms) | set(section_synonyms))

            # Extract inline antonyms and merge with section-level antonyms
            antonyms = extract_inline_antonyms(def_text)
            if section_antonyms:
                antonyms = list(set(antonyms) | set(section_antonyms))

            # Extract collocations from the definition context
            collocations = extract_collocations_from_definition(def_text)

            # Extract any inline usage notes
            usage_notes = extract_usage_notes_from_definition(def_text)

            # Create definition (meaning_cluster will be added by AI synthesis)
            definition = Definition(
                word_id=word_id,
                part_of_speech=part_of_speech,
                text=clean_def,
                sense_number=f"{idx + 1}",
                synonyms=synonyms,
                antonyms=antonyms,
                frequency_band=None,
                collocations=collocations,
                usage_notes=usage_notes,
            )

            # Save definition to get ID
            await save_definition_versioned(definition, word_text)
            assert definition.id is not None  # After save(), id is guaranteed to be not None

            # Extract and save examples from both the definition and the full subsection
            # This ensures we capture quotations that appear after the definition
            example_objs = await extract_examples(subsection_text, definition.id)
            definition.example_ids = [ex.id for ex in example_objs if ex.id is not None]
            await save_definition_versioned(definition, word_text)  # Update with example IDs

            definitions.append(definition)

    return definitions


def extract_wikilist_items(section_text: str) -> list[str]:
    """Extract numbered definition items from section text, separating definitions from examples."""
    items = []

    # Strip multi-line quote templates BEFORE line splitting.
    # wtp.parse handles templates that span multiple lines correctly,
    # whereas the line-by-line regex below would miss split templates.
    try:
        parsed = wtp.parse(section_text)
        for template in parsed.templates:
            tname = template.name.strip().lower()
            if tname.startswith("quote-") or tname in ("quote", "quotation"):
                template.string = ""
        section_text = str(parsed)
    except Exception:
        pass  # Fall through to line-by-line parsing (valid recovery path)

    # Split section into lines for more precise processing
    lines = section_text.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for numbered definition lines starting with #
        if re.match(r"^#\s+", line):
            # Extract the definition part (everything after # until we hit a quote template or new definition)
            definition_text = line[1:].strip()  # Remove the # and leading whitespace

            # Check if this line contains quote templates - if so, extract only the part before quotes
            quote_match = re.search(r"\{\{quote-", definition_text)
            if quote_match:
                # Take only the part before the quote template
                definition_text = definition_text[: quote_match.start()].strip()

            # Continue collecting the definition if it spans multiple lines (before hitting quotes)
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()

                # Stop if we hit another definition, quote template, or section header
                if (
                    re.match(r"^#", next_line)
                    or next_line.startswith("{{quote-")
                    or next_line.startswith("==")
                    or next_line.startswith("===")
                ):
                    break

                # Add non-quote content to definition
                if next_line and not next_line.startswith("{{quote-"):
                    # Check if this line contains quote templates
                    quote_match = re.search(r"\{\{quote-", next_line)
                    if quote_match:
                        # Take only the part before the quote template
                        definition_text += " " + next_line[: quote_match.start()].strip()
                        break
                    definition_text += " " + next_line
                i += 1

            # Clean and validate the definition text
            if definition_text and len(definition_text.strip()) > 5:
                items.append(definition_text.strip())

            # Don't increment i again since we already processed multiple lines
            continue

        i += 1

    return items


async def extract_examples(
    definition_text: str,
    definition_id: PydanticObjectId,
) -> list[Example]:
    """Extract and save examples using new model structure."""
    examples = []

    try:
        parsed = wtp.parse(definition_text)

        # Extract from templates
        for template in parsed.templates:
            template_name = template.name.strip().lower()

            if template_name in ["ux", "uxi", "usex"]:
                # Usage example templates
                if len(template.arguments) >= 2:
                    example_text = str(template.arguments[1].value).strip()
                    clean_example = _cleaner.clean_text(
                        example_text,
                        preserve_structure=True,
                    )
                    if clean_example and len(clean_example) > 10:
                        example = Example(
                            definition_id=definition_id,
                            text=clean_example,
                            type="literature",  # Wiktionary examples are from real usage
                        )
                        await example.save()
                        examples.append(example)

            elif template_name.startswith("quote-") or template_name in [
                "quote",
                "quotation",
            ]:
                # Quote templates (e.g., quote-book, quote-journal, etc.)
                # Extract the passage/text parameter
                passage = None
                year = None
                author = None

                for arg in template.arguments:
                    arg_name = str(arg.name).strip().lower() if arg.name else ""
                    arg_value = str(arg.value).strip()

                    if arg_name in ["passage", "text", "quote"]:
                        passage = arg_value
                    elif arg_name == "year":
                        year = arg_value
                    elif arg_name in [
                        "author",
                        "last",
                        "1",
                    ]:  # Add "1" as potential author field
                        if not author:  # Only set if we don't already have an author
                            author = arg_value

                if passage:
                    # Clean up {{...}} placeholders commonly found in quotes
                    passage = re.sub(r"\{\{\.\.\.+\}\}", "...", passage)

                    clean_passage = _cleaner.clean_text(passage, preserve_structure=True)
                    if clean_passage and len(clean_passage) > 10:
                        # Format with metadata if available
                        if year or author:
                            metadata_parts = []
                            if year:
                                metadata_parts.append(year)
                            if author:
                                metadata_parts.append(author)
                            full_text = f"({', '.join(metadata_parts)}) {clean_passage}"
                        else:
                            full_text = clean_passage

                        example = Example(
                            definition_id=definition_id,
                            text=full_text,
                            type="literature",
                        )
                        await example.save()
                        examples.append(example)
    except Exception as e:
        logger.error(f"Error extracting examples: {e}")

    return examples


def extract_inline_synonyms(definition_text: str) -> list[str]:
    """Extract synonyms from inline templates in definitions."""
    synonyms = []

    try:
        parsed = wtp.parse(definition_text)

        for template in parsed.templates:
            template_name = template.name.strip().lower()

            if template_name in ["syn", "synonym", "synonyms", "l", "link"]:
                for arg in template.arguments:
                    if arg.name == "1":
                        continue
                    if arg.name and not arg.name.isdigit():
                        continue
                    arg_value = str(arg.value).strip()
                    if arg_value and len(arg_value) > 1 and arg_value not in ["en", "eng", "lang"]:
                        clean_syn = clean_synonym(arg_value)
                        if clean_syn and is_valid_synonym(clean_syn):
                            synonyms.append(clean_syn)

    except Exception as e:
        logger.debug(f"Error extracting inline synonyms: {e}")

    return synonyms[:10]  # Limit to 10 synonyms


def extract_inline_antonyms(definition_text: str) -> list[str]:
    """Extract antonyms from inline templates in definitions."""
    antonyms = []

    try:
        parsed = wtp.parse(definition_text)

        for template in parsed.templates:
            template_name = template.name.strip().lower()

            if template_name in ["ant", "antonym", "antonyms"]:
                for arg in template.arguments:
                    if arg.name == "1":
                        continue
                    if arg.name and not arg.name.isdigit():
                        continue
                    arg_value = str(arg.value).strip()
                    if arg_value and len(arg_value) > 1 and arg_value not in ["en", "eng", "lang"]:
                        clean_ant = clean_synonym(arg_value)
                        if clean_ant and is_valid_synonym(clean_ant):
                            antonyms.append(clean_ant)

    except Exception as e:
        logger.debug(f"Error extracting inline antonyms: {e}")

    return antonyms[:10]


def _extract_words_from_templates(parsed: wtp.WikiText) -> list[str]:
    """Extract word lists from wtp templates.

    Handles all common Wiktionary word-list template patterns:
    - {{l|en|word}}, {{link|en|word}} — single-word links
    - {{m|en|word}}, {{mention|en|word}} — mentions
    - {{syn|en|w1|w2|w3}}, {{ant|en|w1|w2}} — inline syn/ant lists
    - {{col2|en|w1|w2|...}} through {{col5|...}} — multi-column layouts

    All share the same structure: arg 1 = language code, remaining = words.
    """
    # Template names that contain word lists (arg 1 = lang, rest = words)
    WORD_LIST_TEMPLATES = {
        "l", "link", "m", "mention",
        "syn", "synonym", "synonyms",
        "ant", "antonym", "antonyms",
        "col", "col1", "col2", "col3", "col4", "col5",
        "col-auto", "der2", "der3", "der4", "der5",
        "rel2", "rel3", "rel4", "rel5",
        "hyp2", "hyp3", "hyp4", "hyp5",
    }

    words: list[str] = []
    for template in parsed.templates:
        template_name = template.name.strip().lower()
        if template_name not in WORD_LIST_TEMPLATES:
            continue
        for arg in template.arguments:
            if arg.name == "1":
                continue  # Skip language code
            value = str(arg.value).strip()
            if not value or len(value) < 2:
                continue
            if value in ("en", "eng", "English", "lang"):
                continue
            # Skip named parameters like sort=, title=, etc.
            if arg.name and not arg.name.isdigit():
                continue
            cleaned = clean_synonym(value)
            if cleaned and is_valid_synonym(cleaned):
                words.append(cleaned)
    return words


def _dedupe(items: list[str], limit: int = 20) -> list[str]:
    """Deduplicate while preserving order, with a cap."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result[:limit]


def extract_section_synonyms(section: wtp.Section) -> list[str]:
    """Extract synonyms from dedicated Synonyms and See also sections."""
    all_synonyms: list[str] = []

    for subsection in section.sections:
        if not subsection.title:
            continue
        if not any(kw in subsection.title.lower() for kw in ("synonym", "see also")):
            continue

        parsed = wtp.parse(str(subsection))
        all_synonyms.extend(_extract_words_from_templates(parsed))

        # Also extract from wikilinks in list items
        for item in extract_wikilist_items(str(subsection)):
            clean_item = _cleaner.clean_text(item)
            if clean_item and len(clean_item) > 1:
                if "thesaurus:" in clean_item.lower():
                    continue
                for part in clean_item.split(","):
                    syn = part.strip()
                    if syn and len(syn) > 1 and is_valid_synonym(syn):
                        all_synonyms.append(syn)

    return _dedupe(all_synonyms, 30)


def extract_section_antonyms(section: wtp.Section) -> list[str]:
    """Extract antonyms from dedicated Antonyms sections."""
    all_antonyms: list[str] = []

    for subsection in section.sections:
        if not subsection.title or "antonym" not in subsection.title.lower():
            continue

        parsed = wtp.parse(str(subsection))
        all_antonyms.extend(_extract_words_from_templates(parsed))

        for item in extract_wikilist_items(str(subsection)):
            clean_item = _cleaner.clean_text(item)
            if clean_item and len(clean_item) > 1:
                if "thesaurus:" in clean_item.lower():
                    continue
                for part in clean_item.split(","):
                    ant = part.strip()
                    if ant and len(ant) > 1 and is_valid_synonym(ant):
                        all_antonyms.append(ant)

    return _dedupe(all_antonyms, 30)


def extract_derived_terms(section: wtp.Section) -> list[str]:
    """Extract derived terms from ====Derived terms==== sections."""
    return _extract_term_section(section, ["derived term", "derived forms"])


def extract_related_terms(section: wtp.Section) -> list[str]:
    """Extract related terms from ====Related terms==== sections."""
    return _extract_term_section(section, ["related term"])


def extract_hypernyms(section: wtp.Section) -> list[str]:
    """Extract hypernyms from ====Hypernyms==== sections."""
    return _extract_term_section(section, ["hypernym"])


def extract_hyponyms(section: wtp.Section) -> list[str]:
    """Extract hyponyms from ====Hyponyms==== sections."""
    return _extract_term_section(section, ["hyponym"])


def extract_coordinate_terms(section: wtp.Section) -> list[str]:
    """Extract coordinate terms from ====Coordinate terms==== sections."""
    return _extract_term_section(section, ["coordinate term"])


def extract_alternative_forms(section: wtp.Section) -> list[str]:
    """Extract alternative forms from ===Alternative forms=== sections."""
    return _extract_term_section(section, ["alternative form"])


def _extract_term_section(section: wtp.Section, keywords: list[str]) -> list[str]:
    """Generic extraction for term-list sections (derived, related, hypernyms, etc.)."""
    all_terms: list[str] = []

    for subsection in section.sections:
        if not subsection.title or not any(kw in subsection.title.lower() for kw in keywords):
            continue

        parsed = wtp.parse(str(subsection))
        all_terms.extend(_extract_words_from_templates(parsed))

        # Also extract from bare wikilinks (not inside templates)
        for wikilink in parsed.wikilinks:
            target = (wikilink.text or wikilink.target or "").strip()
            if target and len(target) > 1 and is_valid_synonym(target):
                all_terms.append(target)

    return _dedupe(all_terms, 30)


def extract_section_usage_notes(section: wtp.Section) -> list[UsageNote]:
    """Extract usage notes from dedicated ====Usage notes==== sections.

    Unlike extract_usage_notes_from_definition() which detects inline indicators,
    this extracts prose from dedicated Usage notes subsections.
    """
    notes: list[UsageNote] = []

    for subsection in section.sections:
        if subsection.title and "usage note" in subsection.title.lower():
            # Get the prose content (stop at next subsection)
            text_parts = []
            for line in subsection.contents.split("\n"):
                stripped = line.strip()
                if stripped.startswith("===") or stripped.startswith("===="):
                    break
                if stripped.startswith("*") or stripped.startswith("#"):
                    # List items — extract the text after the marker
                    item_text = re.sub(r"^[*#]+\s*", "", stripped)
                    if item_text:
                        text_parts.append(item_text)
                elif stripped:
                    text_parts.append(stripped)

            for part in text_parts:
                clean_text = _cleaner.clean_text(part)
                if clean_text and len(clean_text) > 10:
                    # Classify the usage note type
                    note_type = _classify_usage_note(clean_text)
                    notes.append(UsageNote(type=note_type, text=clean_text))

    return notes[:5]


def _classify_usage_note(text: str) -> Literal[
    "grammar",
    "confusion",
    "regional",
    "register",
    "error",
]:
    """Classify a usage note into one of the valid types based on content."""
    lower = text.lower()

    # Grammar patterns
    if any(kw in lower for kw in ["plural", "singular", "countable", "uncountable",
                                    "transitive", "intransitive", "conjugat",
                                    "inflect", "participle", "tense"]):
        return "grammar"

    # Confusion patterns
    if any(kw in lower for kw in ["confused with", "not to be confused",
                                    "distinguish", "compare", "versus",
                                    "as opposed to", "different from"]):
        return "confusion"

    # Regional patterns
    if any(kw in lower for kw in ["british", "american", "australian",
                                    "canadian", "irish", "scottish",
                                    "regional", "dialect"]):
        return "regional"

    # Error patterns
    if any(kw in lower for kw in ["incorrect", "error", "wrong", "avoid",
                                    "nonstandard", "proscribed"]):
        return "error"

    # Default to register
    return "register"


def is_valid_synonym(synonym: str) -> bool:
    """Check if a synonym/term is valid (not a meta-reference)."""
    lower_syn = synonym.lower()
    # Filter out meta-references
    invalid_patterns = [
        "thesaurus:",
        "see also",
        "appendix:",
        "category:",
        "wikipedia:",
        "wikisaurus:",
    ]
    return not any(pattern in lower_syn for pattern in invalid_patterns)


def extract_etymology(section: wtp.Section) -> str | None:
    """Extract etymology from dedicated section."""
    for subsection in section.sections:
        if subsection.title and "etymology" in subsection.title.lower():
            # Get only the direct text content, not subsections
            # This avoids including pronunciation, noun definitions, etc.
            text_parts = []
            for content in subsection.contents.split("\n"):
                # Stop at the first subsection marker
                if content.strip().startswith("===") or content.strip().startswith("===="):
                    break
                text_parts.append(content)

            etymology_text = "\n".join(text_parts).strip()
            if etymology_text:
                # Special cleaning for etymology to preserve language links
                return clean_etymology_text(etymology_text)

    return None


def clean_etymology_text(text: str) -> str:
    """Clean etymology wikitext into readable prose.

    Uses a collect-then-replace strategy to avoid mutating the wtp parse tree
    (modifying template.string invalidates sibling Section objects, causing
    "object has died" errors in the caller).
    """
    if not text:
        return ""

    lang_map = {
        "enm": "Middle English", "ang": "Old English", "fro": "Old French",
        "frm": "Middle French", "fr": "French", "la": "Latin",
        "la-lat": "Late Latin", "la-med": "Medieval Latin",
        "grc": "Ancient Greek", "el": "Greek",
        "de": "German", "gmh": "Middle High German", "goh": "Old High German",
        "es": "Spanish", "it": "Italian", "pt": "Portuguese",
        "nl": "Dutch", "dum": "Middle Dutch",
        "non": "Old Norse", "da": "Danish", "sv": "Swedish", "no": "Norwegian",
        "ar": "Arabic", "fa": "Persian", "sa": "Sanskrit", "hi": "Hindi",
        "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
        "ru": "Russian", "pl": "Polish", "cy": "Welsh", "ga": "Irish",
        "sga": "Old Irish", "cel-pro": "Proto-Celtic",
        "gem-pro": "Proto-Germanic", "ine-pro": "Proto-Indo-European",
    }

    # Etymology templates: arg structure is {{name|source_lang|target_lang|word|t=gloss}}
    ETYM_TEMPLATES = {"der", "inh", "bor", "cog", "m", "mention", "l", "lang",
                      "inherited", "derived", "borrowed", "cognate", "noncog",
                      "uder", "ubor", "lbor", "slbor", "psm", "calque", "cal",
                      "semi-calque", "learned borrowing", "orthographic borrowing"}

    # Collect (span, replacement) pairs from wtp, then apply to raw text
    replacements: list[tuple[tuple[int, int], str]] = []

    try:
        parsed = wtp.parse(text)

        for template in parsed.templates:
            tname = template.name.strip().lower()
            span = template.span

            if tname in ETYM_TEMPLATES:
                args = [str(a.value).strip() for a in template.arguments]
                # Find the word and language code
                # Patterns: {{m|la|word}}, {{der|en|la|word}}, {{inh|en|enm|word|t=gloss}}
                word = None
                lang_code = None
                gloss = None
                for a in template.arguments:
                    aname = str(a.name).strip() if a.name else ""
                    aval = str(a.value).strip()
                    if aname in ("t", "gloss", "tr"):
                        gloss = aval
                # Find lang + word from positional args
                positional = [str(a.value).strip() for a in template.arguments
                              if not a.name or a.name.isdigit()]
                if len(positional) >= 3:
                    lang_code = positional[1]
                    word = positional[2]
                elif len(positional) >= 2:
                    lang_code = positional[0]
                    word = positional[1]

                if word:
                    lang_name = lang_map.get(lang_code, "")
                    parts = [lang_name, word] if lang_name else [word]
                    if gloss:
                        parts.append(f'("{gloss}")')
                    replacements.append((span, " ".join(parts)))
                else:
                    replacements.append((span, ""))

            elif tname in ("gloss", "gl"):
                args = [str(a.value).strip() for a in template.arguments]
                gloss = args[0] if args else ""
                replacements.append((span, f'("{gloss}")' if gloss else ""))

            elif tname in ("doublet", "see"):
                args = [str(a.value).strip() for a in template.arguments]
                word = args[-1] if args and len(args[-1]) > 1 else ""
                replacements.append((span, word))

            elif tname in ("suffix", "prefix", "af", "affix", "confix"):
                # {{suffix|en|perspicac|ious}} → "perspicac- + -ious"
                parts = [str(a.value).strip() for a in template.arguments
                         if not a.name or a.name.isdigit()]
                parts = [p for p in parts if p and p not in ("en", "eng") and len(p) > 0]
                replacements.append((span, " + ".join(parts) if parts else ""))

            elif tname in ("w", "wikipedia", "wp", "pedialite", "root",
                          "senseid", "anchor", "rfe", "etystub"):
                replacements.append((span, ""))

            elif tname == "circa" or tname == "c." or tname == "circa2":
                args = [str(a.value).strip() for a in template.arguments]
                replacements.append((span, f"c. {args[0]}" if args else ""))

            elif tname in ("quote", "quote-book", "quote-journal", "quote-web"):
                replacements.append((span, ""))

            else:
                # Unknown template — remove
                replacements.append((span, ""))

        # Apply replacements in reverse order to preserve spans
        cleaned = text
        for (start, end), replacement in sorted(replacements, key=lambda r: r[0][0], reverse=True):
            cleaned = cleaned[:start] + replacement + cleaned[end:]

        # Convert wikilinks: [[target|display]] → display, [[word]] → word
        cleaned = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", cleaned)

    except Exception as e:
        logger.debug(f"Etymology parsing error: {e}")
        cleaned = text
        # Regex fallback for etymology templates
        def _etym_template_replace(m: re.Match[str]) -> str:
            inner = m.group(1)
            parts = inner.split("|")
            tname = parts[0].strip().lower()
            if tname in ETYM_TEMPLATES and len(parts) >= 4:
                lang_code = parts[2].strip()
                word = parts[3].strip()
                lang_name = lang_map.get(lang_code, "")
                return f"{lang_name} {word}" if lang_name else word
            return ""
        cleaned = re.sub(r"\{\{([^}]+)\}\}", _etym_template_replace, cleaned)
        cleaned = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", cleaned)

    # Final cleanup
    cleaned = re.sub(r"\[\[(Image|File):[^\]]*\]\]", "", cleaned)  # Remove image/file links
    cleaned = re.sub(r"<ref[^>]*>.*?</ref>", "", cleaned, flags=re.DOTALL)  # Remove references
    cleaned = re.sub(r"<ref[^/]*/?>", "", cleaned)  # Self-closing refs
    cleaned = re.sub(r"<[^>]+>", "", cleaned)  # Any remaining HTML tags
    cleaned = re.sub(r"'''+", "", cleaned)  # Bold/italic markers
    cleaned = re.sub(r"''+", "", cleaned)
    # Strip any remaining templates/wikilinks that survived parsing
    for _ in range(3):
        cleaned = re.sub(r"\{\{[^{}]*\}\}", "", cleaned)
    cleaned = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", cleaned)
    cleaned = re.sub(r"[{}|\[\]]", "", cleaned)  # Stray brackets
    cleaned = html.unescape(cleaned)

    # Clean up punctuation and whitespace
    cleaned = re.sub(r"\s*([,;])\s*([,;])", r"\1", cleaned)  # Multiple punctuation
    cleaned = re.sub(r"\s+([,;.!?])", r"\1", cleaned)  # Space before punctuation
    cleaned = re.sub(r"([,;])\s*$", ".", cleaned)  # Change trailing comma/semicolon to period
    cleaned = re.sub(r"^\s*[,;.]\s*", "", cleaned)  # Remove leading punctuation
    cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace
    cleaned = re.sub(r"\.\s*\.", ".", cleaned)  # Multiple periods

    # Ensure it ends with a period if it doesn't have ending punctuation
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."

    cleaned = cleaned.strip()

    return cleaned


def extract_pronunciation(
    section: wtp.Section,
    word_id: PydanticObjectId,
) -> Pronunciation | None:
    """Extract pronunciation comprehensively."""
    ipa_american = None
    ipa_british = None
    phonetic = None

    try:
        # Look for pronunciation section
        for subsection in section.sections:
            if subsection.title and "pronunciation" in subsection.title.lower():
                section_text = str(subsection)
                break
        else:
            section_text = str(section)

        parsed = wtp.parse(section_text)

        # Extract from IPA templates
        for template in parsed.templates:
            template_name = template.name.strip().lower()

            if "ipa" in template_name:
                # Extract IPA values and dialect information
                ipa_value = None
                dialect = None

                for i, arg in enumerate(template.arguments):
                    arg_value = str(arg.value).strip()

                    # First argument is usually the language code
                    if i == 0 and arg_value in ["en", "eng", "english"]:
                        continue

                    # Check if this is a dialect indicator
                    if arg_value.lower() in [
                        "us",
                        "usa",
                        "american",
                        "ame",
                        "gen-am",
                        "genam",
                    ]:
                        dialect = "american"
                    elif arg_value.lower() in ["uk", "british", "rp", "gb", "bre"]:
                        dialect = "british"
                    elif "/" in arg_value or "[" in arg_value:
                        # This is likely an IPA transcription
                        ipa_value = arg_value

                # Assign based on dialect or use as American by default
                if ipa_value:
                    if dialect == "british":
                        ipa_british = ipa_value
                    else:
                        ipa_american = ipa_value

            elif template_name == "audio":
                # Skip audio templates entirely
                continue

            elif template_name in ["pron", "pronunciation", "enpr"]:
                # Extract traditional pronunciation guides
                for arg in template.arguments:
                    arg_value = str(arg.value).strip()
                    # Filter out file extensions and language codes
                    if (
                        arg_value
                        and len(arg_value) > 2
                        and not any(
                            marker in arg_value.lower()
                            for marker in [
                                ".ogg",
                                ".mp3",
                                ".wav",
                                "audio",
                                "file:",
                                "en",
                                "us",
                                "uk",
                            ]
                        )
                        and "/" not in arg_value
                        and "|" not in arg_value
                    ):  # Avoid template syntax
                        # This might be a phonetic pronunciation
                        if not phonetic and not arg_value.startswith("{{"):
                            phonetic = arg_value
                            break

        # Generate phonetic from IPA if we don't have one
        if not phonetic and ipa_american:
            phonetic = ipa_to_phonetic(ipa_american)
        elif not phonetic and ipa_british:
            phonetic = ipa_to_phonetic(ipa_british)

        # Return pronunciation if we have any data
        if ipa_american or ipa_british or phonetic:
            # IPA ordering: American preferred, then British, then raw phonetic
            primary_ipa = ipa_american or ipa_british or phonetic or "unknown"
            return Pronunciation(
                word_id=word_id,
                phonetic=phonetic if phonetic else "unknown",
                ipa=primary_ipa,
                syllables=[],
                stress_pattern=None,
            )

    except Exception as e:
        logger.debug(f"Error extracting pronunciation: {e}")

    return None


def extract_collocations_from_definition(definition_text: str) -> list[Collocation]:
    """Extract collocations from definition text."""
    collocations = []

    try:
        # Look for common collocation patterns in parentheses or after "with", "of", etc.
        patterns = [
            r"\((?:with|of|to|for|in|on|at|by)\s+([^)]+)\)",  # (with something)
            r"(?:used|often|typically|usually)\s+(?:with|of|to|for)\s+([^,.;]+)",
            r"(?:followed\s+by|preceded\s+by)\s+([^,.;]+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, definition_text, re.IGNORECASE)
            for match in matches:
                clean_match = _cleaner.clean_text(match)
                if clean_match and len(clean_match) > 2:
                    collocation = Collocation(
                        text=clean_match,
                        type="contextual",
                        frequency=0.5,  # Default medium frequency
                    )
                    collocations.append(collocation)

    except Exception as e:
        logger.debug(f"Error extracting collocations: {e}")

    return collocations[:5]  # Limit to 5 collocations


def extract_usage_notes_from_definition(definition_text: str) -> list[UsageNote]:
    """Extract usage notes from definition text."""
    notes = []

    try:
        # Look for usage indicators in the definition
        indicators = {
            "informal": ["informal", "colloquial", "slang"],
            "formal": ["formal", "literary", "written"],
            "regional": ["british", "american", "australian", "chiefly"],
            "archaic": ["archaic", "obsolete", "dated", "historical"],
            "technical": ["technical", "specialized", "scientific"],
        }

        lower_text = definition_text.lower()

        for note_type, keywords in indicators.items():
            for keyword in keywords:
                if keyword in lower_text:
                    # Extract context around the keyword
                    pattern = rf"[^.]*{keyword}[^.]*"
                    matches = re.findall(pattern, lower_text)
                    if matches:
                        note_text = _cleaner.clean_text(matches[0])
                        if note_text:
                            # Map to valid UsageNote types
                            # Valid types: "grammar", "confusion", "regional", "register", "error"
                            usage_type: Literal[
                                "grammar",
                                "confusion",
                                "regional",
                                "register",
                                "error",
                            ]

                            if note_type in [
                                "informal",
                                "formal",
                                "archaic",
                                "technical",
                            ]:
                                usage_type = "register"
                            elif note_type == "regional":
                                usage_type = "regional"
                            else:
                                usage_type = "register"  # Safe default

                            usage_note = UsageNote(type=usage_type, text=note_text)
                            notes.append(usage_note)
                            break  # Only one note per type

    except Exception as e:
        logger.debug(f"Error extracting usage notes: {e}")

    return notes[:3]  # Limit to 3 notes


def ipa_to_phonetic(ipa: str) -> str:
    """Convert IPA to simplified phonetic representation."""
    if not ipa:
        return "unknown"

    phonetic = ipa.replace("/", "").replace("[", "").replace("]", "")
    phonetic = phonetic.replace("ˈ", "").replace("ˌ", "")  # Remove stress

    # Enhanced IPA to phonetic mapping
    substitutions = {
        "ɪ": "i",
        "ɛ": "e",
        "æ": "a",
        "ɑ": "ah",
        "ɔ": "aw",
        "ʊ": "u",
        "ə": "uh",
        "θ": "th",
        "ð": "th",
        "ʃ": "sh",
        "ʒ": "zh",
        "ŋ": "ng",
        "ʧ": "ch",
        "ʤ": "j",
        "ɹ": "r",
        "ɾ": "t",
        "ʔ": "",
        "ː": "",
        "ˑ": "",
        "eɪ": "ay",
        "aɪ": "eye",
        "ɔɪ": "oy",
        "aʊ": "ow",
        "oʊ": "oh",
    }

    for ipa_char, simple_char in substitutions.items():
        phonetic = phonetic.replace(ipa_char, simple_char)

    return phonetic.strip() or "unknown"


def clean_synonym(synonym_text: str) -> str | None:
    """Clean and validate synonym text."""
    if not synonym_text:
        return None

    cleaned = _cleaner.clean_text(synonym_text)

    # Validation
    if (
        len(cleaned) < 2
        or len(cleaned) > 50
        or cleaned.lower() in {"thesaurus", "see", "also", "compare", "etc", "and", "or"}
    ):
        return None

    return cleaned
