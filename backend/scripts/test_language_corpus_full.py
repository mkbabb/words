#!/usr/bin/env python3
"""Test complete language-level corpus building with proper aggregation and indexing."""

import asyncio
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import track

from floridify.corpus.language.core import LanguageCorpus
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.models.base import Language
from floridify.search.core import Search
from floridify.search.models import SearchIndex
from floridify.search.semantic.models import SemanticIndex
from floridify.storage.mongodb import init_db
from floridify.utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


async def build_and_aggregate_corpus():
    """Build language corpus and properly aggregate vocabulary."""
    console.print("\n[bold blue]🏗️  Building Language Corpus with Aggregation[/bold blue]")
    console.print("=" * 80)

    start_time = time.time()

    # Initialize database
    await init_db()

    # Step 1: Create language corpus
    console.print("\n[yellow]📚 Step 1: Creating language corpus with parallel sources...[/yellow]")
    corpus = await LanguageCorpus.create_from_language(
        language=Language.ENGLISH,
        corpus_name="language_english_full"
    )

    console.print(f"[green]✅ Initial corpus created[/green]")
    console.print(f"  • Corpus ID: {corpus.corpus_id}")
    console.print(f"  • Initial vocabulary: {len(corpus.vocabulary):,}")
    console.print(f"  • Children: {len(corpus.child_corpus_ids or [])}")

    # Step 2: Aggregate vocabulary from children
    console.print("\n[yellow]🔄 Step 2: Aggregating vocabulary from child corpora...[/yellow]")
    manager = get_tree_corpus_manager()

    if corpus.corpus_id:
        agg_start = time.time()
        aggregated_vocab = await manager.aggregate_vocabularies(
            corpus_id=corpus.corpus_id,
            update_parent=True
        )
        agg_time = time.time() - agg_start

        console.print(f"[green]✅ Vocabulary aggregated in {agg_time:.2f}s[/green]")
        console.print(f"  • Aggregated vocabulary: {len(aggregated_vocab):,}")

        # Reload corpus to get updated vocabulary
        corpus = await manager.get_corpus(corpus_id=corpus.corpus_id)
        console.print(f"  • Updated corpus vocabulary: {len(corpus.vocabulary):,}")
        console.print(f"  • Lemmatized vocabulary: {len(corpus.lemmatized_vocabulary):,}")

    build_time = time.time() - start_time
    console.print(f"  • Total build time: {build_time:.2f}s")

    return corpus


async def build_search_indices(corpus):
    """Build all search indices including SemanticIndex."""
    console.print("\n[bold blue]🔎 Building Search Indices[/bold blue]")
    console.print("=" * 80)

    start_time = time.time()

    # Create search with semantic enabled
    console.print("\n[yellow]Building unified search index...[/yellow]")
    search = await Search.from_corpus(
        corpus=corpus,
        semantic_model="Alibaba-NLP/gte-Qwen2-1.5B-instruct"
    )

    index_time = time.time() - start_time
    console.print(f"[green]✅ Search indices built in {index_time:.2f}s[/green]")
    console.print(f"  • Trie index: {'✓' if search.trie_search else '✗'}")
    console.print(f"  • Fuzzy search: {'✓' if search.fuzzy_search else '✗'}")
    console.print(f"  • Semantic search: {'✓' if search.semantic_search else '✗'}")

    return search


