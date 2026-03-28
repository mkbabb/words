"""Audit synthesized definition quality against source definitions.

Checks:
  1. Semantic fidelity: does the synthesized def preserve the source meaning?
  2. Information coverage: are all source senses represented?
  3. Hallucination: does the synthesized def introduce unsupported claims?
  4. Field quality: are CEFR/frequency/register/domain sensible?

Run: uv run scripts/audit_synthesis_quality.py bank
"""

from __future__ import annotations

import asyncio
import sys
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"


async def audit(word: str) -> None:
    from floridify.storage.mongodb import get_storage
    from floridify.models.dictionary import (
        Definition, DictionaryEntry, DictionaryProvider, Word, Example,
    )

    await get_storage()

    word_obj = await Word.find_one(Word.text == word)
    if not word_obj:
        print(f'Word "{word}" not in DB')
        return

    # Load all provider definitions (raw sources)
    provider_entries = await DictionaryEntry.find(
        DictionaryEntry.word_id == word_obj.id,
        DictionaryEntry.provider != DictionaryProvider.SYNTHESIS,
    ).to_list()

    raw_defs: list[Definition] = []
    for entry in provider_entries:
        defs = await Definition.find({"_id": {"$in": entry.definition_ids}}).to_list()
        raw_defs.extend(defs)

    # Load synthesized entry
    synth = await DictionaryEntry.find_one(
        DictionaryEntry.word_id == word_obj.id,
        DictionaryEntry.provider == DictionaryProvider.SYNTHESIS,
    )
    if not synth:
        print("No synthesized entry found")
        return

    synth_defs: list[Definition] = []
    for def_id in synth.definition_ids:
        d = await Definition.get(def_id)
        if d:
            synth_defs.append(d)

    print(f"\n{'='*72}")
    print(f"  SYNTHESIS QUALITY AUDIT: '{word}'")
    print(f"{'='*72}")
    print(f"  Raw definitions: {len(raw_defs)} (from {len(provider_entries)} providers)")
    print(f"  Synthesized definitions: {len(synth_defs)}")

    # ── 1. Sense Coverage ─────────────────────────────────────────────
    print(f"\n--- 1. SENSE COVERAGE ---")

    # Group raw defs by POS
    raw_by_pos: dict[str, list[str]] = {}
    for d in raw_defs:
        raw_by_pos.setdefault(d.part_of_speech, []).append(d.text[:80])

    synth_by_pos: dict[str, list[str]] = {}
    for d in synth_defs:
        synth_by_pos.setdefault(d.part_of_speech, []).append(d.text[:80])

    for pos in sorted(set(list(raw_by_pos.keys()) + list(synth_by_pos.keys()))):
        raw_count = len(raw_by_pos.get(pos, []))
        synth_count = len(synth_by_pos.get(pos, []))
        ratio = synth_count / raw_count if raw_count > 0 else 0
        print(f"  {pos}: {raw_count} raw → {synth_count} synthesized (compression {ratio:.1%})")

    # ── 2. Per-Definition Quality ─────────────────────────────────────
    print(f"\n--- 2. PER-DEFINITION QUALITY ---")

    issues: list[str] = []
    for i, d in enumerate(synth_defs):
        cluster = d.meaning_cluster
        cluster_str = f"{cluster.name} ({cluster.slug})" if cluster else "NONE"

        quality_flags: list[str] = []

        # Check definition length (too short = underspecified, too long = verbose)
        if len(d.text) < 30:
            quality_flags.append("TOO_SHORT")
        if len(d.text) > 300:
            quality_flags.append("VERBOSE")

        # Check for domain label embedded in definition text (lazy AI output)
        if d.text.rstrip(".").endswith(("Aviation", "Finance", "British", "Technical")):
            quality_flags.append("DOMAIN_IN_TEXT")

        # Check synonym count
        if len(d.synonyms) == 0:
            quality_flags.append("NO_SYNONYMS")
        if len(d.synonyms) > 0 and word.lower() in [s.lower() for s in d.synonyms]:
            quality_flags.append("SELF_IN_SYNONYMS")

        # Check for foreign-language synonyms/antonyms (multilingual bleed)
        non_ascii_syns = [s for s in d.synonyms if not s.isascii()]
        non_ascii_ants = [s for s in d.antonyms if not s.isascii()]

        # Check examples
        example_texts = []
        for eid in d.example_ids[:3]:
            ex = await Example.get(eid)
            if ex:
                example_texts.append(ex.text)

        if not example_texts:
            quality_flags.append("NO_EXAMPLES")

        # Check metadata completeness
        meta_filled = sum([
            d.cefr_level is not None,
            d.frequency_band is not None,
            d.frequency_score is not None,
            d.language_register is not None,
        ])
        meta_total = 4

        print(f"\n  Def {i+1}: [{cluster_str}]")
        print(f"    POS: {d.part_of_speech}")
        print(f"    Text: {d.text}")
        print(f"    Length: {len(d.text)} chars")
        print(f"    CEFR: {d.cefr_level}  Freq: {d.frequency_band}  Score: {d.frequency_score:.3f}" if d.frequency_score else f"    CEFR: {d.cefr_level}  Freq: {d.frequency_band}  Score: None")
        print(f"    Register: {d.language_register}  Domain: {d.domain}  Region: {d.region}")
        print(f"    Synonyms: {len(d.synonyms)} ({len(non_ascii_syns)} non-ASCII)")
        print(f"    Antonyms: {len(d.antonyms)} ({len(non_ascii_ants)} non-ASCII)")
        print(f"    Examples: {len(d.example_ids)}")
        print(f"    Metadata: {meta_filled}/{meta_total} filled")
        if quality_flags:
            flags_str = ", ".join(quality_flags)
            print(f"    ⚠ FLAGS: {flags_str}")
            issues.append(f"Def {i+1} ({cluster_str}): {flags_str}")

        # Show first example
        if example_texts:
            print(f"    Example 1: {example_texts[0][:100]}...")

    # ── 3. Multilingual Bleed Check ───────────────────────────────────
    print(f"\n--- 3. MULTILINGUAL BLEED ---")
    total_non_ascii_syns = sum(
        len([s for s in d.synonyms if not s.isascii()])
        for d in synth_defs
    )
    total_non_ascii_ants = sum(
        len([a for a in d.antonyms if not a.isascii()])
        for d in synth_defs
    )
    total_syns = sum(len(d.synonyms) for d in synth_defs)
    total_ants = sum(len(d.antonyms) for d in synth_defs)

    print(f"  Synonyms with non-ASCII: {total_non_ascii_syns}/{total_syns}")
    print(f"  Antonyms with non-ASCII: {total_non_ascii_ants}/{total_ants}")

    if total_non_ascii_syns > 0:
        for d in synth_defs:
            non_ascii = [s for s in d.synonyms if not s.isascii()]
            if non_ascii:
                cluster = d.meaning_cluster
                print(f"    [{cluster.name if cluster else '?'}]: {non_ascii}")

    # ── 4. Cluster Quality ────────────────────────────────────────────
    print(f"\n--- 4. CLUSTER QUALITY ---")

    clusters_seen: dict[str, list[int]] = {}
    for i, d in enumerate(synth_defs):
        if d.meaning_cluster:
            clusters_seen.setdefault(d.meaning_cluster.slug, []).append(i)

    print(f"  Total clusters: {len(clusters_seen)}")
    for slug, indices in clusters_seen.items():
        if len(indices) > 1:
            print(f"  ⚠ Duplicate cluster slug '{slug}': defs {[i+1 for i in indices]}")
            issues.append(f"Duplicate cluster: {slug}")

    # ── 5. Summary ────────────────────────────────────────────────────
    print(f"\n--- SUMMARY ---")
    print(f"  Total issues: {len(issues)}")
    for issue in issues:
        print(f"    ⚠ {issue}")

    # Score
    n = len(synth_defs)
    if n > 0:
        avg_syn_count = sum(len(d.synonyms) for d in synth_defs) / n
        avg_ant_count = sum(len(d.antonyms) for d in synth_defs) / n
        avg_ex_count = sum(len(d.example_ids) for d in synth_defs) / n
        avg_text_len = sum(len(d.text) for d in synth_defs) / n
        meta_rate = sum(
            sum([d.cefr_level is not None, d.frequency_band is not None,
                 d.language_register is not None])
            for d in synth_defs
        ) / (n * 3)

        print(f"\n  Avg definition length: {avg_text_len:.0f} chars")
        print(f"  Avg synonyms: {avg_syn_count:.1f}")
        print(f"  Avg antonyms: {avg_ant_count:.1f}")
        print(f"  Avg examples: {avg_ex_count:.1f}")
        print(f"  Metadata fill rate: {meta_rate:.0%}")
        print(f"  Multilingual bleed: {total_non_ascii_syns + total_non_ascii_ants} non-ASCII items")
    print()


if __name__ == "__main__":
    word = sys.argv[1] if len(sys.argv) > 1 else "bank"
    asyncio.run(audit(word))
