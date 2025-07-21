"""Cache performance and effectiveness benchmarking.

Tests multi-level caching performance, hit rates, and memory efficiency
across the search pipeline caching layers.
"""

from __future__ import annotations

import asyncio
import gc
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Import caching components
from floridify.caching.cache_manager import CacheManager
from floridify.core.search_pipeline import search_word_pipeline
from floridify.storage.mongodb import get_storage


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    cache_hits: int = 0
    cache_misses: int = 0
    cache_writes: int = 0
    hit_times: list[float] = field(default_factory=list)
    miss_times: list[float] = field(default_factory=list)
    write_times: list[float] = field(default_factory=list)
    memory_usage_mb: float = 0.0
    cache_size_items: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0
    
    @property
    def avg_hit_time_ms(self) -> float:
        return (sum(self.hit_times) / len(self.hit_times) * 1000) if self.hit_times else 0
    
    @property
    def avg_miss_time_ms(self) -> float:
        return (sum(self.miss_times) / len(self.miss_times) * 1000) if self.miss_times else 0


class CacheBenchmark:
    """Cache performance and effectiveness benchmarking."""
    
    def __init__(self):
        self.console = Console()
        self.cache_manager = CacheManager()
        
        # Test data sets for cache warming and testing
        self.test_queries = {
            "frequent": ["the", "and", "cat", "dog", "run", "happy", "good", "time"],
            "medium": ["algorithm", "computer", "language", "system", "process"],
            "rare": ["antidisestablishmentarianism", "floccinaucinihilipilification"],
            "patterns": [
                "test", "testing", "tested", "tester",  # Similar words
                "run", "running", "runner", "runs"
            ]
        }
    
    async def benchmark_cache_warming(self, queries: list[str]) -> dict[str, float]:
        """Benchmark cache warming performance."""
        self.console.print(f"[dim]Warming cache with {len(queries)} queries...[/dim]")
        
        warming_times = []
        
        for query in queries:
            start_time = time.perf_counter()
            
            try:
                # Execute search to populate cache
                await search_word_pipeline(query, max_results=10)
                elapsed = time.perf_counter() - start_time
                warming_times.append(elapsed)
            
            except Exception as e:
                self.console.print(f"[red]Cache warming error for '{query}': {e}[/red]")
        
        return {
            "total_time_s": sum(warming_times),
            "avg_time_ms": (sum(warming_times) / len(warming_times) * 1000) if warming_times else 0,
            "queries_processed": len(warming_times)
        }
    
    async def benchmark_cache_hits_vs_misses(self, queries: list[str], iterations: int = 50) -> CacheMetrics:
        """Compare cache hit vs miss performance."""
        metrics = CacheMetrics()
        
        # First, warm the cache with half the queries
        warm_queries = queries[:len(queries)//2]
        cold_queries = queries[len(queries)//2:]
        
        # Warm cache
        for query in warm_queries:
            try:
                await search_word_pipeline(query, max_results=10)
                metrics.cache_writes += 1
            except Exception:
                pass
        
        # Now test cache hits (warm queries) vs misses (cold queries)
        for _ in range(iterations):
            # Test cache hits
            for query in warm_queries:
                start_time = time.perf_counter()
                
                try:
                    await search_word_pipeline(query, max_results=10)
                    elapsed = time.perf_counter() - start_time
                    metrics.hit_times.append(elapsed)
                    metrics.cache_hits += 1
                
                except Exception:
                    pass
            
            # Test cache misses (use modified queries to force misses)
            for i, query in enumerate(cold_queries):
                modified_query = f"{query}_{i}_{datetime.now().timestamp()}"  # Ensure unique query
                start_time = time.perf_counter()
                
                try:
                    await search_word_pipeline(modified_query, max_results=10)
                    elapsed = time.perf_counter() - start_time
                    metrics.miss_times.append(elapsed)
                    metrics.cache_misses += 1
                
                except Exception:
                    pass
        
        return metrics
    
    async def benchmark_cache_memory_efficiency(self) -> dict[str, float]:
        """Benchmark cache memory usage patterns."""
        import psutil
        process = psutil.Process()
        
        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        # Fill cache with test data
        test_data = []
        for category, queries in self.test_queries.items():
            test_data.extend(queries)
        
        # Memory before cache operations
        before_memory = process.memory_info().rss / 1024 / 1024
        
        # Populate cache
        for query in test_data * 5:  # Multiple passes to fill cache
            try:
                await search_word_pipeline(query, max_results=10)
            except Exception:
                pass
        
        # Memory after cache operations
        after_memory = process.memory_info().rss / 1024 / 1024
        
        # Get cache statistics if available
        cache_size = 0
        if hasattr(self.cache_manager, 'get_cache_size'):
            cache_size = self.cache_manager.get_cache_size()
        elif hasattr(self.cache_manager, '_memory_cache'):
            cache_size = len(self.cache_manager._memory_cache)
        
        return {
            "baseline_memory_mb": baseline_memory,
            "before_cache_mb": before_memory,
            "after_cache_mb": after_memory,
            "cache_overhead_mb": after_memory - before_memory,
            "cache_size_items": cache_size,
            "memory_per_item_kb": ((after_memory - before_memory) * 1024 / cache_size) if cache_size > 0 else 0
        }
    
    async def benchmark_cache_ttl_effectiveness(self) -> dict[str, Any]:
        """Test cache TTL (Time To Live) effectiveness."""
        test_query = "cache_ttl_test"
        results = {}
        
        # Test immediate cache hit
        start_time = time.perf_counter()
        await search_word_pipeline(test_query, max_results=10)
        first_time = time.perf_counter() - start_time
        
        # Test cache hit within TTL
        start_time = time.perf_counter()
        await search_word_pipeline(test_query, max_results=10)
        cached_time = time.perf_counter() - start_time
        
        results["cache_speedup"] = first_time / cached_time if cached_time > 0 else 1.0
        results["first_request_ms"] = first_time * 1000
        results["cached_request_ms"] = cached_time * 1000
        
        # Note: TTL expiration testing would require waiting or mocking time
        # For now, we'll just measure the immediate cache effectiveness
        
        return results
    
    async def benchmark_api_cache_headers(self) -> dict[str, Any]:
        """Test API-level caching with HTTP headers."""
        base_url = "http://localhost:8000"
        test_endpoints = [
            ("/api/v1/search", {"q": "algorithm"}),
            ("/api/v1/lookup/computer", {}),
            ("/api/v1/search", {"q": "happiness"})
        ]
        
        cache_header_results = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint, params in test_endpoints:
                endpoint_results = {
                    "first_request_ms": 0,
                    "cached_request_ms": 0,
                    "cache_headers_present": False,
                    "cache_hit_detected": False
                }
                
                # First request
                start_time = time.perf_counter()
                try:
                    response1 = await client.get(f"{base_url}{endpoint}", params=params)
                    endpoint_results["first_request_ms"] = (time.perf_counter() - start_time) * 1000
                    
                    # Check for cache-related headers
                    cache_headers = [
                        'X-Cache-Hit', 'X-Cache-Status', 'Cache-Control',
                        'ETag', 'X-Process-Time'
                    ]
                    
                    for header in cache_headers:
                        if header in response1.headers:
                            endpoint_results["cache_headers_present"] = True
                            break
                
                except Exception as e:
                    self.console.print(f"[red]API cache test error for {endpoint}: {e}[/red]")
                    continue
                
                # Second request (should be cached)
                start_time = time.perf_counter()
                try:
                    response2 = await client.get(f"{base_url}{endpoint}", params=params)
                    endpoint_results["cached_request_ms"] = (time.perf_counter() - start_time) * 1000
                    
                    # Check for cache hit indicators
                    if 'X-Cache-Hit' in response2.headers:
                        endpoint_results["cache_hit_detected"] = response2.headers['X-Cache-Hit'] == 'true'
                
                except Exception as e:
                    self.console.print(f"[red]API cache test error for {endpoint} (cached): {e}[/red]")
                
                cache_header_results[f"{endpoint}?{params}"] = endpoint_results
        
        return cache_header_results
    
    async def benchmark_concurrent_cache_access(self, concurrency: int = 10) -> dict[str, float]:
        """Test cache performance under concurrent access."""
        test_query = "concurrent_test"
        
        # Warm cache first
        await search_word_pipeline(test_query, max_results=10)
        
        async def concurrent_search():
            start_time = time.perf_counter()
            await search_word_pipeline(test_query, max_results=10)
            return time.perf_counter() - start_time
        
        # Create concurrent tasks
        tasks = [concurrent_search() for _ in range(concurrency)]
        
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.perf_counter() - start_time
        
        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, float)]
        
        return {
            "concurrent_requests": concurrency,
            "successful_requests": len(valid_results),
            "total_time_s": total_time,
            "avg_request_time_ms": (sum(valid_results) / len(valid_results) * 1000) if valid_results else 0,
            "requests_per_second": len(valid_results) / total_time if total_time > 0 else 0,
            "cache_contention_detected": any(r > 0.1 for r in valid_results) if valid_results else False
        }
    
    async def run_comprehensive_cache_benchmark(self) -> dict[str, Any]:
        """Run complete cache benchmark suite."""
        results = {
            "timestamp": datetime.now(),
            "cache_warming": {},
            "hit_vs_miss": {},
            "memory_efficiency": {},
            "ttl_effectiveness": {},
            "api_cache_headers": {},
            "concurrent_access": {},
            "optimization_recommendations": []
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            # 1. Cache warming benchmarks
            task1 = progress.add_task("Benchmarking cache warming...", total=None)
            all_queries = [q for queries in self.test_queries.values() for q in queries]
            warming_results = await self.benchmark_cache_warming(all_queries)
            results["cache_warming"] = warming_results
            progress.remove_task(task1)
            
            # 2. Cache hits vs misses
            task2 = progress.add_task("Testing cache hits vs misses...", total=None)
            hit_miss_metrics = await self.benchmark_cache_hits_vs_misses(all_queries)
            results["hit_vs_miss"] = {
                "hit_rate_percent": hit_miss_metrics.hit_rate,
                "avg_hit_time_ms": hit_miss_metrics.avg_hit_time_ms,
                "avg_miss_time_ms": hit_miss_metrics.avg_miss_time_ms,
                "cache_speedup": hit_miss_metrics.avg_miss_time_ms / hit_miss_metrics.avg_hit_time_ms if hit_miss_metrics.avg_hit_time_ms > 0 else 1.0,
                "total_hits": hit_miss_metrics.cache_hits,
                "total_misses": hit_miss_metrics.cache_misses
            }
            progress.remove_task(task2)
            
            # 3. Memory efficiency
            task3 = progress.add_task("Analyzing cache memory efficiency...", total=None)
            memory_results = await self.benchmark_cache_memory_efficiency()
            results["memory_efficiency"] = memory_results
            progress.remove_task(task3)
            
            # 4. TTL effectiveness
            task4 = progress.add_task("Testing cache TTL effectiveness...", total=None)
            ttl_results = await self.benchmark_cache_ttl_effectiveness()
            results["ttl_effectiveness"] = ttl_results
            progress.remove_task(task4)
            
            # 5. API cache headers
            task5 = progress.add_task("Testing API cache headers...", total=None)
            try:
                api_cache_results = await self.benchmark_api_cache_headers()
                results["api_cache_headers"] = api_cache_results
            except Exception as e:
                self.console.print(f"[yellow]API cache test skipped: {e}[/yellow]")
                results["api_cache_headers"] = {"error": str(e)}
            progress.remove_task(task5)
            
            # 6. Concurrent access
            task6 = progress.add_task("Testing concurrent cache access...", total=None)
            concurrent_results = await self.benchmark_concurrent_cache_access()
            results["concurrent_access"] = concurrent_results
            progress.remove_task(task6)
            
            # 7. Generate recommendations
            results["optimization_recommendations"] = self._generate_cache_recommendations(results)
        
        return results
    
    def _generate_cache_recommendations(self, results: dict[str, Any]) -> list[str]:
        """Generate cache optimization recommendations."""
        recommendations = []
        
        # Check hit rate
        hit_miss = results.get("hit_vs_miss", {})
        hit_rate = hit_miss.get("hit_rate_percent", 0)
        if hit_rate < 70:
            recommendations.append(f"Low cache hit rate: {hit_rate:.1f}% - consider increasing cache size or TTL")
        
        # Check cache speedup
        speedup = hit_miss.get("cache_speedup", 1.0)
        if speedup < 2.0:
            recommendations.append(f"Low cache speedup: {speedup:.1f}x - investigate cache effectiveness")
        
        # Check memory efficiency
        memory_eff = results.get("memory_efficiency", {})
        memory_per_item = memory_eff.get("memory_per_item_kb", 0)
        if memory_per_item > 100:  # > 100KB per cached item
            recommendations.append(f"High memory per cache item: {memory_per_item:.1f}KB - consider compression")
        
        # Check concurrent performance
        concurrent = results.get("concurrent_access", {})
        if concurrent.get("cache_contention_detected", False):
            recommendations.append("Cache contention detected under load - consider lock-free caching")
        
        # Check API caching
        api_cache = results.get("api_cache_headers", {})
        if isinstance(api_cache, dict) and not api_cache.get("error"):
            headers_present = any(
                endpoint.get("cache_headers_present", False) 
                for endpoint in api_cache.values() 
                if isinstance(endpoint, dict)
            )
            if not headers_present:
                recommendations.append("No cache headers detected in API responses - implement HTTP caching")
        
        return recommendations
    
    def generate_cache_report(self, results: dict[str, Any]) -> None:
        """Generate comprehensive cache performance report."""
        self.console.print("\n[bold cyan]💾 Cache Performance Analysis[/bold cyan]\n")
        
        # Cache effectiveness table
        hit_miss = results.get("hit_vs_miss", {})
        if hit_miss:
            cache_table = Table(title="Cache Effectiveness")
            cache_table.add_column("Metric", style="cyan")
            cache_table.add_column("Value", justify="right")
            cache_table.add_column("Performance", style="green")
            
            hit_rate = hit_miss.get("hit_rate_percent", 0)
            speedup = hit_miss.get("cache_speedup", 1.0)
            
            cache_table.add_row(
                "Hit Rate",
                f"{hit_rate:.1f}%",
                "Excellent" if hit_rate > 90 else "Good" if hit_rate > 70 else "Poor"
            )
            cache_table.add_row(
                "Cache Speedup",
                f"{speedup:.1f}x",
                "Excellent" if speedup > 5 else "Good" if speedup > 2 else "Poor"
            )
            cache_table.add_row(
                "Avg Hit Time",
                f"{hit_miss.get('avg_hit_time_ms', 0):.1f}ms",
                "-"
            )
            cache_table.add_row(
                "Avg Miss Time",
                f"{hit_miss.get('avg_miss_time_ms', 0):.1f}ms",
                "-"
            )
            
            self.console.print(cache_table)
        
        # Memory efficiency
        memory_eff = results.get("memory_efficiency", {})
        if memory_eff:
            self.console.print(f"\n[bold]Memory Efficiency:[/bold]")
            self.console.print(f"  • Cache overhead: {memory_eff.get('cache_overhead_mb', 0):.1f}MB")
            self.console.print(f"  • Items cached: {memory_eff.get('cache_size_items', 0):,}")
            self.console.print(f"  • Memory per item: {memory_eff.get('memory_per_item_kb', 0):.1f}KB")
        
        # Concurrent performance
        concurrent = results.get("concurrent_access", {})
        if concurrent:
            self.console.print(f"\n[bold]Concurrent Access:[/bold]")
            self.console.print(f"  • Requests per second: {concurrent.get('requests_per_second', 0):.1f}")
            self.console.print(f"  • Avg response time: {concurrent.get('avg_request_time_ms', 0):.1f}ms")
            
            contention = concurrent.get("cache_contention_detected", False)
            status = "[red]Detected[/red]" if contention else "[green]None[/green]"
            self.console.print(f"  • Cache contention: {status}")
        
        # API caching status
        api_cache = results.get("api_cache_headers", {})
        if isinstance(api_cache, dict) and not api_cache.get("error"):
            self.console.print(f"\n[bold]API Cache Performance:[/bold]")
            
            for endpoint, data in api_cache.items():
                if isinstance(data, dict):
                    first_time = data.get("first_request_ms", 0)
                    cached_time = data.get("cached_request_ms", 0)
                    speedup = first_time / cached_time if cached_time > 0 else 1.0
                    
                    self.console.print(f"  • {endpoint}")
                    self.console.print(f"    - First request: {first_time:.1f}ms")
                    self.console.print(f"    - Cached request: {cached_time:.1f}ms")
                    self.console.print(f"    - Speedup: {speedup:.1f}x")
        
        # Recommendations
        recommendations = results.get("optimization_recommendations", [])
        if recommendations:
            self.console.print(f"\n[bold]🎯 Cache Optimization Recommendations:[/bold]")
            for i, rec in enumerate(recommendations, 1):
                self.console.print(f"  {i}. {rec}")
        else:
            self.console.print(f"\n[green]✅ Cache performance is optimal![/green]")


async def main():
    """Run cache benchmarks."""
    benchmark = CacheBenchmark()
    console = Console()
    
    console.print("[bold cyan]💾 Starting cache performance benchmarks...[/bold cyan]\n")
    
    try:
        results = await benchmark.run_comprehensive_cache_benchmark()
        benchmark.generate_cache_report(results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cache_benchmark_{timestamp}.json"
        
        import json
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        console.print(f"\n[green]✅ Cache benchmark results saved to {filename}[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Cache benchmark failed: {e}[/red]")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)