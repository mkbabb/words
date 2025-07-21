"""Performance benchmarking script to ensure no regression.

This script runs comprehensive performance tests and generates a report
comparing current performance against baseline metrics.
"""

from __future__ import annotations

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""
    endpoint: str
    method: str
    params: dict[str, str]
    times: list[float]
    status_codes: list[int]
    
    @property
    def avg_time(self) -> float:
        """Average response time in milliseconds."""
        return statistics.mean(self.times) * 1000 if self.times else 0
    
    @property
    def min_time(self) -> float:
        """Minimum response time in milliseconds."""
        return min(self.times) * 1000 if self.times else 0
    
    @property
    def max_time(self) -> float:
        """Maximum response time in milliseconds."""  
        return max(self.times) * 1000 if self.times else 0
    
    @property
    def p95_time(self) -> float:
        """95th percentile response time in milliseconds."""
        if not self.times:
            return 0
        sorted_times = sorted(self.times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index] * 1000
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful requests."""
        if not self.status_codes:
            return 0
        success_count = sum(1 for code in self.status_codes if 200 <= code < 300)
        return (success_count / len(self.status_codes)) * 100


class PerformanceBenchmark:
    """Performance benchmarking for backwards compatibility."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.console = Console()
        
    def run_single_request(self, endpoint: str, method: str = "GET", params: dict[str, str] | None = None) -> tuple[float, int]:
        """Run a single request and return timing and status code."""
        with httpx.Client() as client:
            start = time.perf_counter()
            response = client.request(method, f"{self.base_url}{endpoint}", params=params)
            elapsed = time.perf_counter() - start
            return elapsed, response.status_code
    
    async def run_async_request(self, endpoint: str, method: str = "GET", params: dict[str, str] | None = None) -> tuple[float, int]:
        """Run an async request and return timing and status code."""
        async with httpx.AsyncClient() as client:
            start = time.perf_counter()
            response = await client.request(method, f"{self.base_url}{endpoint}", params=params)
            elapsed = time.perf_counter() - start
            return elapsed, response.status_code
    
    def benchmark_endpoint(self, endpoint: str, method: str = "GET", params: dict[str, str] | None = None, 
                         iterations: int = 100, concurrent: bool = False) -> BenchmarkResult:
        """Benchmark a single endpoint."""
        times = []
        status_codes = []
        
        if concurrent:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(self.run_single_request, endpoint, method, params)
                    for _ in range(iterations)
                ]
                
                for future in as_completed(futures):
                    elapsed, status = future.result()
                    times.append(elapsed)
                    status_codes.append(status)
        else:
            for _ in range(iterations):
                elapsed, status = self.run_single_request(endpoint, method, params)
                times.append(elapsed)
                status_codes.append(status)
        
        return BenchmarkResult(
            endpoint=endpoint,
            method=method,
            params=params or {},
            times=times,
            status_codes=status_codes
        )
    
    def run_benchmarks(self) -> list[BenchmarkResult]:
        """Run all benchmarks."""
        benchmarks = [
            # Lookup endpoints - various scenarios
            ("Lookup - Simple word", "/api/v1/lookup/happy", "GET", None),
            ("Lookup - With force refresh", "/api/v1/lookup/algorithm", "GET", {"force_refresh": "true"}),
            ("Lookup - No AI", "/api/v1/lookup/beautiful", "GET", {"no_ai": "true"}),
            ("Lookup - Multiple providers", "/api/v1/lookup/computer", "GET", 
             {"providers": ["wiktionary", "dictionary_com"]}),
            
            # Search endpoints - various methods
            ("Search - Simple", "/api/v1/search", "GET", {"q": "test"}),
            ("Search - Fuzzy", "/api/v1/search", "GET", {"q": "happ", "method": "fuzzy"}),
            ("Search - Semantic", "/api/v1/search", "GET", {"q": "joy", "method": "semantic"}),
            ("Search - With filters", "/api/v1/search", "GET", 
             {"q": "algorithm", "max_results": "10", "min_score": "0.8"}),
            
            # Other endpoints
            ("Health check", "/api/v1/health", "GET", None),
            ("Synonyms", "/api/v1/synonyms/happy", "GET", None),
        ]
        
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            for name, endpoint, method, params in benchmarks:
                task = progress.add_task(f"Benchmarking {name}...", total=None)
                
                # Run with different concurrency levels
                result_seq = self.benchmark_endpoint(endpoint, method, params, iterations=50, concurrent=False)
                result_con = self.benchmark_endpoint(endpoint, method, params, iterations=50, concurrent=True)
                
                # Store both results
                results.append((f"{name} (Sequential)", result_seq))
                results.append((f"{name} (Concurrent)", result_con))
                
                progress.remove_task(task)
        
        return results
    
    def generate_report(self, results: list[tuple[str, BenchmarkResult]]) -> None:
        """Generate performance report."""
        self.console.print("\n[bold cyan]Performance Benchmark Report[/bold cyan]\n")
        
        # Create results table
        table = Table(title="API Performance Metrics")
        table.add_column("Endpoint", style="cyan", no_wrap=True)
        table.add_column("Avg (ms)", justify="right", style="green")
        table.add_column("Min (ms)", justify="right")
        table.add_column("Max (ms)", justify="right")
        table.add_column("P95 (ms)", justify="right", style="yellow")
        table.add_column("Success %", justify="right", style="magenta")
        
        # Baseline thresholds (milliseconds)
        thresholds = {
            "Lookup": {"avg": 500, "p95": 800},
            "Search": {"avg": 200, "p95": 400},
            "Health": {"avg": 50, "p95": 100},
            "Synonyms": {"avg": 300, "p95": 500},
        }
        
        regressions = []
        
        for name, result in results:
            # Determine threshold based on endpoint type
            threshold_key = None
            for key in thresholds:
                if key.lower() in name.lower():
                    threshold_key = key
                    break
            
            # Check for regression
            is_regression = False
            if threshold_key:
                if result.avg_time > thresholds[threshold_key]["avg"]:
                    is_regression = True
                    regressions.append(f"{name}: avg {result.avg_time:.1f}ms > threshold {thresholds[threshold_key]['avg']}ms")
                elif result.p95_time > thresholds[threshold_key]["p95"]:
                    is_regression = True
                    regressions.append(f"{name}: p95 {result.p95_time:.1f}ms > threshold {thresholds[threshold_key]['p95']}ms")
            
            # Add row with highlighting for regressions
            style = "red" if is_regression else None
            table.add_row(
                name,
                f"{result.avg_time:.1f}",
                f"{result.min_time:.1f}",
                f"{result.max_time:.1f}",
                f"{result.p95_time:.1f}",
                f"{result.success_rate:.1f}%",
                style=style
            )
        
        self.console.print(table)
        
        # Report regressions
        if regressions:
            self.console.print("\n[bold red]⚠️  Performance Regressions Detected:[/bold red]")
            for regression in regressions:
                self.console.print(f"  • {regression}")
        else:
            self.console.print("\n[bold green]✅ No performance regressions detected![/bold green]")
        
        # Additional metrics
        self.console.print("\n[bold]Summary Statistics:[/bold]")
        
        # Calculate overall metrics
        all_times = []
        for _, result in results:
            all_times.extend(result.times)
        
        if all_times:
            overall_avg = statistics.mean(all_times) * 1000
            overall_p95 = sorted(all_times)[int(len(all_times) * 0.95)] * 1000
            
            self.console.print(f"  • Overall average response time: {overall_avg:.1f}ms")
            self.console.print(f"  • Overall P95 response time: {overall_p95:.1f}ms")
            self.console.print(f"  • Total requests: {len(all_times)}")
    
    def save_results(self, results: list[tuple[str, BenchmarkResult]], filename: str = "benchmark_results.json") -> None:
        """Save benchmark results to JSON file."""
        data = {
            "timestamp": datetime.now(),
            "results": [
                {
                    "name": name,
                    "endpoint": result.endpoint,
                    "method": result.method,
                    "params": result.params,
                    "metrics": {
                        "avg_ms": result.avg_time,
                        "min_ms": result.min_time,
                        "max_ms": result.max_time,
                        "p95_ms": result.p95_time,
                        "success_rate": result.success_rate,
                        "total_requests": len(result.times),
                    }
                }
                for name, result in results
            ]
        }
        
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        
        self.console.print(f"\n[green]Results saved to {filename}[/green]")


def main():
    """Run performance benchmarks."""
    console = Console()
    
    # Check if server is running
    try:
        response = httpx.get("http://localhost:8000/api/v1/health")
        if response.status_code != 200:
            console.print("[red]Server health check failed![/red]")
            return
    except Exception:
        console.print("[red]Could not connect to server at http://localhost:8000[/red]")
        console.print("Please ensure the backend server is running.")
        return
    
    # Run benchmarks
    benchmark = PerformanceBenchmark()
    console.print("[bold cyan]Starting performance benchmarks...[/bold cyan]\n")
    
    results = benchmark.run_benchmarks()
    benchmark.generate_report(results)
    benchmark.save_results(results)
    
    # Check for critical regressions
    critical_regressions = []
    for name, result in results:
        if result.avg_time > 1000:  # 1 second
            critical_regressions.append(f"{name}: {result.avg_time:.1f}ms average")
    
    if critical_regressions:
        console.print("\n[bold red]❌ CRITICAL: Some endpoints exceed 1s response time:[/bold red]")
        for regression in critical_regressions:
            console.print(f"  • {regression}")
        exit(1)
    
    console.print("\n[bold green]✅ All performance benchmarks passed![/bold green]")


if __name__ == "__main__":
    main()