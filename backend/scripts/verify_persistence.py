#!/usr/bin/env python3
"""Verify that all search indices are properly persisted and working."""

import asyncio
from rich.console import Console
from rich.table import Table

from floridify.storage.mongodb import init_db
from floridify.corpus.core import Corpus
from floridify.search.models import SearchIndex, TrieIndex
from floridify.search.semantic.models import SemanticIndex
from floridify.caching.models import VersionConfig

console = Console()


async def verify_persistence():
    """Verify all indices are persisted."""
    console.print("\n[bold cyan]Verifying Search Pipeline Persistence[/bold cyan]\n")

    # Connect to MongoDB
    await init_db()

    corpus_name = "language_english"
    config = VersionConfig()

    # 1. Verify Corpus
    console.print(f"[yellow]1. Checking Corpus: {corpus_name}[/yellow]")
    corpus = await Corpus.get(corpus_name=corpus_name, config=config)
    if corpus:
        console.print(f"   ✅ Corpus found: {len(corpus.vocabulary):,} words")
        console.print(f"   ✅ Child corpora: {len(corpus.child_corpus_ids or [])}")
    else:
        console.print("   ❌ Corpus NOT found")
        return

    # 2. Verify SearchIndex
    console.print(f"\n[yellow]2. Checking SearchIndex[/yellow]")
    search_index = await SearchIndex.get(corpus_id=corpus.corpus_id, config=config)
    if search_index:
        console.print(f"   ✅ SearchIndex found")
        console.print(f"   ✅ Has Trie: {search_index.has_trie}")
        console.print(f"   ✅ Has Fuzzy: {search_index.has_fuzzy}")
        console.print(f"   ✅ Semantic enabled: {search_index.semantic_enabled}")
    else:
        console.print("   ❌ SearchIndex NOT found")

    # 3. Verify TrieIndex
    console.print(f"\n[yellow]3. Checking TrieIndex[/yellow]")
    trie_index = await TrieIndex.get(corpus_id=corpus.corpus_id, config=config)
    if trie_index:
        console.print(f"   ✅ TrieIndex found")
        console.print(f"   ✅ Words indexed: {len(trie_index.trie_data) if trie_index.trie_data else 0:,}")
    else:
        console.print("   ❌ TrieIndex NOT found")

    # 4. Verify SemanticIndex
    console.print(f"\n[yellow]4. Checking SemanticIndex[/yellow]")
    model_name = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
    semantic_index = await SemanticIndex.get(
        corpus_id=corpus.corpus_id,
        model_name=model_name,
        config=config
    )
    if semantic_index:
        console.print(f"   ✅ SemanticIndex found")
        console.print(f"   ✅ Model: {semantic_index.model_name}")
        console.print(f"   ✅ Device: {semantic_index.device}")
        console.print(f"   ✅ Has embeddings: {bool(semantic_index.embeddings)}")
        console.print(f"   ✅ Has FAISS index: {bool(semantic_index.index_data)}")
    else:
        console.print("   ❌ SemanticIndex NOT found")

    # Summary table
    table = Table(title="\nPersistence Summary")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")

    table.add_row(
        "Corpus",
        "✅" if corpus else "❌",
        f"{len(corpus.vocabulary):,} words" if corpus else "Not found"
    )
    table.add_row(
        "SearchIndex",
        "✅" if search_index else "❌",
        f"Trie: {search_index.has_trie}, Fuzzy: {search_index.has_fuzzy}" if search_index else "Not found"
    )
    table.add_row(
        "TrieIndex",
        "✅" if trie_index else "❌",
        f"{len(trie_index.trie_data) if trie_index and trie_index.trie_data else 0:,} words" if trie_index else "Not found"
    )
    table.add_row(
        "SemanticIndex",
        "✅" if semantic_index else "❌",
        f"Embeddings: {bool(semantic_index.embeddings if semantic_index else False)}" if semantic_index else "Not found"
    )

    console.print(table)

    # Check if all components present
    all_present = all([corpus, search_index, trie_index, semantic_index])
    if all_present:
        console.print("\n[bold green]✅ All indices properly persisted and ready![/bold green]\n")
    else:
        console.print("\n[bold red]❌ Some indices are missing - pipeline not fully persisted[/bold red]\n")


if __name__ == "__main__":
    asyncio.run(verify_persistence())
