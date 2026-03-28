"""Before/after pipeline comparison for multiple words.

Shows raw provider data, then re-synthesizes with the hybrid pipeline,
then displays the enriched result with quality metrics.

Usage: uv run scripts/pipeline_comparison.py dog bank "en coulisses"
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["LOKY_MAX_CPU_COUNT"] = "1"


def _trunc(s: str, n: int = 90) -> str:
    return s[:n] + "..." if len(s) > n else s


async def show_raw(word_obj, provider_entries):
    from floridify.models.dictionary import Definition

    total = 0
    for entry in provider_entries:
        prov = entry.provider if isinstance(entry.provider, str) else entry.provider
        defs = await Definition.find({"_id": {"$in": entry.definition_ids}}).to_list()
        total += len(defs)
        print(f"    [{prov}] {len(defs)} defs", end="")
        if entry.etymology:
            print(f"  etymology: {_trunc(entry.etymology.text, 60)}", end="")
        print()
        for j, d in enumerate(defs[:3]):
            syn_info = f"  syns={len(d.synonyms)}" if d.synonyms else ""
            ant_info = f"  ants={len(d.antonyms)}" if d.antonyms else ""
            print(f"      [{j}] ({d.part_of_speech}) {_trunc(d.text, 70)}{syn_info}{ant_info}")
        if len(defs) > 3:
            print(f"      ... +{len(defs) - 3} more")
    return total


async def show_synthesized(entry):
    from floridify.models.dictionary import Definition, Example

    defs = []
    for def_id in entry.definition_ids:
        d = await Definition.get(def_id)
        if d:
            defs.append(d)

    print(f"    Definitions: {len(defs)}")
    print(f"    Sources: {[str(s.provider) for s in entry.source_entries]}")
    if entry.etymology:
        print(f"    Etymology: {_trunc(entry.etymology.text, 100)}")
    print(f"    Facts: {len(entry.fact_ids)}")
    if entry.attribution_text:
        print(f"    Attribution: {entry.attribution_text}")

    for i, d in enumerate(defs):
        cluster = d.meaning_cluster
        cluster_str = f"{cluster.name} ({cluster.slug})" if cluster else "unclustered"
        print(f"\n    Def {i+1}: [{cluster_str}]")
        print(f"      POS: {d.part_of_speech}")
        print(f"      Text: {_trunc(d.text, 120)}")
        score_str = f"{d.frequency_score:.3f}" if d.frequency_score is not None else "None"
        print(f"      CEFR: {d.cefr_level}  Freq: {d.frequency_band}  Score: {score_str}")
        print(f"      Register: {d.language_register}  Domain: {d.domain}  Region: {d.region}")

        non_ascii_s = sum(1 for s in d.synonyms if not s.isascii())
        non_ascii_a = sum(1 for a in d.antonyms if not a.isascii())
        print(f"      Synonyms ({len(d.synonyms)}, {non_ascii_s} non-ASCII): {d.synonyms[:5]}")
        print(f"      Antonyms ({len(d.antonyms)}, {non_ascii_a} non-ASCII): {d.antonyms[:4]}")
        if d.cognates:
            print(f"      Cognates: {d.cognates[:5]}")

        exs = []
        for eid in d.example_ids[:2]:
            ex = await Example.get(eid)
            if ex:
                exs.append(_trunc(ex.text, 80))
        if exs:
            print(f"      Ex: {exs[0]}")

    # Quality summary
    n = len(defs)
    if n > 0:
        cefr_filled = sum(1 for d in defs if d.cefr_level)
        freq_filled = sum(1 for d in defs if d.frequency_band)
        reg_filled = sum(1 for d in defs if d.language_register)
        dom_filled = sum(1 for d in defs if d.domain)
        rgn_filled = sum(1 for d in defs if d.region)
        total_non_ascii = sum(1 for d in defs for s in d.synonyms if not s.isascii())
        total_non_ascii += sum(1 for d in defs for a in d.antonyms if not a.isascii())
        cefr_values = set(d.cefr_level for d in defs if d.cefr_level)

        print(f"\n    --- Quality ---")
        print(f"    Fill: CEFR={cefr_filled}/{n} Freq={freq_filled}/{n} Reg={reg_filled}/{n} Dom={dom_filled}/{n} Rgn={rgn_filled}/{n}")
        print(f"    CEFR variety: {cefr_values}")
        print(f"    Non-ASCII in syn/ant: {total_non_ascii}")

    return defs


async def process_word(word: str):
    from floridify.models.dictionary import (
        Definition, DictionaryEntry, DictionaryProvider, Word,
    )
    from floridify.models.base import Language
    from floridify.ai.synthesizer import get_definition_synthesizer

    print(f"\n{'='*72}")
    print(f"  WORD: '{word}'")
    print(f"{'='*72}")

    word_obj = await Word.find_one(Word.text == word)
    if not word_obj:
        print(f"  Not in DB — running fresh lookup...")
        # Do a provider fetch first
        from floridify.core.lookup_pipeline import lookup_word_pipeline
        result = await lookup_word_pipeline(word)
        if result is None:
            print(f"  Lookup returned None")
            return
        word_obj = await Word.find_one(Word.text == word)
        if not word_obj:
            print(f"  Word still not found after lookup")
            return

    # Get provider entries
    provider_entries = await DictionaryEntry.find(
        DictionaryEntry.word_id == word_obj.id,
        DictionaryEntry.provider != DictionaryProvider.SYNTHESIS,
    ).to_list()

    # ── BEFORE: Raw provider data ──
    print(f"\n  ── RAW PROVIDER DATA ──")
    total_raw = await show_raw(word_obj, provider_entries)
    print(f"    Total raw: {total_raw}")

    # ── BEFORE: Existing synthesis (if any) ──
    old_synth = await DictionaryEntry.find_one(
        DictionaryEntry.word_id == word_obj.id,
        DictionaryEntry.provider == DictionaryProvider.SYNTHESIS,
    )
    if old_synth:
        print(f"\n  ── OLD SYNTHESIZED ──")
        await show_synthesized(old_synth)

    # ── Re-synthesize ──
    print(f"\n  ── RE-SYNTHESIZING... ──")
    synthesizer = get_definition_synthesizer()
    t0 = time.perf_counter()
    new_entry = await synthesizer.resynthesize_from_provenance(
        word=word,
        languages=list(word_obj.languages),
    )
    elapsed = time.perf_counter() - t0
    print(f"    Done in {elapsed:.1f}s")

    if new_entry:
        new_entry = await DictionaryEntry.get(new_entry.id)
        print(f"\n  ── NEW SYNTHESIZED ──")
        await show_synthesized(new_entry)
    else:
        print(f"    Re-synthesis returned None")


async def main():
    words = sys.argv[1:] if len(sys.argv) > 1 else ["dog", "bank"]

    from floridify.storage.mongodb import get_storage
    await get_storage()

    for word in words:
        await process_word(word)

    print(f"\n{'='*72}")
    print(f"  DONE — processed {len(words)} words")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    asyncio.run(main())
