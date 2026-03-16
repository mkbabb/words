"""Migrate WordListItem from embedded arrays on WordList to standalone WordListItemDoc collection.

For each WordList that has an embedded `words` array:
1. Read the embedded words
2. Create WordListItemDoc per item with the wordlist's ID
3. Bulk insert them
4. Recompute stats (unique_words, total_words, learning_stats)
5. $unset the `words` field from the WordList document

Usage:
    cd backend && uv run scripts/migrate_wordlist_items.py
    cd backend && uv run scripts/migrate_wordlist_items.py --dry-run
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import click
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from floridify.storage.mongodb import get_database, get_storage
from floridify.wordlist.models import WordListItemDoc
from floridify.wordlist.review import ReviewData
from floridify.wordlist.stats import LearningStats

console = Console()

BATCH_SIZE = 5000


async def migrate(dry_run: bool = False) -> None:
    """Migrate embedded WordListItem arrays to the word_list_items collection."""
    await get_storage()
    db = await get_database()

    word_lists_col = db["word_lists"]
    items_col = db["word_list_items"]

    # Find all WordList documents that still have an embedded `words` array
    cursor = word_lists_col.find(
        {"words": {"$exists": True, "$ne": []}},
        projection={"_id": 1, "name": 1, "words": 1},
    )

    total_lists = 0
    total_items = 0
    t0 = time.perf_counter()

    async for wl_doc in cursor:
        wl_id = wl_doc["_id"]
        wl_name = wl_doc.get("name", "<unnamed>")
        embedded_words = wl_doc.get("words", [])

        if not embedded_words:
            continue

        total_lists += 1
        console.print(
            f"[bold]Migrating '{wl_name}' (id={wl_id}): "
            f"{len(embedded_words):,} items[/bold]"
        )

        if dry_run:
            total_items += len(embedded_words)
            continue

        # Build WordListItemDoc raw documents for bulk insert
        docs_to_insert = []
        for item in embedded_words:
            doc = {
                "wordlist_id": wl_id,
                "word_id": item["word_id"],
                "frequency": item.get("frequency", 1),
                "selected_definition_ids": item.get("selected_definition_ids", []),
                "mastery_level": item.get("mastery_level", "default"),
                "temperature": item.get("temperature", "cold"),
                "review_data": item.get("review_data", {}),
                "last_visited": item.get("last_visited"),
                "added_date": item.get("added_date"),
                "notes": item.get("notes", ""),
                "tags": item.get("tags", []),
            }
            docs_to_insert.append(doc)

        # Bulk insert in batches
        for batch_start in range(0, len(docs_to_insert), BATCH_SIZE):
            batch = docs_to_insert[batch_start : batch_start + BATCH_SIZE]
            try:
                await items_col.insert_many(batch, ordered=False)
            except Exception as e:
                # Duplicate key errors are expected if migration is re-run
                console.print(f"  [yellow]Batch insert warning: {e}[/yellow]")

        total_items += len(docs_to_insert)

        # Recompute stats from the items we just inserted
        unique_words = len(docs_to_insert)
        total_words_count = sum(d.get("frequency", 1) for d in docs_to_insert)

        # Compute learning stats
        learning_stats = LearningStats()
        # Build lightweight WordListItem-like objects for stats computation
        from floridify.wordlist.models import WordListItem

        word_items = []
        for d in docs_to_insert:
            try:
                word_items.append(
                    WordListItem(
                        word_id=d["word_id"],
                        frequency=d.get("frequency", 1),
                        mastery_level=d.get("mastery_level", "default"),
                        temperature=d.get("temperature", "cold"),
                        review_data=ReviewData(**(d.get("review_data") or {})),
                    )
                )
            except Exception:
                # Skip items that fail validation
                pass

        learning_stats.update_from_words(word_items)

        # Update the WordList: set stats and $unset the embedded words array
        await word_lists_col.update_one(
            {"_id": wl_id},
            {
                "$set": {
                    "unique_words": unique_words,
                    "total_words": total_words_count,
                    "learning_stats": learning_stats.model_dump(),
                },
                "$unset": {"words": ""},
            },
        )

        console.print(
            f"  [green]Migrated {len(docs_to_insert):,} items, "
            f"unset embedded words[/green]"
        )

    elapsed = time.perf_counter() - t0
    action = "Would migrate" if dry_run else "Migrated"
    console.print(
        f"\n[bold green]{action} {total_items:,} items "
        f"across {total_lists} wordlists in {elapsed:.2f}s[/bold green]"
    )


@click.command()
@click.option("--dry-run", is_flag=True, default=False, help="Preview without writing")
def main(dry_run: bool) -> None:
    """Migrate embedded WordListItem arrays to standalone collection."""
    if dry_run:
        console.print("[yellow bold]DRY RUN — no changes will be made[/yellow bold]\n")
    asyncio.run(migrate(dry_run=dry_run))


if __name__ == "__main__":
    main()
