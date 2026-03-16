"""Generate a pathological 50k-word test wordlist for performance testing.

Usage:
    uv run scripts/generate_test_wordlist.py
    uv run scripts/generate_test_wordlist.py --count 100000
    uv run scripts/generate_test_wordlist.py --name "my-perf-test" --count 50000
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from floridify.models.dictionary import Word
from floridify.storage.mongodb import get_storage
from floridify.wordlist.models import WordList, WordListItemDoc
from floridify.wordlist.utils import generate_wordlist_hash

console = Console()

BATCH_SIZE = 5000


async def generate_wordlist(
    name: str,
    count: int,
    description: str,
    is_public: bool,
    tags: list[str],
) -> WordList:
    """Create a test wordlist with `count` generated words."""
    await get_storage()

    # Generate synthetic word texts
    word_texts = [f"test-{i:05d}" for i in range(1, count + 1)]
    hash_id = generate_wordlist_hash(word_texts)

    # Create real Word documents in batches
    console.print(
        f"[bold]Creating {count:,} Word documents in batches of {BATCH_SIZE:,}...[/bold]"
    )
    t0 = time.perf_counter()

    all_word_docs: list[Word] = []
    for batch_start in range(0, count, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, count)
        batch_texts = word_texts[batch_start:batch_end]
        word_docs = [Word(text=text) for text in batch_texts]
        inserted = await Word.insert_many(word_docs)
        all_word_docs.extend(inserted)
        console.print(f"  Inserted Word docs {batch_end:,}/{count:,}")

    t1 = time.perf_counter()
    console.print(f"  Word documents created in {t1 - t0:.2f}s")

    # Create the WordList document
    wordlist = WordList(
        name=name,
        description=description,
        hash_id=hash_id,
        total_words=count,
        unique_words=count,
        tags=tags,
        is_public=is_public,
    )

    console.print("[bold]Saving WordList document...[/bold]")
    t2 = time.perf_counter()
    await wordlist.insert()
    t3 = time.perf_counter()
    console.print(f"  Saved WordList in {t3 - t2:.2f}s (id: {wordlist.id})")

    # Bulk-insert WordListItemDoc objects in batches using real Word IDs
    console.print(
        f"[bold]Generating and inserting {count:,} items in batches of {BATCH_SIZE:,}...[/bold]"
    )
    t4 = time.perf_counter()

    for batch_start in range(0, count, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, count)
        items = [
            WordListItemDoc(
                word_id=all_word_docs[i].id,
                wordlist_id=wordlist.id,
            )
            for i in range(batch_start, batch_end)
        ]
        await WordListItemDoc.insert_many(items)
        console.print(f"  Inserted items {batch_end:,}/{count:,}")

    t5 = time.perf_counter()
    console.print(f"  Bulk insert completed in {t5 - t4:.2f}s")

    console.print(
        f"\n[green bold]Created wordlist '{name}' with {count:,} words[/green bold]"
    )
    console.print(f"  ID: {wordlist.id}")
    console.print(f"  Hash: {hash_id}")
    console.print(f"  Total time: {t5 - t0:.2f}s")

    return wordlist


@click.command()
@click.option("--name", default="perf-test-50k", help="Wordlist name")
@click.option("--count", default=50_000, type=int, help="Number of words to generate")
@click.option("--description", default=None, help="Wordlist description")
@click.option("--public/--private", default=True, help="Public visibility")
def main(name: str, count: int, description: str | None, public: bool) -> None:
    """Generate a pathological test wordlist for performance testing."""
    if description is None:
        description = (
            f"Pathological test wordlist with {count:,} generated words "
            "for performance testing"
        )

    asyncio.run(
        generate_wordlist(
            name=name,
            count=count,
            description=description,
            is_public=public,
            tags=["test", "performance"],
        )
    )


if __name__ == "__main__":
    main()
