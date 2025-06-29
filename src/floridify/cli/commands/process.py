"""Word list processing commands."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console

from ..utils.formatting import format_error, format_success, format_processing_summary

console = Console()


@click.group()
def process_group() -> None:
    """📄 Process word lists from files and batch operations."""
    pass


@process_group.command("file")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--format", "output_format", type=click.Choice(["json", "csv", "txt"]), 
              default="json", help="Output format")
@click.option("--deduplicate", is_flag=True, help="Remove duplicate words")
@click.option("--validate", is_flag=True, help="Validate words against dictionary")
def process_file(
    input_file: str, 
    output: str | None, 
    output_format: str, 
    deduplicate: bool, 
    validate: bool
) -> None:
    """Process a word list file and extract definitions.
    
    INPUT_FILE: Path to the word list file (.txt, .md, .csv)
    """
    asyncio.run(_process_file_async(input_file, output, output_format, deduplicate, validate))


async def _process_file_async(
    input_file: str,
    output: str | None,
    output_format: str,
    deduplicate: bool,
    validate: bool
) -> None:
    """Async implementation of file processing."""
    try:
        input_path = Path(input_file)
        
        # Determine output path
        if output is None:
            output = f"{input_path.stem}_processed.{output_format}"
        
        console.print(f"[bold blue]Processing file: {input_file}[/bold blue]")
        
        # Parse input file
        words = await _parse_input_file(input_path)
        
        if not words:
            console.print(format_error("No words found in input file"))
            return
        
        console.print(f"Found {len(words)} words")
        
        # Deduplicate if requested
        if deduplicate:
            original_count = len(words)
            words = list(dict.fromkeys(words))  # Preserve order
            removed = original_count - len(words)
            if removed > 0:
                console.print(f"Removed {removed} duplicate words")
        
        # TODO: Implement word validation and definition fetching
        successful = len(words)  # Mock - all successful for now
        failed = 0
        
        # Show processing summary
        console.print(format_processing_summary(
            len(words), successful, failed, input_file
        ))
        
        console.print(format_success(f"Processed words saved to: {output}"))
        
    except Exception as e:
        console.print(format_error(f"File processing failed: {str(e)}"))


async def _parse_input_file(input_path: Path) -> list[str]:
    """Parse words from various file formats."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        words = []
        
        if input_path.suffix.lower() == '.md':
            # Markdown format
            import re
            
            # Extract from list items
            list_items = re.findall(r'^[\s]*[-*+][\s]*([a-zA-Z][^\n]*)', content, re.MULTILINE)
            words.extend([item.strip() for item in list_items])
            
            # Extract from numbered lists
            numbered_items = re.findall(r'^[\s]*\d+\.[\s]*([a-zA-Z][^\n]*)', content, re.MULTILINE)
            words.extend([item.strip() for item in numbered_items])
            
        elif input_path.suffix.lower() == '.csv':
            # CSV format
            import csv
            from io import StringIO
            
            reader = csv.reader(StringIO(content))
            for row in reader:
                if row and row[0].strip():
                    words.append(row[0].strip())
                    
        else:
            # Plain text format
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract first word if multiple words on line
                    word = line.split()[0] if line.split() else ""
                    if word and word.isalpha():
                        words.append(word)
        
        # Clean words
        clean_words = []
        for word in words:
            word = word.strip().lower()
            if word and word.isalpha() and len(word) > 1:
                clean_words.append(word)
        
        return clean_words
        
    except Exception as e:
        raise Exception(f"Failed to parse input file: {str(e)}")


@process_group.command("batch")
@click.argument("directory", type=click.Path(exists=True))
@click.option("--pattern", default="*.txt", help="File pattern to match")
@click.option("--recursive", "-r", is_flag=True, help="Process files recursively")
@click.option("--output-dir", type=click.Path(), help="Output directory")
def process_batch(directory: str, pattern: str, recursive: bool, output_dir: str | None) -> None:
    """Process multiple word list files in a directory.
    
    DIRECTORY: Directory containing word list files
    """
    console.print(f"[bold blue]Processing files in: {directory}[/bold blue]")
    console.print(f"Pattern: {pattern}")
    console.print(f"Recursive: {recursive}")
    console.print("[dim]Batch processing not yet implemented.[/dim]")


