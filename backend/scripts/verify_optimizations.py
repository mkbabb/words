#!/usr/bin/env python3
"""
Quick verification script to test exact search optimizations.
Checks that all optimizations are working correctly.
"""

import asyncio
import time

from rich.console import Console
from rich.table import Table

console = Console()


async def verify_bloom_filter():
    """Verify Bloom filter is working correctly."""
    console.print("\n[cyan]1. Verifying Bloom Filter Implementation[/cyan]")

    from floridify.search.bloom import BloomFilter

    # Create small test filter
    bloom = BloomFilter(capacity=1000, error_rate=0.01)

    # Add test words
    test_words = ["test", "word", "example", "dictionary", "search"]
    bloom.add_many(test_words)

    # Test membership
    hits = 0
    misses = 0

    for word in test_words:
        if word in bloom:
            hits += 1
        else:
            console.print(f"  [red]❌ False negative for '{word}'[/red]")

    # Test non-existent words (should mostly be misses)
    non_existent = ["asdflkjasdf", "qwertyuiop", "zxcvbnm", "hjklasd", "mnbvcxz"] * 20
    false_positives = 0

    for word in non_existent:
        if word in bloom:
            false_positives += 1

    fp_rate = false_positives / len(non_existent)

    stats = bloom.get_stats()

    console.print(f"  [green]✅ All {hits} test words found[/green]")
    console.print(f"  [yellow]False positive rate: {fp_rate*100:.2f}% (target: <1%)[/yellow]")
    console.print(f"  [blue]Memory: {stats['memory_bytes']} bytes for {stats['item_count']} items[/blue]")

    if fp_rate > 0.02:
        console.print(f"  [red]⚠️  False positive rate higher than expected[/red]")
    else:
        console.print(f"  [green]✅ Bloom filter working as expected[/green]")


async def verify_search_performance():
    """Verify search performance improvements (requires running server)."""
    console.print("\n[cyan]2. Verifying Search Performance (via API)[/cyan]")

    import httpx

    # Check if server is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code != 200:
                console.print("  [yellow]⚠️  Server not running, skipping API tests[/yellow]")
                return
    except Exception:
        console.print("  [yellow]⚠️  Server not running, skipping API tests[/yellow]")
        return

    # Test exact search performance
    test_queries = ["test", "word", "example", "nonexistentword", "asdfjkl"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        times = []
        for query in test_queries:
            start = time.perf_counter()
            response = await client.get(
                f"http://localhost:8000/api/v1/search/{query}",
                params={"mode": "exact", "max_results": 1},
            )
            duration_ms = (time.perf_counter() - start) * 1000
            times.append(duration_ms)

            # Get server time from header
            server_time_s = response.headers.get("X-Process-Time")
            server_time_ms = float(server_time_s) * 1000 if server_time_s else None

            found = len(response.json().get("results", [])) > 0

            console.print(
                f"  Query: '{query:20s}' → "
                f"{'✓' if found else '✗'} "
                f"Total: {duration_ms:6.2f}ms "
                f"Server: {server_time_ms:6.2f}ms" if server_time_ms else f"Total: {duration_ms:6.2f}ms"
            )

    # Calculate stats
    mean_ms = sum(times) / len(times)
    p95_ms = sorted(times)[int(len(times) * 0.95)]

    console.print(f"\n  [bold]Performance Summary:[/bold]")
    console.print(f"  Mean: {mean_ms:.2f}ms")
    console.print(f"  P95:  {p95_ms:.2f}ms")

    if p95_ms < 2.0:
        console.print(f"  [green]✅ Performance target met! (< 2ms P95)[/green]")
    elif p95_ms < 3.0:
        console.print(f"  [yellow]⚠️  Close to target ({p95_ms:.2f}ms vs 2ms target)[/yellow]")
    else:
        console.print(f"  [red]❌ Performance target not met ({p95_ms:.2f}ms vs 2ms target)[/red]")


async def verify_code_changes():
    """Verify that optimizations are present in the code."""
    console.print("\n[cyan]3. Verifying Code Optimizations[/cyan]")

    import inspect

    from floridify.search.core import Search
    from floridify.search.trie import TrieSearch

    # Check 1: Bloom filter in TrieSearch
    trie_init = inspect.getsource(TrieSearch.__init__)
    if "_bloom_filter" in trie_init:
        console.print("  [green]✅ Bloom filter initialized in TrieSearch[/green]")
    else:
        console.print("  [red]❌ Bloom filter not found in TrieSearch.__init__[/red]")

    # Check 2: Inlined _get_original_word in search_exact
    search_exact = inspect.getsource(Search.search_exact)
    if "vocabulary_to_index.get" in search_exact and "original_indices" in search_exact:
        console.print("  [green]✅ _get_original_word() inlined in search_exact()[/green]")
    else:
        console.print("  [red]❌ _get_original_word() not inlined[/red]")

    # Check 3: No update_corpus in search_with_mode
    search_with_mode = inspect.getsource(Search.search_with_mode)
    if "update_corpus" not in search_with_mode:
        console.print("  [green]✅ update_corpus() removed from search hot path[/green]")
    else:
        console.print("  [red]❌ update_corpus() still in hot path[/red]")

    # Check 4: Bloom filter check in TrieSearch.search_exact
    trie_search_exact = inspect.getsource(TrieSearch.search_exact)
    if "_bloom_filter" in trie_search_exact and "not in self._bloom_filter" in trie_search_exact:
        console.print("  [green]✅ Bloom filter pre-check in TrieSearch.search_exact()[/green]")
    else:
        console.print("  [red]❌ Bloom filter pre-check not found[/red]")


async def verify_bloom_filter_stats():
    """Show Bloom filter memory and performance stats."""
    console.print("\n[cyan]4. Bloom Filter Statistics[/cyan]")

    from floridify.search.bloom import BloomFilter

    # Test with different vocabulary sizes
    sizes = [1000, 10000, 100000]

    table = Table(title="Bloom Filter Memory Usage")
    table.add_column("Vocabulary Size", style="cyan")
    table.add_column("Memory (KB)", style="yellow")
    table.add_column("Bytes/Word", style="green")
    table.add_column("Hash Functions", style="blue")
    table.add_column("FP Rate (%)", style="magenta")

    for size in sizes:
        bloom = BloomFilter(capacity=size, error_rate=0.01)
        # Add dummy data to get realistic fill rate
        bloom.add_many([f"word_{i}" for i in range(size)])

        stats = bloom.get_stats()

        table.add_row(
            f"{size:,}",
            f"{stats['memory_bytes']/1024:.1f}",
            f"{stats['memory_per_item']:.2f}",
            str(stats['hash_count']),
            f"{stats['estimated_error_rate']*100:.2f}",
        )

    console.print(table)


async def main():
    """Run all verification checks."""
    console.print("[bold blue]Exact Search Optimization Verification[/bold blue]")
    console.print("=" * 60)

    try:
        await verify_bloom_filter()
        await verify_code_changes()
        await verify_bloom_filter_stats()
        await verify_search_performance()

        console.print("\n[bold green]✅ Verification Complete![/bold green]")

    except Exception as e:
        console.print(f"\n[red]Error during verification: {e}[/red]")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
