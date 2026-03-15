"""Reproducible wikitext parsing benchmarks."""

from __future__ import annotations

import wikitextparser as wtp

import pytest

from floridify.audit import (
    AUDIT_WIKITEXT_FULL_ENTRY,
    AUDIT_WIKITEXT_SAMPLE,
    WIKITEXT_CORRECTNESS_CASES,
    benchmark_sync,
)
from floridify.providers.dictionary.scraper.wikitext_cleaner import WikitextCleaner
from floridify.providers.dictionary.scraper.wiktionary_parser import (
    extract_etymology,
    extract_section_synonyms,
    extract_wikilist_items,
    find_language_section,
)


def _english_section():
    parsed = wtp.parse(AUDIT_WIKITEXT_SAMPLE)
    return find_language_section(parsed, "English")


@pytest.mark.performance
def test_wikitext_cleaning_and_section_parsing() -> None:
    section = _english_section()
    assert section is not None

    cleaner_case, cleaner_results = benchmark_sync(
        "wikitext-clean",
        "provider",
        lambda: WikitextCleaner.clean_text("{{lb|en|formal}} '''audit trail''' {{gloss|history}}"),
        iterations=40,
        warmup=2,
    )
    list_case, list_results = benchmark_sync(
        "wikitext-wikilist",
        "provider",
        lambda: extract_wikilist_items(str(section)),
        iterations=24,
        warmup=2,
    )
    etymology_case, etymology_results = benchmark_sync(
        "wikitext-etymology",
        "provider",
        lambda: extract_etymology(section),
        iterations=24,
        warmup=2,
    )
    synonym_case, synonym_results = benchmark_sync(
        "wikitext-synonym-section",
        "provider",
        lambda: extract_section_synonyms(section),
        iterations=24,
        warmup=2,
    )

    assert "audit trail" in cleaner_results[-1]
    assert list_results[-1]
    assert etymology_results[-1] is not None
    assert isinstance(synonym_results[-1], list)
    assert cleaner_case.stats.p95_ms < 15.0
    assert list_case.stats.p95_ms < 25.0
    assert etymology_case.stats.p95_ms < 20.0
    assert synonym_case.stats.p95_ms < 20.0


@pytest.mark.performance
@pytest.mark.provider
def test_wikitext_cleaner_correctness() -> None:
    """Known input/output pairs through WikitextCleaner."""
    for wikitext_input, expected in WIKITEXT_CORRECTNESS_CASES:
        result = WikitextCleaner.clean_text(wikitext_input).strip()
        assert result == expected, (
            f"Input: {wikitext_input!r}\n  Expected: {expected!r}\n  Got: {result!r}"
        )


@pytest.mark.performance
@pytest.mark.provider
def test_pronunciation_ipa_parsing() -> None:
    """Extract IPA from wikitext pronunciation section (no DB required)."""
    parsed = wtp.parse(AUDIT_WIKITEXT_FULL_ENTRY)
    section = find_language_section(parsed, "English")
    assert section is not None

    def extract_ipa_values():
        """Extract raw IPA values without creating Beanie documents."""
        ipa_values = []
        for subsection in section.sections:
            if subsection.title and "pronunciation" in subsection.title.lower():
                pron_parsed = wtp.parse(str(subsection))
                for template in pron_parsed.templates:
                    if "ipa" in template.name.strip().lower():
                        for i, arg in enumerate(template.arguments):
                            val = str(arg.value).strip()
                            if i > 0 and ("/" in val or "[" in val):
                                ipa_values.append(val)
                break
        return ipa_values

    case, results = benchmark_sync(
        "pronunciation-ipa-parse",
        "provider",
        extract_ipa_values,
        iterations=24,
        warmup=2,
    )

    ipa_values = results[-1]
    assert len(ipa_values) >= 1, "Should find at least one IPA transcription"
    assert all("/" in v for v in ipa_values), f"IPA values should have slashes: {ipa_values}"
    assert case.stats.p95_ms < 30.0


@pytest.mark.performance
@pytest.mark.provider
def test_full_entry_extraction() -> None:
    """Parse a complete wikitext entry through all extractors."""
    parsed = wtp.parse(AUDIT_WIKITEXT_FULL_ENTRY)
    section = find_language_section(parsed, "English")
    assert section is not None

    def extract_all():
        defs = extract_wikilist_items(str(section))
        etym = extract_etymology(section)
        syns = extract_section_synonyms(section)
        return defs, etym, syns

    case, results = benchmark_sync(
        "full-entry-extract",
        "provider",
        extract_all,
        iterations=16,
        warmup=2,
    )

    defs, etym, syns = results[-1]
    assert len(defs) >= 3, f"Expected ≥3 definitions, got {len(defs)}"
    assert etym is not None, "Etymology should be present"
    # Verify no raw wikitext markup in cleaned definitions
    for d in defs:
        cleaned = WikitextCleaner.clean_text(d)
        assert "{{" not in cleaned, f"Raw template in definition: {cleaned}"
        assert "[[" not in cleaned, f"Raw wikilink in definition: {cleaned}"
    assert case.stats.p95_ms < 80.0