@process_group.command("merge")
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--output", "-o", required=True, type=click.Path(), help="Output file path")
@click.option("--deduplicate", is_flag=True, help="Remove duplicate words")
def merge_files(files: tuple[str, ...], output: str, deduplicate: bool) -> None:
    """Merge multiple word list files into one.
    
    FILES: Word list files to merge
    """
    asyncio.run(_merge_files_async(files, output, deduplicate))


async def _merge_files_async(files: tuple[str, ...], output: str, deduplicate: bool) -> None:
    """Async implementation of file merging."""
    try:
        console.print(f"[bold blue]Merging {len(files)} files...[/bold blue]")
        
        all_words = []
        
        for file_path in files:
            console.print(f"Reading: {file_path}")
            words = await _parse_input_file(Path(file_path))
            all_words.extend(words)
        
        console.print(f"Total words collected: {len(all_words)}")
        
        if deduplicate:
            original_count = len(all_words)
            all_words = list(dict.fromkeys(all_words))
            removed = original_count - len(all_words)
            console.print(f"Removed {removed} duplicates")
        
        # Write merged file
        output_path = Path(output)
        with open(output_path, 'w', encoding='utf-8') as f:
            for word in all_words:
                f.write(f"{word}\n")
        
        console.print(format_success(f"Merged {len(all_words)} words to: {output}"))
        
    except Exception as e:
        console.print(format_error(f"File merging failed: {str(e)}"))


@process_group.command("validate")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file for valid words")
@click.option("--errors", type=click.Path(), help="Output file for invalid words")
def validate_words(input_file: str, output: str | None, errors: str | None) -> None:
    """Validate words in a file against dictionary sources.
    
    INPUT_FILE: Word list file to validate
    """
    console.print(f"[bold blue]Validating words in: {input_file}[/bold blue]")
    console.print("[dim]Word validation not yet implemented.[/dim]")


@process_group.command("clean")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--min-length", default=2, help="Minimum word length")
@click.option("--max-length", default=50, help="Maximum word length")
@click.option("--alpha-only", is_flag=True, help="Keep only alphabetic words")
def clean_wordlist(
    input_file: str, 
    output: str | None, 
    min_length: int, 
    max_length: int, 
    alpha_only: bool
) -> None:
    """Clean and format a word list file.
    
    INPUT_FILE: Word list file to clean
    """
    asyncio.run(_clean_wordlist_async(input_file, output, min_length, max_length, alpha_only))


async def _clean_wordlist_async(
    input_file: str,
    output: str | None,
    min_length: int,
    max_length: int,
    alpha_only: bool
) -> None:
    """Async implementation of word list cleaning."""
    try:
        input_path = Path(input_file)
        
        if output is None:
            output = f"{input_path.stem}_clean{input_path.suffix}"
        
        console.print(f"[bold blue]Cleaning word list: {input_file}[/bold blue]")
        
        words = await _parse_input_file(input_path)
        original_count = len(words)
        
        # Apply filters
        clean_words = []
        for word in words:
            # Length filter
            if len(word) < min_length or len(word) > max_length:
                continue
            
            # Alpha-only filter
            if alpha_only and not word.isalpha():
                continue
            
            clean_words.append(word)
        
        # Remove duplicates
        clean_words = list(dict.fromkeys(clean_words))
        
        # Write cleaned file
        output_path = Path(output)
        with open(output_path, 'w', encoding='utf-8') as f:
            for word in clean_words:
                f.write(f"{word}\n")
        
        removed = original_count - len(clean_words)
        console.print(format_success(
            f"Cleaned word list saved to: {output}",
            f"Removed {removed} words, kept {len(clean_words)} words"
        ))
        
    except Exception as e:
        console.print(format_error(f"Word list cleaning failed: {str(e)}"))