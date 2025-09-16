#!/usr/bin/env python3
"""
Quick performance benchmark script for measuring current search performance.
Run this before and after optimizations to measure improvements.
"""

import asyncio
import json
import random
import statistics
import time
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np
from rich.console import Console
from rich.table import Table

# Test queries for benchmarking
TEST_QUERIES = {
    "common": [
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
    ],
    "rare": [
        "perspicacious",
        "sesquipedalian",
        "defenestration",
        "tmesis",
        "zugzwang",
        "callipygian",
        "petrichor",
    ],
    "misspelled": ["tset", "wrod", "exmaple", "dictionery", "meanign", "serach", "fnid", "lokk"],
    "short": ["a", "i", "to", "be", "it", "is", "in", "on", "at", "by"],
    "long": [
        "antidisestablishmentarianism",
        "pneumonoultramicroscopicsilicovolcanoconiosis",
        "hippopotomonstrosesquippedaliophobia",
    ],
}

console = Console()


async def measure_request_time(client: httpx.AsyncClient, url: str, params: dict) -> float:
    """Measure the time for a single request in milliseconds."""
    start_time = time.perf_counter()
    response = await client.get(url, params=params)
    end_time = time.perf_counter()

    if response.status_code != 200:
        console.print(f"[red]Error: {response.status_code} for {url}[/red]")
        return -1

    return (end_time - start_time) * 1000  # Convert to milliseconds


async def benchmark_search_type(search_type: str, iterations: int = 50) -> dict:
    """Benchmark a specific search type."""
    base_url = "http://localhost:8000/api/v1/search"
    results = []

    console.print(f"\n[cyan]Benchmarking {search_type} search...[/cyan]")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(iterations):
            # Select random query type and query
            query_type = random.choice(list(TEST_QUERIES.keys()))
            query = random.choice(TEST_QUERIES[query_type])

            # Set parameters based on search type
            params = {"max_results": 20}
            if search_type == "exact":
                params["mode"] = "exact"
            elif search_type == "fuzzy":
                params["mode"] = "fuzzy"
            elif search_type == "semantic":
                params["mode"] = "semantic"
            elif search_type == "combined":
                params["mode"] = "smart"  # Smart mode is the new combined mode

            # Measure request time
            time_ms = await measure_request_time(client, f"{base_url}/{query}", params)
            if time_ms > 0:
                results.append({"query": query, "query_type": query_type, "time_ms": time_ms})

            # Progress indicator
            if (i + 1) % 10 == 0:
                console.print(f"  Progress: {i + 1}/{iterations}")

    # Calculate statistics
    if results:
        times = [r["time_ms"] for r in results]
        stats = {
            "search_type": search_type,
            "iterations": len(results),
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "p95_ms": np.percentile(times, 95),
            "p99_ms": np.percentile(times, 99),
        }

        # Group by query type
        by_type = {}
        for query_type in TEST_QUERIES.keys():
            type_times = [r["time_ms"] for r in results if r["query_type"] == query_type]
            if type_times:
                by_type[query_type] = {
                    "mean_ms": statistics.mean(type_times),
                    "count": len(type_times),
                }
        stats["by_query_type"] = by_type

        return stats

    return {"search_type": search_type, "error": "No successful requests"}


async def benchmark_cache_performance(iterations: int = 20) -> dict:
    """Benchmark cache performance by making repeated requests."""
    base_url = "http://localhost:8000/api/v1/search"
    cache_queries = ["test", "word", "example"]  # Use same queries to ensure cache hits

    console.print("\n[cyan]Benchmarking cache performance...[/cyan]")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Warm up cache
        console.print("  Warming up cache...")
        for query in cache_queries:
            await client.get(f"{base_url}/{query}", params={"max_results": 20})

        # Measure cached responses
        results = []
        for i in range(iterations):
            query = random.choice(cache_queries)
            time_ms = await measure_request_time(
                client, f"{base_url}/{query}", params={"max_results": 20}
            )
            if time_ms > 0:
                results.append(time_ms)

    if results:
        return {
            "search_type": "cache",
            "iterations": len(results),
            "mean_ms": statistics.mean(results),
            "median_ms": statistics.median(results),
            "min_ms": min(results),
            "max_ms": max(results),
            "p95_ms": np.percentile(results, 95),
        }

    return {"search_type": "cache", "error": "No successful requests"}


async def benchmark_concurrent_load(
    concurrent_requests: int = 20, duration_seconds: int = 10
) -> dict:
    """Benchmark system under concurrent load."""
    base_url = "http://localhost:8000/api/v1/search"

    console.print(
        f"\n[cyan]Benchmarking concurrent load ({concurrent_requests} concurrent requests)...[/cyan]"
    )

    start_time = time.time()
    end_time = start_time + duration_seconds
    results = []
    errors = 0

    async def make_requests():
        nonlocal errors
        async with httpx.AsyncClient(timeout=30.0) as client:
            while time.time() < end_time:
                query = random.choice(random.choice(list(TEST_QUERIES.values())))
                try:
                    time_ms = await measure_request_time(
                        client, f"{base_url}/{query}", params={"max_results": 10}
                    )
                    if time_ms > 0:
                        results.append(time_ms)
                    else:
                        errors += 1
                except Exception:
                    errors += 1

                await asyncio.sleep(0.1)  # Small delay between requests

    # Run concurrent tasks
    tasks = [make_requests() for _ in range(concurrent_requests)]
    await asyncio.gather(*tasks)

    duration = time.time() - start_time
    total_requests = len(results) + errors

    if results:
        return {
            "search_type": "concurrent",
            "concurrent_requests": concurrent_requests,
            "duration_seconds": duration,
            "total_requests": total_requests,
            "successful_requests": len(results),
            "errors": errors,
            "error_rate": errors / total_requests if total_requests > 0 else 0,
            "throughput_qps": total_requests / duration,
            "mean_ms": statistics.mean(results),
            "median_ms": statistics.median(results),
            "p95_ms": np.percentile(results, 95),
            "p99_ms": np.percentile(results, 99),
        }

    return {"search_type": "concurrent", "error": "No successful requests"}


