#!/usr/bin/env python3
"""
Profile exact search performance to identify bottlenecks.
Measures each step in the search_exact path to find optimization opportunities.
"""

import asyncio
import cProfile
import io
import pstats
import statistics
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Add backend to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from floridify.caching.models import VersionConfig
from floridify.corpus.core import Corpus
from floridify.search.core import Search

console = Console()

# Test queries
TEST_QUERIES = [
    "test",
    "word",
    "example",
    "dictionary",
    "meaning",
    "search",
    "find",
    "look",
    "definition",
    "language",
    "perspicacious",
    "sesquipedalian",
    "defenestration",
    "the",
    "a",
    "and",
    "run",
    "running",
    "ran",
]


class TimingContext:
    """Context manager for precise timing measurements."""

    def __init__(self, name: str):
        self.name = name
        self.start_time = 0
        self.duration_ms = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000


async def profile_search_exact_detailed(search: Search, query: str) -> dict:
    """Profile a single exact search with detailed timing."""
    timings = {}

    # 1. Normalization
    with TimingContext("normalize") as t:
        from floridify.text import normalize

        normalized_query = normalize(query)
    timings["normalize"] = t.duration_ms

    # 2. Trie lookup
    with TimingContext("trie_lookup") as t:
        if search.trie_search:
            match = search.trie_search.search_exact(normalized_query)
        else:
            match = None
    timings["trie_lookup"] = t.duration_ms

    # 3. Original word mapping (if match found)
    if match:
        with TimingContext("get_original_word") as t:
            original = search._get_original_word(match)
        timings["get_original_word"] = t.duration_ms
    else:
        timings["get_original_word"] = 0

    # 4. Result construction
    with TimingContext("result_construction") as t:
        if match:
            from floridify.search.constants import SearchMethod
            from floridify.search.models import SearchResult

            result = [
                SearchResult(
                    word=original if match else match,
                    lemmatized_word=None,
                    score=1.0,
                    method=SearchMethod.EXACT,
                    language=None,
                    metadata=None,
                )
            ]
        else:
            result = []
    timings["result_construction"] = t.duration_ms

    # Total time
    timings["total"] = sum(timings.values())
    timings["match_found"] = match is not None

    return timings


async def benchmark_exact_search_microbenchmark():
    """Run microbenchmark on exact search components."""
    console.print("[bold blue]Exact Search Performance Microbenchmark[/bold blue]")
    console.print("=" * 60)

    # Load corpus and search engine
    console.print("\n[cyan]Loading corpus and search engine...[/cyan]")
    corpus = await Corpus.get(corpus_name="english", config=VersionConfig())
    if not corpus:
        console.print("[red]Error: Could not load 'english' corpus[/red]")
        return

    search = await Search.from_corpus(
        corpus_name="english", semantic=False, config=VersionConfig()
    )
    await search.initialize()

    console.print(f"  Corpus: {len(corpus.vocabulary)} words")
    console.print(f"  Vocabulary hash: {corpus.vocabulary_hash[:8]}...")

    # Run detailed profiling for each test query
    all_timings = []
    console.print(f"\n[cyan]Profiling {len(TEST_QUERIES)} test queries...[/cyan]")

    for query in TEST_QUERIES:
        timings = await profile_search_exact_detailed(search, query)
        all_timings.append({"query": query, **timings})

    # Calculate statistics for each component
    components = ["normalize", "trie_lookup", "get_original_word", "result_construction", "total"]
    stats = {}

    for component in components:
        times = [t[component] for t in all_timings if t[component] > 0]
        if times:
            stats[component] = {
                "mean": statistics.mean(times),
                "median": statistics.median(times),
                "min": min(times),
                "max": max(times),
                "stdev": statistics.stdev(times) if len(times) > 1 else 0,
                "p95": sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0],
            }
        else:
            stats[component] = {
                "mean": 0,
                "median": 0,
                "min": 0,
                "max": 0,
                "stdev": 0,
                "p95": 0,
            }

    # Display results
    table = Table(title="Exact Search Component Timings (microseconds)")
    table.add_column("Component", style="cyan")
    table.add_column("Mean (μs)", style="yellow")
    table.add_column("Median (μs)", style="yellow")
    table.add_column("P95 (μs)", style="magenta")
    table.add_column("Min (μs)", style="green")
    table.add_column("Max (μs)", style="red")

    for component in components:
        s = stats[component]
        table.add_row(
            component,
            f"{s['mean']*1000:.2f}",
            f"{s['median']*1000:.2f}",
            f"{s['p95']*1000:.2f}",
            f"{s['min']*1000:.2f}",
            f"{s['max']*1000:.2f}",
        )

    console.print("\n")
    console.print(table)

    # Percentage breakdown
    console.print("\n[bold]Time Distribution:[/bold]")
    total_mean = stats["total"]["mean"]
    if total_mean > 0:
        for component in components[:-1]:  # Exclude 'total'
            pct = (stats[component]["mean"] / total_mean) * 100
            console.print(f"  {component:25s}: {pct:5.1f}%")

    # Hit rate
    hit_rate = sum(1 for t in all_timings if t["match_found"]) / len(all_timings) * 100
    console.print(f"\n[bold]Match hit rate:[/bold] {hit_rate:.1f}%")

    # Performance assessment
    console.print("\n[bold]Performance Assessment:[/bold]")
    p95_total_ms = stats["total"]["p95"]
    target_ms = 2.0

    if p95_total_ms <= target_ms:
        console.print(
            f"  ✅ P95 latency: {p95_total_ms:.3f}ms (target: <{target_ms}ms) - PASSING"
        )
    else:
        console.print(
            f"  ❌ P95 latency: {p95_total_ms:.3f}ms (target: <{target_ms}ms) - NEEDS OPTIMIZATION"
        )
        improvement_needed = ((p95_total_ms / target_ms) - 1) * 100
        console.print(f"     Need {improvement_needed:.1f}% improvement")

    return stats, all_timings


