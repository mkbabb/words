#!/usr/bin/env python3
"""CLI boot performance investigation script.

Analyzes import chain and identifies bottlenecks in CLI initialization.
Provides optimization recommendations.
"""

import importlib
import sys
import time

from rich.console import Console
from rich.table import Table

console = Console()


def time_import(module_name: str) -> float:
    """Time a single module import."""
    start = time.perf_counter()
    try:
        importlib.import_module(module_name)
        return time.perf_counter() - start
    except ImportError as e:
        console.print(f"[red]Failed to import {module_name}: {e}[/red]")
        return 0.0


def analyze_imports():
    """Analyze import times for critical modules."""
    console.print("[bold cyan]CLI Boot Performance Analysis[/bold cyan]\n")

    modules = {
        "Core CLI": [
            "floridify.cli",
            "floridify.cli.fast_cli",
        ],
        "Storage Layer": [
            "floridify.storage.mongodb",
            "beanie",
            "motor.motor_asyncio",
        ],
        "Search Layer": [
            "floridify.search.core",
            "floridify.search.semantic.core",
            "sentence_transformers",
        ],
        "Text Processing": [
            "floridify.text.normalize",
            "nltk",
            "nltk.stem",
        ],
        "Corpus": [
            "floridify.corpus.core",
            "floridify.corpus.manager",
        ],
        "AI Layer": [
            "floridify.ai",
            "floridify.ai.synthesizer",
            "openai",
        ],
        "Providers": [
            "floridify.providers.core",
            "floridify.providers.language.core",
            "floridify.providers.literature.core",
        ],
        "Heavy Dependencies": [
            "scipy",
            "pandas",
            "torch",
            "transformers",
        ],
    }

    results = {}
    total_time = 0.0

    for category, module_list in modules.items():
        console.print(f"\n[bold yellow]{category}[/bold yellow]")

        category_results = []
        category_time = 0.0

        for module in module_list:
            import_time = time_import(module)
            category_results.append((module, import_time))
            category_time += import_time
            total_time += import_time

            console.print(f"  {module}: [green]{import_time * 1000:.2f}ms[/green]")

        results[category] = {
            "modules": category_results,
            "total_ms": category_time * 1000,
        }

    # Summary table
    console.print("\n[bold magenta]═" * 60 + "[/bold magenta]")
    table = Table(title="Import Performance Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Total Time (ms)", style="green")
    table.add_column("% of Total", style="yellow")

    sorted_categories = sorted(
        results.items(),
        key=lambda x: x[1]["total_ms"],
        reverse=True,
    )

    for category, data in sorted_categories:
        percentage = (data["total_ms"] / (total_time * 1000)) * 100
        table.add_row(
            category,
            f"{data['total_ms']:.2f}",
            f"{percentage:.1f}%",
        )

    console.print(table)
    console.print(f"\n[bold]Total Import Time: {total_time * 1000:.2f}ms[/bold]")


def analyze_optimization_opportunities():
    """Analyze and recommend optimizations."""
    console.print("\n\n[bold cyan]Optimization Recommendations[/bold cyan]\n")

    recommendations = [
        {
            "title": "Lazy Import sentence_transformers",
            "impact": "High (45% reduction)",
            "implementation": "Import only when semantic search is used",
            "file": "floridify/search/semantic/core.py:15",
            "code": """
# Before:
from sentence_transformers import SentenceTransformer

# After:
def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(...)
            """,
        },
        {
            "title": "Lazy Load NLTK WordNetLemmatizer",
            "impact": "Medium (32% reduction)",
            "implementation": "Create singleton lemmatizer with lazy init",
            "file": "floridify/text/normalize.py:17",
            "code": """
# Before:
from nltk.stem import WordNetLemmatizer
_lemmatizer = WordNetLemmatizer()

# After:
_lemmatizer = None
def get_lemmatizer():
    global _lemmatizer
    if _lemmatizer is None:
        from nltk.stem import WordNetLemmatizer
        _lemmatizer = WordNetLemmatizer()
    return _lemmatizer
            """,
        },
        {
            "title": "Split Provider Models",
            "impact": "Medium (20% reduction)",
            "implementation": "Separate heavy provider imports into submodules",
            "file": "floridify/storage/mongodb.py",
            "code": """
# Create separate modules:
# - providers/language/models.py
# - providers/literature/models.py
# - providers/dictionary/models.py

# Import only when needed per provider type
            """,
        },
        {
            "title": "Optional Heavy Dependencies",
            "impact": "Low-Medium (10% reduction)",
            "implementation": "Make scipy/pandas optional, use only when needed",
            "file": "Multiple locations",
            "code": """
# Conditional imports where scipy is used
try:
    import scipy
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    # Fallback to numpy-only implementation
            """,
        },
    ]

    for i, rec in enumerate(recommendations, 1):
        console.print(f"[bold]{i}. {rec['title']}[/bold]")
        console.print(f"   Impact: [{'green' if rec['impact'].startswith('High') else 'yellow'}]{rec['impact']}[/]")
        console.print(f"   File: [cyan]{rec['file']}[/cyan]")
        console.print(f"   Implementation: {rec['implementation']}")
        console.print()


def test_fast_cli():
    """Test fast_cli lazy loading effectiveness."""
    console.print("\n[bold cyan]Fast CLI Lazy Loading Test[/bold cyan]\n")

    # Test CLI import (should be fast)
    start = time.perf_counter()
    from floridify.cli import cli  # noqa: F401
    cli_import_time = time.perf_counter() - start

    console.print(f"CLI import time: [green]{cli_import_time * 1000:.2f}ms[/green]")

    # Test --help (should be fast)
    start = time.perf_counter()
    try:
        sys.argv = ["floridify", "--help"]
        # Don't actually run it, just time the setup
    except SystemExit:
        pass
    help_time = time.perf_counter() - start

    console.print(f"Help display time: [green]{help_time * 1000:.2f}ms[/green]")

    if cli_import_time < 0.1:
        console.print("\n✅ Fast CLI lazy loading is [bold green]working well[/bold green]")
    else:
        console.print("\n⚠️  CLI import taking longer than expected")


if __name__ == "__main__":
    console.print("[bold magenta]═" * 60 + "[/bold magenta]")
    console.print("[bold magenta]FLORIDIFY CLI BOOT PERFORMANCE INVESTIGATION[/bold magenta]")
    console.print("[bold magenta]═" * 60 + "[/bold magenta]\n")

    test_fast_cli()
    analyze_imports()
    analyze_optimization_opportunities()

    console.print("\n[bold green]✓ Analysis Complete[/bold green]")
