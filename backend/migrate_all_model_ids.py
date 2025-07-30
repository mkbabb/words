#!/usr/bin/env python3
"""
Comprehensive migration script to convert ALL string IDs to PydanticObjectIds.

This script migrates the entire database to use native ObjectIds for all foreign key
relationships, eliminating string-to-ObjectId conversion overhead system-wide.

Updated Models:
- Definition (word_id, example_ids, image_ids, provider_data_id)
- Example (definition_id)  
- Pronunciation (word_id, audio_file_ids)
- Fact (word_id)
- ProviderData (word_id, definition_ids, pronunciation_id)
- SynthesizedDictionaryEntry (word_id, pronunciation_id, definition_ids, fact_ids, image_ids, source_provider_data_ids)
- WordRelationship (from_word_id, to_word_id)
- PhrasalExpression (base_word_id, definition_ids)
- WordListItem (already completed in previous migration)

Usage:
    python migrate_all_model_ids.py [--dry-run] [--batch-size 100] [--model MODEL_NAME]
"""

import asyncio
import sys
from typing import Any, Dict, List, Type

from beanie import Document, PydanticObjectId, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

# Import all models that need migration
from src.floridify.models.models import (
    Definition,
    Example, 
    Pronunciation,
    Fact,
    ProviderData,
    SynthesizedDictionaryEntry,
)
from src.floridify.models.relationships import WordRelationship
from src.floridify.models.phrasal import PhrasalExpression
from src.floridify.wordlist.models import WordList

console = Console()


class MigrationStats:
    """Track migration statistics."""
    
    def __init__(self):
        self.total_documents = 0
        self.successful_conversions = 0
        self.failed_conversions = 0
        self.skipped_documents = 0
        self.models_migrated = {}
    
    def add_model_stats(self, model_name: str, docs: int, success: int, failed: int, skipped: int):
        """Add statistics for a model."""
        self.models_migrated[model_name] = {
            'documents': docs,
            'successful': success,
            'failed': failed,
            'skipped': skipped
        }
        self.total_documents += docs
        self.successful_conversions += success
        self.failed_conversions += failed
        self.skipped_documents += skipped


async def convert_string_to_objectid(id_string: str | None) -> PydanticObjectId | None:
    """Convert string ID to ObjectId with validation."""
    if not id_string:
        return None
    try:
        return PydanticObjectId(id_string)
    except Exception as e:
        console.print(f"[red]Failed to convert ID '{id_string}': {e}[/red]")
        return None


async def convert_string_list_to_objectids(id_list: List[str]) -> List[PydanticObjectId]:
    """Convert list of string IDs to ObjectIds."""
    result = []
    for id_string in id_list:
        if isinstance(id_string, str):
            object_id = await convert_string_to_objectid(id_string)
            if object_id:
                result.append(object_id)
        else:
            # Already an ObjectId
            result.append(id_string)
    return result


async def migrate_definition_model(dry_run: bool = False) -> tuple[int, int, int, int]:
    """Migrate Definition model IDs."""
    console.print("[blue]Migrating Definition model...[/blue]")
    
    total_docs = 0
    successful = 0
    failed = 0
    skipped = 0
    
    async for definition in Definition.find():
        total_docs += 1
        needs_update = False
        
        # Migrate word_id
        if isinstance(definition.word_id, str):
            object_id = await convert_string_to_objectid(definition.word_id)
            if object_id:
                if not dry_run:
                    definition.word_id = object_id
                needs_update = True
                successful += 1
            else:
                failed += 1
                
        # Migrate example_ids
        if definition.example_ids and isinstance(definition.example_ids[0], str):
            new_ids = await convert_string_list_to_objectids(definition.example_ids)
            if not dry_run:
                definition.example_ids = new_ids
            needs_update = True
            successful += len(new_ids)
            
        # Migrate image_ids
        if definition.image_ids and isinstance(definition.image_ids[0], str):
            new_ids = await convert_string_list_to_objectids(definition.image_ids)
            if not dry_run:
                definition.image_ids = new_ids
            needs_update = True
            successful += len(new_ids)
            
        # Migrate provider_data_id
        if isinstance(definition.provider_data_id, str):
            object_id = await convert_string_to_objectid(definition.provider_data_id)
            if object_id:
                if not dry_run:
                    definition.provider_data_id = object_id
                needs_update = True
                successful += 1
            else:
                failed += 1
        
        # Save if needed
        if needs_update and not dry_run:
            try:
                await definition.save()
            except Exception as e:
                console.print(f"[red]Failed to save Definition {definition.id}: {e}[/red]")
                failed += 1
        elif not needs_update:
            skipped += 1
            
    return total_docs, successful, failed, skipped


