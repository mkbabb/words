"""Record golden fixtures from existing MongoDB data for quality testing.

Pulls already-synthesized entries from the database — zero AI API calls.
Words must already exist in the database (look them up via the app first).

Run:
    cd backend && uv run python -m tests.quality.record_fixtures
    cd backend && uv run python -m tests.quality.record_fixtures --force  # re-record existing
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure backend source is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

GOLDEN_DIR = Path(__file__).parent / "golden_fixtures"

# Words to record fixtures for
FIXTURE_WORDS = [
    {"word": "bank", "language": "en", "fixture_name": "bank_en"},
    {"word": "fork", "language": "en", "fixture_name": "fork_en"},
    {"word": "en coulisses", "language": "fr", "fixture_name": "en_coulisses_fr"},
]


async def record_from_db(word: str, language: str) -> dict | None:
    """Pull existing synthesis data from MongoDB. Zero AI calls."""
    from floridify.models.dictionary import (
        Definition,
        DictionaryEntry,
        DictionaryProvider,
        Example,
        Fact,
        Pronunciation,
        Word,
    )
    from floridify.storage.mongodb import _ensure_initialized

    await _ensure_initialized()

    # Find the word
    word_doc = await Word.find_one(Word.text == word)
    if not word_doc:
        print(f"  Word '{word}' not found in database")
        return None

    # Find synthesized entry
    entry = await DictionaryEntry.find_one(
        DictionaryEntry.word_id == word_doc.id,
        DictionaryEntry.provider == DictionaryProvider.SYNTHESIS,
    )
    if not entry:
        print(f"  No synthesized entry for '{word}'")
        return None

    # Fetch definitions
    definitions = await Definition.find(
        Definition.word_id == word_doc.id,
        Definition.dictionary_entry_id == entry.id,
    ).to_list()

    if not definitions:
        # Fetch by definition_ids from entry
        definitions = [d for def_id in entry.definition_ids if (d := await Definition.get(def_id))]

    # Fetch pronunciation
    pronunciation = None
    if entry.pronunciation_id:
        pronunciation = await Pronunciation.get(entry.pronunciation_id)

    # Fetch facts
    facts = []
    for fact_id in entry.fact_ids:
        fact = await Fact.get(fact_id)
        if fact:
            facts.append(fact)

    # Fetch examples for each definition
    def_dicts = []
    for d in definitions:
        d_dict = d.model_dump(mode="json")
        # Resolve example_ids to actual example texts
        examples = []
        for ex_id in d.example_ids:
            ex = await Example.get(ex_id)
            if ex:
                examples.append({"text": ex.text, "type": ex.type})
        d_dict["examples"] = examples
        def_dicts.append(d_dict)

    entry_data: dict = {
        "word": word,
        "language": language,
        "definitions": def_dicts,
    }

    if pronunciation:
        entry_data["pronunciation"] = pronunciation.model_dump(mode="json")

    if entry.etymology:
        entry_data["etymology"] = entry.etymology.model_dump(mode="json")

    if facts:
        entry_data["facts"] = [f.content for f in facts]

    return entry_data


async def main() -> None:
    """Record all golden fixtures."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    force = "--force" in sys.argv

    for fixture in FIXTURE_WORDS:
        word = fixture["word"]
        language = fixture["language"]
        fixture_name = fixture["fixture_name"]
        output_path = GOLDEN_DIR / f"{fixture_name}.json"

        if output_path.exists() and not force:
            print(f"\nSkipping '{word}' — fixture exists. Use --force to re-record.")
            continue

        print(f"\nRecording fixture for '{word}' ({language})...")

        try:
            data = await record_from_db(word, language)

            if data is None:
                print(f"  Not in database. Use the app to look up '{word}' first,")
                print("  then re-run this script.")
                continue

            def_count = len(data.get("definitions", []))
            if def_count == 0:
                print(f"  WARNING: '{word}' has 0 definitions")

            output_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            print(f"  Saved to {output_path} ({def_count} definitions)")

        except Exception as e:
            print(f"  ERROR recording '{word}': {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