async def verify_persistence(corpus_name: str):
    """Verify all indices are properly persisted."""
    console.print("\n[bold blue]💾 Verifying Index Persistence[/bold blue]")
    console.print("=" * 80)

    results = []

    # Check SearchIndex
    console.print("\n[yellow]Checking SearchIndex...[/yellow]")
    search_index = await SearchIndex.get(corpus_name=corpus_name)
    if search_index:
        console.print(f"[green]✅ SearchIndex found[/green]")
        console.print(f"  • Vocabulary hash: {search_index.vocabulary_hash[:16]}...")
        console.print(f"  • Has trie: {search_index.has_trie}")
        console.print(f"  • Has fuzzy: {search_index.has_fuzzy}")
        console.print(f"  • Has semantic: {search_index.has_semantic}")
        results.append(("SearchIndex", "✅", search_index.vocabulary_hash[:8]))
    else:
        console.print("[red]❌ SearchIndex not found[/red]")
        results.append(("SearchIndex", "❌", "N/A"))

    # Check SemanticIndex
    console.print("\n[yellow]Checking SemanticIndex...[/yellow]")
    semantic_index = await SemanticIndex.get(
        corpus_name=corpus_name,
        model_name="Alibaba-NLP/gte-Qwen2-1.5B-instruct"
    )
    if semantic_index:
        console.print(f"[green]✅ SemanticIndex found[/green]")
        console.print(f"  • Model: {semantic_index.model_name}")
        console.print(f"  • Vocabulary hash: {semantic_index.vocabulary_hash[:16]}...")
        console.print(f"  • Embeddings: {semantic_index.num_embeddings:,}")
        console.print(f"  • Index type: {semantic_index.index_type}")
        console.print(f"  • Memory usage: {semantic_index.memory_usage_mb:.2f} MB")
        console.print(f"  • Build time: {semantic_index.build_time_seconds:.2f}s")
        results.append(("SemanticIndex", "✅", f"{semantic_index.num_embeddings:,} embeddings"))
    else:
        console.print("[red]❌ SemanticIndex not found[/red]")
        results.append(("SemanticIndex", "❌", "N/A"))

    # Check MongoDB persistence
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017")
    db = client.floridify

    console.print("\n[yellow]Checking MongoDB persistence...[/yellow]")
    table = Table(title="Versioned Data Summary")
    table.add_column("Resource Type", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_column("Latest", style="green")

    for resource_type in ["corpus", "search", "semantic", "trie"]:
        count = db.versioned_data.count_documents({"resource_type": resource_type})
        latest = db.versioned_data.find_one(
            {"resource_type": resource_type, "version_info.is_latest": True},
            {"version_info.version": 1}
        )
        version = latest["version_info"]["version"] if latest else "N/A"
        table.add_row(resource_type, str(count), version)

    console.print(table)

    return all(status == "✅" for _, status, _ in results[:2])  # Check main indices


async def test_search_performance(search):
    """Test search performance with various queries."""
    console.print("\n[bold blue]⚡ Testing Search Performance[/bold blue]")
    console.print("=" * 80)

    test_queries = [
        ("hello", "exact"),
        ("perspicacious", "exact"),
        ("helllo", "fuzzy"),
        ("quick brown fox", "semantic"),
        ("language", "combined"),
    ]

    results = []
    for query, method in test_queries:
        start = time.time()
        search_results = await search.search(query, method=method, max_results=5)
        elapsed = (time.time() - start) * 1000  # Convert to ms

        if search_results:
            result_str = f"{len(search_results)} results, top: {search_results[0].word}"
            console.print(f"  {method:10s} '{query:20s}': {elapsed:6.2f}ms - {result_str}")
            results.append((method, elapsed))
        else:
            console.print(f"  {method:10s} '{query:20s}': {elapsed:6.2f}ms - No results")

    # Performance summary
    if results:
        console.print("\n[yellow]Performance Summary:[/yellow]")
        for method, elapsed in results:
            status = "✅" if elapsed < 10 else "⚠️" if elapsed < 50 else "❌"
            console.print(f"  {status} {method}: {elapsed:.2f}ms")


async def check_multiprocessing_evidence():
    """Check for evidence of multiprocessing optimizations."""
    console.print("\n[bold blue]🔧 Optimization Evidence[/bold blue]")
    console.print("=" * 80)

    # Check latest log for multiprocessing evidence
    import subprocess

    # Check for parallel source fetching
    result = subprocess.run(
        "tail -100 corpus_build_optimized.log 2>/dev/null | grep -c 'Successfully added.*sources' || echo 0",
        shell=True,
        capture_output=True,
        text=True
    )

    if int(result.stdout.strip()) > 0:
        console.print("[green]✅ Parallel source fetching detected[/green]")

    # Check for multiprocess embeddings
    result = subprocess.run(
        "tail -100 corpus_build_optimized.log 2>/dev/null | grep -c 'Encoding.*with.*workers' || echo 0",
        shell=True,
        capture_output=True,
        text=True
    )

    if int(result.stdout.strip()) > 0:
        console.print("[green]✅ Multiprocess embedding generation detected[/green]")

    # Check for FAISS OpenMP
    result = subprocess.run(
        "tail -100 corpus_build_optimized.log 2>/dev/null | grep -c 'FAISS OpenMP' || echo 0",
        shell=True,
        capture_output=True,
        text=True
    )

    if int(result.stdout.strip()) > 0:
        console.print("[green]✅ FAISS OpenMP threading configured[/green]")


async def main():
    """Main execution."""
    console.print("\n[bold cyan]═" * 80 + "[/bold cyan]")
    console.print("[bold cyan] COMPREHENSIVE LANGUAGE CORPUS TEST WITH FULL INDEXING[/bold cyan]")
    console.print("[bold cyan]═" * 80 + "[/bold cyan]")
    console.print(f"\n📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        overall_start = time.time()

        # Build and aggregate corpus
        corpus = await build_and_aggregate_corpus()

        if len(corpus.vocabulary) == 0:
            console.print("\n[red]❌ ERROR: Corpus has no vocabulary after aggregation![/red]")
            return

        # Build search indices
        search = await build_search_indices(corpus)

        # Verify persistence
        all_persisted = await verify_persistence(corpus.corpus_name)

        # Test search performance
        await test_search_performance(search)

        # Check for optimization evidence
        await check_multiprocessing_evidence()

        # Final summary
        overall_time = time.time() - overall_start

        console.print("\n[bold green]═" * 80 + "[/bold green]")
        console.print("[bold green] ✅ TEST COMPLETE[/bold green]")
        console.print("[bold green]═" * 80 + "[/bold green]")
        console.print(f"\n📊 Final Summary:")
        console.print(f"  • Total time: {overall_time:.1f}s")
        console.print(f"  • Corpus vocabulary: {len(corpus.vocabulary):,} words")
        console.print(f"  • Lemmatized: {len(corpus.lemmatized_vocabulary):,} words")
        console.print(f"  • All indices persisted: {'✅ Yes' if all_persisted else '❌ No'}")

        # Performance targets
        console.print(f"\n🎯 Performance vs Targets:")
        console.print(f"  • Fuzzy search: < 10ms target")
        console.print(f"  • Semantic search: < 20ms target")
        console.print(f"  • Combined search: < 50ms target")

    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        logger.exception("Test failed")
        raise


if __name__ == "__main__":
    asyncio.run(main())