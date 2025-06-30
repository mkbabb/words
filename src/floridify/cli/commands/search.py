"""Search and discovery commands for the new unified search engine."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from ...search import Language, SearchEngine, SearchMethod, SearchResult
from ..utils.formatting import format_error

console = Console()

# Global search engine instance
_search_engine: SearchEngine | None = None


async def get_search_engine() -> SearchEngine:
    """Get or create the global search engine instance."""
    global _search_engine

    if _search_engine is None:
        # Initialize search engine with default settings
        cache_dir = Path("data/search")
        _search_engine = SearchEngine(
            cache_dir=cache_dir,
            languages=[Language.ENGLISH],
            min_score=0.6,
            enable_semantic=True,
        )
        await _search_engine.initialize()

    return _search_engine


@click.group()
def search_group() -> None:
    """🔎 Search for words using exact, fuzzy, and semantic matching."""
    pass


@search_group.command("find")
@click.argument("query")
@click.option("--max-results", "-n", default=20, help="Maximum number of results")
@click.option("--min-score", "-s", default=None, type=float, help="Minimum match score (0.0-1.0)")
@click.option(
    "--method",
    "-m",
    multiple=True,
    type=click.Choice(["exact", "prefix", "fuzzy", "semantic", "auto"]),
    help="Search methods to use (can specify multiple)",
)
@click.option(
    "--languages",
    "-l",
    multiple=True,
    type=click.Choice(["en", "fr"]),
    help="Languages to search (defaults to English)",
)
def search_find(
    query: str,
    max_results: int,
    min_score: float | None,
    method: tuple[str, ...],
    languages: tuple[str, ...],
) -> None:
    """Find words and phrases using the unified search engine.

    Supports multiple search methods:
    - exact: Exact string matching
    - prefix: Prefix matching for autocomplete
    - fuzzy: Typo-tolerant fuzzy matching
    - semantic: Meaning-based similarity search
    - auto: Automatic method selection (default)

    QUERY: The word or phrase to search for
    """
    asyncio.run(_search_find_async(query, max_results, min_score, method, languages))


async def _search_find_async(
    query: str,
    max_results: int,
    min_score: float | None,
    methods: tuple[str, ...],
    languages: tuple[str, ...],
) -> None:
    """Async implementation of unified search."""
    try:
        # Get search engine
        search_engine = await get_search_engine()

        # Convert string methods to SearchMethod enums
        search_methods = []
        if methods:
            method_map = {
                "exact": SearchMethod.EXACT,
                "prefix": SearchMethod.PREFIX,
                "fuzzy": SearchMethod.FUZZY,
                "semantic": SearchMethod.SEMANTIC,
                "auto": SearchMethod.AUTO,
            }
            search_methods = [method_map[m] for m in methods if m in method_map]
        else:
            search_methods = [SearchMethod.AUTO]

        # Perform search
        with console.status(f"[bold blue]Searching for '{query}'..."):
            results = await search_engine.search(
                query=query,
                max_results=max_results,
                min_score=min_score,
                methods=search_methods,
            )

        # Display results
        if results:
            _display_search_results(query, results)

            # Show performance stats
            stats = search_engine.get_search_stats()
            _display_performance_stats(stats)
        else:
            console.print(
                format_error(
                    f"No results found for '{query}'",
                    "Try using a different query, lowering the minimum score, or using different search methods.",
                )
            )

    except Exception as e:
        console.print(format_error(f"Search failed: {e}"))


@search_group.command("exact")
@click.argument("query")
@click.option("--max-results", "-n", default=10, help="Maximum number of results")
def search_exact(query: str, max_results: int) -> None:
    """Find exact matches for a word or phrase.

    QUERY: The exact word or phrase to search for
    """
    asyncio.run(_search_method_async(query, max_results, [SearchMethod.EXACT]))


@search_group.command("prefix")
@click.argument("prefix")
@click.option("--max-results", "-n", default=20, help="Maximum number of results")
def search_prefix(prefix: str, max_results: int) -> None:
    """Find words that start with the given prefix (autocomplete).

    PREFIX: The prefix to search for
    """
    asyncio.run(_search_method_async(prefix, max_results, [SearchMethod.PREFIX]))


@search_group.command("fuzzy")
@click.argument("query")
@click.option("--max-results", "-n", default=15, help="Maximum number of results")
@click.option("--min-score", "-s", default=0.6, help="Minimum match score (0.0-1.0)")
def search_fuzzy(query: str, max_results: int, min_score: float) -> None:
    """Find words using fuzzy matching (typo tolerance).

    Great for finding words when you have typos or don't know the exact spelling.

    QUERY: The word to search for (typos OK)
    """
    asyncio.run(_search_method_async(query, max_results, [SearchMethod.FUZZY], min_score))


@search_group.command("semantic")
@click.argument("query")
@click.option("--max-results", "-n", default=20, help="Maximum number of results")
@click.option("--min-score", "-s", default=0.5, help="Minimum similarity score (0.0-1.0)")
def search_semantic(query: str, max_results: int, min_score: float) -> None:
    """Find words using semantic similarity (meaning-based).

    Finds words with similar meanings, synonyms, and related concepts.

    QUERY: The word or concept to find similar words for
    """
    asyncio.run(_search_method_async(query, max_results, [SearchMethod.SEMANTIC], min_score))


async def _search_method_async(
    query: str,
    max_results: int,
    methods: list[SearchMethod],
    min_score: float | None = None,
) -> None:
    """Helper for method-specific searches."""
    try:
        search_engine = await get_search_engine()

        with console.status(f"[bold blue]Searching for '{query}'..."):
            results = await search_engine.search(
                query=query,
                max_results=max_results,
                min_score=min_score,
                methods=methods,
            )

        if results:
            _display_search_results(query, results)
        else:
            method_name = methods[0].value if methods else "search"
            console.print(
                format_error(
                    f"No {method_name} results found for '{query}'",
                    "Try using a different query or search method.",
                )
            )

    except Exception as e:
        console.print(format_error(f"Search failed: {e}"))


@search_group.command("stats")
def search_stats() -> None:
    """Show search engine statistics and performance metrics."""
    asyncio.run(_search_stats_async())


async def _search_stats_async() -> None:
    """Display search engine statistics."""
    try:
        search_engine = await get_search_engine()

        # Get lexicon statistics
        if search_engine.lexicon_loader:
            lexicon_stats = search_engine.lexicon_loader.get_statistics()
            _display_lexicon_stats(lexicon_stats)

        # Get search performance statistics
        search_stats = search_engine.get_search_stats()
        _display_performance_stats(search_stats)

        # Get component statistics
        if search_engine.trie_search:
            trie_stats = search_engine.trie_search.get_statistics()
            _display_trie_stats(trie_stats)

        if search_engine.semantic_search:
            semantic_stats = search_engine.semantic_search.get_statistics()
            _display_semantic_stats(semantic_stats)

    except Exception as e:
        console.print(format_error(f"Failed to get statistics: {e}"))


def _display_search_results(query: str, results: list[SearchResult]) -> None:
    """Display search results in a formatted table."""

    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Word/Phrase", style="cyan", no_wrap=False, width=30)
    table.add_column("Score", style="magenta", justify="right", width=8)
    table.add_column("Method", style="green", width=12)
    table.add_column("Type", style="yellow", width=8)

    for result in results:
        # Format score as percentage
        score_text = f"{result.score:.1%}"

        # Color-code by score
        if result.score >= 0.9:
            score_style = "bright_green"
        elif result.score >= 0.7:
            score_style = "green"
        elif result.score >= 0.5:
            score_style = "yellow"
        else:
            score_style = "red"

        # Determine type
        type_text = "Phrase" if result.is_phrase else "Word"

        # Add method-specific styling
        method_text = result.method.value.title()
        if result.method == SearchMethod.EXACT:
            method_style = "bright_green"
        elif result.method == SearchMethod.PREFIX:
            method_style = "green"
        elif result.method == SearchMethod.FUZZY:
            method_style = "blue"
        elif result.method == SearchMethod.SEMANTIC:
            method_style = "magenta"
        else:
            method_style = "white"

        table.add_row(
            result.word,
            Text(score_text, style=score_style),
            Text(method_text, style=method_style),
            type_text,
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(results)} results[/dim]")


def _display_performance_stats(stats: dict[str, dict[str, Any]]) -> None:
    """Display search performance statistics."""

    if not any(data["count"] > 0 for data in stats.values()):
        return

    table = Table(title="Search Performance")
    table.add_column("Method", style="cyan")
    table.add_column("Searches", justify="right", style="magenta")
    table.add_column("Total Time", justify="right", style="green")
    table.add_column("Avg Time", justify="right", style="yellow")

    for method, data in stats.items():
        if data["count"] > 0:
            table.add_row(
                method.title(),
                str(data["count"]),
                f"{data['total_time']:.3f}s",
                f"{data['avg_time']:.3f}s",
            )

    console.print(table)


def _display_lexicon_stats(stats: dict[str, Any]) -> None:
    """Display lexicon loading statistics."""

    table = Table(title="Lexicon Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="magenta")

    table.add_row("Total Words", f"{stats['total_words']:,}")
    table.add_row("Total Phrases", f"{stats['total_phrases']:,}")

    # Show per-language breakdown
    for lang, lang_stats in stats.get("languages", {}).items():
        table.add_row(f"Words ({lang.upper()})", f"{lang_stats['words']:,}")
        table.add_row(f"Phrases ({lang.upper()})", f"{lang_stats['phrases']:,}")

    console.print(table)


def _display_trie_stats(stats: dict[str, Any]) -> None:
    """Display trie search statistics."""

    table = Table(title="Trie Index Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="magenta")

    table.add_row("Indexed Words", f"{stats['word_count']:,}")
    table.add_row("Memory Nodes", f"{stats['memory_nodes']:,}")
    table.add_row("Average Depth", f"{stats['average_depth']:.1f}")
    table.add_row("Max Frequency", f"{stats['max_frequency']:,}")

    console.print(table)


def _display_semantic_stats(stats: dict[str, Any]) -> None:
    """Display semantic search statistics."""

    table = Table(title="Semantic Search Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="magenta")

    table.add_row("Vocabulary Size", f"{stats['vocabulary_size']:,}")
    table.add_row("FAISS Available", "Yes" if stats["has_faiss"] else "No")
    table.add_row("Scikit-learn Available", "Yes" if stats["has_sklearn"] else "No")

    # Show embedding levels
    for level, level_stats in stats.get("embedding_levels", {}).items():
        table.add_row(f"{level.title()} Embeddings", f"{level_stats['features']}D")

    console.print(table)


@search_group.command("init")
@click.option("--cache-dir", default="./data/search/", help="Cache directory for search index")
@click.option(
    "--languages",
    "-l",
    multiple=True,
    type=click.Choice(["en", "fr", "es", "de", "it"]),
    default=["en"],
    help="Languages to initialize",
)
@click.option("--enable-semantic/--no-semantic", default=True, help="Enable semantic search")
@click.option("--force", "-f", is_flag=True, help="Force rebuild of existing index")
def search_init(
    cache_dir: str, languages: tuple[str, ...], enable_semantic: bool, force: bool
) -> None:
    """Initialize the search engine index with lexical data.

    This command builds the search index by downloading lexical sources,
    creating trie structures, and initializing semantic embeddings.
    """
    asyncio.run(_search_init_async(cache_dir, languages, enable_semantic, force))


async def _search_init_async(
    cache_dir: str, languages: tuple[str, ...], enable_semantic: bool, force: bool
) -> None:
    """Initialize search engine index."""
    from pathlib import Path

    try:
        # Convert language strings to Language enums
        lang_map = {
            "en": Language.ENGLISH,
            "fr": Language.FRENCH,
            "es": Language.SPANISH,
            "de": Language.GERMAN,
            "it": Language.ITALIAN,
        }

        selected_languages = [lang_map[lang] for lang in languages if lang in lang_map]

        console.print("[bold blue]🚀 Initializing search index...[/bold blue]")
        console.print(f"Cache directory: {cache_dir}")
        console.print(f"Languages: {', '.join(languages)}")
        console.print(f"Semantic search: {'enabled' if enable_semantic else 'disabled'}")

        # Check if index already exists
        cache_path = Path(cache_dir)
        if cache_path.exists() and not force:
            existing_files = list(cache_path.glob("*.pkl"))
            if existing_files:
                console.print(
                    f"[yellow]⚠️  Index already exists with {len(existing_files)} cache files.[/yellow]"
                )
                console.print(
                    "Use --force to rebuild, or run without --force to use existing index."
                )
                return

        # Initialize search engine
        search_engine = SearchEngine(
            cache_dir=cache_path,
            languages=selected_languages,
            enable_semantic=enable_semantic,
        )

        with console.status("[bold blue]Building search index..."):
            await search_engine.initialize()

        # Display statistics
        console.print("\n[bold green]✅ Search index initialized successfully![/bold green]")

        # Show index statistics
        if search_engine.lexicon_loader:
            lexicon_stats = search_engine.lexicon_loader.get_statistics()
            _display_lexicon_stats(lexicon_stats)

        if search_engine.trie_search:
            trie_stats = search_engine.trie_search.get_statistics()
            _display_trie_stats(trie_stats)

        if search_engine.semantic_search:
            semantic_stats = search_engine.semantic_search.get_statistics()
            _display_semantic_stats(semantic_stats)

        # Cleanup
        await search_engine.close()

    except Exception as e:
        console.print(format_error(f"Failed to initialize search index: {e}"))


@search_group.command("benchmark")
@click.option("--queries", "-q", default=10, help="Number of test queries")
@click.option(
    "--methods",
    "-m",
    multiple=True,
    type=click.Choice(["exact", "prefix", "fuzzy", "semantic"]),
    help="Methods to benchmark",
)
def search_benchmark(queries: int, methods: tuple[str, ...]) -> None:
    """Benchmark search performance with test queries."""
    asyncio.run(_search_benchmark_async(queries, methods))


async def _search_benchmark_async(query_count: int, methods: tuple[str, ...]) -> None:
    """Run search benchmarks."""
    try:
        search_engine = await get_search_engine()

        # Default methods if none specified
        if not methods:
            methods = ("exact", "prefix", "fuzzy", "semantic")

        # Test queries of different types
        test_queries = [
            "hello",
            "definition",
            "search",
            "world",
            "language",
            "machine learning",
            "natural language",
            "hello world",
            "helo",
            "defintion",
            "machne learing",  # Typos
            "happy",
            "joyful",
            "sad",
            "angry",
            "excited",  # For semantic
        ]

        method_map = {
            "exact": SearchMethod.EXACT,
            "prefix": SearchMethod.PREFIX,
            "fuzzy": SearchMethod.FUZZY,
            "semantic": SearchMethod.SEMANTIC,
        }

        console.print(f"[bold blue]Running benchmark with {query_count} queries...[/bold blue]")

        # Run benchmarks for each method
        for method_name in methods:
            if method_name not in method_map:
                continue

            method = method_map[method_name]
            console.print(f"\n[cyan]Benchmarking {method_name} search...[/cyan]")

            import time

            start_time = time.perf_counter()

            total_results = 0
            for i in range(query_count):
                query = test_queries[i % len(test_queries)]
                results = await search_engine.search(
                    query=query,
                    max_results=10,
                    methods=[method],
                )
                total_results += len(results)

            end_time = time.perf_counter()
            elapsed = end_time - start_time

            console.print(f"  Total time: {elapsed:.3f}s")
            console.print(f"  Average per query: {elapsed / query_count:.3f}s")
            console.print(f"  Total results: {total_results}")
            console.print(f"  Average results per query: {total_results / query_count:.1f}")

        # Show final performance stats
        console.print("\n[bold green]Final Performance Statistics:[/bold green]")
        stats = search_engine.get_search_stats()
        _display_performance_stats(stats)

    except Exception as e:
        console.print(format_error(f"Benchmark failed: {e}"))


# Register with the main CLI
search_cmd = search_group
