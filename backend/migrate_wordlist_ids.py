#!/usr/bin/env python3
"""
Migration script to convert WordListItem string IDs to PydanticObjectIds.

This script safely migrates existing wordlist data from string-based foreign keys
to native MongoDB ObjectIds for improved performance and type safety.

Usage:
    python migrate_wordlist_ids.py [--dry-run] [--batch-size 100]
"""

import asyncio
import sys

from beanie import PydanticObjectId, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.floridify.wordlist.models import WordList

console = Console()


async def validate_object_id(id_string: str) -> PydanticObjectId | None:
    """Validate and convert string ID to ObjectId."""
    try:
        return PydanticObjectId(id_string)
    except Exception:
        return None


async def migrate_wordlist_item_ids(
    wordlist: WordList,
    dry_run: bool = False
) -> tuple[int, int]:
    """
    Migrate WordListItem IDs from strings to ObjectIds.
    
    Returns:
        Tuple of (successful_conversions, failed_conversions)
    """
    successful = 0
    failed = 0
    
    # Check each word item
    for item in wordlist.words:
        # Migrate word_id
        if isinstance(item.word_id, str):
            object_id = await validate_object_id(item.word_id)
            if object_id:
                if not dry_run:
                    item.word_id = object_id
                successful += 1
            else:
                console.print(f"[red]Failed to convert word_id: {item.word_id}[/red]")
                failed += 1
                
        # Migrate selected_definition_ids
        new_definition_ids = []
        for def_id in item.selected_definition_ids:
            if isinstance(def_id, str):
                object_id = await validate_object_id(def_id)
                if object_id:
                    new_definition_ids.append(object_id)
                    successful += 1
                else:
                    console.print(f"[red]Failed to convert definition_id: {def_id}[/red]")
                    failed += 1
            else:
                new_definition_ids.append(def_id)
                
        if not dry_run:
            item.selected_definition_ids = new_definition_ids
    
    # Save the wordlist if not dry run
    if not dry_run:
        try:
            await wordlist.save()
            console.print(f"[green]✓[/green] Migrated wordlist: {wordlist.name}")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to save wordlist {wordlist.name}: {e}")
            return 0, successful + failed
    
    return successful, failed


async def main():
    """Main migration function."""
    import argparse
    parser = argparse.ArgumentParser(description="Migrate WordList IDs to ObjectIds")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of wordlists to process per batch")
    args = parser.parse_args()
    
    console.print("[bold blue]WordList ID Migration Tool[/bold blue]")
    console.print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    
    # Initialize database connection
    console.print("Connecting to database...")
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        database = client.floridify
        
        # Initialize Beanie
        await init_beanie(
            database=database,
            document_models=[WordList]
        )
        console.print("[green]✓[/green] Database connected")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to connect to database: {e}")
        sys.exit(1)
    
    # Get total count of wordlists
    total_wordlists = await WordList.count()
    console.print(f"Found {total_wordlists} wordlists to migrate")
    
    if total_wordlists == 0:
        console.print("No wordlists found. Exiting.")
        return
    
    # Process wordlists in batches
    total_successful = 0
    total_failed = 0
    processed_wordlists = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Migrating wordlists...", total=total_wordlists)
        
        async for wordlist in WordList.find():
            # Migrate this wordlist
            successful, failed = await migrate_wordlist_item_ids(wordlist, args.dry_run)
            
            total_successful += successful
            total_failed += failed
            processed_wordlists += 1
            
            progress.update(task, advance=1)
            
            # Log progress every batch_size wordlists
            if processed_wordlists % args.batch_size == 0:
                console.print(f"Processed {processed_wordlists}/{total_wordlists} wordlists")
    
    # Summary
    console.print("\n[bold green]Migration Complete![/bold green]")
    console.print(f"Wordlists processed: {processed_wordlists}")
    console.print(f"Successful ID conversions: {total_successful}")
    console.print(f"Failed ID conversions: {total_failed}")
    
    if args.dry_run:
        console.print("\n[yellow]This was a dry run. No changes were made.[/yellow]")
        console.print("Run without --dry-run to perform the actual migration.")
    else:
        console.print("\n[green]Migration completed successfully![/green]")
        
    # Close database connection
    client.close()


if __name__ == "__main__":
    asyncio.run(main())