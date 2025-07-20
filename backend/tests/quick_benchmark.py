"""Quick performance benchmark to test basic search pipeline functionality."""

import asyncio
import time
import statistics
from typing import Any, Dict

import httpx
from rich.console import Console
from rich.table import Table


class QuickBenchmark:
    """Simple, fast benchmark for initial performance testing."""
    
    def __init__(self):
        self.console = Console()
        self.base_url = "http://localhost:8000"
    
    async def check_server_health(self) -> bool:
        """Check if server is responsive."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/v1/health")
                return response.status_code == 200
        except Exception:
            return False
    
    async def benchmark_endpoint(self, endpoint: str, params: dict = None, iterations: int = 20) -> Dict[str, Any]:
        """Benchmark a single endpoint."""
        times = []
        errors = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(iterations):
                start_time = time.perf_counter()
                
                try:
                    response = await client.get(f"{self.base_url}{endpoint}", params=params)
                    elapsed = time.perf_counter() - start_time
                    
                    if response.status_code == 200:
                        times.append(elapsed)
                    else:
                        errors += 1
                        
                except Exception as e:
                    errors += 1
                    self.console.print(f"[red]Error {i+1}: {e}[/red]")
                
                # Small delay between requests
                await asyncio.sleep(0.1)
        
        if not times:
            return {"error": "No successful requests", "errors": errors}
        
        return {
            "avg_ms": statistics.mean(times) * 1000,
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
            "p95_ms": sorted(times)[int(len(times) * 0.95)] * 1000,
            "success_rate": len(times) / iterations * 100,
            "errors": errors,
            "total_requests": iterations
        }
    
    async def run_quick_benchmarks(self) -> Dict[str, Any]:
        """Run a quick set of benchmarks."""
        self.console.print("[bold cyan]🚀 Quick Search Pipeline Benchmark[/bold cyan]\n")
        
        # Check server health first
        if not await self.check_server_health():
            self.console.print("[red]❌ Server is not healthy - cannot run benchmarks[/red]")
            return {"error": "Server not healthy"}
        
        results = {}
        
        # Test cases ordered by complexity/speed
        test_cases = [
            ("Health Check", "/api/v1/health", {}),
            ("Simple Search", "/api/v1/search", {"q": "cat"}),
            ("Fuzzy Search", "/api/v1/search", {"q": "algoritm"}),  # intentional typo
            ("Phrase Search", "/api/v1/search", {"q": "machine learning"}),
            ("Word Lookup", "/api/v1/lookup/computer", {}),
            ("Word with Force Refresh", "/api/v1/lookup/algorithm", {"force_refresh": "false"}),
        ]
        
        for name, endpoint, params in test_cases:
            self.console.print(f"[dim]Testing {name}...[/dim]")
            
            try:
                result = await self.benchmark_endpoint(endpoint, params, iterations=10)
                results[name] = result
                
                if "error" not in result:
                    avg_time = result["avg_ms"]
                    success_rate = result["success_rate"]
                    status = "🟢" if avg_time < 100 and success_rate >= 90 else "🟡" if avg_time < 500 else "🔴"
                    self.console.print(f"  {status} {avg_time:.1f}ms avg ({success_rate:.0f}% success)")
                else:
                    self.console.print(f"  🔴 {result['error']}")
                    
            except Exception as e:
                self.console.print(f"[red]Failed to test {name}: {e}[/red]")
                results[name] = {"error": str(e)}
        
        return results
    
    def generate_report(self, results: Dict[str, Any]) -> None:
        """Generate a simple performance report."""
        if "error" in results:
            return
        
        self.console.print("\n[bold]📊 Performance Summary[/bold]")
        
        table = Table(title="Quick Benchmark Results")
        table.add_column("Test", style="cyan")
        table.add_column("Avg (ms)", justify="right")
        table.add_column("Min (ms)", justify="right")
        table.add_column("Max (ms)", justify="right") 
        table.add_column("P95 (ms)", justify="right")
        table.add_column("Success %", justify="right", style="green")
        table.add_column("Status", justify="center")
        
        for test_name, data in results.items():
            if "error" in data:
                table.add_row(test_name, "-", "-", "-", "-", "-", "🔴 Error")
                continue
            
            avg_ms = data["avg_ms"]
            status = "🟢 Fast" if avg_ms < 100 else "🟡 OK" if avg_ms < 500 else "🔴 Slow"
            
            table.add_row(
                test_name,
                f"{avg_ms:.1f}",
                f"{data['min_ms']:.1f}",
                f"{data['max_ms']:.1f}",
                f"{data['p95_ms']:.1f}",
                f"{data['success_rate']:.0f}%",
                status
            )
        
        self.console.print(table)
        
        # Quick insights
        self.console.print("\n[bold]🎯 Quick Insights:[/bold]")
        
        slow_tests = [name for name, data in results.items() 
                     if "error" not in data and data["avg_ms"] > 500]
        
        if slow_tests:
            self.console.print(f"[yellow]• Slow operations detected: {', '.join(slow_tests)}[/yellow]")
        
        failed_tests = [name for name, data in results.items() if "error" in data]
        if failed_tests:
            self.console.print(f"[red]• Failed operations: {', '.join(failed_tests)}[/red]")
        
        if not slow_tests and not failed_tests:
            self.console.print("[green]• All operations performing well![/green]")
        
        # Performance recommendations
        lookup_data = results.get("Word Lookup")
        search_data = results.get("Simple Search")
        
        if lookup_data and search_data and "error" not in lookup_data and "error" not in search_data:
            lookup_time = lookup_data["avg_ms"]
            search_time = search_data["avg_ms"]
            
            if lookup_time > search_time * 3:
                self.console.print(f"[yellow]• Word lookup ({lookup_time:.1f}ms) is significantly slower than search ({search_time:.1f}ms)[/yellow]")
            
            if search_time > 100:
                self.console.print(f"[yellow]• Search performance could be improved ({search_time:.1f}ms avg)[/yellow]")


async def main():
    """Run quick benchmark."""
    benchmark = QuickBenchmark()
    
    try:
        results = await benchmark.run_quick_benchmarks()
        benchmark.generate_report(results)
        
        # Simple pass/fail determination
        if "error" in results:
            return False
        
        # Check if any critical operations are too slow
        critical_ops = ["Health Check", "Simple Search"]
        for op in critical_ops:
            if op in results and "error" not in results[op]:
                if results[op]["avg_ms"] > 1000:  # 1 second threshold
                    benchmark.console.print(f"\n[red]❌ Critical operation '{op}' is too slow: {results[op]['avg_ms']:.1f}ms[/red]")
                    return False
        
        benchmark.console.print("\n[green]✅ Quick benchmark completed successfully![/green]")
        return True
        
    except Exception as e:
        benchmark.console.print(f"[red]❌ Quick benchmark failed: {e}[/red]")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)