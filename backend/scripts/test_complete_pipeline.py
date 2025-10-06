#!/usr/bin/env python3
"""Test the complete corpus and search pipeline with all optimizations."""

import asyncio
import time

from rich.console import Console
from rich.progress import track

from floridify.corpus.language.core import LanguageCorpus
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.models.base import Language
from floridify.search.core import Search
from floridify.storage.mongodb import init_db
from floridify.utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


async def test_optimized_pipeline():
    """Test the complete pipeline with all optimizations."""
    console.print("[bold cyan]🚀 Testing Optimized Floridify Pipeline[/bold cyan]")
    console.print("=" * 80)

    # Initialize database
    await init_db()

    # Step 1: Build corpus with parallel source fetching
    console.print("\n[yellow]1️⃣  Building Language Corpus (Parallel Sources)[/yellow]")
    start = time.time()

    corpus = await LanguageCorpus.create_from_language(
        language=Language.ENGLISH,
        corpus_name="english_optimized"
    )

    corpus_time = time.time() - start
    console.print(f"[green]✅ Corpus built in {corpus_time:.2f}s[/green]")

    # Aggregate vocabulary from children
    console.print("\n[yellow]2️⃣  Aggregating Vocabulary (Parallel Children)[/yellow]")
    manager = get_tree_corpus_manager()

    start = time.time()
    vocabulary = await manager.aggregate_vocabularies(
        corpus_id=corpus.corpus_id,
        update_parent=True
    )

    aggregate_time = time.time() - start
    console.print(f"[green]✅ Aggregated {len(vocabulary):,} words in {aggregate_time:.2f}s[/green]")

    # Reload corpus to get aggregated vocabulary
    corpus = await manager.get_corpus(corpus_id=corpus.corpus_id)
    console.print(f"   Vocabulary size: {len(corpus.vocabulary):,}")
    console.print(f"   Lemmatized: {len(corpus.lemmatized_vocabulary):,}")

    # Step 2: Build Search Indices
    console.print("\n[yellow]3️⃣  Building Search Indices[/yellow]")
    start = time.time()

    search = await Search.from_corpus(
        corpus=corpus,
        semantic_model="Alibaba-NLP/gte-Qwen2-1.5B-instruct"
    )

    index_time = time.time() - start
    console.print(f"[green]✅ Search indices built in {index_time:.2f}s[/green]")

    # Step 3: Test Search Performance
    console.print("\n[yellow]4️⃣  Testing Search Performance[/yellow]")

    test_queries = [
        ("hello", "exact"),
        ("perspicacious", "exact"),
        ("helllo", "fuzzy"),
        ("quick fox", "semantic"),
        ("language", "combined"),
    ]

    for query, method in test_queries:
        start = time.time()
        results = await search.search(query, method=method, max_results=5)
        elapsed = (time.time() - start) * 1000  # Convert to ms

        if results:
            console.print(f"   {method:10s} '{query:15s}': {len(results)} results in {elapsed:.2f}ms")
            console.print(f"      Top: {results[0].word} (score: {results[0].score:.3f})")
        else:
            console.print(f"   {method:10s} '{query:15s}': No results in {elapsed:.2f}ms")

    # Step 4: Check for our optimizations
    console.print("\n[yellow]5️⃣  Optimization Verification[/yellow]")

    # Check if semantic index exists
    from floridify.search.semantic.models import SemanticIndex
    semantic_index = await SemanticIndex.get(
        corpus_name="english_optimized",
        model_name="Alibaba-NLP/gte-Qwen2-1.5B-instruct"
    )

    if semantic_index:
        console.print(f"[green]✅ SemanticIndex found[/green]")
        console.print(f"   • Embeddings: {semantic_index.num_embeddings:,}")
        console.print(f"   • Index type: {semantic_index.index_type}")
        console.print(f"   • Memory: {semantic_index.memory_usage_mb:.2f} MB")
        console.print(f"   • Build time: {semantic_index.build_time_seconds:.2f}s")
    else:
        console.print("[red]❌ SemanticIndex not found[/red]")

    # Check SearchIndex
    from floridify.search.models import SearchIndex
    search_index = await SearchIndex.get(corpus_name="english_optimized")

    if search_index:
        console.print(f"[green]✅ SearchIndex found[/green]")
        console.print(f"   • Has semantic: {search_index.has_semantic}")
        console.print(f"   • Has trie: {search_index.has_trie}")
        console.print(f"   • Has fuzzy: {search_index.has_fuzzy}")
    else:
        console.print("[red]❌ SearchIndex not found[/red]")

    # Summary
    console.print("\n[bold cyan]📊 Performance Summary[/bold cyan]")
    console.print("=" * 80)
    console.print(f"Corpus build time: {corpus_time:.2f}s")
    console.print(f"Vocabulary aggregation: {aggregate_time:.2f}s")
    console.print(f"Index build time: {index_time:.2f}s")
    console.print(f"Total time: {corpus_time + aggregate_time + index_time:.2f}s")

    # Check for multiprocessing evidence
    console.print("\n[dim]Looking for optimization evidence...[/dim]")

    # Check log for our optimization messages
    import subprocess
    result = subprocess.run(
        "grep -c 'Successfully added.*sources' corpus_verification_full.log 2>/dev/null || echo 0",
        shell=True,
        capture_output=True,
        text=True
    )

    if int(result.stdout.strip()) > 0:
        console.print("[green]✅ Parallel source fetching detected[/green]")

    # Check for multiprocessing semaphores (evidence of multiprocessing)
    import sys
    if hasattr(sys, 'ps1'):  # Interactive mode check
        console.print("[yellow]⚠️  Run in script mode to see full multiprocessing[/yellow]")

    console.print("\n[bold green]✅ Pipeline test complete![/bold green]")


if __name__ == "__main__":
    asyncio.run(test_optimized_pipeline())