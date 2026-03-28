"""Tests for the Wiktionary wholesale parser.

Tests the complete extraction pipeline using real Wiktionary wikitext samples.
Each test word is chosen to exercise specific parser capabilities.
"""

import pytest
import wikitextparser as wtp

from floridify.providers.dictionary.scraper.wikitext_cleaner import WikitextCleaner
from floridify.providers.dictionary.scraper.wiktionary_parser import (
    POS_MAPPINGS,
    _extract_words_from_templates,
    extract_alternative_forms,
    extract_coordinate_terms,
    extract_derived_terms,
    extract_etymology,
    extract_hypernyms,
    extract_hyponyms,
    extract_inline_antonyms,
    extract_inline_synonyms,
    extract_pronunciation,
    extract_related_terms,
    extract_section_antonyms,
    extract_section_synonyms,
    extract_wikilist_items,
    find_language_section,
    is_valid_synonym,
)
from floridify.providers.dictionary.wholesale import (
    WiktionaryWholesaleConnector,
)

# ── Fixtures: real Wiktionary wikitext samples ────────────────────────


ABANDON_WIKITEXT = """==English==
===Pronunciation===
* {{IPA|en|/əˈbæn.dən/}}

===Etymology 1===
From {{inh|en|enm|abandounen}}, from {{der|en|fro|abandoner}}.

====Verb====
{{en-verb}}

# {{lb|en|transitive}} To give up or [[relinquish]] control of, to [[surrender]] or to give oneself over.
#: {{syn|en|give up|desert|forsake|relinquish}}
#: {{ant|en|keep|maintain|retain}}
# {{lb|en|transitive}} To desist in doing, practicing, following, holding, or adhering to.
#* {{quote-book|en|year=1859|title=The Works|passage=He '''abandoned''' the project.}}

=====Synonyms=====
{{col4|en
|abdicate
|abjure
|cast aside
|cease
|cede
|desert
|forsake
|give up
|relinquish
|renounce
}}

=====Antonyms=====
{{col3|en
|acquire
|adopt
|claim
|keep
|retain
}}

=====Derived terms=====
{{col3|en
|reabandon
|unabandon
|self-abandon
}}

===Etymology 2===
====Noun====
{{en-noun|~}}

# A yielding to natural impulses or inhibitions; freedom from artificial constraint.
#: {{syn|en|wantonness|unrestraint|abandonment}}
"""

INSPISSATE_WIKITEXT = """==English==
{{wp}}

===Etymology===
Formed from {{bor|en|la-lat|inspissātus|t=thickened}}, from {{m|la|inspissō|inspissāre|t=to thicken}}.

===Pronunciation===
* {{IPA|en|/ɪnˈspɪ.seɪt/}}

===Verb===
{{en-verb}}

# {{lb|en|transitive}} To [[thicken]] a fluid, especially by [[boiling]] or [[evaporation]]; to [[condense]].
# {{lb|en|intransitive}} Of a fluid: to become more [[viscous]].

====Synonyms====
* {{sense|to thicken}} {{l|en|reduce}}; see also [[Thesaurus:thicken]]

====Related terms====
* {{l|en|inspissation}}
* {{l|en|inspissator}}
* {{l|en|inspissant}}
"""

DOG_WIKITEXT = """==English==
===Etymology 1===
From {{inh|en|enm|dogge}}.

====Noun====
{{en-noun}}

# A mammal of the family [[Canidae]].
# {{lb|en|slang}} A man regarded as unpleasant.

=====Synonyms=====
{{col4|en
|domestic dog
|hound
|canine
|dogflesh
}}

=====Hypernyms=====
* {{l|en|canid}}
* {{l|en|quadruped}}

=====Hyponyms=====
{{col5|en
|Afghan hound
|beagle
|bloodhound
|borzoi
|boxer
}}

=====Coordinate terms=====
* {{l|en|cat}}
* {{l|en|fox}}
* {{l|en|wolf}}
"""

HAPPY_WIKITEXT = """==English==
===Etymology===
From {{inh|en|enm|happy}}, perhaps an alteration of {{inh|en|enm|happie}}.

===Adjective===
{{en-adj|happier}}

# Having a feeling arising from a consciousness of well-being.
#: {{syn|en|cheerful|content|delighted|glad|joyful|merry|Thesaurus:happy}}
#: {{ant|en|sad|unhappy|miserable|depressed}}
# Experiencing the effect of favourable fortune.
#: {{syn|en|fortunate|lucky|Thesaurus:lucky}}

====Usage notes====
* ''Happy'' is generally used with positive contexts.
* Compare {{m|en|glad}}, which is more formal.

====Derived terms====
{{col4|en
|happily
|happiness
|unhappy
|happy-go-lucky
}}
"""


