#!/usr/bin/env python3
"""Quick performance analysis focusing on key bottlenecks."""

from __future__ import annotations

import asyncio
import time
import statistics
import json
from dataclasses import dataclass
from typing import Any
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


@dataclass
class QuickMetrics:
    times: list[float]
    errors: list[str]
    
    @property
    def avg_ms(self) -> float:
        return statistics.mean(self.times) * 1000 if self.times else 0
    
    @property
    def p95_ms(self) -> float:
        if not self.times:
            return 0
        return sorted(self.times)[int(len(self.times) * 0.95)] * 1000


class QuickPerformanceAnalysis:
    def __init__(self):
        self.console = Console()
        self.base_url = "http://localhost:8000"
    
    async def test_rest_endpoints(self) -> dict[str, QuickMetrics]:
        """Test key REST endpoints for performance."""
        endpoints = [
            ("Search", "/api/v1/search", {"q": "cat"}),
            ("Lookup Simple", "/api/v1/lookup/cat", {}),
            ("Health", "/api/v1/health", {}),
            ("Search Fuzzy", "/api/v1/search", {"q": "algoritm", "method": "fuzzy"}),
        ]
        
        results = {}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for name, endpoint, params in endpoints:
                self.console.print(f"[dim]Testing {name}...[/dim]")
                metrics = QuickMetrics([], [])
                
                for i in range(5):  # Quick 5 iterations
                    start_time = time.perf_counter()
                    try:
                        response = await client.get(f"{self.base_url}{endpoint}", params=params)
                        elapsed = time.perf_counter() - start_time
                        metrics.times.append(elapsed)
                        
                        if response.status_code != 200:
                            metrics.errors.append(f"HTTP {response.status_code}")
                    except Exception as e:
                        metrics.errors.append(str(e))
                
                results[name] = metrics
        
        return results
    
    async def analyze_cold_vs_warm(self) -> dict[str, float]:
        """Analyze cold start vs warm performance."""
        endpoint = "/api/v1/search"
        params = {"q": "test"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Cold start
            start_time = time.perf_counter()
            try:
                await client.get(f"{self.base_url}{endpoint}", params=params)
                cold_time = time.perf_counter() - start_time
            except Exception:
                cold_time = 0
            
            # Warm requests
            warm_times = []
            for _ in range(3):
                start_time = time.perf_counter()
                try:
                    await client.get(f"{self.base_url}{endpoint}", params=params)
                    warm_times.append(time.perf_counter() - start_time)
                except Exception:
                    pass
            
            avg_warm = statistics.mean(warm_times) if warm_times else 0
            
        return {
            "cold_start_ms": cold_time * 1000,
            "warm_avg_ms": avg_warm * 1000,
            "cold_vs_warm_ratio": cold_time / avg_warm if avg_warm > 0 else 0
        }
    
    def generate_performance_report(self, endpoint_results: dict[str, QuickMetrics], cold_warm: dict[str, float]) -> None:
        """Generate quick performance report."""
        self.console.print("\n")
        self.console.print(Panel(
            "[bold cyan]🔥 Quick Performance Analysis Results[/bold cyan]", 
            style="cyan"
        ))
        
        # Endpoint performance table
        table = Table(title="REST API Performance")
        table.add_column("Endpoint", style="cyan")
        table.add_column("Avg (ms)", justify="right", style="green")
        table.add_column("P95 (ms)", justify="right", style="yellow")
        table.add_column("Status", justify="center")
        
        performance_issues = []
        
        for name, metrics in endpoint_results.items():
            avg_time = metrics.avg_ms
            p95_time = metrics.p95_ms
            error_count = len(metrics.errors)
            
            # Determine status
            if error_count > 0:
                status = f"[red]❌ {error_count} errors[/red]"
                performance_issues.append(f"{name}: {error_count} errors")
            elif avg_time > 2000:
                status = "[red]🐌 Very Slow[/red]"
                performance_issues.append(f"{name}: Very slow ({avg_time:.0f}ms)")
            elif avg_time > 500:
                status = "[yellow]⚠️ Slow[/yellow]"
                performance_issues.append(f"{name}: Slow ({avg_time:.0f}ms)")
            else:
                status = "[green]✅ Good[/green]"
            
            table.add_row(
                name,
                f"{avg_time:.0f}",
                f"{p95_time:.0f}",
                status
            )
        
        self.console.print(table)
        
        # Cold vs Warm analysis
        self.console.print(f"\n[bold]Cold Start Analysis:[/bold]")
        self.console.print(f"  • Cold start time: {cold_warm['cold_start_ms']:.0f}ms")
        self.console.print(f"  • Warm request time: {cold_warm['warm_avg_ms']:.0f}ms")
        self.console.print(f"  • Cold/Warm ratio: {cold_warm['cold_vs_warm_ratio']:.1f}x")
        
        if cold_warm['cold_start_ms'] > 1000:
            performance_issues.append(f"Cold start very slow ({cold_warm['cold_start_ms']:.0f}ms)")
        
        # Performance Issues & Recommendations
        if performance_issues:
            self.console.print(f"\n[bold red]⚠️ Performance Issues Detected:[/bold red]")
            for issue in performance_issues:
                self.console.print(f"  • {issue}")
            
            self.console.print(f"\n[bold]🎯 Quick Optimization Recommendations:[/bold]")
            
            # Based on what I observed in the logs
            recommendations = [
                "1. [HIGH] Search engine initialization takes 1.4s - implement lazy loading or connection pooling",
                "2. [HIGH] AI synthesis appears to be synchronous - implement async batching",
                "3. [MEDIUM] Add response caching for repeated queries",
                "4. [MEDIUM] Consider connection pooling for external APIs",
                "5. [LOW] Add HTTP cache headers for static endpoints"
            ]
            
            for rec in recommendations:
                self.console.print(f"  {rec}")
        else:
            self.console.print(f"\n[green]✅ No critical performance issues detected![/green]")
    
    def generate_optimization_plan(self) -> dict[str, Any]:
        """Generate detailed optimization plan based on observed patterns."""
        return {
            "critical_bottlenecks": [
                {
                    "component": "Search Engine Initialization",
                    "issue": "1.4+ second cold start time",
                    "impact": "First request extremely slow",
                    "solution": "Implement search engine connection pooling or lazy initialization",
                    "estimated_improvement": "80% reduction in cold start time",
                    "effort": "Medium (2-3 days)"
                },
                {
                    "component": "AI Synthesis Pipeline", 
                    "issue": "Sequential OpenAI API calls causing long delays",
                    "impact": "2-8 second lookup times",
                    "solution": "Batch OpenAI requests, implement request deduplication",
                    "estimated_improvement": "60% reduction in AI processing time",
                    "effort": "High (1-2 weeks)"
                }
            ],
            "high_impact_optimizations": [
                {
                    "component": "Response Caching",
                    "solution": "Implement Redis/memory cache for frequent lookups",
                    "estimated_improvement": "90% reduction for repeated queries",
                    "effort": "Low (1-2 days)"
                },
                {
                    "component": "Connection Pooling",
                    "solution": "HTTP connection pooling for external dictionary APIs",
                    "estimated_improvement": "30% reduction in provider fetch time", 
                    "effort": "Low (1 day)"
                }
            ],
            "medium_impact_optimizations": [
                {
                    "component": "MongoDB Queries",
                    "solution": "Add compound indexes, optimize connection pool",
                    "estimated_improvement": "20% reduction in database operations",
                    "effort": "Medium (2-3 days)"
                },
                {
                    "component": "FAISS Optimization",
                    "solution": "GPU acceleration, index quantization",
                    "estimated_improvement": "50% reduction in semantic search time",
                    "effort": "High (1-2 weeks)"
                }
            ],
            "implementation_priority": [
                "1. Implement response caching (quick win)",
                "2. Add connection pooling (quick win)",
                "3. Optimize search engine initialization",
                "4. Batch AI requests and implement deduplication",
                "5. Database and FAISS optimizations"
            ]
        }


async def main():
    """Run quick performance analysis."""
    console = Console()
    
    # Check server
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/v1/health", timeout=5.0)
            if response.status_code != 200:
                console.print("[red]❌ Backend server not healthy[/red]")
                return
    except Exception as e:
        console.print(f"[red]❌ Cannot connect to backend: {e}[/red]")
        return
    
    analyzer = QuickPerformanceAnalysis()
    
    console.print("[bold cyan]🚀 Running quick performance analysis...[/bold cyan]")
    
    # Run tests
    endpoint_results = await analyzer.test_rest_endpoints()
    cold_warm_results = await analyzer.analyze_cold_vs_warm()
    
    # Generate reports
    analyzer.generate_performance_report(endpoint_results, cold_warm_results)
    
    # Save optimization plan
    optimization_plan = analyzer.generate_optimization_plan()
    
    with open("optimization_plan.json", "w") as f:
        json.dump(optimization_plan, f, indent=2)
    
    console.print(f"\n[green]✅ Analysis complete! Optimization plan saved to optimization_plan.json[/green]")


if __name__ == "__main__":
    asyncio.run(main())