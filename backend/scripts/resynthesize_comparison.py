"""Before/after comparison: re-synthesize 'bank' with the hybrid pipeline.

Shows:
  1. Raw provider definitions (before synthesis)
  2. Old synthesized entry (before re-synthesis)
  3. New synthesized entry (after re-synthesis with hybrid pipeline)

Run: uv run scripts/resynthesize_comparison.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def fmt_list(items: list, n: int = 6) -> str:
    if not items:
        return "[]"
    shown = items[:n]
    extra = f" +{len(items) - n} more" if len(items) > n else ""
    return f"{shown}{extra}"


async def print_entry(entry, label: str, indent: str = "  "):
    from floridify.models.dictionary import Definition, Example

    print(f"\n{'='*72}")
    print(f"  {label}")
    print(f"{'='*72}")

    print(f"{indent}Definitions: {len(entry.definition_ids)}")
    print(f"{indent}Sources: {[str(s.provider) for s in entry.source_entries]}")
    if entry.etymology:
        print(f"{indent}Etymology: {entry.etymology.text[:120]}...")
    print(f"{indent}Facts: {len(entry.fact_ids)}")
    if entry.model_info:
        print(f"{indent}Model: {entry.model_info.name}")
    if hasattr(entry, "attribution_text") and entry.attribution_text:
        print(f"{indent}Attribution: {entry.attribution_text}")

    for i, def_id in enumerate(entry.definition_ids):
        defn = await Definition.get(def_id)
        if not defn:
            continue

        cluster = defn.meaning_cluster
        cluster_str = f"{cluster.name} ({cluster.slug})" if cluster else "unclustered"

        print(f"\n{indent}--- Def {i+1}: [{cluster_str}] ---")
        print(f"{indent}  POS: {defn.part_of_speech}")
        print(f"{indent}  Text: {defn.text}")
        print(f"{indent}  CEFR: {defn.cefr_level}  Freq: {defn.frequency_band}  Score: {defn.frequency_score}")
        print(f"{indent}  Register: {defn.language_register}  Domain: {defn.domain}  Region: {defn.region}")
        print(f"{indent}  Synonyms ({len(defn.synonyms)}): {fmt_list(defn.synonyms)}")
        print(f"{indent}  Antonyms ({len(defn.antonyms)}): {fmt_list(defn.antonyms)}")

        exs = []
        for eid in defn.example_ids[:2]:
            ex = await Example.get(eid)
            if ex:
                exs.append(ex.text[:80] + "...")
        if exs:
            print(f"{indent}  Examples: {exs}")
        if defn.collocations:
            print(f"{indent}  Collocations: {[(c.text, c.type) for c in defn.collocations[:3]]}")
        if defn.usage_notes:
            print(f"{indent}  Usage notes: {[(n.type, n.text[:50]) for n in defn.usage_notes[:2]]}")
        if defn.grammar_patterns:
            print(f"{indent}  Grammar: {[(g.pattern, (g.description or '')[:40]) for g in defn.grammar_patterns[:2]]}")


async def print_raw_provider_defs(word_obj):
    from floridify.models.dictionary import Definition, DictionaryEntry, DictionaryProvider

    entries = await DictionaryEntry.find(
        DictionaryEntry.word_id == word_obj.id,
        DictionaryEntry.provider != DictionaryProvider.SYNTHESIS,
    ).to_list()

    print(f"\n{'='*72}")
    print(f"  RAW PROVIDER DEFINITIONS (before synthesis)")
    print(f"{'='*72}")

    total_defs = 0
    for entry in entries:
        prov = entry.provider if isinstance(entry.provider, str) else entry.provider
        defs = await Definition.find({"_id": {"$in": entry.definition_ids}}).to_list()
        total_defs += len(defs)
        print(f"\n  [{prov}] — {len(defs)} definitions")
        if entry.etymology:
            print(f"    Etymology: {entry.etymology.text[:100]}...")
        for j, d in enumerate(defs[:5]):
            syns = fmt_list(d.synonyms, 4)
            ants = fmt_list(d.antonyms, 3)
            print(f"    [{j}] ({d.part_of_speech}) {d.text[:90]}")
            if d.synonyms:
                print(f"        synonyms: {syns}")
            if d.antonyms:
                print(f"        antonyms: {ants}")
        if len(defs) > 5:
            print(f"    ... +{len(defs)-5} more")

    print(f"\n  Total raw definitions across all providers: {total_defs}")
    return total_defs


async def main():
    word = sys.argv[1] if len(sys.argv) > 1 else "bank"

    # Initialize storage
    from floridify.storage.mongodb import get_storage
    await get_storage()

    from floridify.models.dictionary import (
        Definition, DictionaryEntry, DictionaryProvider, Word,
    )

    word_obj = await Word.find_one(Word.text == word)
    if not word_obj:
        print(f'Word "{word}" not in DB. Run a lookup first.')
        return

    # ── 1. Raw provider definitions ──────────────────────────────────
    total_raw = await print_raw_provider_defs(word_obj)

    # ── 2. Old synthesized entry (BEFORE) ────────────────────────────
    old_synth = await DictionaryEntry.find_one(
        DictionaryEntry.word_id == word_obj.id,
        DictionaryEntry.provider == DictionaryProvider.SYNTHESIS,
    )

    if old_synth:
        await print_entry(old_synth, f"OLD SYNTHESIZED ENTRY (before re-synthesis)")
    else:
        print("\n  No existing synthesized entry found.")

    # ── 3. Re-synthesize with new hybrid pipeline ────────────────────
    print(f"\n{'='*72}")
    print(f"  RE-SYNTHESIZING with hybrid pipeline...")
    print(f"{'='*72}")

    from floridify.ai.synthesizer import get_definition_synthesizer
    from floridify.models.base import Language

    synthesizer = get_definition_synthesizer()
    t0 = time.perf_counter()
    new_entry = await synthesizer.resynthesize_from_provenance(
        word=word,
        languages=[Language.ENGLISH],
    )
    elapsed = time.perf_counter() - t0

    if new_entry:
        # Reload to get the saved version
        new_entry = await DictionaryEntry.get(new_entry.id)
        await print_entry(new_entry, f"NEW SYNTHESIZED ENTRY (after re-synthesis, {elapsed:.1f}s)")
    else:
        print("  Re-synthesis returned None!")

    # ── 4. Summary comparison ────────────────────────────────────────
    print(f"\n{'='*72}")
    print(f"  COMPARISON SUMMARY")
    print(f"{'='*72}")
    print(f"  Raw provider definitions: {total_raw}")
    if old_synth and new_entry:
        old_defs = len(old_synth.definition_ids)
        new_defs = len(new_entry.definition_ids)
        print(f"  Old synthesized definitions: {old_defs}")
        print(f"  New synthesized definitions: {new_defs}")

        # Count filled fields in new vs old
        for label, entry in [("OLD", old_synth), ("NEW", new_entry)]:
            defs = await Definition.find({"_id": {"$in": entry.definition_ids}}).to_list()
            cefr_filled = sum(1 for d in defs if d.cefr_level)
            freq_filled = sum(1 for d in defs if d.frequency_band)
            score_filled = sum(1 for d in defs if d.frequency_score)
            reg_filled = sum(1 for d in defs if d.language_register)
            dom_filled = sum(1 for d in defs if d.domain)
            rgn_filled = sum(1 for d in defs if d.region)
            total = len(defs)
            print(f"  {label} field fill rates ({total} defs):")
            print(f"    CEFR: {cefr_filled}/{total}  Freq: {freq_filled}/{total}  Score: {score_filled}/{total}")
            print(f"    Register: {reg_filled}/{total}  Domain: {dom_filled}/{total}  Region: {rgn_filled}/{total}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