async def migrate_example_model(dry_run: bool = False) -> tuple[int, int, int, int]:
    """Migrate Example model IDs."""
    console.print("[blue]Migrating Example model...[/blue]")
    
    total_docs = 0
    successful = 0
    failed = 0
    skipped = 0
    
    async for example in Example.find():
        total_docs += 1
        
        # Migrate definition_id
        if isinstance(example.definition_id, str):
            object_id = await convert_string_to_objectid(example.definition_id)
            if object_id:
                if not dry_run:
                    example.definition_id = object_id
                    try:
                        await example.save()
                    except Exception as e:
                        console.print(f"[red]Failed to save Example {example.id}: {e}[/red]")
                        failed += 1
                        continue
                successful += 1
            else:
                failed += 1
        else:
            skipped += 1
            
    return total_docs, successful, failed, skipped


async def migrate_pronunciation_model(dry_run: bool = False) -> tuple[int, int, int, int]:
    """Migrate Pronunciation model IDs."""
    console.print("[blue]Migrating Pronunciation model...[/blue]")
    
    total_docs = 0
    successful = 0
    failed = 0
    skipped = 0
    
    async for pronunciation in Pronunciation.find():
        total_docs += 1
        needs_update = False
        
        # Migrate word_id
        if isinstance(pronunciation.word_id, str):
            object_id = await convert_string_to_objectid(pronunciation.word_id)
            if object_id:
                if not dry_run:
                    pronunciation.word_id = object_id
                needs_update = True
                successful += 1
            else:
                failed += 1
                
        # Migrate audio_file_ids
        if pronunciation.audio_file_ids and isinstance(pronunciation.audio_file_ids[0], str):
            new_ids = await convert_string_list_to_objectids(pronunciation.audio_file_ids)
            if not dry_run:
                pronunciation.audio_file_ids = new_ids
            needs_update = True
            successful += len(new_ids)
        
        # Save if needed
        if needs_update and not dry_run:
            try:
                await pronunciation.save()
            except Exception as e:
                console.print(f"[red]Failed to save Pronunciation {pronunciation.id}: {e}[/red]")
                failed += 1
        elif not needs_update:
            skipped += 1
            
    return total_docs, successful, failed, skipped


async def migrate_fact_model(dry_run: bool = False) -> tuple[int, int, int, int]:
    """Migrate Fact model IDs."""
    console.print("[blue]Migrating Fact model...[/blue]")
    
    total_docs = 0
    successful = 0
    failed = 0
    skipped = 0
    
    async for fact in Fact.find():
        total_docs += 1
        
        # Migrate word_id
        if isinstance(fact.word_id, str):
            object_id = await convert_string_to_objectid(fact.word_id)
            if object_id:
                if not dry_run:
                    fact.word_id = object_id
                    try:
                        await fact.save()
                    except Exception as e:
                        console.print(f"[red]Failed to save Fact {fact.id}: {e}[/red]")
                        failed += 1
                        continue
                successful += 1
            else:
                failed += 1
        else:
            skipped += 1
            
    return total_docs, successful, failed, skipped


async def migrate_provider_data_model(dry_run: bool = False) -> tuple[int, int, int, int]:
    """Migrate ProviderData model IDs."""
    console.print("[blue]Migrating ProviderData model...[/blue]")
    
    total_docs = 0
    successful = 0
    failed = 0
    skipped = 0
    
    async for provider_data in ProviderData.find():
        total_docs += 1
        needs_update = False
        
        # Migrate word_id
        if isinstance(provider_data.word_id, str):
            object_id = await convert_string_to_objectid(provider_data.word_id)
            if object_id:
                if not dry_run:
                    provider_data.word_id = object_id
                needs_update = True
                successful += 1
            else:
                failed += 1
                
        # Migrate definition_ids
        if provider_data.definition_ids and isinstance(provider_data.definition_ids[0], str):
            new_ids = await convert_string_list_to_objectids(provider_data.definition_ids)
            if not dry_run:
                provider_data.definition_ids = new_ids
            needs_update = True
            successful += len(new_ids)
            
        # Migrate pronunciation_id
        if isinstance(provider_data.pronunciation_id, str):
            object_id = await convert_string_to_objectid(provider_data.pronunciation_id)
            if object_id:
                if not dry_run:
                    provider_data.pronunciation_id = object_id
                needs_update = True
                successful += 1
            else:
                failed += 1
        
        # Save if needed
        if needs_update and not dry_run:
            try:
                await provider_data.save()
            except Exception as e:
                console.print(f"[red]Failed to save ProviderData {provider_data.id}: {e}[/red]")
                failed += 1
        elif not needs_update:
            skipped += 1
            
    return total_docs, successful, failed, skipped


