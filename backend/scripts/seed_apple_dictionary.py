"""Seed definitions from macOS Apple Dictionary into the database.

Massively parallel: uses asyncio.Semaphore for concurrent DB writes and
a thread pool for the synchronous PyObjC lookups.

Usage:
    uv run scripts/seed_apple_dictionary.py --from-corpus language_english
    uv run scripts/seed_apple_dictionary.py --from-corpus language_english --limit 1000
    uv run scripts/seed_apple_dictionary.py --wordlist words.txt
"""

from __future__ import annotations

import asyncio
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from floridify.models.base import Language
from floridify.models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Etymology,
    Example,
    Pronunciation,
    Word,
)
from floridify.providers.dictionary.local.apple_dictionary import AppleDictionaryConnector
from floridify.storage.mongodb import get_storage

console = Console()

# Concurrency controls
LOOKUP_WORKERS = 8  # Thread pool for synchronous PyObjC calls
DB_CONCURRENCY = 50  # Max concurrent MongoDB write tasks


async def seed(
    words: list[str],
    skip_existing: bool = True,
) -> dict[str, int]:
    """Seed Apple Dictionary entries for a list of words."""
    await get_storage()

    connector = AppleDictionaryConnector()
    stats = {"total": len(words), "processed": 0, "skipped": 0, "no_def": 0, "failed": 0}
    sem = asyncio.Semaphore(DB_CONCURRENCY)

    # Pre-fetch existing Apple Dictionary entries for skip check
    existing_apple_words: set[str] = set()
    if skip_existing:
        console.print("[dim]Checking existing Apple Dictionary entries...[/dim]")
        apple_entries = await DictionaryEntry.find(
            {"provider": DictionaryProvider.APPLE_DICTIONARY.value}
        ).to_list()
        apple_word_ids = {e.word_id for e in apple_entries}
        # Resolve word IDs to text
        if apple_word_ids:
            existing_words = await Word.find({"_id": {"$in": list(apple_word_ids)}}).to_list()
            existing_apple_words = {w.text for w in existing_words}
        console.print(f"[dim]Found {len(existing_apple_words)} existing entries to skip[/dim]")

    # Pre-load all Word documents into a dict for fast lookup
    console.print("[dim]Loading word index...[/dim]")
    word_index: dict[str, Word] = {}
    async for w in Word.find_all():
        word_index[w.text] = w

    # Filter words
    work_list: list[str] = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        if skip_existing and w in existing_apple_words:
            stats["skipped"] += 1
            continue
        work_list.append(w)

    console.print(
        f"[bold]Processing {len(work_list)} words "
        f"({stats['skipped']} skipped as existing)[/bold]"
    )

    if not work_list:
        return stats

    # Phase 1: Batch lookup all words through Apple Dictionary (thread pool)
    # PyObjC DCSCopyTextDefinition is synchronous C, ~0.1ms per call
    console.print(f"[bold cyan]Phase 1:[/bold cyan] Looking up {len(work_list)} words...")
    lookup_start = time.perf_counter()

    def lookup_word(word: str) -> tuple[str, str | None]:
        """Synchronous Apple Dictionary lookup."""
        try:
            return (word, connector._lookup_definition(word))
        except Exception:
            return (word, None)

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=LOOKUP_WORKERS, thread_name_prefix="apple-dict") as pool:
        lookup_results = await asyncio.gather(
            *[loop.run_in_executor(pool, lookup_word, w) for w in work_list]
        )

    # Separate hits from misses
    hits: list[tuple[str, str]] = []
    for word, raw_def in lookup_results:
        if raw_def:
            hits.append((word, raw_def))
        else:
            stats["no_def"] += 1

    lookup_elapsed = time.perf_counter() - lookup_start
    console.print(
        f"  [green]{len(hits)} definitions found[/green], "
        f"[dim]{stats['no_def']} no definition[/dim] "
        f"({lookup_elapsed:.1f}s, {len(work_list) / lookup_elapsed:.0f} lookups/sec)"
    )

    if not hits:
        return stats

    # Phase 2: Parse all raw definitions (CPU-bound but fast)
    console.print(f"[bold cyan]Phase 2:[/bold cyan] Parsing {len(hits)} definitions...")
    parsed: list[tuple[str, list[dict], str | None, str | None, str]] = []
    for word, raw_def in hits:
        defs, pronunciation, etymology = connector._parse_definition_text(raw_def)
        if defs:
            parsed.append((word, defs, pronunciation, etymology, raw_def))

    console.print(f"  [green]{len(parsed)} words with parseable definitions[/green]")

    # Phase 3: Save to MongoDB with massive concurrency
    console.print(
        f"[bold cyan]Phase 3:[/bold cyan] Saving {len(parsed)} entries to MongoDB "
        f"(concurrency={DB_CONCURRENCY})..."
    )
    save_start = time.perf_counter()

    async def save_word_entry(
        word_text: str,
        definitions: list[dict],
        pronunciation_ipa: str | None,
        etymology_text: str | None,
        raw_definition: str,
        progress: Progress,
        task_id: int,
    ) -> bool:
        """Save a single word's Apple Dictionary entry to MongoDB."""
        async with sem:
            try:
                # Get or create Word document
                word_obj = word_index.get(word_text)
                if not word_obj:
                    word_obj = Word(text=word_text, languages=[Language.ENGLISH.value])
                    await word_obj.save()
                    word_index[word_text] = word_obj

                # Create Definition documents (direct insert, no versioning)
                definition_ids = []
                for def_data in definitions:
                    definition = Definition(
                        word_id=word_obj.id,
                        part_of_speech=def_data.get("part_of_speech", "unknown"),
                        text=def_data.get("text", ""),
                        synonyms=def_data.get("synonyms", []),
                        antonyms=def_data.get("antonyms", []),
                        providers=[DictionaryProvider.APPLE_DICTIONARY],
                    )
                    await definition.insert()

                    # Save examples
                    example_ids = []
                    for ex_text in def_data.get("examples", []):
                        example = Example(
                            definition_id=definition.id,
                            text=ex_text,
                            type="generated",
                        )
                        await example.insert()
                        if example.id:
                            example_ids.append(example.id)

                    if example_ids:
                        definition.example_ids = example_ids
                        await definition.save()

                    if definition.id:
                        definition_ids.append(definition.id)

                # Save pronunciation
                pronunciation_id = None
                if pronunciation_ipa:
                    pron = Pronunciation(
                        word_id=word_obj.id,
                        phonetic=connector._ipa_to_phonetic(pronunciation_ipa),
                        ipa=pronunciation_ipa,
                    )
                    await pron.insert()
                    pronunciation_id = pron.id

                # Build etymology
                etymology = None
                if etymology_text:
                    etymology = Etymology(text=etymology_text)

                # Create DictionaryEntry
                entry = DictionaryEntry(
                    word_id=word_obj.id,
                    definition_ids=definition_ids,
                    pronunciation_id=pronunciation_id,
                    provider=DictionaryProvider.APPLE_DICTIONARY,
                    languages=word_obj.languages,
                    etymology=etymology,
                    raw_data={
                        "raw_definition": raw_definition,
                        "source": "apple_dictionary_seed",
                    },
                )
                await entry.insert()

                progress.advance(task_id)
                return True
            except Exception as e:
                console.print(f"[red]Error saving '{word_text}': {e}[/red]")
                progress.advance(task_id)
                return False

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("Saving...", total=len(parsed))

        results = await asyncio.gather(
            *[
                save_word_entry(word, defs, pron, etym, raw, progress, task_id)
                for word, defs, pron, etym, raw in parsed
            ]
        )

    stats["processed"] = sum(1 for r in results if r)
    stats["failed"] = sum(1 for r in results if not r)

    save_elapsed = time.perf_counter() - save_start
    console.print(
        f"  [green]{stats['processed']} saved[/green], "
        f"[red]{stats['failed']} failed[/red] "
        f"({save_elapsed:.1f}s, {stats['processed'] / save_elapsed:.0f} saves/sec)"
    )

    return stats


