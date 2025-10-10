#!/usr/bin/env python3
"""
Profile exact search performance via API to identify bottlenecks.
Works with running API server.
"""

import asyncio
import statistics
import time
from collections import defaultdict

import httpx
from rich.console import Console
from rich.table import Table

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
    "the",
    "a",
    "and",
    "run",
]


async def measure_exact_search_time(client: httpx.AsyncClient, query: str) -> dict:
    """Measure exact search time and extract server timing info."""
    start_time = time.perf_counter()

    try:
        response = await client.get(
            f"http://localhost:8000/api/v1/search/{query}",
            params={"mode": "exact", "max_results": 1},
        )
        end_time = time.perf_counter()

        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}"}

        total_time_ms = (end_time - start_time) * 1000

        # Extract server timing headers if available
        server_time = None
        if "X-Process-Time" in response.headers:
            server_time = float(response.headers["X-Process-Time"]) * 1000  # Convert to ms

        result = response.json()
        found = len(result.get("results", [])) > 0

        return {
            "query": query,
            "total_time_ms": total_time_ms,
            "server_time_ms": server_time,
            "network_time_ms": total_time_ms - server_time if server_time else None,
            "found": found,
        }

    except Exception as e:
        return {"query": query, "error": str(e)}


async def benchmark_exact_search():
    """Benchmark exact search performance."""
    console.print("[bold blue]Exact Search API Performance Benchmark[/bold blue]")
    console.print("=" * 60)

    # Check server
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code != 200:
                console.print("[red]Error: Server not responding correctly[/red]")
                return
    except Exception:
        console.print("[red]Error: Cannot connect to server at http://localhost:8000[/red]")
        return

    # Run benchmark
    iterations = 100
    results = []

    console.print(f"\n[cyan]Running {iterations} exact searches...[/cyan]")

    async with httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=10.0,
        ),
    ) as client:
        # Warm up
        for query in TEST_QUERIES[:3]:
            await measure_exact_search_time(client, query)

        # Actual benchmark
        for i in range(iterations):
            query = TEST_QUERIES[i % len(TEST_QUERIES)]
            result = await measure_exact_search_time(client, query)
            if "error" not in result:
                results.append(result)

            if (i + 1) % 20 == 0:
                console.print(f"  Progress: {i + 1}/{iterations}")

    # Analyze results
    if not results:
        console.print("[red]No successful results[/red]")
        return

    total_times = [r["total_time_ms"] for r in results]
    server_times = [r["server_time_ms"] for r in results if r["server_time_ms"] is not None]
    network_times = [r["network_time_ms"] for r in results if r["network_time_ms"] is not None]

    # Statistics
    console.print("\n[bold]Performance Statistics:[/bold]")
    table = Table(title="Exact Search Timing Breakdown")
    table.add_column("Metric", style="cyan")
    table.add_column("Mean (ms)", style="yellow")
    table.add_column("Median (ms)", style="yellow")
    table.add_column("P95 (ms)", style="magenta")
    table.add_column("P99 (ms)", style="magenta")
    table.add_column("Min (ms)", style="green")
    table.add_column("Max (ms)", style="red")

    def add_stats_row(name, times):
        if times:
            table.add_row(
                name,
                f"{statistics.mean(times):.3f}",
                f"{statistics.median(times):.3f}",
                f"{sorted(times)[int(len(times) * 0.95)]:.3f}",
                f"{sorted(times)[int(len(times) * 0.99)]:.3f}",
                f"{min(times):.3f}",
                f"{max(times):.3f}",
            )
        else:
            table.add_row(name, "-", "-", "-", "-", "-", "-")

    add_stats_row("Total (client)", total_times)
    add_stats_row("Server processing", server_times)
    add_stats_row("Network overhead", network_times)

    console.print("\n")
    console.print(table)

    # Hit rate
    hit_rate = sum(1 for r in results if r["found"]) / len(results) * 100
    console.print(f"\n[bold]Match hit rate:[/bold] {hit_rate:.1f}%")

    # Performance assessment
    if server_times:
        p95_server = sorted(server_times)[int(len(server_times) * 0.95)]
        target_ms = 2.0

        console.print("\n[bold]Performance Assessment:[/bold]")
        if p95_server <= target_ms:
            console.print(
                f"  ✅ Server P95: {p95_server:.3f}ms (target: <{target_ms}ms) - PASSING"
            )
        else:
            console.print(
                f"  ❌ Server P95: {p95_server:.3f}ms (target: <{target_ms}ms) - NEEDS OPTIMIZATION"
            )
            improvement_needed = ((p95_server / target_ms) - 1) * 100
            console.print(f"     Need {improvement_needed:.1f}% improvement to reach target")

    # Query breakdown
    query_times = defaultdict(list)
    for r in results:
        if r.get("server_time_ms"):
            query_times[r["query"]].append(r["server_time_ms"])

    console.print("\n[bold]Per-Query Performance:[/bold]")
    for query in TEST_QUERIES:
        if query in query_times:
            times = query_times[query]
            mean_ms = statistics.mean(times)
            console.print(f"  {query:15s}: {mean_ms:.3f}ms mean")


async def main():
    """Run benchmark."""
    try:
        await benchmark_exact_search()
        console.print("\n[bold green]Profiling complete![/bold green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
