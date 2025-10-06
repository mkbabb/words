#!/usr/bin/env python3
"""Build semantic index for a corpus."""

import asyncio
import sys
import time

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from floridify.caching.models import VersionConfig
from floridify.corpus.core import Corpus
from floridify.search.semantic.constants import GTE_QWEN2_MODEL
from floridify.search.semantic.core import SemanticSearch
from floridify.search.semantic.models import SemanticIndex
from floridify.storage.mongodb import get_storage

console = Console()


async def build_semantic_index(corpus_name: str, model_name: str = GTE_QWEN2_MODEL):
    """Build semantic index for a corpus.

    Args:
        corpus_name: Name of the corpus to build index for
        model_name: Embedding model to use (default: GTE-Qwen2-1.5B-instruct)

    """
    console.print(f"\n[bold cyan]Building Semantic Index[/bold cyan]\n")
    console.print(f"Corpus: [bold]{corpus_name}[/bold]")
    console.print(f"Model: [bold]{model_name}[/bold]\n")

    # Initialize database
    await get_storage()

    # Get the corpus
    corpus = await Corpus.get(corpus_name=corpus_name, config=VersionConfig())

    if not corpus:
        console.print(f"[bold red]✗[/bold red] Corpus not found: {corpus_name}\n")
        return

    # Display corpus info
    console.print(f"[bold]Corpus Information:[/bold]")
    console.print(f"  Vocabulary Size: {corpus.unique_word_count:,}")
    console.print(f"  Lemmatized Size: {len(corpus.lemmatized_vocabulary):,}")
    console.print(f"  Corpus ID: {corpus.corpus_id}\n")

    # Build semantic search with progress indicator
    start_time = time.perf_counter()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Building semantic index...", total=None)

        # Create semantic search (this will trigger index building)
        semantic_search = await SemanticSearch.from_corpus(
            corpus=corpus, model_name=model_name, config=VersionConfig()
        )

        progress.update(task, completed=True)

    elapsed = time.perf_counter() - start_time

    # Get the built index
    index = await SemanticIndex.get(
        corpus_name=corpus.corpus_name, model_name=model_name, config=VersionConfig()
    )

    if not index or not index.embeddings:
        console.print(f"\n[bold red]✗[/bold red] Failed to build semantic index\n")
        return

    # Display results
    console.print(f"\n[bold green]✓[/bold green] Semantic index built successfully!\n")

    results_table = Table(title="Build Results")
    results_table.add_column("Metric", style="cyan")
    results_table.add_column("Value", style="green")

    results_table.add_row("Total Time", f"{elapsed:.2f}s")
    results_table.add_row("Embeddings Created", f"{index.num_embeddings:,}")
    results_table.add_row("Embedding Dimension", str(index.embedding_dimension))
    results_table.add_row("Index Type", index.index_type)
    results_table.add_row("Memory Usage", f"{index.memory_usage_mb:.2f} MB")
    results_table.add_row("Device", index.device)
    results_table.add_row("Embeddings/sec", f"{index.embeddings_per_second:.0f}")

    console.print(results_table)
    console.print()

    # Calculate compression ratio
    if index.embedding_dimension and index.num_embeddings:
        base_memory_mb = (index.num_embeddings * index.embedding_dimension * 4) / (1024 * 1024)
        compression_ratio = (index.memory_usage_mb / base_memory_mb) * 100 if base_memory_mb > 0 else 0
        console.print(
            f"[bold]Compression:[/bold] {compression_ratio:.1f}% of baseline "
            f"({base_memory_mb:.2f} MB → {index.memory_usage_mb:.2f} MB)\n"
        )

    # Test the index with a sample query
    console.print("[bold cyan]Testing Index[/bold cyan]\n")

    test_query = "hello"
    results = await semantic_search.search(test_query, max_results=5, min_score=0.5)

    if results:
        test_table = Table(title=f'Test Query: "{test_query}"')
        test_table.add_column("Rank", style="cyan")
        test_table.add_column("Word", style="green")
        test_table.add_column("Score", style="yellow")

        for i, result in enumerate(results, 1):
            test_table.add_row(str(i), result.word, f"{result.score:.4f}")

        console.print(test_table)
        console.print()
    else:
        console.print("[yellow]No results found for test query[/yellow]\n")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        console.print("\n[bold red]Error:[/bold red] Corpus name required\n")
        console.print("Usage: python scripts/build_semantic_index.py <corpus_name> [model_name]\n")
        console.print("Examples:")
        console.print(
            "  python scripts/build_semantic_index.py english_language_master_sowpods_scrabble_words"
        )
        console.print(
            '  python scripts/build_semantic_index.py my_corpus "BAAI/bge-m3"\n'
        )
        sys.exit(1)

    corpus_name = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else GTE_QWEN2_MODEL

    await build_semantic_index(corpus_name, model_name)


if __name__ == "__main__":
    asyncio.run(main())