SIMPLE_WIKITEXT = """==English==
===Noun===
{{en-noun}}

# A simple test word.
# Another definition.
"""


# ── Template extraction tests ─────────────────────────────────────────


class TestExtractWordsFromTemplates:
    """Test the shared _extract_words_from_templates helper."""

    def test_syn_template_multi_arg(self):
        parsed = wtp.parse("{{syn|en|give up|desert|forsake|relinquish}}")
        words = _extract_words_from_templates(parsed)
        assert "give up" in words
        assert "desert" in words
        assert "forsake" in words
        assert "relinquish" in words
        assert len(words) == 4

    def test_ant_template(self):
        parsed = wtp.parse("{{ant|en|keep|maintain|retain}}")
        words = _extract_words_from_templates(parsed)
        assert set(words) == {"keep", "maintain", "retain"}

    def test_col4_template(self):
        parsed = wtp.parse("{{col4|en|abdicate|abjure|cast aside|cease|cede}}")
        words = _extract_words_from_templates(parsed)
        assert "abdicate" in words
        assert "abjure" in words
        assert len(words) == 5

    def test_col3_template(self):
        parsed = wtp.parse("{{col3|en|word1|word2|word3}}")
        words = _extract_words_from_templates(parsed)
        assert len(words) == 3

    def test_der3_template(self):
        parsed = wtp.parse("{{der3|en|derived1|derived2|derived3}}")
        words = _extract_words_from_templates(parsed)
        assert len(words) == 3

    def test_l_link_template(self):
        parsed = wtp.parse("{{l|en|reduce}}")
        words = _extract_words_from_templates(parsed)
        assert words == ["reduce"]

    def test_skips_language_code(self):
        parsed = wtp.parse("{{syn|en|word1|word2}}")
        words = _extract_words_from_templates(parsed)
        assert "en" not in words

    def test_skips_named_params(self):
        parsed = wtp.parse("{{col4|en|word1|word2|sort=alpha|title=Synonyms}}")
        words = _extract_words_from_templates(parsed)
        assert "alpha" not in words
        assert "Synonyms" not in words
        assert "word1" in words

    def test_filters_thesaurus_refs(self):
        parsed = wtp.parse("{{syn|en|cheerful|Thesaurus:happy}}")
        words = _extract_words_from_templates(parsed)
        assert "cheerful" in words
        assert not any("thesaurus" in w.lower() for w in words)

    def test_empty_template(self):
        parsed = wtp.parse("{{syn|en}}")
        words = _extract_words_from_templates(parsed)
        assert words == []


# ── Section extraction tests ──────────────────────────────────────────


class TestSectionSynonyms:
    """Test extract_section_synonyms with real section structures."""

    def test_col4_synonym_section(self):
        """Synonyms in {{col4}} template — the format that was broken before."""
        parsed = wtp.parse(ABANDON_WIKITEXT)
        lang = find_language_section(parsed, "English")
        syns = extract_section_synonyms(lang)
        assert "abdicate" in syns
        assert "abjure" in syns
        assert "relinquish" in syns
        assert len(syns) >= 8

    def test_link_template_synonyms(self):
        """Synonyms as {{l|en|word}} list items."""
        parsed = wtp.parse(INSPISSATE_WIKITEXT)
        lang = find_language_section(parsed, "English")
        syns = extract_section_synonyms(lang)
        assert "reduce" in syns

    def test_section_antonyms(self):
        parsed = wtp.parse(ABANDON_WIKITEXT)
        lang = find_language_section(parsed, "English")
        ants = extract_section_antonyms(lang)
        assert "acquire" in ants
        assert "keep" in ants
        assert len(ants) >= 3


class TestInlineSynonyms:
    """Test inline {{syn}}/{{ant}} extraction from definition context."""

    def test_inline_syn_template(self):
        text = "{{syn|en|cheerful|content|delighted|glad|joyful|merry}}"
        syns = extract_inline_synonyms(text)
        assert "cheerful" in syns
        assert "merry" in syns
        assert len(syns) >= 5

    def test_inline_ant_template(self):
        text = "{{ant|en|sad|unhappy|miserable|depressed}}"
        ants = extract_inline_antonyms(text)
        assert "sad" in ants
        assert "depressed" in ants
        assert len(ants) == 4

    def test_filters_thesaurus(self):
        text = "{{syn|en|cheerful|Thesaurus:happy}}"
        syns = extract_inline_synonyms(text)
        assert not any("thesaurus" in s.lower() for s in syns)

    def test_filters_language_codes(self):
        text = "{{syn|en|word1|word2}}"
        syns = extract_inline_synonyms(text)
        assert "en" not in syns


