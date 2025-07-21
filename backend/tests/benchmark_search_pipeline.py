"""Comprehensive search pipeline benchmarking suite.

Tests both core search pipeline (direct) and REST API layer performance
with advanced metrics, memory tracking, and optimization insights.
"""

from __future__ import annotations

import asyncio
import gc
import json
import psutil
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.tree import Tree

# Import core search components for direct testing
from floridify.core.search_pipeline import get_search_engine, search_word_pipeline
from floridify.search.language import LanguageSearch
from floridify.models.search import Language, SearchMethod


@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    times: list[float] = field(default_factory=list)
    memory_usage: list[float] = field(default_factory=list)
    cpu_percent: list[float] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    errors: list[str] = field(default_factory=list)
    
    @property
    def avg_time_ms(self) -> float:
        return statistics.mean(self.times) * 1000 if self.times else 0
    
    @property
    def p95_time_ms(self) -> float:
        if not self.times:
            return 0
        return sorted(self.times)[int(len(self.times) * 0.95)] * 1000
    
    @property
    def avg_memory_mb(self) -> float:
        return statistics.mean(self.memory_usage) if self.memory_usage else 0
    
    @property
    def peak_memory_mb(self) -> float:
        return max(self.memory_usage) if self.memory_usage else 0
    
    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""
    iterations: int = 100
    warmup_iterations: int = 10
    concurrent_workers: int = 10
    memory_sampling_interval: float = 0.1
    enable_profiling: bool = True
    test_data_size: str = "small"  # small, medium, large


