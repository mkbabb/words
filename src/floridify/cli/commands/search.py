"""Search and discovery commands for fuzzy and semantic word finding."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console

from ...search import SearchManager
from ...search.enums import SearchMethod, VectorSearchMethod, LanguageCode
from ..utils.formatting import format_search_results, format_similarity_results, format_error

console = Console()

# Global search manager instance
search_manager = SearchManager()


@click.group()
def search_group() -> None:
    """🔎 Search for words using fuzzy matching and semantic similarity."""
    pass


@search_group.command("fuzzy")
@click.argument("pattern")
@click.option("--max-results", "-n", default=10, help="Maximum number of results")
@click.option("--threshold", "-t", default=0.6, help="Minimum match score (0.0-1.0)")
@click.option("--include-abbreviations", "-a", is_flag=True, 
              help="Include abbreviation matches (e.g., 'syn' → 'synonym')")
def fuzzy_search(pattern: str, max_results: int, threshold: float, include_abbreviations: bool) -> None:
    """Find words using fuzzy string matching.
    
    Uses VSCode-style fuzzy matching with character sequence matching,
    position weighting, and consecutive character bonuses.
    
    PATTERN: The search pattern (can be partial word, abbreviation, etc.)
    """
    asyncio.run(_fuzzy_search_async(pattern, max_results, threshold, include_abbreviations))


async def _fuzzy_search_async(
    pattern: str, max_results: int, threshold: float, include_abbreviations: bool
) -> None:
    """Async implementation of fuzzy search using advanced search engine."""
    try:
        with console.status(f"[bold blue]Searching for '{pattern}'..."):
            # Use the advanced search manager
            search_methods = [SearchMethod.HYBRID, SearchMethod.RAPIDFUZZ]
            if include_abbreviations:
                search_methods.append(SearchMethod.VECTORIZED)
            
            results = await search_manager.search(
                pattern, 
                max_results=max_results,
                methods=search_methods,
                score_threshold=threshold
            )
            
            if results:
                # Convert to display format
                display_results = [(result.score, result.word) for result in results]
                table = format_search_results(display_results, f"Fuzzy matches for '{pattern}'")
                console.print(table)
                
                # Show search statistics
                search_stats = search_manager.get_search_stats()
                total_words = search_stats['index']['unique_words']
                console.print(f"\n⚡ Found {len(results)} matches from {total_words:,} words")
                
                # Show method breakdown
                methods_used = set(result.method for result in results)
                if len(methods_used) > 1:
                    method_summary = ", ".join(methods_used)
                    console.print(f"[dim]Search methods: {method_summary}[/dim]")
                
                # Show performance info
                avg_time = search_stats['performance']['avg_search_time']
                console.print(f"[dim]Average search time: {avg_time:.3f}s[/dim]")
            else:
                console.print(format_error(
                    f"No fuzzy matches found for '{pattern}'",
                    f"Try lowering the threshold (current: {threshold:.1f}) or using a different pattern."
                ))
    
    except Exception as e:
        console.print(format_error(f"Fuzzy search failed: {str(e)}"))


@search_group.command("similar")
@click.argument("word")
@click.option("--count", "-c", default=10, help="Number of similar words to find")
@click.option("--threshold", "-t", default=0.7, help="Minimum similarity score (0.0-1.0)")
@click.option("--explain", "-e", is_flag=True, help="Include similarity explanations")
def semantic_search(word: str, count: int, threshold: float, explain: bool) -> None:
    """Find semantically similar words using vector embeddings.
    
    Uses AI-generated embeddings to find words with similar meanings,
    concepts, or usage patterns.
    
    WORD: The word to find similarities for
    """
    asyncio.run(_semantic_search_async(word, count, threshold, explain))


async def _semantic_search_async(word: str, count: int, threshold: float, explain: bool) -> None:
    """Async implementation of semantic search using vectorized embeddings."""
    try:
        with console.status(f"[bold blue]Finding words similar to '{word}'..."):
            # Use semantic search from search manager
            results = await search_manager.semantic_search(word, max_results=count)
            
            if results:
                if explain:
                    # Format with explanations
                    similarity_results = [
                        (result.score, result.word, result.explanation) 
                        for result in results
                        if result.score >= threshold
                    ]
                    table = format_similarity_results(similarity_results, f"Similar to '{word}'")
                else:
                    # Simple format
                    display_results = [
                        (result.score, result.word) 
                        for result in results
                        if result.score >= threshold
                    ]
                    table = format_search_results(display_results, f"Similar to '{word}'")
                
                console.print(table)
                
                # Show semantic search info
                vector_stats = search_manager.get_search_stats()['vectorized']
                embedding_dim = vector_stats.get('embedding_dim', 'N/A')
                console.print(f"\n🧠 [dim]Semantic similarity via {embedding_dim}D embeddings[/dim]")
                
                # Show method breakdown
                methods_used = set(result.method.replace('semantic_', '') for result in results)
                if methods_used:
                    method_summary = ", ".join(methods_used)
                    console.print(f"[dim]Embedding methods: {method_summary}[/dim]")
                
            else:
                console.print(format_error(
                    f"No similar words found for '{word}'",
                    f"Try lowering the threshold (current: {threshold:.1f}) or using a different word."
                ))
            
    except Exception as e:
        console.print(format_error(f"Semantic search failed: {str(e)}"))


@search_group.command("browse")
@click.argument("category", type=click.Choice(["recent", "popular", "random", "difficult"]))
@click.option("--count", "-c", default=10, help="Number of words to show")
@click.option("--timeframe", "-t", default="week", type=click.Choice(["day", "week", "month"]),
              help="Timeframe for 'recent' and 'popular' categories")
def browse_words(category: str, count: int, timeframe: str) -> None:
    """Browse words by category.
    
    CATEGORY: Type of words to browse
    """
    console.print(f"[bold blue]Browsing {category} words ({timeframe} timeframe)...[/bold blue]")
    console.print("[dim]This feature requires database integration with usage statistics.[/dim]")


@search_group.command("init")
@click.option("--force", is_flag=True, help="Force rebuild of search indices")
def init_search(force: bool) -> None:
    """Initialize the search engine with comprehensive word indices."""
    asyncio.run(_init_search_async(force))


async def _init_search_async(force: bool) -> None:
    """Async implementation of search engine initialization."""
    try:
        console.print("[bold blue]🔍 Initializing Floridify Search Engine[/bold blue]")
        
        if force:
            console.print("[yellow]⚠️  Force rebuild enabled - this will take several minutes[/yellow]")
        
        await search_manager.initialize(force_rebuild=force)
        
        # Show final statistics
        stats = search_manager.get_search_stats()
        console.print("\n[bold green]✅ Search Engine Ready![/bold green]")
        console.print(f"📊 Total words: {stats['index']['unique_words']:,}")
        console.print(f"🌍 Languages: {', '.join(stats['index']['languages'])}")
        console.print(f"🧠 Vector dimensions: {stats['vectorized'].get('embedding_dim', 'N/A')}")
        console.print(f"📁 Cache location: {stats['cache_dir']}")
        
    except Exception as e:
        console.print(format_error(f"Search initialization failed: {str(e)}"))


@search_group.command("advanced")
@click.argument("query")
@click.option("--min-length", type=int, help="Minimum word length")
@click.option("--max-length", type=int, help="Maximum word length")
@click.option("--starts-with", help="Words that start with this prefix")
@click.option("--ends-with", help="Words that end with this suffix")
@click.option("--language", type=click.Choice(["en", "fr", "all"]), default="all", help="Language filter")
@click.option("--method", type=click.Choice(["hybrid", "vectorized", "rapidfuzz", "all"]), default="all", help="Search method")
@click.option("--max-results", "-n", default=20, help="Maximum results")
@click.option("--threshold", "-t", default=0.6, help="Score threshold")
def advanced_search(
    query: str, min_length: int | None, max_length: int | None, 
    starts_with: str | None, ends_with: str | None, language: str,
    method: str, max_results: int, threshold: float
) -> None:
    """Advanced search with filtering options."""
    asyncio.run(_advanced_search_async(
        query, min_length, max_length, starts_with, ends_with,
        language, method, max_results, threshold
    ))


async def _advanced_search_async(
    query: str, min_length: int | None, max_length: int | None,
    starts_with: str | None, ends_with: str | None, language: str,
    method: str, max_results: int, threshold: float
) -> None:
    """Async implementation of advanced search."""
    try:
        with console.status(f"[bold blue]Advanced search for '{query}'..."):
            # Determine search methods
            if method == "all":
                methods = [SearchMethod.HYBRID, SearchMethod.VECTORIZED, SearchMethod.RAPIDFUZZ]
            else:
                # Convert string to enum
                method_map = {
                    "hybrid": SearchMethod.HYBRID,
                    "vectorized": SearchMethod.VECTORIZED,
                    "rapidfuzz": SearchMethod.RAPIDFUZZ
                }
                methods = [method_map.get(method, SearchMethod.HYBRID)]
            
            # Perform filtered search
            results = await search_manager.search_with_filters(
                query=query,
                language=None if language == "all" else language,
                min_length=min_length,
                max_length=max_length,
                starts_with=starts_with,
                ends_with=ends_with,
                max_results=max_results
            )
            
            # Apply score threshold
            filtered_results = [r for r in results if r.score >= threshold]
            
            if filtered_results:
                display_results = [(result.score, result.word) for result in filtered_results]
                table = format_search_results(display_results, f"Advanced search: '{query}'")
                console.print(table)
                
                # Show filter summary
                filters_applied = []
                if min_length: filters_applied.append(f"min length: {min_length}")
                if max_length: filters_applied.append(f"max length: {max_length}")
                if starts_with: filters_applied.append(f"starts with: '{starts_with}'")
                if ends_with: filters_applied.append(f"ends with: '{ends_with}'")
                if language != "all": filters_applied.append(f"language: {language}")
                
                if filters_applied:
                    filter_summary = ", ".join(filters_applied)
                    console.print(f"\n🔍 [dim]Filters applied: {filter_summary}[/dim]")
                
                console.print(f"⚡ Found {len(filtered_results)} matches")
                
            else:
                console.print(format_error(
                    f"No matches found for '{query}' with current filters",
                    "Try relaxing the filters or using a different query."
                ))
    
    except Exception as e:
        console.print(format_error(f"Advanced search failed: {str(e)}"))


@search_group.command("stats")
def search_stats() -> None:
    """Show search engine statistics and performance metrics."""
    asyncio.run(_search_stats_async())


async def _search_stats_async() -> None:
    """Show comprehensive search statistics."""
    try:
        if not search_manager.is_initialized:
            console.print(format_error(
                "Search engine not initialized",
                "Run 'floridify search init' to initialize the search engine first."
            ))
            return
        
        stats = search_manager.get_search_stats()
        
        console.print("[bold blue]🔍 Search Engine Statistics[/bold blue]\n")
        
        # Index statistics
        index_stats = stats['index']
        console.print("[bold]📊 Word Index:[/bold]")
        console.print(f"  • Total words: {index_stats['total_words']:,}")
        console.print(f"  • Unique words: {index_stats['unique_words']:,}")
        console.print(f"  • Languages: {', '.join(index_stats['languages'])}")
        console.print(f"  • Index status: {'✅ Loaded' if index_stats['is_loaded'] else '❌ Not loaded'}")
        
        # Vector statistics
        vector_stats = stats['vectorized']
        console.print("\n[bold]🧠 Vector Search:[/bold]")
        console.print(f"  • Vector status: {'✅ Built' if vector_stats['is_built'] else '❌ Not built'}")
        console.print(f"  • Embedding dimension: {vector_stats.get('embedding_dim', 'N/A')}")
        console.print(f"  • Character vocab: {vector_stats.get('char_vocab_size', 'N/A'):,}")
        console.print(f"  • Subword vocab: {vector_stats.get('subword_vocab_size', 'N/A'):,}")
        
        # Performance statistics
        perf_stats = stats['performance']
        console.print("\n[bold]⚡ Performance:[/bold]")
        console.print(f"  • Total searches: {perf_stats['total_searches']:,}")
        console.print(f"  • Average time: {perf_stats['avg_search_time']:.3f}s")
        
        if perf_stats['method_usage']:
            console.print("  • Method usage:")
            for method, count in perf_stats['method_usage'].items():
                console.print(f"    - {method}: {count:,} searches")
        
        # Lexicon statistics
        lexicon_stats = stats['lexicons']
        console.print("\n[bold]📚 Lexicon Sources:[/bold]")
        console.print(f"  • Online sources: {lexicon_stats['online_sources']}")
        console.print(f"  • Local collections: {lexicon_stats['local_collections']}")
        console.print(f"  • Cache directory: {lexicon_stats['cache_dir']}")
        
        console.print(f"\n💾 Cache location: {stats['cache_dir']}")
        
    except Exception as e:
        console.print(format_error(f"Failed to get search stats: {str(e)}"))


# Aliases for common search patterns
@search_group.command("find")
@click.argument("pattern")
@click.pass_context
def find_alias(ctx: click.Context, pattern: str) -> None:
    """Alias for fuzzy search."""
    ctx.invoke(fuzzy_search, pattern=pattern)


@search_group.command("like")
@click.argument("word")
@click.pass_context
def like_alias(ctx: click.Context, word: str) -> None:
    """Alias for semantic search."""
    ctx.invoke(semantic_search, word=word)