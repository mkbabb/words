#!/usr/bin/env python3
"""Build and verify a complete language corpus with all indices."""

import asyncio
import time
from datetime import datetime

from rich.console import Console
from rich.table import Table

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


async def build_language_corpus():
    """Build a complete language corpus with proper indexing."""
    console.print("\n[bold blue]🏗️  Building Language-Level Corpus[/bold blue]")
    console.print("=" * 80)

    start_time = time.time()

    # Initialize database
    await init_db()

    # Create language corpus
    console.print("\n[yellow]📚 Step 1: Creating language corpus with parallel source fetching...[/yellow]")
    corpus = await LanguageCorpus.create_from_language(
        language=Language.ENGLISH,
        corpus_name="language_english_full"
    )

    # Get corpus statistics
    console.print(f"[green]✅ Corpus created: {corpus.corpus_name}[/green]")
    console.print(f"  • Vocabulary size: {len(corpus.vocabulary):,}")
    console.print(f"  • Lemmatized vocabulary: {len(corpus.lemmatized_vocabulary):,}")
    console.print(f"  • Child corpora: {len(corpus.child_corpus_ids or [])}")
    console.print(f"  • Vocabulary hash: {corpus.vocabulary_hash[:16]}...")

    build_time = time.time() - start_time
    console.print(f"  • Build time: {build_time:.2f} seconds")

    return corpus


async def verify_indices(corpus_name: str):
    """Verify all indices are properly built and persisted."""
    console.print("\n[bold blue]🔍 Verifying Indices[/bold blue]")
    console.print("=" * 80)

    # Check SearchIndex
    console.print("\n[yellow]Checking SearchIndex...[/yellow]")
    search_index = await SearchIndex.get(corpus_name=corpus_name)
    if search_index:
        console.print(f"[green]✅ SearchIndex found[/green]")
        console.print(f"  • Vocabulary hash: {search_index.vocabulary_hash[:16]}...")
        console.print(f"  • Has trie: {search_index.has_trie}")
        console.print(f"  • Has fuzzy: {search_index.has_fuzzy}")
        console.print(f"  • Has semantic: {search_index.has_semantic}")
    else:
        console.print("[red]❌ SearchIndex not found[/red]")

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
    else:
        console.print("[red]❌ SemanticIndex not found[/red]")

    return search_index, semantic_index


async def test_search_functionality(corpus_name: str):
    """Test search functionality on the corpus."""
    console.print("\n[bold blue]🔎 Testing Search Functionality[/bold blue]")
    console.print("=" * 80)

    # Create search engine
    search = await Search.from_corpus(corpus_name=corpus_name)

    test_queries = [
        "hello",      # Common word
        "perspicacious",  # Rare word
        "helllo",     # Misspelled
        "quick brown fox",  # Phrase
    ]

    for query in test_queries:
        console.print(f"\n[yellow]Query: '{query}'[/yellow]")

        # Test exact search
        results = await search.search(query, method="exact", max_results=3)
        console.print(f"  Exact: {len(results)} results")
        if results:
            console.print(f"    Top: {results[0].word} (score: {results[0].score:.3f})")

        # Test fuzzy search
        results = await search.search(query, method="fuzzy", max_results=3)
        console.print(f"  Fuzzy: {len(results)} results")
        if results:
            console.print(f"    Top: {results[0].word} (score: {results[0].score:.3f})")

        # Test semantic search
        results = await search.search(query, method="semantic", max_results=3)
        console.print(f"  Semantic: {len(results)} results")
        if results:
            console.print(f"    Top: {results[0].word} (score: {results[0].score:.3f})")


async def check_persistence():
    """Verify indices persist across restarts."""
    console.print("\n[bold blue]💾 Checking Persistence[/bold blue]")
    console.print("=" * 80)

    from pymongo import MongoClient

    client = MongoClient("mongodb://localhost:27017")
    db = client.floridify

    # Create summary table
    table = Table(title="Persisted Indices")
    table.add_column("Resource Type", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_column("Latest Version", style="green")

    for resource_type in ["corpus", "search", "semantic", "trie"]:
        count = db.versioned_data.count_documents({"resource_type": resource_type})
        latest = db.versioned_data.find_one(
            {"resource_type": resource_type, "version_info.is_latest": True},
            {"version_info.version": 1}
        )
        version = latest["version_info"]["version"] if latest else "N/A"
        table.add_row(resource_type, str(count), version)

    console.print(table)

    # Check cache directory
    import os
    cache_dir = "/Users/mkbabb/Programming/words/backend/cache/floridify/unified"
    if os.path.exists(cache_dir):
        cache_files = len(os.listdir(cache_dir))
        console.print(f"\n[cyan]Filesystem cache: {cache_files} files[/cyan]")


async def main():
    """Main execution."""
    try:
        # Build corpus
        corpus = await build_language_corpus()

        # Wait a moment for indices to save
        await asyncio.sleep(2)

        # Verify indices
        search_index, semantic_index = await verify_indices(corpus.corpus_name)

        # Test search
        if search_index:
            await test_search_functionality(corpus.corpus_name)

        # Check persistence
        await check_persistence()

        # Summary
        console.print("\n[bold green]✅ Corpus build and verification complete![/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        logger.exception("Build failed")
        raise


if __name__ == "__main__":
    asyncio.run(main())