def display_results(results: list[dict]):
    """Display benchmark results in a formatted table."""
    # Main results table
    table = Table(title="Search Performance Benchmark Results")
    table.add_column("Search Type", style="cyan", no_wrap=True)
    table.add_column("Iterations", style="white")
    table.add_column("Mean (ms)", style="yellow")
    table.add_column("Median (ms)", style="yellow")
    table.add_column("P95 (ms)", style="magenta")
    table.add_column("P99 (ms)", style="magenta")
    table.add_column("Min (ms)", style="green")
    table.add_column("Max (ms)", style="red")

    for result in results:
        if "error" in result:
            table.add_row(result["search_type"], "ERROR", "-", "-", "-", "-", "-", "-")
        else:
            table.add_row(
                result["search_type"],
                str(result.get("iterations", "-")),
                f"{result.get('mean_ms', 0):.2f}",
                f"{result.get('median_ms', 0):.2f}",
                f"{result.get('p95_ms', 0):.2f}",
                f"{result.get('p99_ms', 0):.2f}",
                f"{result.get('min_ms', 0):.2f}",
                f"{result.get('max_ms', 0):.2f}",
            )

    console.print("\n")
    console.print(table)

    # Concurrent load details
    concurrent_result = next((r for r in results if r.get("search_type") == "concurrent"), None)
    if concurrent_result and "error" not in concurrent_result:
        console.print("\n[bold]Concurrent Load Test Details:[/bold]")
        console.print(f"  Total Requests: {concurrent_result['total_requests']}")
        console.print(f"  Successful: {concurrent_result['successful_requests']}")
        console.print(
            f"  Errors: {concurrent_result['errors']} ({concurrent_result['error_rate']:.1%})"
        )
        console.print(f"  Throughput: {concurrent_result['throughput_qps']:.2f} QPS")

    # Performance assessment
    console.print("\n[bold]Performance Assessment:[/bold]")
    targets = {
        "exact": 1.0,
        "fuzzy": 5.0,
        "semantic": 10.0,
        "combined": 10.0,
        "cache": 0.5,
    }

    for result in results:
        if "error" not in result and result["search_type"] in targets:
            target = targets[result["search_type"]]
            p95 = result.get("p95_ms", 0)
            if p95 <= target:
                console.print(
                    f"  ✅ {result['search_type']}: P95 = {p95:.2f}ms (target: <{target}ms)"
                )
            else:
                console.print(
                    f"  ❌ {result['search_type']}: P95 = {p95:.2f}ms (target: <{target}ms)"
                )


def save_results(results: list[dict], filename: str = None):
    """Save benchmark results to JSON file with human-readable naming."""
    if filename is None:
        # Create human-readable timestamp: 2025-01-15_14-30-25_search_benchmark
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}_search_benchmark.json"

    output_dir = Path("benchmark_results")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / filename

    # Enhanced metadata
    benchmark_data = {
        "benchmark_info": {
            "timestamp": datetime.now().isoformat(),
            "readable_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "benchmark_type": "search_performance",
            "version": "1.0",
        },
        "results": results,
    }

    with open(output_path, "w") as f:
        json.dump(benchmark_data, f, indent=2)

    console.print(f"\n[green]Results saved to: {output_path}[/green]")
    return output_path


async def main():
    """Run all benchmarks."""
    console.print("[bold blue]Floridify Search Performance Benchmark[/bold blue]")
    console.print("=" * 50)

    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code != 200:
                console.print("[red]Error: Server is not responding correctly[/red]")
                return
    except Exception:
        console.print("[red]Error: Cannot connect to server at http://localhost:8000[/red]")
        console.print("[red]Make sure the backend server is running[/red]")
        return

    results = []

    # Run benchmarks
    try:
        # Individual search types
        results.append(await benchmark_search_type("exact", iterations=30))
        results.append(await benchmark_search_type("fuzzy", iterations=30))
        results.append(await benchmark_search_type("semantic", iterations=30))
        results.append(await benchmark_search_type("combined", iterations=30))

        # Cache performance
        results.append(await benchmark_cache_performance(iterations=20))

        # Concurrent load
        results.append(await benchmark_concurrent_load(concurrent_requests=10, duration_seconds=5))

    except Exception as e:
        console.print(f"[red]Error during benchmarking: {e}[/red]")
        import traceback

        traceback.print_exc()

    # Display and save results
    if results:
        display_results(results)
        save_results(results)


if __name__ == "__main__":
    asyncio.run(main())
