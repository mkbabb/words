#!/usr/bin/env python3
"""CLI for Apple Dictionary batch extraction operations."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

from src.floridify.batch.apple_dictionary_extractor import (
    AppleDictionaryBatchExtractor,
    ExtractionConfig,
    extract_common_words,
)
from src.floridify.storage.mongodb import MongoDBStorage

console = Console()


async def get_mongodb() -> MongoDBStorage | None:
    """Initialize MongoDB connection if available."""
    try:
        mongodb = MongoDBStorage()
        await mongodb.connect()
        console.print("[green]✓[/green] MongoDB connected successfully")
        return mongodb
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] MongoDB connection failed: {e}")
        console.print("[yellow]⚠[/yellow] Proceeding without MongoDB storage")
        return None


@click.group()
def cli() -> None:
    """Apple Dictionary batch extraction CLI for macOS."""
    import platform
    
    if platform.system() != 'Darwin':
        console.print(f"[red]✗[/red] Apple Dictionary extraction requires macOS")
        console.print(f"[red]✗[/red] Current platform: {platform.system()}")
        sys.exit(1)


@cli.command()
@click.option(
    "--word-list", "-w", 
    type=click.Path(exists=True, path_type=Path),
    help="Path to word list file (one word per line)"
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output JSON file for extracted definitions"
)
@click.option(
    "--batch-size", "-b",
    type=int,
    default=100,
    help="Number of words to process in each batch"
)
@click.option(
    "--concurrent", "-c",
    type=int,
    default=10,
    help="Maximum concurrent extractions"
)
@click.option(
    "--rate-limit", "-r",
    type=float,
    default=20.0,
    help="Requests per second (higher for local API)"
)
@click.option(
    "--no-mongodb",
    is_flag=True,
    help="Skip saving to MongoDB"
)
@click.option(
    "--quiet", "-q",
    is_flag=True,
    help="Suppress progress output"
)
def extract(
    word_list: Path | None,
    output: Path | None,
    batch_size: int,
    concurrent: int,
    rate_limit: float,
    no_mongodb: bool,
    quiet: bool,
) -> None:
    """Extract definitions from Apple Dictionary for a list of words."""
    
    async def _extract() -> None:
        # Initialize MongoDB if not disabled
        mongodb = None if no_mongodb else await get_mongodb()
        
        try:
            # Configure extraction
            config = ExtractionConfig(
                batch_size=batch_size,
                max_concurrent=concurrent,
                output_file=output,
                save_to_mongodb=mongodb is not None,
                rate_limit=rate_limit,
                log_progress=not quiet
            )
            
            # Create extractor
            extractor = AppleDictionaryBatchExtractor(config, mongodb)
            
            # Extract definitions
            if word_list:
                console.print(f"[blue]📖[/blue] Extracting from word list: {word_list}")
                results = await extractor.extract_from_word_list(word_list)
            else:
                console.print("[red]✗[/red] No word list provided. Use --word-list option.")
                sys.exit(1)
            
            # Summary
            console.print(f"[green]✓[/green] Extraction completed!")
            console.print(f"[green]✓[/green] Extracted {len(results)} definitions")
            
            if output:
                console.print(f"[green]✓[/green] Results saved to: {output}")
            
            if mongodb:
                console.print(f"[green]✓[/green] Definitions stored in MongoDB")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Extraction failed: {e}")
            sys.exit(1)
        finally:
            if mongodb:
                await mongodb.close()
    
    asyncio.run(_extract())


@cli.command()
@click.option(
    "--count", "-n",
    type=int,
    default=1000,
    help="Number of common words to extract"
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output JSON file for extracted definitions"
)
@click.option(
    "--no-mongodb",
    is_flag=True,
    help="Skip saving to MongoDB"
)
def extract_common(
    count: int,
    output: Path | None,
    no_mongodb: bool,
) -> None:
    """Extract definitions for the most common English words."""
    
    async def _extract_common() -> None:
        # Initialize MongoDB if not disabled
        mongodb = None if no_mongodb else await get_mongodb()
        
        try:
            console.print(f"[blue]📖[/blue] Extracting {count:,} common words...")
            
            results = await extract_common_words(
                word_count=count,
                output_file=output,
                mongodb=mongodb
            )
            
            console.print(f"[green]✓[/green] Extracted {len(results)} definitions")
            
            if output:
                console.print(f"[green]✓[/green] Results saved to: {output}")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Extraction failed: {e}")
            sys.exit(1)
        finally:
            if mongodb:
                await mongodb.close()
    
    asyncio.run(_extract_common())


@cli.command()
@click.argument("words", nargs=-1, required=True)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Output JSON file for extracted definitions"
)
@click.option(
    "--no-mongodb",
    is_flag=True,
    help="Skip saving to MongoDB"
)
def lookup(
    words: tuple[str, ...],
    output: Path | None,
    no_mongodb: bool,
) -> None:
    """Look up specific words in Apple Dictionary."""
    
    async def _lookup() -> None:
        # Initialize MongoDB if not disabled
        mongodb = None if no_mongodb else await get_mongodb()
        
        try:
            # Configure extraction
            config = ExtractionConfig(
                batch_size=len(words),
                max_concurrent=min(10, len(words)),
                output_file=output,
                save_to_mongodb=mongodb is not None,
                rate_limit=20.0,
                log_progress=True
            )
            
            # Create extractor
            extractor = AppleDictionaryBatchExtractor(config, mongodb)
            
            # Extract definitions
            console.print(f"[blue]📖[/blue] Looking up {len(words)} words...")
            results = await extractor.extract_word_list(list(words))
            
            # Display results
            for result in results:
                console.print(f"\n[bold cyan]{result.definitions[0].definition if result.definitions else 'No definition found'}[/bold cyan]")
                for i, definition in enumerate(result.definitions, 1):
                    console.print(f"  {i}. [{definition.word_type}] {definition.definition}")
            
            console.print(f"\n[green]✓[/green] Lookup completed for {len(results)} words")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Lookup failed: {e}")
            sys.exit(1)
        finally:
            if mongodb:
                await mongodb.close()
    
    asyncio.run(_lookup())


@cli.command()
def info() -> None:
    """Display information about Apple Dictionary service."""
    
    async def _info() -> None:
        try:
            from src.floridify.connectors.apple_dictionary import AppleDictionaryConnector
            
            connector = AppleDictionaryConnector()
            service_info = connector.get_service_info()
            
            console.print("\n[bold]Apple Dictionary Service Information[/bold]")
            console.print("=" * 50)
            
            for key, value in service_info.items():
                if key == "is_available":
                    status = "[green]✓ Available[/green]" if value else "[red]✗ Not Available[/red]"
                    console.print(f"{key.replace('_', ' ').title()}: {status}")
                elif isinstance(value, bool):
                    status = "[green]✓[/green]" if value else "[red]✗[/red]"
                    console.print(f"{key.replace('_', ' ').title()}: {status}")
                else:
                    console.print(f"{key.replace('_', ' ').title()}: {value}")
            
            console.print()
            
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to get service info: {e}")
            sys.exit(1)
    
    asyncio.run(_info())


@cli.command()
@click.option(
    "--input-file", "-i",
    type=click.Path(exists=True, path_type=Path),
    help="Input word list file"
)
@click.option(
    "--output-file", "-o", 
    type=click.Path(path_type=Path),
    help="Output word list file"
)
def create_wordlist(
    input_file: Path | None,
    output_file: Path | None,
) -> None:
    """Create a word list from various sources for batch extraction."""
    
    # For now, create a sample word list
    sample_words = [
        "apple", "banana", "cherry", "date", "elderberry",
        "fig", "grape", "honeydew", "kiwi", "lemon",
        "mango", "orange", "papaya", "quince", "raspberry",
        "strawberry", "tangerine", "ugli", "vanilla", "watermelon",
        "house", "car", "computer", "phone", "book",
        "chair", "table", "window", "door", "light",
        "beautiful", "happy", "sad", "angry", "peaceful",
        "run", "walk", "jump", "swim", "fly",
        "quickly", "slowly", "carefully", "gently", "loudly"
    ]
    
    output = output_file or Path("sample_wordlist.txt")
    
    try:
        with open(output, 'w', encoding='utf-8') as f:
            for word in sample_words:
                f.write(f"{word}\n")
        
        console.print(f"[green]✓[/green] Created word list with {len(sample_words)} words: {output}")
        console.print(f"[blue]💡[/blue] Use: python apple_dict_cli.py extract --word-list {output}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to create word list: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()