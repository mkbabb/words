"""Tests for extended Wiktionary parser: antonyms, derived terms, usage notes, etc."""

from __future__ import annotations

import pytest
import wikitextparser as wtp

from floridify.providers.dictionary.scraper.wiktionary_parser import (
    extract_derived_terms,
    extract_hypernyms,
    extract_hyponyms,
    extract_inline_antonyms,
    extract_related_terms,
    extract_section_antonyms,
    extract_section_usage_notes,
)

# ── Sample wikitext sections ──────────────────────────────────────────

SAMPLE_WITH_ANTONYMS = """
==English==
===Noun===
# A positive quality.

====Antonyms====
* {{l|en|weakness}}
* {{l|en|flaw}}
* {{l|en|deficiency}}
"""

SAMPLE_WITH_INLINE_ANTONYMS = """
{{ant|en|weakness|flaw}} A positive quality or attribute.
"""

SAMPLE_WITH_DERIVED_TERMS = """
==English==
===Noun===
# A rounded fruit.

====Derived terms====
* {{l|en|applesauce}}
* {{l|en|apple pie}}
* [[apple tree]]
"""

SAMPLE_WITH_RELATED_TERMS = """
==English==
===Noun===
# A large body of water.

====Related terms====
* {{l|en|oceanic}}
* {{l|en|maritime}}
"""

SAMPLE_WITH_USAGE_NOTES = """
==English==
===Noun===
# The fruit of the apple tree.

====Usage notes====
* In British English, "apple" is sometimes used informally to refer to any round fruit.
* The plural "apples" is countable; the uncountable form is rare.
"""

SAMPLE_WITH_HYPERNYMS = """
==English==
===Noun===
# A rounded fruit.

====Hypernyms====
* {{l|en|fruit}}
* {{l|en|food}}
"""

SAMPLE_WITH_HYPONYMS = """
==English==
===Noun===
# A fruit tree of the genus Malus.

====Hyponyms====
* {{l|en|crabapple}}
* {{l|en|cooking apple}}
"""


# ── Helpers ───────────────────────────────────────────────────────────


def _english_section(wikitext: str) -> wtp.Section:
    parsed = wtp.parse(wikitext)
    for section in parsed.sections:
        if section.title and section.title.strip() == "English":
            return section
    pytest.fail("No English section found in sample wikitext")


# ── Tests: Antonyms ──────────────────────────────────────────────────


class TestSectionAntonyms:
    def test_extracts_antonyms_from_section(self) -> None:
        section = _english_section(SAMPLE_WITH_ANTONYMS)
        antonyms = extract_section_antonyms(section)
        assert len(antonyms) >= 2
        assert "weakness" in antonyms
        assert "flaw" in antonyms

    def test_returns_empty_when_no_antonyms_section(self) -> None:
        section = _english_section(SAMPLE_WITH_DERIVED_TERMS)
        antonyms = extract_section_antonyms(section)
        assert antonyms == []

    def test_deduplicates_antonyms(self) -> None:
        wikitext = """
==English==
===Noun===
# Good.

====Antonyms====
* {{l|en|bad}}
* {{l|en|Bad}}
* {{l|en|evil}}
"""
        section = _english_section(wikitext)
        antonyms = extract_section_antonyms(section)
        lower_antonyms = [a.lower() for a in antonyms]
        assert lower_antonyms.count("bad") == 1


class TestInlineAntonyms:
    def test_extracts_from_ant_template(self) -> None:
        antonyms = extract_inline_antonyms(SAMPLE_WITH_INLINE_ANTONYMS)
        assert "weakness" in antonyms
        assert "flaw" in antonyms

    def test_returns_empty_for_no_templates(self) -> None:
        antonyms = extract_inline_antonyms("A simple definition with no templates.")
        assert antonyms == []


# ── Tests: Derived / Related Terms ───────────────────────────────────


class TestDerivedTerms:
    def test_extracts_from_link_templates(self) -> None:
        section = _english_section(SAMPLE_WITH_DERIVED_TERMS)
        terms = extract_derived_terms(section)
        assert "applesauce" in terms
        assert "apple pie" in terms

    def test_extracts_from_wikilinks(self) -> None:
        section = _english_section(SAMPLE_WITH_DERIVED_TERMS)
        terms = extract_derived_terms(section)
        assert "apple tree" in terms

    def test_returns_empty_when_no_section(self) -> None:
        section = _english_section(SAMPLE_WITH_ANTONYMS)
        terms = extract_derived_terms(section)
        assert terms == []


class TestRelatedTerms:
    def test_extracts_related_terms(self) -> None:
        section = _english_section(SAMPLE_WITH_RELATED_TERMS)
        terms = extract_related_terms(section)
        assert "oceanic" in terms
        assert "maritime" in terms


# ── Tests: Usage Notes ───────────────────────────────────────────────


class TestSectionUsageNotes:
    def test_extracts_usage_notes(self) -> None:
        section = _english_section(SAMPLE_WITH_USAGE_NOTES)
        notes = extract_section_usage_notes(section)
        assert len(notes) >= 1
        # Should classify the countable/uncountable note as grammar
        texts = [n.text for n in notes]
        assert any("countable" in t.lower() for t in texts)

    def test_classifies_grammar_note(self) -> None:
        section = _english_section(SAMPLE_WITH_USAGE_NOTES)
        notes = extract_section_usage_notes(section)
        grammar_notes = [n for n in notes if n.type == "grammar"]
        assert len(grammar_notes) >= 1

    def test_returns_empty_when_no_section(self) -> None:
        section = _english_section(SAMPLE_WITH_ANTONYMS)
        notes = extract_section_usage_notes(section)
        assert notes == []


# ── Tests: Hypernyms / Hyponyms ──────────────────────────────────────


class TestHypernyms:
    def test_extracts_hypernyms(self) -> None:
        section = _english_section(SAMPLE_WITH_HYPERNYMS)
        terms = extract_hypernyms(section)
        assert "fruit" in terms
        assert "food" in terms


class TestHyponyms:
    def test_extracts_hyponyms(self) -> None:
        section = _english_section(SAMPLE_WITH_HYPONYMS)
        terms = extract_hyponyms(section)
        assert "crabapple" in terms
        assert "cooking apple" in terms
