"""Comprehensive search pipeline benchmarking orchestrator.

Runs all benchmark suites and generates unified performance analysis
with optimization recommendations prioritized by impact.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.tree import Tree

# Import all benchmark modules
from benchmark_search_pipeline import SearchPipelineBenchmark, BenchmarkConfig
from benchmark_faiss import FAISSBenchmark
from benchmark_cache import CacheBenchmark


@dataclass
class ComprehensiveResults:
    """Container for all benchmark results."""
    search_pipeline: dict[str, Any] = None
    faiss_performance: dict[str, Any] = None
    cache_performance: dict[str, Any] = None
    system_health: dict[str, Any] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class ComprehensiveBenchmarkOrchestrator:
    """Orchestrates all benchmark suites for complete performance analysis."""
    
    def __init__(self, config: BenchmarkConfig = None):
        self.config = config or BenchmarkConfig(
            iterations=100,
            warmup_iterations=10,
            concurrent_workers=10,
            enable_profiling=True
        )
        self.console = Console()
        self.results = ComprehensiveResults()
    
    async def check_system_health(self) -> dict[str, Any]:
        """Comprehensive system health check before benchmarking."""
        health = {
            "backend_status": "unknown",
            "mongodb_status": "unknown", 
            "faiss_available": False,
            "cache_initialized": False,
            "memory_available_mb": 0,
            "cpu_cores": 0,
            "python_version": "",
            "dependencies": {}
        }
        
        # Check backend server
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:8000/api/v1/health")
                health["backend_status"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            health["backend_status"] = f"error: {e}"
        
        # Check MongoDB
        try:
            from floridify.storage.mongodb import get_storage
            storage = await get_storage()
            if storage and hasattr(storage, 'client'):
                await storage.client.admin.command('ping')
                health["mongodb_status"] = "connected"
            else:
                health["mongodb_status"] = "not_available"
        except Exception as e:
            health["mongodb_status"] = f"error: {e}"
        
        # Check FAISS availability
        try:
            import faiss
            health["faiss_available"] = True
            health["dependencies"]["faiss"] = faiss.__version__
        except ImportError:
            health["faiss_available"] = False
        
        # Check cache initialization
        try:
            from floridify.caching.cache_manager import CacheManager
            cache_manager = CacheManager()
            health["cache_initialized"] = True
        except Exception:
            health["cache_initialized"] = False
        
        # System resources
        try:
            import psutil
            health["memory_available_mb"] = psutil.virtual_memory().available / 1024 / 1024
            health["cpu_cores"] = psutil.cpu_count()
        except ImportError:
            pass
        
        # Python and key dependencies
        import sys
        health["python_version"] = sys.version
        
        try:
            import fastapi
            health["dependencies"]["fastapi"] = fastapi.__version__
        except ImportError:
            pass
        
        try:
            import motor
            health["dependencies"]["motor"] = motor.version
        except ImportError:
            pass
        
        return health
    
    async def run_search_pipeline_benchmarks(self) -> dict[str, Any]:
        """Run core search pipeline benchmarks."""
        self.console.print("[dim]Running search pipeline benchmarks...[/dim]")
        
        benchmark = SearchPipelineBenchmark(self.config)
        try:
            results = await benchmark.run_comprehensive_benchmark()
            return results
        except Exception as e:
            self.console.print(f"[red]Search pipeline benchmark failed: {e}[/red]")
            return {"error": str(e), "timestamp": time.time()}
    
    async def run_faiss_benchmarks(self) -> dict[str, Any]:
        """Run FAISS and semantic search benchmarks."""
        self.console.print("[dim]Running FAISS benchmarks...[/dim]")
        
        benchmark = FAISSBenchmark()
        try:
            results = await benchmark.run_comprehensive_faiss_benchmark()
            return results
        except Exception as e:
            self.console.print(f"[red]FAISS benchmark failed: {e}[/red]")
            return {"error": str(e), "timestamp": time.time()}
    
    async def run_cache_benchmarks(self) -> dict[str, Any]:
        """Run cache performance benchmarks."""
        self.console.print("[dim]Running cache benchmarks...[/dim]")
        
        benchmark = CacheBenchmark()
        try:
            results = await benchmark.run_comprehensive_cache_benchmark()
            return results
        except Exception as e:
            self.console.print(f"[red]Cache benchmark failed: {e}[/red]")
            return {"error": str(e), "timestamp": time.time()}
    
    async def run_all_benchmarks(self) -> ComprehensiveResults:
        """Run all benchmark suites with progress tracking."""
        self.console.print("[bold cyan]🚀 Starting Comprehensive Search Pipeline Performance Analysis[/bold cyan]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            
            # 1. System health check
            task1 = progress.add_task("Checking system health...", total=1)
            self.results.system_health = await self.check_system_health()
            progress.advance(task1, 1)
            
            # Verify system is ready for benchmarking
            if self.results.system_health["backend_status"] != "healthy":
                self.console.print("[red]❌ Backend server is not healthy - cannot proceed with benchmarks[/red]")
                return self.results
            
            # 2. Search pipeline benchmarks
            task2 = progress.add_task("Search pipeline benchmarks...", total=1)
            self.results.search_pipeline = await self.run_search_pipeline_benchmarks()
            progress.advance(task2, 1)
            
            # 3. FAISS benchmarks (if available)
            if self.results.system_health["faiss_available"]:
                task3 = progress.add_task("FAISS & semantic search benchmarks...", total=1)
                self.results.faiss_performance = await self.run_faiss_benchmarks()
                progress.advance(task3, 1)
            else:
                self.console.print("[yellow]⚠️  FAISS not available - skipping semantic search benchmarks[/yellow]")
            
            # 4. Cache benchmarks
            task4 = progress.add_task("Cache performance benchmarks...", total=1)
            self.results.cache_performance = await self.run_cache_benchmarks()
            progress.advance(task4, 1)
        
        return self.results
    
    def analyze_cross_benchmark_patterns(self, results: ComprehensiveResults) -> dict[str, Any]:
        """Analyze patterns across all benchmark results."""
        analysis = {
            "performance_bottlenecks": [],
            "optimization_priorities": [],
            "system_recommendations": [],
            "comparative_insights": {}
        }
        
        # Compare core vs REST performance
        if results.search_pipeline and "comparison" in results.search_pipeline:
            comparison = results.search_pipeline["comparison"]
            rest_overhead = comparison.get("rest_overhead_percent", 0)
            
            if rest_overhead > 100:
                analysis["performance_bottlenecks"].append({
                    "component": "REST API",
                    "severity": "critical",
                    "issue": f"REST overhead: {rest_overhead:.1f}%",
                    "impact": "High latency for all API requests"
                })
            elif rest_overhead > 50:
                analysis["performance_bottlenecks"].append({
                    "component": "REST API", 
                    "severity": "high",
                    "issue": f"REST overhead: {rest_overhead:.1f}%",
                    "impact": "Moderate latency impact"
                })
        
        # Analyze FAISS performance
        if results.faiss_performance and "index_performance" in results.faiss_performance:
            faiss_perf = results.faiss_performance["index_performance"]
            search_time = faiss_perf.get("avg_search_ms", 0)
            
            if search_time > 50:
                analysis["performance_bottlenecks"].append({
                    "component": "FAISS Semantic Search",
                    "severity": "high",
                    "issue": f"Slow semantic search: {search_time:.1f}ms",
                    "impact": "Poor user experience for semantic queries"
                })
        
        # Analyze cache effectiveness
        if results.cache_performance and "hit_vs_miss" in results.cache_performance:
            cache_perf = results.cache_performance["hit_vs_miss"]
            hit_rate = cache_perf.get("hit_rate_percent", 0)
            speedup = cache_perf.get("cache_speedup", 1.0)
            
            if hit_rate < 70:
                analysis["performance_bottlenecks"].append({
                    "component": "Cache Layer",
                    "severity": "medium",
                    "issue": f"Low cache hit rate: {hit_rate:.1f}%",
                    "impact": "Increased database load and latency"
                })
            
            if speedup < 2.0:
                analysis["performance_bottlenecks"].append({
                    "component": "Cache Layer",
                    "severity": "medium", 
                    "issue": f"Low cache speedup: {speedup:.1f}x",
                    "impact": "Cache not providing expected performance benefit"
                })
        
        # Generate optimization priorities
        analysis["optimization_priorities"] = self._prioritize_optimizations(analysis["performance_bottlenecks"])
        
        # System-level recommendations
        memory_mb = results.system_health.get("memory_available_mb", 0)
        if memory_mb < 1024:  # Less than 1GB available
            analysis["system_recommendations"].append("Low available memory - consider increasing system resources")
        
        cpu_cores = results.system_health.get("cpu_cores", 0)
        if cpu_cores < 4:
            analysis["system_recommendations"].append("Limited CPU cores - consider enabling GPU acceleration for FAISS")
        
        return analysis
    
    def _prioritize_optimizations(self, bottlenecks: list[dict]) -> list[dict]:
        """Prioritize optimizations by impact and effort."""
        # Define impact scores
        impact_scores = {"critical": 10, "high": 7, "medium": 4, "low": 2}
        
        # Score and sort bottlenecks
        scored_bottlenecks = []
        for bottleneck in bottlenecks:
            score = impact_scores.get(bottleneck["severity"], 1)
            
            # Add component-specific scoring
            if bottleneck["component"] == "REST API":
                score += 3  # High impact on all requests
            elif bottleneck["component"] == "FAISS Semantic Search":
                score += 2  # Affects specific search types
            elif bottleneck["component"] == "Cache Layer":
                score += 2  # Affects all cached operations
            
            scored_bottlenecks.append({**bottleneck, "priority_score": score})
        
        return sorted(scored_bottlenecks, key=lambda x: x["priority_score"], reverse=True)
    
    def generate_comprehensive_report(self, results: ComprehensiveResults) -> None:
        """Generate unified performance analysis report."""
        layout = Layout()
        
        # Create main sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Header
        layout["header"].update(
            Panel(
                "[bold cyan]🚀 Comprehensive Search Pipeline Performance Analysis[/bold cyan]\n"
                f"[dim]Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
                style="cyan"
            )
        )
        
        # Main content
        self._generate_performance_summary(results)
        self._generate_bottleneck_analysis(results)
        self._generate_optimization_roadmap(results)
        
        # Footer
        footer_text = "✅ Analysis complete - See detailed results in saved JSON files"
        if any(results.system_health.get(key, "").startswith("error") for key in ["backend_status", "mongodb_status"]):
            footer_text = "⚠️  Some system components unavailable - partial analysis only"
        
        layout["footer"].update(Panel(footer_text, style="green"))
    
    def _generate_performance_summary(self, results: ComprehensiveResults) -> None:
        """Generate high-level performance summary."""
        self.console.print("\n[bold]📊 Performance Summary[/bold]")
        
        summary_table = Table(title="Component Performance Overview")
        summary_table.add_column("Component", style="cyan")
        summary_table.add_column("Status", justify="center")
        summary_table.add_column("Key Metric", justify="right")
        summary_table.add_column("Performance", style="green")
        
        # Core search pipeline
        if results.search_pipeline and "comparison" in results.search_pipeline:
            comp = results.search_pipeline["comparison"]
            overhead = comp.get("rest_overhead_percent", 0)
            status = "🔴 Critical" if overhead > 100 else "🟡 Needs Attention" if overhead > 50 else "🟢 Good"
            summary_table.add_row("Core Search", status, f"{overhead:.1f}% REST overhead", "")
        
        # FAISS performance
        if results.faiss_performance and "index_performance" in results.faiss_performance:
            faiss_perf = results.faiss_performance["index_performance"]
            search_time = faiss_perf.get("avg_search_ms", 0)
            status = "🔴 Slow" if search_time > 50 else "🟡 Moderate" if search_time > 20 else "🟢 Fast"
            summary_table.add_row("FAISS Search", status, f"{search_time:.1f}ms avg", "")
        
        # Cache performance
        if results.cache_performance and "hit_vs_miss" in results.cache_performance:
            cache_perf = results.cache_performance["hit_vs_miss"]
            hit_rate = cache_perf.get("hit_rate_percent", 0)
            status = "🟢 Excellent" if hit_rate > 90 else "🟡 Good" if hit_rate > 70 else "🔴 Poor"
            summary_table.add_row("Cache Layer", status, f"{hit_rate:.1f}% hit rate", "")
        
        # System health
        backend_status = results.system_health.get("backend_status", "unknown")
        system_status = "🟢 Healthy" if backend_status == "healthy" else "🔴 Issues"
        memory_gb = results.system_health.get("memory_available_mb", 0) / 1024
        summary_table.add_row("System Health", system_status, f"{memory_gb:.1f}GB available", "")
        
        self.console.print(summary_table)
    
    def _generate_bottleneck_analysis(self, results: ComprehensiveResults) -> None:
        """Generate detailed bottleneck analysis."""
        analysis = self.analyze_cross_benchmark_patterns(results)
        bottlenecks = analysis["performance_bottlenecks"]
        
        if not bottlenecks:
            self.console.print("\n[green]🎉 No significant performance bottlenecks detected![/green]")
            return
        
        self.console.print("\n[bold]🎯 Performance Bottlenecks[/bold]")
        
        bottleneck_tree = Tree("Identified Issues")
        
        for bottleneck in bottlenecks[:5]:  # Top 5 issues
            severity_color = {
                "critical": "red",
                "high": "yellow", 
                "medium": "blue",
                "low": "dim"
            }.get(bottleneck["severity"], "white")
            
            issue_node = bottleneck_tree.add(
                f"[{severity_color}]{bottleneck['component']}[/{severity_color}]: {bottleneck['issue']}"
            )
            issue_node.add(f"Impact: {bottleneck['impact']}")
            issue_node.add(f"Severity: {bottleneck['severity'].title()}")
        
        self.console.print(bottleneck_tree)
    
    def _generate_optimization_roadmap(self, results: ComprehensiveResults) -> None:
        """Generate prioritized optimization roadmap."""
        analysis = self.analyze_cross_benchmark_patterns(results)
        priorities = analysis["optimization_priorities"]
        
        if not priorities:
            return
        
        self.console.print("\n[bold]🛣️  Optimization Roadmap (Prioritized)[/bold]")
        
        roadmap_table = Table(title="Recommended Optimizations")
        roadmap_table.add_column("Priority", style="cyan")
        roadmap_table.add_column("Component", style="blue")
        roadmap_table.add_column("Issue", style="yellow")
        roadmap_table.add_column("Estimated Impact", justify="center")
        
        for i, item in enumerate(priorities[:10], 1):  # Top 10 priorities
            impact_emoji = "🔴" if item["severity"] == "critical" else "🟡" if item["severity"] == "high" else "🟢"
            roadmap_table.add_row(
                f"#{i}",
                item["component"],
                item["issue"],
                f"{impact_emoji} {item['severity'].title()}"
            )
        
        self.console.print(roadmap_table)
        
        # Quick wins vs major efforts
        self.console.print("\n[bold]Quick Wins vs Major Efforts:[/bold]")
        
        quick_wins = [
            "Optimize response object creation (eliminate unnecessary instantiation)",
            "Configure MongoDB connection pooling (maxPoolSize=50, minPoolSize=10)",
            "Implement HTTP cache headers for API responses",
            "Add request rate limiting to prevent resource exhaustion"
        ]
        
        major_efforts = [
            "GPU acceleration for FAISS operations",
            "Implement search result streaming for large datasets", 
            "Advanced caching strategies (Redis cluster, CDN integration)",
            "Search index optimization and quantization"
        ]
        
        self.console.print("\n[green]Quick Wins (1-2 days):[/green]")
        for i, item in enumerate(quick_wins, 1):
            self.console.print(f"  {i}. {item}")
        
        self.console.print("\n[blue]Major Efforts (1-2 weeks):[/blue]")
        for i, item in enumerate(major_efforts, 1):
            self.console.print(f"  {i}. {item}")
    
    def save_comprehensive_results(self, results: ComprehensiveResults, base_filename: str = None) -> list[str]:
        """Save all benchmark results to organized files."""
        if base_filename is None:
            timestamp = int(time.time())
            base_filename = f"comprehensive_benchmark_{timestamp}"
        
        saved_files = []
        
        # Save unified results
        unified_file = f"{base_filename}_unified.json"
        unified_data = {
            "timestamp": results.timestamp,
            "system_health": results.system_health,
            "search_pipeline": results.search_pipeline,
            "faiss_performance": results.faiss_performance,
            "cache_performance": results.cache_performance,
            "cross_analysis": self.analyze_cross_benchmark_patterns(results)
        }
        
        with open(unified_file, "w") as f:
            json.dump(unified_data, f, indent=2, default=str)
        saved_files.append(unified_file)
        
        # Save individual benchmark results
        if results.search_pipeline:
            search_file = f"{base_filename}_search_pipeline.json"
            with open(search_file, "w") as f:
                json.dump(results.search_pipeline, f, indent=2, default=str)
            saved_files.append(search_file)
        
        if results.faiss_performance:
            faiss_file = f"{base_filename}_faiss.json"
            with open(faiss_file, "w") as f:
                json.dump(results.faiss_performance, f, indent=2, default=str)
            saved_files.append(faiss_file)
        
        if results.cache_performance:
            cache_file = f"{base_filename}_cache.json"
            with open(cache_file, "w") as f:
                json.dump(results.cache_performance, f, indent=2, default=str)
            saved_files.append(cache_file)
        
        return saved_files


async def main():
    """Run comprehensive benchmarking suite."""
    console = Console()
    
    # Configuration
    config = BenchmarkConfig(
        iterations=100,
        warmup_iterations=10,
        concurrent_workers=10,
        enable_profiling=True
    )
    
    # Run comprehensive benchmarks
    orchestrator = ComprehensiveBenchmarkOrchestrator(config)
    
    try:
        results = await orchestrator.run_all_benchmarks()
        
        # Generate comprehensive report
        orchestrator.generate_comprehensive_report(results)
        
        # Save all results
        saved_files = orchestrator.save_comprehensive_results(results)
        
        console.print(f"\n[bold green]✅ Comprehensive benchmark analysis complete![/bold green]")
        console.print(f"\n[bold]📁 Results saved to:[/bold]")
        for file in saved_files:
            console.print(f"  • {file}")
        
        # Return success/failure based on critical issues
        analysis = orchestrator.analyze_cross_benchmark_patterns(results)
        critical_issues = [b for b in analysis["performance_bottlenecks"] if b["severity"] == "critical"]
        
        if critical_issues:
            console.print(f"\n[red]⚠️  {len(critical_issues)} critical performance issue(s) detected[/red]")
            return False
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Comprehensive benchmark failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)