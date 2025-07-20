#!/usr/bin/env python3
"""Enhanced comprehensive benchmark suite for floridify lookup pipeline.

This script tests both core lookup pipeline (direct) and REST API performance
with detailed optimization insights.
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
from pathlib import Path
from typing import Any, Callable

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

# Import with correct paths
import sys
sys.path.insert(0, "/Users/mkbabb/Programming/words/backend/src")

from floridify.core.search_pipeline import get_search_engine, search_word_pipeline
from floridify.core.lookup_pipeline import lookup_word_pipeline
from floridify.constants import Language
from floridify.search.constants import SearchMethod


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


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""
    iterations: int = 50
    warmup_iterations: int = 5
    concurrent_workers: int = 5
    enable_profiling: bool = True


class EnhancedLookupBenchmark:
    """Enhanced lookup pipeline benchmarking."""
    
    def __init__(self, config: BenchmarkConfig = None):
        self.config = config or BenchmarkConfig()
        self.console = Console()
        self.process = psutil.Process()
        
        # Test queries organized by complexity and use case
        self.test_queries = {
            "simple": ["cat", "dog", "run", "jump", "happy"],
            "medium": ["algorithm", "beautiful", "understanding", "consciousness"],
            "complex": ["antidisestablishmentarianism", "pneumonoultramicroscopicsilicovolcanoconiosiswith"],
            "phrases": ["machine learning", "artificial intelligence", "quantum computing"],
            "fuzzy": ["algoritm", "beatiful", "hapiness", "recieve"],  # intentional typos
            "semantic": ["joy", "bliss", "elation", "euphoria", "contentment"]  # similar meanings
        }
    
    def _monitor_memory(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024
    
    def _monitor_cpu(self) -> float:
        """Get current CPU usage percentage."""
        return self.process.cpu_percent()
    
    async def benchmark_core_lookup(self, word: str, iterations: int = None) -> PerformanceMetrics:
        """Benchmark core lookup pipeline directly (no REST)."""
        iterations = iterations or self.config.iterations
        metrics = PerformanceMetrics()
        
        # Warmup
        for _ in range(self.config.warmup_iterations):
            try:
                await lookup_word_pipeline(word)
            except Exception:
                pass
        
        # Benchmark
        for i in range(iterations):
            gc.collect()
            
            start_memory = self._monitor_memory()
            start_cpu = self._monitor_cpu()
            start_time = time.perf_counter()
            
            try:
                result = await lookup_word_pipeline(word)
                
                elapsed = time.perf_counter() - start_time
                end_memory = self._monitor_memory()
                
                metrics.times.append(elapsed)
                metrics.memory_usage.append(end_memory - start_memory)
                metrics.cpu_percent.append(self._monitor_cpu() - start_cpu)
                
            except Exception as e:
                metrics.errors.append(str(e))
        
        return metrics
    
    async def benchmark_rest_lookup(self, word: str, iterations: int = None) -> PerformanceMetrics:
        """Benchmark REST API lookup endpoint."""
        iterations = iterations or self.config.iterations
        metrics = PerformanceMetrics()
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Warmup
            for _ in range(self.config.warmup_iterations):
                try:
                    await client.get(f"{base_url}/api/v1/lookup/{word}")
                except Exception:
                    pass
            
            # Benchmark
            for i in range(iterations):
                start_memory = self._monitor_memory()
                start_time = time.perf_counter()
                
                try:
                    response = await client.get(f"{base_url}/api/v1/lookup/{word}")
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
                metrics = await self.benchmark_core_search(query, method, iterations=20)
                results[method.value] = metrics
            except Exception as e:
                self.console.print(f"[red]Error benchmarking {method.value}: {e}[/red]")
                results[method.value] = PerformanceMetrics(errors=[str(e)])
        
        return results
    
    async def benchmark_core_search(self, query: str, method: SearchMethod = SearchMethod.AUTO, iterations: int = None) -> PerformanceMetrics:
        """Benchmark core search pipeline directly."""
        iterations = iterations or self.config.iterations
        metrics = PerformanceMetrics()
        
        # Warmup
        for _ in range(self.config.warmup_iterations):
            try:
                await search_word_pipeline(query, max_results=20, languages=[Language.ENGLISH])
            except Exception:
                pass
        
        # Benchmark
        for i in range(iterations):
            gc.collect()
            
            start_memory = self._monitor_memory()
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
                
            except Exception as e:
                metrics.errors.append(str(e))
        
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
            "timestamp": time.time(),
            "config": self.config.__dict__,
            "core_lookup": {},
            "rest_lookup": {},
            "core_search": {},
            "search_methods": {},
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
            
            # 1. Core lookup benchmarks
            task1 = progress.add_task("Core lookup benchmarks...", total=len(self.test_queries))
            for category, queries in self.test_queries.items():
                category_results = {}
                for query in queries[:2]:  # Limit to 2 per category for speed
                    metrics = await self.benchmark_core_lookup(query)
                    category_results[query] = {
                        "avg_ms": metrics.avg_time_ms,
                        "p95_ms": metrics.p95_time_ms,
                        "memory_mb": metrics.avg_memory_mb,
                        "errors": len(metrics.errors)
                    }
                results["core_lookup"][category] = category_results
                progress.advance(task1)
            
            # 2. REST lookup benchmarks
            task2 = progress.add_task("REST lookup benchmarks...", total=len(self.test_queries))
            for category, queries in self.test_queries.items():
                category_results = {}
                for query in queries[:2]:  # Limit to 2 per category for speed
                    metrics = await self.benchmark_rest_lookup(query)
                    category_results[query] = {
                        "avg_ms": metrics.avg_time_ms,
                        "p95_ms": metrics.p95_time_ms,
                        "memory_mb": metrics.avg_memory_mb,
                        "cache_hit_rate": (metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses) * 100) if (metrics.cache_hits + metrics.cache_misses) > 0 else 0,
                        "errors": len(metrics.errors)
                    }
                results["rest_lookup"][category] = category_results
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
            
            # 4. Generate comparisons and insights
            task4 = progress.add_task("Generating insights...", total=1)
            
            # Compare core vs REST for a sample query
            sample_query = "algorithm"
            core_sample = await self.benchmark_core_lookup(sample_query, iterations=20)
            rest_sample = await self.benchmark_rest_lookup(sample_query, iterations=20)
            
            results["comparison"] = self.compare_core_vs_rest(core_sample, rest_sample)
            results["optimization_insights"] = self._generate_optimization_insights(results)
            progress.advance(task4)
        
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
                    insights["high_impact"].append("Semantic search significantly slower - consider FAISS optimization")
        
        # Check for slow operations
        slow_queries = []
        for lookup_type in ["core_lookup", "rest_lookup"]:
            for category, queries in results.get(lookup_type, {}).items():
                for query, data in queries.items():
                    if data.get("avg_ms", 0) > 2000:  # 2 seconds
                        slow_queries.append(f"{query} ({data['avg_ms']:.1f}ms)")
        
        if slow_queries:
            insights["critical"].append(f"Very slow queries detected: {', '.join(slow_queries[:3])}")
        
        return insights
    
    def generate_report(self, results: dict[str, Any]) -> None:
        """Generate comprehensive performance report."""
        self.console.print("\n[bold cyan]🚀 Enhanced Lookup Pipeline Performance Analysis[/bold cyan]\n")
        
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
    
    def save_results(self, results: dict[str, Any], filename: str = None) -> None:
        """Save detailed results to JSON."""
        if filename is None:
            timestamp = int(time.time())
            filename = f"enhanced_benchmark_{timestamp}.json"
        
        filepath = Path(filename)
        with filepath.open("w") as f:
            json.dump(results, f, indent=2, default=str)
        
        self.console.print(f"\n[green]✅ Detailed results saved to {filepath}[/green]")


async def main():
    """Run enhanced benchmark suite."""
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
    
    # Configuration for faster execution
    config = BenchmarkConfig(
        iterations=30,
        warmup_iterations=3,
        concurrent_workers=5,
        enable_profiling=True
    )
    
    # Run benchmarks
    benchmark = EnhancedLookupBenchmark(config)
    console.print("[bold cyan]🔥 Starting enhanced lookup pipeline benchmarks...[/bold cyan]")
    console.print(f"[dim]Configuration: {config.iterations} iterations, optimized for speed[/dim]\n")
    
    try:
        results = await benchmark.run_comprehensive_benchmark()
        benchmark.generate_report(results)
        benchmark.save_results(results)
        
        # Check for critical issues
        insights = results.get("optimization_insights", {})
        if insights.get("critical"):
            console.print(f"\n[bold red]⚠️  CRITICAL ISSUES DETECTED: {len(insights['critical'])}[/bold red]")
            return False
        
        console.print("\n[bold green]✅ Enhanced benchmarks completed successfully![/bold green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Benchmark failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)