#!/usr/bin/env python3
"""Check semantic index status for SOWPODS English corpus."""

import asyncio

from rich.console import Console
from rich.table import Table

from floridify.caching.models import VersionConfig
from floridify.corpus.core import Corpus
from floridify.search.semantic.constants import GTE_QWEN2_MODEL
from floridify.search.semantic.models import SemanticIndex
from floridify.storage.mongodb import get_storage

console = Console()


async def check_semantic_index():
    """Check semantic index status for SOWPODS corpus."""
    console.print("\n[bold cyan]Checking Semantic Index Status[/bold cyan]\n")

    # Initialize database
    await get_storage()

    # Try to get the SOWPODS corpus
    corpus_name = "english_language_master_sowpods_scrabble_words"
    corpus = await Corpus.get(corpus_name=corpus_name, config=VersionConfig())

    if not corpus:
        console.print(f"[bold red]✗[/bold red] Corpus not found: {corpus_name}\n")
        return

    # Display corpus info
    corpus_table = Table(title="Corpus Information")
    corpus_table.add_column("Property", style="cyan")
    corpus_table.add_column("Value", style="green")

    corpus_table.add_row("Name", corpus.corpus_name)
    corpus_table.add_row("Vocabulary Size", f"{corpus.unique_word_count:,}")
    corpus_table.add_row("Vocabulary Hash", corpus.vocabulary_hash[:32] + "...")
    corpus_table.add_row("Corpus ID", str(corpus.corpus_id))
    corpus_table.add_row("Language", corpus.language.value)

    console.print(corpus_table)
    console.print()

    # Check semantic index
    console.print(f"[bold cyan]Checking Semantic Index for {GTE_QWEN2_MODEL}[/bold cyan]\n")

    index = await SemanticIndex.get(
        corpus_name=corpus.corpus_name, model_name=GTE_QWEN2_MODEL, config=VersionConfig()
    )

    if not index:
        console.print(f"[bold red]✗[/bold red] No semantic index found\n")
        console.print("[yellow]To build the semantic index, run:[/yellow]")
        console.print(
            f"  [bold]python scripts/build_semantic_index.py {corpus.corpus_name}[/bold]\n"
        )
        return

    # Display index info
    index_table = Table(title="Semantic Index Status")
    index_table.add_column("Property", style="cyan")
    index_table.add_column("Value", style="green")

    index_table.add_row("Model", index.model_name)
    index_table.add_row("Index Type", index.index_type)
    index_table.add_row("Embeddings", f"{index.num_embeddings:,}")
    index_table.add_row("Dimension", str(index.embedding_dimension))
    index_table.add_row("Memory Usage", f"{index.memory_usage_mb:.2f} MB")
    index_table.add_row("Build Time", f"{index.build_time_seconds:.2f}s")
    index_table.add_row("Device", index.device)
    index_table.add_row("Batch Size", str(index.batch_size))
    index_table.add_row("Has Index Data", "✓" if index.index_data else "✗")
    index_table.add_row("Has Embeddings", "✓" if index.embeddings else "✗")
    index_table.add_row("Vocabulary Hash", index.vocabulary_hash[:32] + "...")

    console.print(index_table)
    console.print()

    # Calculate compression ratio
    if index.embedding_dimension and index.num_embeddings:
        base_memory_mb = (index.num_embeddings * index.embedding_dimension * 4) / (1024 * 1024)
        compression_ratio = (index.memory_usage_mb / base_memory_mb) * 100 if base_memory_mb > 0 else 0
        console.print(
            f"[bold]Compression:[/bold] {compression_ratio:.1f}% of baseline "
            f"({base_memory_mb:.2f} MB → {index.memory_usage_mb:.2f} MB)\n"
        )

    # Index configuration details
    if index.index_params:
        params_table = Table(title="Index Parameters")
        params_table.add_column("Parameter", style="cyan")
        params_table.add_column("Value", style="green")

        for key, value in index.index_params.items():
            params_table.add_row(key, str(value))

        console.print(params_table)
        console.print()

    # Performance metrics
    if index.embeddings_per_second > 0:
        console.print(
            f"[bold]Performance:[/bold] {index.embeddings_per_second:.0f} embeddings/second\n"
        )

    console.print("[bold green]✓[/bold green] Semantic index is ready for use\n")


if __name__ == "__main__":
    asyncio.run(check_semantic_index())
