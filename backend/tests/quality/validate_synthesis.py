"""Validate synthesis quality by re-synthesizing words from provider data.

Connects to production MongoDB, runs resynthesize_from_provenance() on a
curated suite of words, and validates the output against quality criteria.

Run:
    cd backend && uv run python -m tests.quality.validate_synthesis
    cd backend && uv run python -m tests.quality.validate_synthesis --words bank fork
    cd backend && uv run python -m tests.quality.validate_synthesis --dry-run  # check provider data only
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Suite of words covering diverse linguistic properties.
# Each word must already have provider data in MongoDB.
VALIDATION_SUITE: list[dict[str, str | set[str]]] = [
    {
        "word": "bank",
        "language": "en",
        "expected_pos": {"noun", "verb"},
        "description": "Polysemous English — financial + river + verb senses (40 raw defs)",
    },
    {
        "word": "fork",
        "language": "en",
        "expected_pos": {"noun", "verb"},
        "description": "Polysemous English — utensil + road + software (44 raw defs)",
    },
    {
        "word": "serendipity",
        "language": "en",
        "expected_pos": {"noun"},
        "description": "Low-frequency literary — tests enrichment on sparse input (3 raw defs)",
    },
    {
        "word": "perspicacious",
        "language": "en",
        "expected_pos": {"adjective"},
        "description": "Rare adjective — tests synonym/antonym quality (4 raw defs)",
    },
    {
        "word": "ephemeral",
        "language": "en",
        "expected_pos": {"adjective", "noun"},
        "description": "Dual POS — adjective + noun usage (4 raw defs)",
    },
    {
        "word": "ubiquitous",
        "language": "en",
        "expected_pos": {"adjective"},
        "description": "Common formal adjective — tests CEFR/frequency accuracy (3 raw defs)",
    },
]


@dataclass
class DefinitionReport:
    """Quality report for a single definition."""

    index: int
    pos: str
    text: str
    text_length: int
    has_synonyms: bool
    synonym_count: int
    has_antonyms: bool
    antonym_count: int
    has_examples: bool
    example_count: int
    has_cefr: bool
    cefr_level: str | None
    has_frequency: bool
    frequency_band: int | None
    has_cluster: bool
    cluster_name: str | None
    has_register: bool
    has_domain: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class WordReport:
    """Quality report for a synthesized word entry."""

    word: str
    language: str
    description: str
    success: bool = False
    error: str | None = None
    duration_seconds: float = 0.0

    # Provider data
    provider_count: int = 0
    provider_names: list[str] = field(default_factory=list)
    raw_definition_count: int = 0

    # Synthesized entry
    definition_count: int = 0
    has_pronunciation: bool = False
    has_etymology: bool = False
    has_facts: bool = False
    fact_count: int = 0
    cluster_count: int = 0
    source_entry_count: int = 0
    version: int = 0

    # Quality checks
    definitions: list[DefinitionReport] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    score: float = 0.0

    # POS coverage
    expected_pos: set[str] = field(default_factory=set)
    actual_pos: set[str] = field(default_factory=set)
    pos_coverage_ok: bool = False


def _score_word(report: WordReport) -> float:
    """Compute a 0-10 quality score for a word synthesis."""
    if not report.success:
        return 0.0

    score = 0.0
    max_score = 0.0

    # Definitions present and reasonable count (2 pts)
    max_score += 2.0
    if report.definition_count > 0:
        score += 1.0
        if 3 <= report.definition_count <= 30:
            score += 1.0
        elif report.definition_count > 0:
            score += 0.5

    # Pronunciation (1 pt)
    max_score += 1.0
    if report.has_pronunciation:
        score += 1.0

    # Etymology (1 pt)
    max_score += 1.0
    if report.has_etymology:
        score += 1.0

    # Facts (0.5 pt)
    max_score += 0.5
    if report.has_facts:
        score += 0.5

    # POS coverage (1 pt)
    max_score += 1.0
    if report.pos_coverage_ok:
        score += 1.0

    # Cluster diversity (1 pt)
    max_score += 1.0
    if report.cluster_count > 1:
        score += 1.0
    elif report.cluster_count == 1:
        score += 0.5

    # Definition enrichment averages (2.5 pts)
    if report.definitions:
        n = len(report.definitions)

        # Synonyms coverage (0.5 pt)
        max_score += 0.5
        syn_rate = sum(1 for d in report.definitions if d.has_synonyms) / n
        score += 0.5 * syn_rate

        # Examples coverage (0.5 pt)
        max_score += 0.5
        ex_rate = sum(1 for d in report.definitions if d.has_examples) / n
        score += 0.5 * ex_rate

        # CEFR coverage (0.5 pt)
        max_score += 0.5
        cefr_rate = sum(1 for d in report.definitions if d.has_cefr) / n
        score += 0.5 * cefr_rate

        # Frequency band coverage (0.5 pt)
        max_score += 0.5
        freq_rate = sum(1 for d in report.definitions if d.has_frequency) / n
        score += 0.5 * freq_rate

        # No issues (0.5 pt)
        max_score += 0.5
        issue_count = sum(len(d.issues) for d in report.definitions) + len(report.issues)
        if issue_count == 0:
            score += 0.5
        elif issue_count <= 2:
            score += 0.25

    # Normalize to 0-10
    return round((score / max_score) * 10, 1) if max_score > 0 else 0.0


async def check_provider_data(word: str) -> dict:
    """Check what provider data exists for a word (no synthesis)."""
    from floridify.models.dictionary import (
        DictionaryEntry,
        DictionaryProvider,
        Word,
    )

    word_doc = await Word.find_one(Word.text == word)
    if not word_doc:
        return {"exists": False, "providers": [], "definition_count": 0}

    entries = await DictionaryEntry.find(
        DictionaryEntry.word_id == word_doc.id,
        DictionaryEntry.provider != DictionaryProvider.SYNTHESIS,
    ).to_list()

    total_defs = 0
    providers = []
    for entry in entries:
        provider_name = (
            entry.provider.value if hasattr(entry.provider, "value") else str(entry.provider)
        )
        def_count = len(entry.definition_ids)
        total_defs += def_count
        providers.append({"name": provider_name, "definitions": def_count})

    return {
        "exists": True,
        "providers": providers,
        "definition_count": total_defs,
    }


async def resynthesize_and_validate(
    word: str,
    language: str,
    expected_pos: set[str],
    description: str,
) -> WordReport:
    """Resynthesize a word and validate the output quality."""
    from floridify.ai.synthesizer import get_definition_synthesizer
    from floridify.models.base import Language
    from floridify.models.dictionary import (
        Definition,
        DictionaryEntry,
        DictionaryProvider,
        Example,
        Word,
    )

    report = WordReport(
        word=word,
        language=language,
        description=description,
        expected_pos=expected_pos,
    )

    try:
        # Check provider data first
        word_doc = await Word.find_one(Word.text == word)
        if not word_doc:
            report.error = "Word not in database"
            return report

        provider_entries = await DictionaryEntry.find(
            DictionaryEntry.word_id == word_doc.id,
            DictionaryEntry.provider != DictionaryProvider.SYNTHESIS,
        ).to_list()

        report.provider_count = len(provider_entries)
        for pe in provider_entries:
            pname = pe.provider.value if hasattr(pe.provider, "value") else str(pe.provider)
            report.provider_names.append(pname)
            report.raw_definition_count += len(pe.definition_ids)

        if not provider_entries:
            report.error = "No provider data"
            return report

        # Run re-synthesis
        synthesizer = get_definition_synthesizer()
        lang = Language(language)

        start = time.perf_counter()
        entry = await synthesizer.resynthesize_from_provenance(
            word=word,
            languages=[lang],
        )
        report.duration_seconds = round(time.perf_counter() - start, 2)

        if not entry:
            report.error = "Synthesis returned None"
            return report

        report.success = True
        report.definition_count = len(entry.definition_ids)
        report.has_pronunciation = entry.pronunciation_id is not None
        report.has_etymology = entry.etymology is not None
        report.source_entry_count = len(entry.source_entries)
        report.version = entry.version

        # Facts
        if entry.fact_ids:
            report.has_facts = True
            report.fact_count = len(entry.fact_ids)

        # Load definitions
        definitions = []
        for def_id in entry.definition_ids:
            d = await Definition.get(def_id)
            if d:
                definitions.append(d)

        # Analyze each definition
        clusters = set()
        word_lower = word.lower()

        for i, d in enumerate(definitions):
            # Load examples
            examples = []
            for ex_id in d.example_ids:
                ex = await Example.get(ex_id)
                if ex:
                    examples.append(ex.text)

            cluster_name = None
            if d.meaning_cluster:
                cluster_name = d.meaning_cluster.name
                clusters.add(d.meaning_cluster.id)

            dr = DefinitionReport(
                index=i,
                pos=d.part_of_speech,
                text=d.text,
                text_length=len(d.text),
                has_synonyms=bool(d.synonyms),
                synonym_count=len(d.synonyms) if d.synonyms else 0,
                has_antonyms=bool(d.antonyms),
                antonym_count=len(d.antonyms) if d.antonyms else 0,
                has_examples=bool(examples),
                example_count=len(examples),
                has_cefr=d.cefr_level is not None,
                cefr_level=d.cefr_level,
                has_frequency=d.frequency_band is not None,
                frequency_band=d.frequency_band,
                has_cluster=d.meaning_cluster is not None,
                cluster_name=cluster_name,
                has_register=d.language_register is not None,
                has_domain=d.domain is not None,
            )

            # Quality checks on this definition
            if len(d.text) < 10:
                dr.issues.append(f"Definition too short ({len(d.text)} chars)")
            if len(d.text) > 500:
                dr.issues.append(f"Definition too long ({len(d.text)} chars)")

            # Self-reference check
            if d.synonyms:
                for syn in d.synonyms:
                    if syn.lower() == word_lower:
                        dr.issues.append(f"Self-referential synonym: '{syn}'")
            if d.antonyms:
                for ant in d.antonyms:
                    if ant.lower() == word_lower:
                        dr.issues.append(f"Self-referential antonym: '{ant}'")

            # Synonym/antonym overlap
            if d.synonyms and d.antonyms:
                syn_set = {s.lower() for s in d.synonyms}
                ant_set = {a.lower() for a in d.antonyms}
                overlap = syn_set & ant_set
                if overlap:
                    dr.issues.append(f"Synonym/antonym overlap: {overlap}")

            report.definitions.append(dr)

        report.cluster_count = len(clusters)
        report.actual_pos = {d.part_of_speech.lower() for d in definitions if d.part_of_speech}
        report.pos_coverage_ok = expected_pos <= report.actual_pos

        # Entry-level issues
        if report.definition_count == 0:
            report.issues.append("No definitions synthesized")
        if not report.has_pronunciation:
            report.issues.append("Missing pronunciation")
        if not report.has_etymology:
            report.issues.append("Missing etymology")
        if not report.pos_coverage_ok:
            missing = expected_pos - report.actual_pos
            report.issues.append(f"Missing POS: {missing}")

        # Duplicate definition check
        seen_texts: dict[str, int] = {}
        for i, d in enumerate(definitions):
            normalized = d.text.strip().lower()
            if normalized in seen_texts:
                report.issues.append(f"Duplicate definition at {i} and {seen_texts[normalized]}")
            else:
                seen_texts[normalized] = i

        report.score = _score_word(report)

    except Exception as e:
        report.error = f"{type(e).__name__}: {e}"
        import traceback

        traceback.print_exc()

    return report


def print_report(reports: list[WordReport]) -> None:
    """Print a formatted quality report."""
    print("\n" + "=" * 80)
    print("SYNTHESIS QUALITY VALIDATION REPORT")
    print("=" * 80)

    for report in reports:
        print(f"\n{'─' * 70}")
        status = "✓" if report.success else "✗"
        score_str = f"{report.score}/10" if report.success else "N/A"
        print(f"{status} {report.word} ({report.language}) — Score: {score_str}")
        print(f"  {report.description}")

        if report.error:
            print(f"  ERROR: {report.error}")
            continue

        print(f"  Providers: {report.provider_count} ({', '.join(report.provider_names)})")
        print(
            f"  Raw definitions: {report.raw_definition_count} → Synthesized: {report.definition_count}"
        )
        print(f"  Duration: {report.duration_seconds}s | Version: {report.version}")
        print(
            f"  Pronunciation: {'✓' if report.has_pronunciation else '✗'} | "
            f"Etymology: {'✓' if report.has_etymology else '✗'} | "
            f"Facts: {'✓' if report.has_facts else '✗'} ({report.fact_count})"
        )
        print(
            f"  Clusters: {report.cluster_count} | "
            f"POS: {report.actual_pos} ({'✓' if report.pos_coverage_ok else '✗ missing ' + str(report.expected_pos - report.actual_pos)})"
        )
        print(f"  Source entries (provenance): {report.source_entry_count}")

        # Definition summary table
        if report.definitions:
            print(
                f"\n  {'#':>3} {'POS':<12} {'Syn':>4} {'Ant':>4} {'Ex':>3} {'CEFR':>5} {'Freq':>5} {'Cluster':<15} {'Issues'}"
            )
            print(f"  {'─' * 68}")
            for d in report.definitions:
                cefr = d.cefr_level or "—"
                freq = str(d.frequency_band) if d.frequency_band else "—"
                cluster = (d.cluster_name or "—")[:15]
                issues = "; ".join(d.issues) if d.issues else ""
                print(
                    f"  {d.index:>3} {d.pos:<12} {d.synonym_count:>4} {d.antonym_count:>4} "
                    f"{d.example_count:>3} {cefr:>5} {freq:>5} {cluster:<15} {issues}"
                )

        if report.issues:
            print("\n  Entry-level issues:")
            for issue in report.issues:
                print(f"    ⚠ {issue}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")

    successful = [r for r in reports if r.success]
    failed = [r for r in reports if not r.success]

    if successful:
        avg_score = sum(r.score for r in successful) / len(successful)
        print(f"  Successful: {len(successful)}/{len(reports)} | Average score: {avg_score:.1f}/10")
        total_time = sum(r.duration_seconds for r in successful)
        print(f"  Total synthesis time: {total_time:.1f}s")

        total_issues = sum(
            len(r.issues) + sum(len(d.issues) for d in r.definitions) for r in successful
        )
        print(f"  Total issues: {total_issues}")

        # Score breakdown
        for r in sorted(successful, key=lambda x: x.score, reverse=True):
            print(
                f"    {r.word:<20} {r.score:>4}/10  ({r.definition_count} defs, {r.duration_seconds}s)"
            )

    if failed:
        print(f"\n  Failed ({len(failed)}):")
        for r in failed:
            print(f"    {r.word}: {r.error}")

    print()


async def main() -> None:
    """Run validation suite."""
    from floridify.storage.mongodb import _ensure_initialized

    await _ensure_initialized()

    # Parse args
    dry_run = "--dry-run" in sys.argv
    words_filter = []
    if "--words" in sys.argv:
        idx = sys.argv.index("--words")
        words_filter = sys.argv[idx + 1 :]

    suite = VALIDATION_SUITE
    if words_filter:
        suite = [w for w in suite if w["word"] in words_filter]

    if not suite:
        print("No matching words in suite. Available:", [w["word"] for w in VALIDATION_SUITE])
        return

    if dry_run:
        print("DRY RUN — checking provider data availability only\n")
        for item in suite:
            word = item["word"]
            info = await check_provider_data(str(word))
            status = "✓" if info["exists"] else "✗"
            print(
                f"{status} {word}: {info['definition_count']} definitions from {len(info['providers'])} providers"
            )
            for p in info["providers"]:
                print(f"    {p['name']}: {p['definitions']} definitions")
        return

    print(f"Validating {len(suite)} words...\n")

    reports = []
    for item in suite:
        word = str(item["word"])
        language = str(item["language"])
        expected_pos = set(item.get("expected_pos", set()))
        description = str(item.get("description", ""))

        print(f"  Re-synthesizing '{word}'...", end="", flush=True)
        report = await resynthesize_and_validate(word, language, expected_pos, description)
        reports.append(report)

        if report.success:
            print(f" {report.score}/10 ({report.duration_seconds}s)")
        else:
            print(f" FAILED: {report.error}")

    print_report(reports)

    # Save report as JSON
    report_path = Path(__file__).parent / "validation_report.json"
    report_data = []
    for r in reports:
        rd = {
            "word": r.word,
            "language": r.language,
            "success": r.success,
            "score": r.score,
            "error": r.error,
            "duration_seconds": r.duration_seconds,
            "provider_count": r.provider_count,
            "provider_names": r.provider_names,
            "raw_definition_count": r.raw_definition_count,
            "definition_count": r.definition_count,
            "has_pronunciation": r.has_pronunciation,
            "has_etymology": r.has_etymology,
            "has_facts": r.has_facts,
            "fact_count": r.fact_count,
            "cluster_count": r.cluster_count,
            "source_entry_count": r.source_entry_count,
            "version": r.version,
            "pos_coverage_ok": r.pos_coverage_ok,
            "actual_pos": sorted(r.actual_pos),
            "issues": r.issues,
            "definitions": [
                {
                    "index": d.index,
                    "pos": d.pos,
                    "text": d.text[:100],
                    "synonym_count": d.synonym_count,
                    "antonym_count": d.antonym_count,
                    "example_count": d.example_count,
                    "cefr_level": d.cefr_level,
                    "frequency_band": d.frequency_band,
                    "cluster_name": d.cluster_name,
                    "issues": d.issues,
                }
                for d in r.definitions
            ],
        }
        report_data.append(rd)

    report_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