class TestTermSections:
    """Test derived/related/hypernym/hyponym extraction."""

    def test_derived_terms_col3(self):
        parsed = wtp.parse(ABANDON_WIKITEXT)
        lang = find_language_section(parsed, "English")
        derived = extract_derived_terms(lang)
        assert "reabandon" in derived
        assert "self-abandon" in derived

    def test_related_terms(self):
        parsed = wtp.parse(INSPISSATE_WIKITEXT)
        lang = find_language_section(parsed, "English")
        related = extract_related_terms(lang)
        assert "inspissation" in related
        assert "inspissator" in related

    def test_hypernyms(self):
        parsed = wtp.parse(DOG_WIKITEXT)
        lang = find_language_section(parsed, "English")
        hyper = extract_hypernyms(lang)
        assert "canid" in hyper
        assert "quadruped" in hyper

    def test_hyponyms_col5(self):
        parsed = wtp.parse(DOG_WIKITEXT)
        lang = find_language_section(parsed, "English")
        hypo = extract_hyponyms(lang)
        assert "beagle" in hypo
        assert "bloodhound" in hypo
        assert len(hypo) >= 4

    def test_coordinate_terms(self):
        parsed = wtp.parse(DOG_WIKITEXT)
        lang = find_language_section(parsed, "English")
        coord = extract_coordinate_terms(lang)
        assert "cat" in coord
        assert "wolf" in coord


# ── Etymology tests ───────────────────────────────────────────────────


class TestEtymology:
    """Test etymology extraction."""

    def test_basic_etymology(self):
        parsed = wtp.parse(INSPISSATE_WIKITEXT)
        lang = find_language_section(parsed, "English")
        etym = extract_etymology(lang)
        assert etym is not None
        assert "inspissātus" in etym or "thicken" in etym.lower()

    def test_etymology_with_language_links(self):
        parsed = wtp.parse(ABANDON_WIKITEXT)
        lang = find_language_section(parsed, "English")
        etym = extract_etymology(lang)
        assert etym is not None
        assert len(etym) > 10

    def test_no_etymology(self):
        parsed = wtp.parse(SIMPLE_WIKITEXT)
        lang = find_language_section(parsed, "English")
        etym = extract_etymology(lang)
        assert etym is None


# ── WikitextCleaner tests ─────────────────────────────────────────────


class TestWikitextCleaner:
    """Test the WikitextCleaner on definition text."""

    def setup_method(self):
        self.cleaner = WikitextCleaner()

    def test_label_preservation(self):
        text = "{{lb|en|transitive}} To give up control."
        clean = self.cleaner.clean_text(text)
        assert "(transitive)" in clean
        assert "give up control" in clean

    def test_gloss_preservation(self):
        text = "{{gloss|informal term}} Something."
        clean = self.cleaner.clean_text(text)
        assert "(informal term)" in clean

    def test_wikilink_conversion(self):
        text = "To [[thicken]] a [[fluid]]."
        clean = self.cleaner.clean_text(text)
        assert "thicken" in clean
        assert "fluid" in clean
        assert "[[" not in clean

    def test_quote_template_removal(self):
        text = "A word. {{quote-book|en|year=2000|title=Test|passage=Example.}}"
        clean = self.cleaner.clean_text(text)
        assert "A word" in clean
        assert "quote-book" not in clean

    def test_html_removal(self):
        text = "A <ref>reference</ref> word."
        clean = self.cleaner.clean_text(text)
        assert "<ref>" not in clean


# ── Wholesale _parse_page integration tests ───────────────────────────