async def get_corpus_vocabulary(corpus_name: str) -> list[str]:
    """Get vocabulary from an existing corpus."""
    from floridify.corpus.manager import get_tree_corpus_manager

    manager = get_tree_corpus_manager()
    corpus = await manager.get_corpus(corpus_name=corpus_name)
    if not corpus:
        raise click.ClickException(f"Corpus '{corpus_name}' not found")
    return list(corpus.vocabulary)


@click.command()
@click.option(
    "--wordlist", type=click.Path(exists=True), help="Path to wordlist file (one word per line)"
)
@click.option("--from-corpus", type=str, help="Use vocabulary from existing corpus")
@click.option(
    "--no-skip", is_flag=True, help="Don't skip words with existing Apple Dictionary entries"
)
@click.option("--limit", type=int, default=0, help="Max words to process (0 = all)")
def main(wordlist: str | None, from_corpus: str | None, no_skip: bool, limit: int) -> None:
    """Seed Apple Dictionary definitions into the database."""
    if not wordlist and not from_corpus:
        raise click.UsageError("Provide --wordlist or --from-corpus")

    async def run() -> None:
        await get_storage()

        if wordlist:
            words = Path(wordlist).read_text().splitlines()
        else:
            assert from_corpus is not None
            words = await get_corpus_vocabulary(from_corpus)

        if limit > 0:
            words = words[:limit]

        total_start = time.perf_counter()
        console.print(f"[bold]Apple Dictionary Seeding: {len(words)} words[/bold]")
        stats = await seed(words, skip_existing=not no_skip)
        total_elapsed = time.perf_counter() - total_start

        console.print(f"\n[bold green]Done in {total_elapsed:.1f}s[/bold green]")
        console.print(f"  Total:      {stats['total']}")
        console.print(f"  Processed:  {stats['processed']}")
        console.print(f"  Skipped:    {stats['skipped']}")
        console.print(f"  No def:     {stats['no_def']}")
        console.print(f"  Failed:     {stats['failed']}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