async def profile_with_cprofile():
    """Run cProfile on exact search to find hotspots."""
    console.print("\n[bold blue]Running cProfile Analysis...[/bold blue]")

    # Load corpus and search engine
    corpus = await Corpus.get(corpus_name="english", config=VersionConfig())
    if not corpus:
        console.print("[red]Error: Could not load 'english' corpus[/red]")
        return

    search = await Search.from_corpus(
        corpus_name="english", semantic=False, config=VersionConfig()
    )
    await search.initialize()

    # Create profiler
    profiler = cProfile.Profile()

    # Profile 1000 searches
    profiler.enable()
    for _ in range(1000):
        for query in TEST_QUERIES[:5]:  # Use subset for profiling
            _ = search.search_exact(query)
    profiler.disable()

    # Analyze results
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(20)  # Top 20 functions

    console.print("\n[cyan]Top 20 functions by cumulative time:[/cyan]")
    console.print(stream.getvalue())

    # Also sort by time
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("time")
    stats.print_stats(20)

    console.print("\n[cyan]Top 20 functions by total time:[/cyan]")
    console.print(stream.getvalue())


async def analyze_corpus_lookups():
    """Analyze the efficiency of corpus vocabulary lookups."""
    console.print("\n[bold blue]Analyzing Corpus Lookup Efficiency...[/bold blue]")

    # Load corpus
    corpus = await Corpus.get(corpus_name="english", config=VersionConfig())
    if not corpus:
        console.print("[red]Error: Could not load 'english' corpus[/red]")
        return

    # Test vocabulary_to_index lookup speed
    from floridify.text import normalize

    test_words = ["test", "word", "example", "dictionary", "meaning"]
    normalized_words = [normalize(w) for w in test_words]

    timings = []
    for _ in range(1000):
        for norm_word in normalized_words:
            with TimingContext("lookup") as t:
                idx = corpus.vocabulary_to_index.get(norm_word)
            timings.append(t.duration_ms)

    mean_us = statistics.mean(timings) * 1000
    p95_us = sorted(timings)[int(len(timings) * 0.95)] * 1000

    console.print(f"  Vocabulary size: {len(corpus.vocabulary)}")
    console.print(f"  vocabulary_to_index type: {type(corpus.vocabulary_to_index)}")
    console.print(f"  vocabulary_to_index size: {len(corpus.vocabulary_to_index)}")
    console.print(f"  Dict lookup mean: {mean_us:.3f}μs")
    console.print(f"  Dict lookup P95: {p95_us:.3f}μs")

    # Test get_original_word_by_index speed
    indices = [corpus.vocabulary_to_index.get(w) for w in normalized_words if w in corpus.vocabulary_to_index]
    timings = []
    for _ in range(1000):
        for idx in indices:
            if idx is not None:
                with TimingContext("get_original") as t:
                    orig = corpus.get_original_word_by_index(idx)
                timings.append(t.duration_ms)

    mean_us = statistics.mean(timings) * 1000
    p95_us = sorted(timings)[int(len(timings) * 0.95)] * 1000

    console.print(f"\n  get_original_word_by_index mean: {mean_us:.3f}μs")
    console.print(f"  get_original_word_by_index P95: {p95_us:.3f}μs")


async def main():
    """Run all profiling analyses."""
    try:
        # Microbenchmark
        stats, timings = await benchmark_exact_search_microbenchmark()

        # Corpus lookup analysis
        await analyze_corpus_lookups()

        # cProfile analysis
        await profile_with_cprofile()

        console.print("\n[bold green]Profiling complete![/bold green]")

    except Exception as e:
        console.print(f"[red]Error during profiling: {e}[/red]")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
