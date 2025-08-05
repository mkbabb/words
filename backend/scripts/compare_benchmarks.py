#!/usr/bin/env python3
"""
Benchmark Comparison Script

Compare two benchmark results and show performance deltas.
Usage: python scripts/compare_benchmarks.py <before.json> <after.json>
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()


def load_benchmark(file_path: str) -> dict[str, Any]:
    """Load benchmark results from JSON file."""
    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        sys.exit(1)
    
    try:
        with open(path) as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON in {file_path}: {e}[/red]")
        sys.exit(1)


def extract_metrics(results: list[dict]) -> dict[str, dict[str, float]]:
    """Extract key metrics from benchmark results."""
    metrics = {}
    for result in results:
        search_type = result.get("search_type", "unknown")
        
        # Handle different result formats
        if "p95_ms" in result:
            metrics[search_type] = {
                "mean_ms": result.get("mean_ms", 0),
                "median_ms": result.get("median_ms", 0),
                "p95_ms": result.get("p95_ms", 0),
                "p99_ms": result.get("p99_ms", 0),
                "throughput_qps": result.get("throughput_qps", 0),
                "error_rate": result.get("error_rate", 0)
            }
        elif "stats" in result:
            # Handle nested stats format
            stats = result["stats"]
            metrics[search_type] = {
                "mean_ms": stats.get("mean_ms", 0),
                "median_ms": stats.get("median_ms", 0),
                "p95_ms": stats.get("p95_ms", 0),
                "p99_ms": stats.get("p99_ms", 0),
                "throughput_qps": stats.get("throughput_qps", 0),
                "error_rate": stats.get("error_rate", 0)
            }
    
    return metrics


def calculate_delta(before: float, after: float) -> tuple[float, float]:
    """Calculate absolute and percentage delta."""
    absolute_delta = after - before
    if before == 0:
        percentage_delta = 0 if after == 0 else float('inf')
    else:
        percentage_delta = (absolute_delta / before) * 100
    return absolute_delta, percentage_delta


def format_delta(absolute: float, percentage: float, unit: str = "ms", lower_is_better: bool = True) -> Text:
    """Format delta with color coding."""
    if absolute == 0:
        return Text("0.00", style="white")
    
    # Determine if this is an improvement
    is_improvement = (absolute < 0) if lower_is_better else (absolute > 0)
    
    # Format the text
    if abs(percentage) == float('inf'):
        delta_text = f"{absolute:+.2f}{unit}"
    else:
        delta_text = f"{absolute:+.2f}{unit} ({percentage:+.1f}%)"
    
    # Color coding
    if is_improvement:
        return Text(delta_text, style="green")
    else:
        return Text(delta_text, style="red")


def compare_benchmarks(before_file: str, after_file: str):
    """Compare two benchmark files and display results."""
    
    # Load benchmarks
    before_data = load_benchmark(before_file)
    after_data = load_benchmark(after_file)
    
    # Extract metadata
    before_info = before_data.get("benchmark_info", {})
    after_info = after_data.get("benchmark_info", {})
    
    # Display comparison header
    console.print("\n[bold blue]Benchmark Comparison Report[/bold blue]")
    console.print("=" * 50)
    
    console.print(f"[cyan]Before:[/cyan] {before_info.get('readable_time', 'Unknown')} ({Path(before_file).name})")
    console.print(f"[cyan]After:[/cyan]  {after_info.get('readable_time', 'Unknown')} ({Path(after_file).name})")
    
    # Extract metrics
    before_metrics = extract_metrics(before_data.get("results", []))
    after_metrics = extract_metrics(after_data.get("results", []))
    
    # Create comparison table
    table = Table(title="Performance Delta Analysis")
    table.add_column("Search Type", style="cyan", no_wrap=True)
    table.add_column("Metric", style="white")
    table.add_column("Before", style="yellow")
    table.add_column("After", style="yellow") 
    table.add_column("Delta", style="bold")
    table.add_column("Status", style="bold")
    
    # Performance targets for status
    targets = {
        "exact": 1.0,
        "fuzzy": 5.0,
        "semantic": 10.0,
        "combined": 10.0,
        "cache": 0.5,
        "concurrent": 10.0
    }
    
    # Compare metrics
    all_search_types = set(before_metrics.keys()) | set(after_metrics.keys())
    
    for search_type in sorted(all_search_types):
        before_vals = before_metrics.get(search_type, {})
        after_vals = after_metrics.get(search_type, {})
        
        # P95 latency comparison (most important)
        before_p95 = before_vals.get("p95_ms", 0)
        after_p95 = after_vals.get("p95_ms", 0)
        
        if before_p95 > 0 or after_p95 > 0:
            abs_delta, pct_delta = calculate_delta(before_p95, after_p95)
            delta_text = format_delta(abs_delta, pct_delta, "ms", lower_is_better=True)
            
            # Status check
            target = targets.get(search_type, 10.0)
            status = "✅ PASS" if after_p95 <= target else "❌ FAIL"
            
            table.add_row(
                search_type,
                "P95 Latency",
                f"{before_p95:.2f}ms",
                f"{after_p95:.2f}ms",
                delta_text,
                status
            )
        
        # Throughput comparison (for concurrent tests)
        before_qps = before_vals.get("throughput_qps", 0)
        after_qps = after_vals.get("throughput_qps", 0)
        
        if before_qps > 0 or after_qps > 0:
            abs_delta, pct_delta = calculate_delta(before_qps, after_qps)
            delta_text = format_delta(abs_delta, pct_delta, " QPS", lower_is_better=False)
            
            table.add_row(
                "",
                "Throughput",
                f"{before_qps:.2f} QPS",
                f"{after_qps:.2f} QPS", 
                delta_text,
                ""
            )
    
    console.print(table)
    
    # Summary
    console.print("\n[bold]Summary:[/bold]")
    improvements = 0
    regressions = 0
    
    for search_type in all_search_types:
        before_vals = before_metrics.get(search_type, {})
        after_vals = after_metrics.get(search_type, {})
        
        before_p95 = before_vals.get("p95_ms", 0)
        after_p95 = after_vals.get("p95_ms", 0)
        
        if before_p95 > 0 and after_p95 > 0:
            if after_p95 < before_p95:
                improvements += 1
            elif after_p95 > before_p95:
                regressions += 1
    
    console.print(f"  [green]Improvements:[/green] {improvements}")
    console.print(f"  [red]Regressions:[/red] {regressions}")
    
    return improvements, regressions


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compare benchmark results")
    parser.add_argument("before", help="Path to 'before' benchmark JSON file")
    parser.add_argument("after", help="Path to 'after' benchmark JSON file")
    
    args = parser.parse_args()
    
    compare_benchmarks(args.before, args.after)


if __name__ == "__main__":
    main()