async def migrate_synthesized_entry_model(dry_run: bool = False) -> tuple[int, int, int, int]:
    """Migrate SynthesizedDictionaryEntry model IDs."""
    console.print("[blue]Migrating SynthesizedDictionaryEntry model...[/blue]")
    
    total_docs = 0
    successful = 0
    failed = 0
    skipped = 0
    
    async for entry in SynthesizedDictionaryEntry.find():
        total_docs += 1
        needs_update = False
        
        # Migrate word_id
        if isinstance(entry.word_id, str):
            object_id = await convert_string_to_objectid(entry.word_id)
            if object_id:
                if not dry_run:
                    entry.word_id = object_id
                needs_update = True
                successful += 1
            else:
                failed += 1
                
        # Migrate pronunciation_id
        if isinstance(entry.pronunciation_id, str):
            object_id = await convert_string_to_objectid(entry.pronunciation_id)
            if object_id:
                if not dry_run:
                    entry.pronunciation_id = object_id
                needs_update = True
                successful += 1
            else:
                failed += 1
                
        # Migrate definition_ids
        if entry.definition_ids and isinstance(entry.definition_ids[0], str):
            new_ids = await convert_string_list_to_objectids(entry.definition_ids)
            if not dry_run:
                entry.definition_ids = new_ids
            needs_update = True
            successful += len(new_ids)
            
        # Migrate fact_ids
        if entry.fact_ids and isinstance(entry.fact_ids[0], str):
            new_ids = await convert_string_list_to_objectids(entry.fact_ids)
            if not dry_run:
                entry.fact_ids = new_ids
            needs_update = True
            successful += len(new_ids)
            
        # Migrate image_ids
        if entry.image_ids and isinstance(entry.image_ids[0], str):
            new_ids = await convert_string_list_to_objectids(entry.image_ids)
            if not dry_run:
                entry.image_ids = new_ids
            needs_update = True
            successful += len(new_ids)
            
        # Migrate source_provider_data_ids
        if entry.source_provider_data_ids and isinstance(entry.source_provider_data_ids[0], str):
            new_ids = await convert_string_list_to_objectids(entry.source_provider_data_ids)
            if not dry_run:
                entry.source_provider_data_ids = new_ids
            needs_update = True
            successful += len(new_ids)
        
        # Save if needed
        if needs_update and not dry_run:
            try:
                await entry.save()
            except Exception as e:
                console.print(f"[red]Failed to save SynthesizedDictionaryEntry {entry.id}: {e}[/red]")
                failed += 1
        elif not needs_update:
            skipped += 1
            
    return total_docs, successful, failed, skipped


async def migrate_word_relationship_model(dry_run: bool = False) -> tuple[int, int, int, int]:
    """Migrate WordRelationship model IDs."""
    console.print("[blue]Migrating WordRelationship model...[/blue]")
    
    total_docs = 0
    successful = 0
    failed = 0
    skipped = 0
    
    async for relationship in WordRelationship.find():
        total_docs += 1
        needs_update = False
        
        # Migrate from_word_id
        if isinstance(relationship.from_word_id, str):
            object_id = await convert_string_to_objectid(relationship.from_word_id)
            if object_id:
                if not dry_run:
                    relationship.from_word_id = object_id
                needs_update = True
                successful += 1
            else:
                failed += 1
                
        # Migrate to_word_id
        if isinstance(relationship.to_word_id, str):
            object_id = await convert_string_to_objectid(relationship.to_word_id)
            if object_id:
                if not dry_run:
                    relationship.to_word_id = object_id
                needs_update = True
                successful += 1
            else:
                failed += 1
        
        # Save if needed
        if needs_update and not dry_run:
            try:
                await relationship.save()
            except Exception as e:
                console.print(f"[red]Failed to save WordRelationship {relationship.id}: {e}[/red]")
                failed += 1
        elif not needs_update:
            skipped += 1
            
    return total_docs, successful, failed, skipped