class SearchPipelineBenchmark:
    """Comprehensive search pipeline benchmarking."""
    
    def __init__(self, config: BenchmarkConfig = None):
        self.config = config or BenchmarkConfig()
        self.console = Console()
        self.process = psutil.Process()
        self._search_engine: LanguageSearch | None = None
        
        # Test queries organized by complexity
        self.test_queries = {
            "simple": ["cat", "dog", "run", "jump", "happy"],
            "medium": ["algorithm", "beautiful", "understanding", "consciousness"],
            "complex": ["antidisestablishmentarianism", "pneumonoultramicroscopicsilicovolcanoconiosiswith"],
            "phrases": ["machine learning", "artificial intelligence", "quantum computing"],
            "fuzzy": ["algoritm", "beatiful", "hapiness", "recieve"],  # intentional typos
            "semantic": ["joy", "bliss", "elation", "euphoria", "contentment"]  # similar meanings
        }
    
    async def _get_search_engine(self) -> LanguageSearch:
        """Get or initialize search engine with timing."""
        if self._search_engine is None:
            start_time = time.perf_counter()
            self._search_engine = await get_search_engine()
            init_time = time.perf_counter() - start_time
            self.console.print(f"[dim]Search engine initialization: {init_time*1000:.1f}ms[/dim]")
        return self._search_engine
    
    def _monitor_memory(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024
    
    def _monitor_cpu(self) -> float:
        """Get current CPU usage percentage."""
        return self.process.cpu_percent()
    
    async def benchmark_core_search(
        self,
        query: str,
        method: SearchMethod = SearchMethod.AUTO,
        iterations: int = None
    ) -> PerformanceMetrics:
        """Benchmark core search pipeline directly (no REST)."""
        iterations = iterations or self.config.iterations
        metrics = PerformanceMetrics()
        
        # Get search engine
        search_engine = await self._get_search_engine()
        
        # Warmup
        for _ in range(self.config.warmup_iterations):
            try:
                await search_word_pipeline(query, max_results=20, languages=[Language.ENGLISH])
            except Exception:
                pass
        
        # Benchmark
        for i in range(iterations):
            gc.collect()  # Force garbage collection for consistent memory measurements
            
            start_memory = self._monitor_memory()
            start_cpu = self._monitor_cpu()
            start_time = time.perf_counter()
            
            try:
                results = await search_word_pipeline(
                    query=query,
                    max_results=20,
                    min_score=0.6,
                    languages=[Language.ENGLISH],
                    search_method=method
                )
                
                elapsed = time.perf_counter() - start_time
                end_memory = self._monitor_memory()
                
                metrics.times.append(elapsed)
                metrics.memory_usage.append(end_memory - start_memory)
                metrics.cpu_percent.append(self._monitor_cpu() - start_cpu)
                
                # Track cache performance (if available)
                if hasattr(search_engine, '_cache_stats'):
                    metrics.cache_hits += getattr(search_engine._cache_stats, 'hits', 0)
                    metrics.cache_misses += getattr(search_engine._cache_stats, 'misses', 0)
                
            except Exception as e:
                metrics.errors.append(str(e))
        
        return metrics
    
    async def benchmark_rest_api(
        self,
        endpoint: str,
        params: dict[str, Any],
        iterations: int = None
    ) -> PerformanceMetrics:
        """Benchmark REST API endpoints."""
        iterations = iterations or self.config.iterations
        metrics = PerformanceMetrics()
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Warmup
            for _ in range(self.config.warmup_iterations):
                try:
                    await client.get(f"{base_url}{endpoint}", params=params)
                except Exception:
                    pass
            
            # Benchmark
            for i in range(iterations):
                start_memory = self._monitor_memory()
                start_time = time.perf_counter()
                
                try:
                    response = await client.get(f"{base_url}{endpoint}", params=params)
                    elapsed = time.perf_counter() - start_time
                    end_memory = self._monitor_memory()
                    
                    metrics.times.append(elapsed)
                    metrics.memory_usage.append(end_memory - start_memory)
                    
                    # Check for cache headers
                    if 'X-Cache-Hit' in response.headers:
                        if response.headers['X-Cache-Hit'] == 'true':
                            metrics.cache_hits += 1
                        else:
                            metrics.cache_misses += 1
                    
                except Exception as e:
                    metrics.errors.append(str(e))
        
        return metrics
    
    async def benchmark_search_methods(self, query: str) -> dict[str, PerformanceMetrics]:
        """Compare all search methods for a single query."""
        methods = [SearchMethod.EXACT, SearchMethod.FUZZY, SearchMethod.SEMANTIC, SearchMethod.AUTO]
        results = {}
        
        for method in methods:
            try:
                metrics = await self.benchmark_core_search(query, method, iterations=50)
                results[method.value] = metrics
            except Exception as e:
                self.console.print(f"[red]Error benchmarking {method.value}: {e}[/red]")
                results[method.value] = PerformanceMetrics(errors=[str(e)])
        
        return results
    
    async def benchmark_concurrent_load(self, queries: list[str], workers: int = None) -> PerformanceMetrics:
        """Benchmark concurrent search load."""
        workers = workers or self.config.concurrent_workers
        metrics = PerformanceMetrics()
        
        async def search_task(query: str) -> tuple[float, float]:
            start_memory = self._monitor_memory()
            start_time = time.perf_counter()
            
            try:
                await search_word_pipeline(query, max_results=20, languages=[Language.ENGLISH])
                elapsed = time.perf_counter() - start_time
                memory_delta = self._monitor_memory() - start_memory
                return elapsed, memory_delta
            except Exception as e:
                metrics.errors.append(str(e))
                return 0.0, 0.0
        
        # Create tasks
        tasks = []
        for _ in range(self.config.iterations):
            query = queries[len(tasks) % len(queries)]
            tasks.append(search_task(query))
        
        # Run with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(workers)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        start_time = time.perf_counter()
        results = await asyncio.gather(*[limited_task(task) for task in tasks])
        total_time = time.perf_counter() - start_time
        
        for elapsed, memory_delta in results:
            if elapsed > 0:
                metrics.times.append(elapsed)
                metrics.memory_usage.append(memory_delta)
        
        # Calculate throughput
        throughput = len(results) / total_time
        self.console.print(f"[dim]Concurrent throughput: {throughput:.1f} requests/second[/dim]")
        
        return metrics
    
    def compare_core_vs_rest(self, core_metrics: PerformanceMetrics, rest_metrics: PerformanceMetrics) -> dict[str, float]:
        """Compare core vs REST performance."""
        if not core_metrics.times or not rest_metrics.times:
            return {}
        
        return {
            "rest_overhead_avg_ms": rest_metrics.avg_time_ms - core_metrics.avg_time_ms,
            "rest_overhead_p95_ms": rest_metrics.p95_time_ms - core_metrics.p95_time_ms,
            "rest_overhead_percent": ((rest_metrics.avg_time_ms / core_metrics.avg_time_ms) - 1) * 100,
            "memory_overhead_mb": rest_metrics.avg_memory_mb - core_metrics.avg_memory_mb,
        }
    
    async def run_comprehensive_benchmark(self) -> dict[str, Any]:
        """Run complete benchmark suite."""
        results = {
            "timestamp": datetime.now(),
            "config": self.config.__dict__,
            "core_search": {},
            "rest_api": {},
            "search_methods": {},
            "concurrent_load": {},
            "comparison": {},
            "optimization_insights": {}
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            
            # 1. Core search benchmarks
            task1 = progress.add_task("Core search benchmarks...", total=len(self.test_queries))
            for category, queries in self.test_queries.items():
                category_results = {}
                for query in queries:
                    metrics = await self.benchmark_core_search(query)
                    category_results[query] = {
                        "avg_ms": metrics.avg_time_ms,
                        "p95_ms": metrics.p95_time_ms,
                        "memory_mb": metrics.avg_memory_mb,
                        "errors": len(metrics.errors)
                    }
                results["core_search"][category] = category_results
                progress.advance(task1)
            
            # 2. REST API benchmarks
            task2 = progress.add_task("REST API benchmarks...", total=len(self.test_queries))
            for category, queries in self.test_queries.items():
                category_results = {}
                for query in queries:
                    metrics = await self.benchmark_rest_api("/api/v1/search", {"q": query})
                    category_results[query] = {
                        "avg_ms": metrics.avg_time_ms,
                        "p95_ms": metrics.p95_time_ms,
                        "memory_mb": metrics.avg_memory_mb,
                        "cache_hit_rate": metrics.cache_hit_rate,
                        "errors": len(metrics.errors)
                    }
                results["rest_api"][category] = category_results
                progress.advance(task2)
            
            # 3. Search method comparison
            task3 = progress.add_task("Search method comparison...", total=1)
            test_query = "algorithm"
            method_results = await self.benchmark_search_methods(test_query)
            results["search_methods"][test_query] = {
                method: {
                    "avg_ms": metrics.avg_time_ms,
                    "p95_ms": metrics.p95_time_ms,
                    "memory_mb": metrics.avg_memory_mb,
                    "errors": len(metrics.errors)
                }
                for method, metrics in method_results.items()
            }
            progress.advance(task3)
            
            # 4. Concurrent load testing
            task4 = progress.add_task("Concurrent load testing...", total=1)
            all_queries = [q for queries in self.test_queries.values() for q in queries]
            concurrent_metrics = await self.benchmark_concurrent_load(all_queries[:10])
            results["concurrent_load"] = {
                "avg_ms": concurrent_metrics.avg_time_ms,
                "p95_ms": concurrent_metrics.p95_time_ms,
                "memory_mb": concurrent_metrics.avg_memory_mb,
                "errors": len(concurrent_metrics.errors)
            }
            progress.advance(task4)
            
            # 5. Generate comparisons and insights
            task5 = progress.add_task("Generating insights...", total=1)
            
            # Compare core vs REST for a sample query
            sample_query = "algorithm"
            core_sample = await self.benchmark_core_search(sample_query, iterations=50)
            rest_sample = await self.benchmark_rest_api("/api/v1/search", {"q": sample_query}, iterations=50)
            
            results["comparison"] = self.compare_core_vs_rest(core_sample, rest_sample)
            results["optimization_insights"] = self._generate_optimization_insights(results)
            progress.advance(task5)
        
        return results
    
    def _generate_optimization_insights(self, results: dict[str, Any]) -> dict[str, list[str]]:
        """Generate actionable optimization insights."""
        insights = {
            "critical": [],
            "high_impact": [],
            "medium_impact": [],
            "low_impact": []
        }
        
        # Check REST overhead
        if "comparison" in results and results["comparison"]:
            overhead_percent = results["comparison"].get("rest_overhead_percent", 0)
            if overhead_percent > 100:
                insights["critical"].append(f"REST overhead is {overhead_percent:.1f}% - investigate serialization/validation")
            elif overhead_percent > 50:
                insights["high_impact"].append(f"REST overhead is {overhead_percent:.1f}% - optimize response creation")
        
        # Check search method performance
        if "search_methods" in results:
            for query, methods in results["search_methods"].items():
                semantic_time = methods.get("semantic", {}).get("avg_ms", 0)
                exact_time = methods.get("exact", {}).get("avg_ms", 0)
                
                if semantic_time > exact_time * 10:
                    insights["high_impact"].append("Semantic search is significantly slower - consider FAISS optimization")
        
        # Check memory usage patterns
        core_memory = 0
        rest_memory = 0
        for category in results.get("core_search", {}).values():
            for query_data in category.values():
                core_memory += query_data.get("memory_mb", 0)
        
        for category in results.get("rest_api", {}).values():
            for query_data in category.values():
                rest_memory += query_data.get("memory_mb", 0)
        
        if rest_memory > core_memory * 2:
            insights["medium_impact"].append("REST API uses significantly more memory - investigate object creation")
        
        # Check for slow queries
        slow_queries = []
        for category, queries in results.get("core_search", {}).items():
            for query, data in queries.items():
                if data.get("avg_ms", 0) > 100:
                    slow_queries.append(f"{query} ({data['avg_ms']:.1f}ms)")
        
        if slow_queries:
            insights["medium_impact"].append(f"Slow queries detected: {', '.join(slow_queries[:3])}")
        
        # Check error rates
        total_errors = 0
        total_tests = 0
        for category in results.get("core_search", {}).values():
            for query_data in category.values():
                total_errors += query_data.get("errors", 0)
                total_tests += 1
        
        if total_errors > 0:
            error_rate = (total_errors / total_tests) * 100
            if error_rate > 5:
                insights["critical"].append(f"High error rate: {error_rate:.1f}% - investigate failures")
            elif error_rate > 1:
                insights["high_impact"].append(f"Error rate: {error_rate:.1f}% - improve error handling")
        
        return insights
    
    def generate_report(self, results: dict[str, Any]) -> None:
        """Generate comprehensive performance report."""
        self.console.print("\n[bold cyan]🚀 Search Pipeline Performance Analysis[/bold cyan]\n")
        
        # Performance comparison table
        table = Table(title="Core vs REST Performance Comparison")
        table.add_column("Metric", style="cyan")
        table.add_column("Core Pipeline", justify="right", style="green")
        table.add_column("REST API", justify="right", style="blue")
        table.add_column("Overhead", justify="right", style="yellow")
        
        if results.get("comparison"):
            comp = results["comparison"]
            table.add_row(
                "Average Response Time",
                "Baseline",
                f"+{comp.get('rest_overhead_avg_ms', 0):.1f}ms",
                f"{comp.get('rest_overhead_percent', 0):.1f}%"
            )
            table.add_row(
                "P95 Response Time",
                "Baseline",
                f"+{comp.get('rest_overhead_p95_ms', 0):.1f}ms",
                "-"
            )
            table.add_row(
                "Memory Usage",
                "Baseline",
                f"+{comp.get('memory_overhead_mb', 0):.1f}MB",
                "-"
            )
        
        self.console.print(table)
        
        # Search method comparison
        if results.get("search_methods"):
            self.console.print("\n[bold]Search Method Performance:[/bold]")
            method_table = Table()
            method_table.add_column("Method", style="cyan")
            method_table.add_column("Avg (ms)", justify="right")
            method_table.add_column("P95 (ms)", justify="right")
            method_table.add_column("Memory (MB)", justify="right")
            
            for query, methods in results["search_methods"].items():
                self.console.print(f"\n[dim]Query: {query}[/dim]")
                for method, data in methods.items():
                    method_table.add_row(
                        method,
                        f"{data.get('avg_ms', 0):.1f}",
                        f"{data.get('p95_ms', 0):.1f}",
                        f"{data.get('memory_mb', 0):.2f}"
                    )
            
            self.console.print(method_table)
        
        # Optimization insights
        insights = results.get("optimization_insights", {})
        if any(insights.values()):
            self.console.print("\n[bold]🎯 Optimization Insights:[/bold]")
            
            insight_tree = Tree("Recommendations")
            
            for priority, items in insights.items():
                if items:
                    priority_node = insight_tree.add(f"[bold]{priority.title()} Priority[/bold]")
                    for item in items:
                        priority_node.add(item)
            
            self.console.print(insight_tree)
        
        # Summary statistics
        if results.get("concurrent_load"):
            concurrent = results["concurrent_load"]
            self.console.print(f"\n[bold]Concurrent Performance:[/bold]")
            self.console.print(f"  • Average response time: {concurrent.get('avg_ms', 0):.1f}ms")
            self.console.print(f"  • P95 response time: {concurrent.get('p95_ms', 0):.1f}ms")
            self.console.print(f"  • Memory usage: {concurrent.get('memory_mb', 0):.1f}MB")
            
            if concurrent.get('errors', 0) > 0:
                self.console.print(f"  • [red]Errors: {concurrent['errors']}[/red]")
            else:
                self.console.print("  • [green]No errors detected[/green]")
    
    def save_results(self, results: dict[str, Any], filename: str = None) -> None:
        """Save detailed results to JSON."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_pipeline_benchmark_{timestamp}.json"
        
        filepath = Path(filename)
        with filepath.open("w") as f:
            json.dump(results, f, indent=2, default=str)
        
        self.console.print(f"\n[green]✅ Detailed results saved to {filepath}[/green]")


async def main():
    """Run comprehensive search pipeline benchmarking."""
    console = Console()
    
    # Check server availability
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/v1/health", timeout=5.0)
            if response.status_code != 200:
                console.print("[red]❌ Backend server health check failed[/red]")
                return False
    except Exception as e:
        console.print(f"[red]❌ Cannot connect to backend server: {e}[/red]")
        console.print("Please ensure backend is running on http://localhost:8000")
        return False
    
    # Configuration
    config = BenchmarkConfig(
        iterations=100,
        warmup_iterations=10,
        concurrent_workers=10,
        enable_profiling=True
    )
    
    # Run benchmarks
    benchmark = SearchPipelineBenchmark(config)
    console.print("[bold cyan]🔥 Starting comprehensive search pipeline benchmarks...[/bold cyan]")
    console.print(f"[dim]Configuration: {config.iterations} iterations, {config.concurrent_workers} workers[/dim]\n")
    
    try:
        results = await benchmark.run_comprehensive_benchmark()
        benchmark.generate_report(results)
        benchmark.save_results(results)
        
        # Check for critical issues
        insights = results.get("optimization_insights", {})
        if insights.get("critical"):
            console.print(f"\n[bold red]⚠️  CRITICAL ISSUES DETECTED: {len(insights['critical'])}[/bold red]")
            return False
        
        console.print("\n[bold green]✅ All benchmarks completed successfully![/bold green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Benchmark failed: {e}[/red]")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)