class TestWholesaleParsePageIntegration:
    """Integration tests for the wholesale _parse_page method."""

    def test_abandon_full_extraction(self):
        result = WiktionaryWholesaleConnector._parse_page(
            "abandon", ABANDON_WIKITEXT, "English"
        )
        assert result is not None
        assert result["title"] == "abandon"

        # Definitions
        defs = result["definitions"]
        assert len(defs) >= 3  # verb + noun definitions
        assert any(d["part_of_speech"] == "verb" for d in defs)
        assert any(d["part_of_speech"] == "noun" for d in defs)

        # Synonyms (from col4 section + inline #: {{syn}})
        all_syns = set()
        for d in defs:
            all_syns.update(d.get("synonyms", []))
        assert "abdicate" in all_syns  # From section
        assert "give up" in all_syns   # From inline
        assert len(all_syns) >= 10

        # Antonyms
        all_ants = set()
        for d in defs:
            all_ants.update(d.get("antonyms", []))
        assert "keep" in all_ants
        assert len(all_ants) >= 3

        # Etymology
        etym = result.get("etymology")
        assert etym is not None

        # Derived terms
        assert len(result.get("derived_terms", [])) >= 2

    def test_inspissate_full_extraction(self):
        result = WiktionaryWholesaleConnector._parse_page(
            "inspissate", INSPISSATE_WIKITEXT, "English"
        )
        assert result is not None
        defs = result["definitions"]
        assert len(defs) == 2

        # Verify labels preserved
        texts = [d["text"] for d in defs]
        assert any("transitive" in t for t in texts)
        assert any("intransitive" in t for t in texts)

        # Related terms
        related = result.get("related_terms", [])
        assert "inspissation" in related

    def test_happy_inline_synonyms(self):
        """Verify inline #: {{syn}} lines are captured."""
        result = WiktionaryWholesaleConnector._parse_page(
            "happy", HAPPY_WIKITEXT, "English"
        )
        assert result is not None

        all_syns = set()
        for d in result["definitions"]:
            all_syns.update(d.get("synonyms", []))
        assert "cheerful" in all_syns
        assert "fortunate" in all_syns

        all_ants = set()
        for d in result["definitions"]:
            all_ants.update(d.get("antonyms", []))
        assert "sad" in all_ants
        assert "unhappy" in all_ants

    def test_dog_hypernyms_hyponyms(self):
        result = WiktionaryWholesaleConnector._parse_page(
            "dog", DOG_WIKITEXT, "English"
        )
        assert result is not None
        assert "canid" in result.get("hypernyms", [])
        assert "beagle" in result.get("hyponyms", [])
        assert "cat" in result.get("coordinate_terms", [])

    def test_simple_word(self):
        result = WiktionaryWholesaleConnector._parse_page(
            "test", SIMPLE_WIKITEXT, "English"
        )
        assert result is not None
        assert len(result["definitions"]) == 2
        assert result["definitions"][0]["text"] == "A simple test word"

    def test_non_english_returns_none(self):
        wikitext = "==French==\n===Noun===\n# French word."
        result = WiktionaryWholesaleConnector._parse_page(
            "mot", wikitext, "English"
        )
        assert result is None

    def test_no_definitions_returns_empty(self):
        wikitext = "==English==\n===Pronunciation===\n* {{IPA|en|/test/}}"
        result = WiktionaryWholesaleConnector._parse_page(
            "test", wikitext, "English"
        )
        # Either None or empty definitions
        assert result is None or len(result.get("definitions", [])) == 0


# ── POS mapping tests ────────────────────────────────────────────────


class TestPOSMappings:
    """Ensure all Wiktionary POS types are mapped."""

    def test_standard_pos(self):
        assert POS_MAPPINGS["noun"] == "noun"
        assert POS_MAPPINGS["verb"] == "verb"
        assert POS_MAPPINGS["adjective"] == "adjective"
        assert POS_MAPPINGS["adverb"] == "adverb"

    def test_mapped_pos(self):
        assert POS_MAPPINGS["proper noun"] == "noun"
        assert POS_MAPPINGS["participle"] == "verb"
        assert POS_MAPPINGS["numeral"] == "adjective"
        assert POS_MAPPINGS["determiner"] == "adjective"

    def test_all_common_pos_covered(self):
        required = [
            "noun", "verb", "adjective", "adverb", "pronoun",
            "preposition", "conjunction", "interjection",
            "determiner", "proper noun", "participle", "numeral",
        ]
        for pos in required:
            assert pos in POS_MAPPINGS, f"Missing POS: {pos}"


# ── Validation helpers ───────────────────────────────────────────────


class TestIsValidSynonym:
    def test_valid(self):
        assert is_valid_synonym("happy") is True

    def test_thesaurus_ref(self):
        assert is_valid_synonym("Thesaurus:happy") is False

    def test_appendix_ref(self):
        assert is_valid_synonym("Appendix:English") is False

    def test_category_ref(self):
        assert is_valid_synonym("Category:English") is False
