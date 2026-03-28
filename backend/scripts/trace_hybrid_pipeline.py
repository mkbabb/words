"""Trace the hybrid synthesis pipeline for a word.

Demonstrates the local components without requiring AI API keys.
Run: uv run scripts/trace_hybrid_pipeline.py bank
"""

from __future__ import annotations

import asyncio
import sys
import time

# macOS safety
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"


async def trace_pipeline(word: str) -> None:
    from bson import ObjectId

    print(f"\n{'='*72}")
    print(f"  HYBRID PIPELINE TRACE: '{word}'")
    print(f"{'='*72}\n")

    # ── Stage 1: Provider Fetch (local only) ─────────────────────────

    print("─── STAGE 1: Provider Fetch (local) ───")

    # WordNet
    from floridify.providers.dictionary.local.wordnet_provider import WordNetConnector
    wn_conn = WordNetConnector()
    t0 = time.perf_counter()
    wn_entry = await wn_conn._fetch_from_provider(word)
    wn_ms = (time.perf_counter() - t0) * 1000

    if wn_entry:
        print(f"  WordNet: {len(wn_entry.definitions)} definitions ({wn_ms:.1f}ms)")
        print(f"    synsets: {wn_entry.provider_metadata.get('synset_count')}")
        print(f"    hypernyms: {wn_entry.provider_metadata.get('hypernyms', [])[:5]}")
        print(f"    hyponyms: {wn_entry.provider_metadata.get('hyponyms', [])[:5]}")
        for i, d in enumerate(wn_entry.definitions[:3]):
            syns = d.get("synonyms", [])[:4]
            ants = d.get("antonyms", [])[:3]
            print(f"    [{i}] ({d['part_of_speech']}) {d['text'][:80]}")
            if syns:
                print(f"        synonyms: {syns}")
            if ants:
                print(f"        antonyms: {ants}")
        if len(wn_entry.definitions) > 3:
            print(f"    ... +{len(wn_entry.definitions)-3} more definitions")
    else:
        print(f"  WordNet: not found ({wn_ms:.1f}ms)")

    # ── Stage 2: Local 3-Tier Dedup ──────────────────────────────────

    print(f"\n─── STAGE 2: Local 3-Tier Dedup ───")

    # Create mock definitions from WordNet to simulate multi-provider data
    from floridify.models.dictionary import Definition

    mock_defs: list[Definition] = []
    if wn_entry:
        for d in wn_entry.definitions:
            mock_defs.append(Definition(
                word_id=ObjectId(),
                part_of_speech=d["part_of_speech"],
                text=d["text"],
                synonyms=d.get("synonyms", [])[:5],
                antonyms=d.get("antonyms", [])[:3],
            ))

    # Add some intentional duplicates for demo
    if mock_defs and len(mock_defs) >= 2:
        # Add a near-duplicate of the first definition
        dup = Definition(
            word_id=mock_defs[0].word_id,
            part_of_speech=mock_defs[0].part_of_speech,
            text=mock_defs[0].text + " ",  # Trivially different
        )
        mock_defs.append(dup)

    if mock_defs:
        from floridify.ai.dedup import local_deduplicate_definitions
        t0 = time.perf_counter()
        dedup_response = await local_deduplicate_definitions(
            word=word,
            definitions=mock_defs,
            enable_semantic=False,  # Skip semantic tier for speed in demo
        )
        dedup_ms = (time.perf_counter() - t0) * 1000
        print(f"  Input: {len(mock_defs)} definitions")
        print(f"  Output: {len(dedup_response.deduplicated_definitions)} unique ({dedup_ms:.1f}ms)")
        print(f"  Removed: {dedup_response.removed_count} duplicates")
        for d in dedup_response.deduplicated_definitions[:4]:
            print(f"    [{d.source_indices}] ({d.part_of_speech}) {d.definition[:70]}")

    # ── Stage 3: Local Clustering ────────────────────────────────────

    print(f"\n─── STAGE 3: Local Sense Clustering (Agglomerative) ───")

    if len(mock_defs) >= 3:
        from floridify.ai.clustering.local_clustering import _cluster_embeddings, _wordnet_sense_count, format_cluster_hints
        import numpy as np

        n = min(len(mock_defs), 18)
        texts = [d.text for d in mock_defs[:n]]
        pos_list = [d.part_of_speech for d in mock_defs[:n]]

        wn_noun_count = _wordnet_sense_count(word, "noun")
        wn_verb_count = _wordnet_sense_count(word, "verb")
        print(f"  WordNet sense prior: {wn_noun_count} noun synsets, {wn_verb_count} verb synsets")

        # Try real encoder, fall back to random
        try:
            from floridify.search.semantic.encoder import SemanticEncoder
            encoder = SemanticEncoder()
            embeddings = encoder.encode(texts)
            print(f"  Encoder: Qwen3-0.6B (real embeddings)")
        except Exception:
            # Create semi-realistic embeddings: each definition gets a different direction
            rng = np.random.RandomState(42)
            embeddings = rng.randn(n, 64).astype(np.float32)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms
            print(f"  Encoder: synthetic (normalized random)")

        t0 = time.perf_counter()
        clusters = _cluster_embeddings(embeddings, pos_list, word=word)
        cluster_ms = (time.perf_counter() - t0) * 1000

        print(f"  {n} definitions → {len(clusters)} sense clusters ({cluster_ms:.1f}ms)")
        hints = format_cluster_hints(mock_defs[:n], clusters)
        for line in hints.split("\n"):
            print(f"    {line}")
    else:
        print(f"  Not enough definitions to cluster ({len(mock_defs)})")

    # ── Stage 4: Local Assessments ───────────────────────────────────

    print(f"\n─── STAGE 4: Local Assessments ───")

    from floridify.ai.assessment import (
        assess_cefr_local,
        assess_frequency_local,
        classify_domain_local,
        classify_register_local,
        detect_regional_local,
    )
    from floridify.ai.assessment.frequency import assess_frequency_score_local

    freq_band = assess_frequency_local(word)
    freq_score = assess_frequency_score_local(word)
    cefr = assess_cefr_local(word)
    print(f"  Frequency: band={freq_band}, score={freq_score:.3f}")
    print(f"  CEFR: {cefr}")

    # Check first few definitions for register/domain/regional
    for i, d in enumerate(mock_defs[:6]):
        reg = classify_register_local(d.text)
        dom = classify_domain_local(d.text, word=word, part_of_speech=d.part_of_speech)
        rgn = detect_regional_local(d.text)
        indicators = []
        if reg:
            indicators.append(f"register={reg}")
        if dom:
            indicators.append(f"domain={dom}")
        if rgn:
            indicators.append(f"regional={rgn}")
        label = f"({d.part_of_speech}) {d.text[:55]}..."
        if indicators:
            print(f"  [{i}] {label}  →  {', '.join(indicators)}")
        else:
            print(f"  [{i}] {label}  →  (AI fallback)")

    # ── Stage 5: Hybrid Synonyms/Antonyms ────────────────────────────

    print(f"\n─── STAGE 5: Hybrid Synonyms/Antonyms ───")

    from floridify.ai.synthesis.hybrid import (
        compute_synonym_delta,
        compute_antonym_delta,
    )

    for i, d in enumerate(mock_defs[:3]):
        merged_syns, ai_syn_needed = compute_synonym_delta(d, word, target_count=10)
        merged_ants, ai_ant_needed = compute_antonym_delta(d, word, target_count=5)
        print(f"  [{i}] ({d.part_of_speech}) {d.text[:50]}...")
        print(f"      synonyms: {len(merged_syns)} local → {ai_syn_needed} from AI  {merged_syns[:6]}")
        print(f"      antonyms: {len(merged_ants)} local → {ai_ant_needed} from AI  {merged_ants[:4]}")

    # ── Summary ──────────────────────────────────────────────────────

    print(f"\n{'='*72}")
    print(f"  PIPELINE SUMMARY for '{word}'")
    print(f"{'='*72}")

    total_ai_saved = 0
    print(f"  Providers: WordNet={len(wn_entry.definitions) if wn_entry else 0} defs")
    print(f"  Dedup: local 3-tier (saves 1 GPT-5-MINI call)")
    total_ai_saved += 1
    print(f"  Clustering: local pre-cluster hints → AI refinement")
    print(f"  Assessments saved from AI:")
    for name in ["frequency_band", "cefr_level"]:
        print(f"    ✓ {name} (always local)")
        total_ai_saved += 1
    for name, d in [("register", mock_defs[0].text if mock_defs else "")]:
        if classify_register_local(d):
            print(f"    ✓ {name} (local hit)")
            total_ai_saved += 1
        else:
            print(f"    ✗ {name} (would use AI)")
    print(f"  Hybrid syn/ant: WordNet fills {sum(len(compute_synonym_delta(d, word)[0]) for d in mock_defs[:3])} synonyms locally")
    print(f"  Estimated AI calls saved: ~{total_ai_saved}+ per definition")
    print()


if __name__ == "__main__":
    word = sys.argv[1] if len(sys.argv) > 1 else "bank"

    async def main():
        # Initialize Beanie with minimal document models
        from motor.motor_asyncio import AsyncIOMotorClient
        from beanie import init_beanie
        from floridify.models.dictionary import (
            Definition, Word, DictionaryEntry, Example, Fact, Pronunciation,
        )
        from floridify.caching.models import BaseVersionedData

        # Connect to local MongoDB (tunnel or local)
        for url in ["mongodb://localhost:27018", "mongodb://localhost:27017"]:
            try:
                client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=2000)
                await client.admin.command("ping")
                await init_beanie(
                    database=client.get_database("floridify"),
                    document_models=[Definition, Word, DictionaryEntry,
                                    Example, Fact, Pronunciation, BaseVersionedData],
                )
                break
            except Exception:
                continue
        else:
            print("ERROR: No MongoDB available. Start tunnel or local mongo.")
            return

        await trace_pipeline(word)

    asyncio.run(main())