async def migrate_phrasal_expression_model(dry_run: bool = False) -> tuple[int, int, int, int]:
    """Migrate PhrasalExpression model IDs."""
    console.print("[blue]Migrating PhrasalExpression model...[/blue]")
    
    total_docs = 0
    successful = 0
    failed = 0
    skipped = 0
    
    async for expression in PhrasalExpression.find():
        total_docs += 1
        needs_update = False
        
        # Migrate base_word_id
        if isinstance(expression.base_word_id, str):
            object_id = await convert_string_to_objectid(expression.base_word_id)
            if object_id:
                if not dry_run:
                    expression.base_word_id = object_id
                needs_update = True
                successful += 1
            else:
                failed += 1
                
        # Migrate definition_ids
        if expression.definition_ids and isinstance(expression.definition_ids[0], str):
            new_ids = await convert_string_list_to_objectids(expression.definition_ids)
            if not dry_run:
                expression.definition_ids = new_ids
            needs_update = True
            successful += len(new_ids)
        
        # Save if needed
        if needs_update and not dry_run:
            try:
                await expression.save()
            except Exception as e:
                console.print(f"[red]Failed to save PhrasalExpression {expression.id}: {e}[/red]")
                failed += 1
        elif not needs_update:
            skipped += 1
            
    return total_docs, successful, failed, skipped


async def main():
    """Main migration function."""
    import argparse
    parser = argparse.ArgumentParser(description="Migrate ALL model IDs to ObjectIds")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of documents to process per batch")
    parser.add_argument("--model", type=str, help="Migrate only specific model (definition, example, pronunciation, etc.)")
    args = parser.parse_args()
    
    console.print("[bold blue]Comprehensive Model ID Migration Tool[/bold blue]")
    console.print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    
    # Initialize database connection
    console.print("Connecting to database...")
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        database = client.floridify
        
        # Initialize Beanie with all models
        await init_beanie(
            database=database,
            document_models=[
                Definition, Example, Pronunciation, Fact, ProviderData,
                SynthesizedDictionaryEntry, WordRelationship, PhrasalExpression,
                WordList
            ]
        )
        console.print("[green]✓[/green] Database connected")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to connect to database: {e}")
        sys.exit(1)
    
    # Define migration functions
    migration_functions = {
        'definition': migrate_definition_model,
        'example': migrate_example_model,
        'pronunciation': migrate_pronunciation_model,
        'fact': migrate_fact_model,
        'provider_data': migrate_provider_data_model,
        'synthesized_entry': migrate_synthesized_entry_model,
        'word_relationship': migrate_word_relationship_model,
        'phrasal_expression': migrate_phrasal_expression_model,
    }
    
    # Filter by specific model if requested
    if args.model:
        if args.model not in migration_functions:
            console.print(f"[red]Unknown model: {args.model}[/red]")
            console.print(f"Available models: {', '.join(migration_functions.keys())}")
            sys.exit(1)
        migration_functions = {args.model: migration_functions[args.model]}
    
    # Track overall statistics
    stats = MigrationStats()
    
    # Run migrations
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        main_task = progress.add_task("Migrating models...", total=len(migration_functions))
        
        for model_name, migration_func in migration_functions.items():
            # Run migration for this model
            docs, success, failed, skipped = await migration_func(args.dry_run)
            stats.add_model_stats(model_name, docs, success, failed, skipped)
            
            console.print(f"[green]✓[/green] {model_name}: {docs} docs, {success} successful, {failed} failed, {skipped} skipped")
            progress.update(main_task, advance=1)
    
    # Display final statistics
    console.print("\n[bold green]Migration Complete![/bold green]")
    
    # Create summary table
    table = Table(title="Migration Summary")
    table.add_column("Model", style="cyan")
    table.add_column("Documents", justify="right")
    table.add_column("Successful", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Skipped", justify="right", style="yellow")
    
    for model_name, model_stats in stats.models_migrated.items():
        table.add_row(
            model_name.replace('_', ' ').title(),
            str(model_stats['documents']),
            str(model_stats['successful']),
            str(model_stats['failed']),
            str(model_stats['skipped'])
        )
    
    # Add totals row
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{stats.total_documents}[/bold]",
        f"[bold green]{stats.successful_conversions}[/bold green]",
        f"[bold red]{stats.failed_conversions}[/bold red]", 
        f"[bold yellow]{stats.skipped_documents}[/bold yellow]"
    )
    
    console.print(table)
    
    if args.dry_run:
        console.print("\n[yellow]This was a dry run. No changes were made.[/yellow]")
        console.print("Run without --dry-run to perform the actual migration.")
    else:
        console.print("\n[green]All model migrations completed successfully![/green]")
        
    # Close database connection
    client.close()


if __name__ == "__main__":
    asyncio.run(main())