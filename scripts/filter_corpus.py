#!/usr/bin/env python3
"""CLI tool for testing corpus filtering with full lexicons."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.floridify.batch.word_filter import FilterMethod, FilterPresets, WordFilter
from src.floridify.constants import Language
from src.floridify.search.lexicon.lexicon import LexiconLoader

console = Console()


async def filter_corpus(
    languages: tuple[str, ...],
    preset: str,
    min_length: int | None,
    max_length: int | None,
    show_samples: bool,
    export: str | None,
    detailed: bool,
) -> None:
    """Test corpus filtering with full English and French lexicons."""

    console.print("🔍 [bold blue]Corpus Filtering Test[/bold blue]")
    console.print()

    # Convert language names to Language enum
    selected_languages = []
    for lang in languages:
        try:
            selected_languages.append(Language(lang))
        except ValueError:
            console.print(f"❌ Unknown language: {lang}")
            continue

    console.print(f"📚 Loading lexicons: {', '.join(languages)}")

    # Load lexicons
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading lexicons...", total=None)

        try:
            lexicon_loader = LexiconLoader(Path("data/search"), force_rebuild=False)
            await lexicon_loader.load_languages(selected_languages)

            progress.update(task, description="Extracting vocabulary...")

            # Get all words and phrases
            all_words = lexicon_loader.get_all_words()
            all_phrases = lexicon_loader.get_all_phrases()
            total_vocabulary = all_words + all_phrases

            progress.update(task, description="Complete!")

        except Exception as e:
            console.print(f"❌ Error loading lexicons: {e}")
            console.print("💡 Try running: uv run ./scripts/floridify search init")
            return

    # Display original corpus stats
    original_words = len(all_words)
    original_phrases = len(all_phrases)
    original_total = len(total_vocabulary)
    original_unique = len(set(total_vocabulary))

    console.print("\n📊 [bold]Original Corpus Statistics[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Category")
    table.add_column("Count", justify="right")
    table.add_column("Details")

    table.add_row("Words", f"{original_words:,}", "Single words from lexicons")
    table.add_row("Phrases", f"{original_phrases:,}", "Multi-word expressions")
    table.add_row("Total Items", f"{original_total:,}", "Words + phrases")
    table.add_row("Unique Items", f"{original_unique:,}", "After deduplication")
    dup_rate = (1 - original_unique / original_total) * 100 if original_total > 0 else 0
    table.add_row("Duplication", f"{dup_rate:.1f}%", "Percentage of duplicates")

    console.print(table)

    # Create filter
    if min_length or max_length:
        word_filter = WordFilter(
            min_length=min_length or 3, max_length=max_length or 32
        )
        console.print(
            f"\n🔧 Using custom filter: min_length={min_length or 3}, max_length={max_length or 25}"
        )
    else:
        word_filter = getattr(FilterPresets, preset)()
        console.print(f"\n🔧 Using [bold]{preset}[/bold] preset filter")

    # Apply filtering
    console.print("\n⚡ Applying filters...")
    start_time = time.time()

    filtered_words, stats = word_filter.filter_words(total_vocabulary)

    filter_time = time.time() - start_time

    # Display results
    console.print("\n✨ [bold]Filtering Results[/bold]")

    results_table = Table(show_header=True, header_style="bold green")
    results_table.add_column("Metric")
    results_table.add_column("Before", justify="right")
    results_table.add_column("After", justify="right")
    results_table.add_column("Change", justify="right")

    retention_rate = (stats.remaining / stats.total) * 100 if stats.total > 0 else 0
    reduction_rate = 100 - retention_rate

    results_table.add_row(
        "Total Words",
        f"{stats.total:,}",
        f"{stats.remaining:,}",
        f"-{stats.filtered:,} (-{reduction_rate:.1f}%)",
    )

    # Calculate processing rate
    words_per_sec = stats.total / filter_time if filter_time > 0 else 0

    results_table.add_row(
        "Processing Rate",
        "-",
        f"{words_per_sec:,.0f} words/sec",
        f"{filter_time:.3f}s total",
    )

    # Quality metrics
    if filtered_words:
        avg_length = sum(len(w) for w in filtered_words) / len(filtered_words)
        long_words = len([w for w in filtered_words if len(w) >= 6])
        long_word_pct = (long_words / len(filtered_words)) * 100

        results_table.add_row("Avg Word Length", "-", f"{avg_length:.1f} chars", "-")

        results_table.add_row(
            "Long Words (6+ chars)",
            "-",
            f"{long_words:,} ({long_word_pct:.1f}%)",
            "Quality indicator",
        )

    console.print(results_table)

    # Show samples if requested
    if show_samples and filtered_words:
        console.print("\n📝 [bold]Sample Results[/bold]")

        # Get diverse samples
        unique_filtered = sorted(set(filtered_words))
        # sample_size = min(20, len(unique_filtered))  # Unused variable

        # Show shortest, longest, and some random samples
        shortest = sorted(unique_filtered, key=len)[:5]
        longest = sorted(unique_filtered, key=len, reverse=True)[:5]
        middle_start = len(unique_filtered) // 2
        middle = unique_filtered[middle_start : middle_start + 10]

        sample_table = Table(show_header=True, header_style="bold cyan")
        sample_table.add_column("Category")
        sample_table.add_column("Words")

        sample_table.add_row("Shortest", ", ".join(shortest))
        sample_table.add_row("Longest", ", ".join(longest))
        sample_table.add_row("Sample", ", ".join(middle))

        console.print(sample_table)

    # Show detailed stats if requested
    if detailed:
        console.print("\n📈 [bold]Detailed Analysis[/bold]")

        # Analyze by length
        length_dist: dict[int, int] = {}
        for word in filtered_words:
            length = len(word)
            length_dist[length] = length_dist.get(length, 0) + 1

        console.print("Word Length Distribution:")
        for length in sorted(length_dist.keys())[:10]:  # Show top 10
            count = length_dist[length]
            pct = (count / len(filtered_words)) * 100 if filtered_words else 0
            console.print(f"  {length} chars: {count:,} words ({pct:.1f}%)")

        # Cost analysis (rough estimate)
        cost_per_word = 0.0005  # Rough estimate for AI synthesis
        original_cost = stats.total * cost_per_word
        filtered_cost = stats.remaining * cost_per_word
        savings = original_cost - filtered_cost

        console.print("\n💰 Cost Impact (estimated):")
        console.print(f"  Original cost: ${original_cost:.2f}")
        console.print(f"  Filtered cost: ${filtered_cost:.2f}")
        console.print(f"  Savings: ${savings:.2f} ({(savings/original_cost)*100:.1f}%)")

    # Export if requested
    if export and filtered_words:
        export_path = Path(export)
        console.print(f"\n💾 Exporting to {export_path}")

        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                for word in sorted(set(filtered_words)):
                    f.write(f"{word}\n")
            console.print(f"✅ Exported {len(set(filtered_words)):,} unique words")
        except Exception as e:
            console.print(f"❌ Export failed: {e}")

    # Summary
    console.print("\n🎯 [bold]Summary[/bold]")
    console.print(f"  Processed: {stats.total:,} → {stats.remaining:,} words")
    console.print(f"  Reduction: {reduction_rate:.1f}%")
    console.print(f"  Performance: {words_per_sec:,.0f} words/sec")

    if retention_rate < 1:
        console.print(
            "  [yellow]⚠️  Very aggressive filtering - consider using 'minimal' preset[/yellow]"
        )
    elif retention_rate > 50:
        console.print(
            "  [yellow]⚠️  High retention rate - consider using 'aggressive' preset[/yellow]"
        )
    else:
        console.print("  [green]✅ Good balance of filtering and retention[/green]")


async def compare_presets(languages: tuple[str, ...]) -> None:
    """Compare all filter presets on the lexicons."""

    console.print("🔍 [bold blue]Filter Preset Comparison[/bold blue]")
    console.print()

    # Convert language names to Language enum
    selected_languages = []
    for lang in languages:
        try:
            # Try direct enum value (e.g., 'en', 'fr')
            selected_languages.append(Language(lang))
        except ValueError:
            console.print(f"❌ Unknown language: {lang}")
            continue

    # Load lexicons
    console.print(f"📚 Loading lexicons: {', '.join(languages)}")

    try:
        lexicon_loader = LexiconLoader(Path("data/search"), force_rebuild=False)
        await lexicon_loader.load_languages(selected_languages)

        total_vocabulary = (
            lexicon_loader.get_all_words() + lexicon_loader.get_all_phrases()
        )
        console.print(f"Loaded {len(total_vocabulary):,} total items")

    except Exception as e:
        console.print(f"❌ Error loading lexicons: {e}")
        return

    # Test all presets
    presets = ['minimal', 'standard', 'aggressive']

    console.print("\n📊 [bold]Preset Comparison[/bold]")

    comparison_table = Table(show_header=True, header_style="bold magenta")
    comparison_table.add_column("Preset")
    comparison_table.add_column("Retained", justify="right")
    comparison_table.add_column("Reduction", justify="right")
    comparison_table.add_column("Avg Length", justify="right")
    comparison_table.add_column("Speed", justify="right")

    for preset in presets:
        word_filter = getattr(FilterPresets, preset)()

        start_time = time.time()
        filtered_words, stats = word_filter.filter_words(total_vocabulary)
        filter_time = time.time() - start_time

        retention_rate = (stats.remaining / stats.total) * 100 if stats.total > 0 else 0
        reduction_rate = 100 - retention_rate

        avg_length = (
            sum(len(w) for w in filtered_words) / len(filtered_words)
            if filtered_words
            else 0
        )
        words_per_sec = stats.total / filter_time if filter_time > 0 else 0

        comparison_table.add_row(
            preset.title(),
            f"{stats.remaining:,}",
            f"{reduction_rate:.1f}%",
            f"{avg_length:.1f}",
            f"{words_per_sec:,.0f}/s",
        )

    console.print(comparison_table)

    console.print("\n💡 [bold]Recommendations[/bold]")
    console.print(
        "• [green]Minimal[/green]: Keep almost everything, only remove invalid words"
    )
    console.print("• [blue]Standard[/blue]: Remove stopwords and slang, good for most uses")
    console.print(
        "• [red]Aggressive[/red]: Heavy filtering + normalization for maximum compression"
    )


if __name__ == "__main__":
    import asyncio

    @click.group()
    def cli() -> None:
        """Corpus filtering test tools."""
        pass

    @cli.command("filter")
    @click.option(
        '--languages',
        '-l',
        multiple=True,
        type=click.Choice([lang.value for lang in Language], case_sensitive=False),
        default=[Language.ENGLISH.value],
        help='Languages to load (can specify multiple)',
    )
    @click.option(
        '--preset',
        '-p',
        type=click.Choice(['minimal', 'standard', 'aggressive']),
        default='standard',
        help='Filter preset to use',
    )
    @click.option(
        '--min-length', type=int, help='Minimum word length (overrides preset)'
    )
    @click.option(
        '--max-length', type=int, help='Maximum word length (overrides preset)'
    )
    @click.option(
        '--show-samples', '-s', is_flag=True, help='Show sample words from results'
    )
    @click.option(
        '--export', '-e', type=click.Path(), help='Export filtered words to file'
    )
    @click.option('--detailed', '-d', is_flag=True, help='Show detailed statistics')
    def filter_cmd(
        languages: tuple[str, ...],
        preset: str,
        min_length: int | None,
        max_length: int | None,
        show_samples: bool,
        export: str | None,
        detailed: bool,
    ) -> None:
        """Test corpus filtering with options."""
        asyncio.run(
            filter_corpus(
                languages,
                preset,
                min_length,
                max_length,
                show_samples,
                export,
                detailed,
            )
        )
        return None

    @cli.command("compare")
    @click.option(
        '--languages',
        '-l',
        multiple=True,
        type=click.Choice([lang.value for lang in Language], case_sensitive=False),
        default=[Language.ENGLISH.value],
        help='Languages to compare',
    )
    def compare_cmd(languages: tuple[str, ...]) -> None:
        """Compare all filter presets."""
        asyncio.run(compare_presets(languages))
        return None

    cli()
