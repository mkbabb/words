#!/usr/bin/env python3
"""Analyze word frequencies from multiple sources to prioritize corpus processing."""

import asyncio
import json
from collections import defaultdict, Counter
from pathlib import Path
from typing import Any
import gzip
import urllib.request
from urllib.error import URLError

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

console = Console()


class FrequencyAnalyzer:
    """Analyze word frequencies from multiple sources."""
    
    def __init__(self, data_dir: Path, output_dir: Path) -> None:
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Frequency sources and their weights
        self.sources = {
            "google_10k": {
                "url": "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt",
                "weight": 2.0,
                "description": "Google 10K most common words",
            },
            "coca_5000": {
                "url": "https://www.wordfrequency.info/samples/lemmas_60k.txt",
                "weight": 3.0,
                "description": "COCA 5K most frequent words",
                "skip_lines": 1,  # Skip header
            },
            "wikipedia_10k": {
                "url": "https://raw.githubusercontent.com/IlyaSemenov/wikipedia-word-frequency/master/results/enwiki-20210820-words-frequency.txt",
                "weight": 1.5,
                "description": "Wikipedia word frequencies",
                "limit": 10000,
            },
            "common_words": {
                "url": "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
                "weight": 0.5,
                "description": "Common English words list",
                "limit": 20000,
            },
        }
        
        self.frequencies: dict[str, dict[str, float]] = {}
        self.combined_frequencies: dict[str, float] = {}
    
    async def download_source(self, name: str, config: dict[str, Any]) -> Path | None:
        """Download a frequency source if not cached."""
        cache_path = self.data_dir / f"{name}.txt"
        
        if cache_path.exists():
            console.print(f"[green]Using cached {name}[/green]")
            return cache_path
        
        console.print(f"[cyan]Downloading {name}...[/cyan]")
        
        try:
            # Download file
            response = urllib.request.urlopen(config["url"])
            content = response.read()
            
            # Handle gzipped content
            if config["url"].endswith(".gz"):
                content = gzip.decompress(content)
            
            # Save to cache
            with open(cache_path, "wb") as f:
                f.write(content)
            
            console.print(f"[green]Downloaded {name}[/green]")
            return cache_path
            
        except URLError as e:
            console.print(f"[red]Failed to download {name}: {e}[/red]")
            return None
    
    def parse_frequency_file(
        self, 
        path: Path, 
        config: dict[str, Any]
    ) -> dict[str, float]:
        """Parse a frequency file and return word frequencies."""
        frequencies: dict[str, float] = {}
        
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
            # Skip header lines if specified
            skip_lines = config.get("skip_lines", 0)
            lines = lines[skip_lines:]
            
            # Apply limit if specified
            limit = config.get("limit", len(lines))
            lines = lines[:limit]
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Parse different formats
                parts = line.split("\t")
                if len(parts) == 1:
                    # Simple word list
                    word = parts[0].lower()
                    # Use rank-based frequency (higher rank = lower frequency)
                    frequencies[word] = 1.0 / (i + 1)
                elif len(parts) >= 2:
                    # Word frequency format
                    word = parts[0].lower()
                    try:
                        freq = float(parts[1])
                        frequencies[word] = freq
                    except ValueError:
                        # Use rank if frequency not parsable
                        frequencies[word] = 1.0 / (i + 1)
        
        return frequencies
    
    def process_literary_corpus(self, corpus_dir: Path) -> dict[str, float]:
        """Process literary texts from a directory."""
        frequencies: Counter[str] = Counter()
        
        # Process all text files in corpus directory
        text_files = list(corpus_dir.glob("**/*.txt")) + list(corpus_dir.glob("**/*.json"))
        
        if not text_files:
            console.print(f"[yellow]No literary texts found in {corpus_dir}[/yellow]")
            return {}
        
        console.print(f"[cyan]Processing {len(text_files)} literary texts...[/cyan]")
        
        for text_file in text_files:
            try:
                with open(text_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    
                # Simple tokenization
                words = content.split()
                for word in words:
                    # Clean punctuation
                    word = word.strip(".,!?;:\"'()[]{}""''")
                    if word and word.isalpha() and len(word) > 2:
                        frequencies[word] += 1
                        
            except Exception as e:
                console.print(f"[red]Error processing {text_file}: {e}[/red]")
        
        # Convert counts to frequencies
        total = sum(frequencies.values())
        return {word: count / total for word, count in frequencies.items()}
    
    async def analyze(
        self, 
        custom_weights: dict[str, float] | None = None
    ) -> tuple[dict[str, float], dict[str, Any]]:
        """Analyze frequencies from all sources."""
        weights = custom_weights or {name: config["weight"] for name, config in self.sources.items()}
        
        # Download and process sources
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Download sources
            download_task = progress.add_task("Downloading sources", total=len(self.sources))
            
            for name, config in self.sources.items():
                path = await self.download_source(name, config)
                if path:
                    self.frequencies[name] = self.parse_frequency_file(path, config)
                progress.update(download_task, advance=1)
            
            # Process literary corpus if available
            corpus_dir = self.data_dir / "corpora"
            if corpus_dir.exists():
                literary_task = progress.add_task("Processing literary corpus", total=1)
                literary_freq = self.process_literary_corpus(corpus_dir)
                if literary_freq:
                    self.frequencies["literary"] = literary_freq
                    weights["literary"] = weights.get("literary", 1.0)
                progress.update(literary_task, advance=1)
        
        # Combine frequencies with weights
        console.print("[cyan]Combining frequencies with weights...[/cyan]")
        combined: defaultdict[str, float] = defaultdict(float)
        
        for source, freq_dict in self.frequencies.items():
            weight = weights.get(source, 1.0)
            for word, freq in freq_dict.items():
                combined[word] += freq * weight
        
        # Normalize
        max_freq = max(combined.values()) if combined else 1.0
        self.combined_frequencies = {
            word: freq / max_freq 
            for word, freq in combined.items()
        }
        
        # Calculate statistics
        stats = {
            "total_unique_words": len(self.combined_frequencies),
            "sources_used": list(self.frequencies.keys()),
            "weights": weights,
        }
        
        return self.combined_frequencies, stats
    
    def generate_word_lists(
        self, 
        frequencies: dict[str, float], 
        sizes: list[int] = [1000, 5000, 10000, 20000, 50000]
    ) -> dict[int, list[str]]:
        """Generate word lists of various sizes."""
        # Sort by frequency
        sorted_words = sorted(
            frequencies.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        word_lists = {}
        for size in sizes:
            word_lists[size] = [word for word, _ in sorted_words[:size]]
        
        return word_lists
    
    def save_results(
        self, 
        frequencies: dict[str, float], 
        word_lists: dict[int, list[str]], 
        stats: dict[str, Any]
    ) -> None:
        """Save analysis results."""
        # Save frequency lists
        for size, words in word_lists.items():
            output_path = self.output_dir / f"frequency_list_{size}.txt"
            with open(output_path, "w") as f:
                for word in words:
                    f.write(f"{word}\n")
            console.print(f"[green]Saved {size}-word list to {output_path}[/green]")
        
        # Save detailed frequency data
        detailed_path = self.output_dir / "frequency_detailed.json"
        detailed_data = {
            "frequencies": dict(sorted(
                frequencies.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:50000]),  # Top 50k
            "stats": stats,
        }
        
        with open(detailed_path, "w") as f:
            json.dump(detailed_data, f, indent=2)
        
        console.print(f"[green]Saved detailed data to {detailed_path}[/green]")
    
    def display_statistics(
        self, 
        frequencies: dict[str, float], 
        word_lists: dict[int, list[str]]
    ) -> None:
        """Display analysis statistics."""
        table = Table(title="Frequency Analysis Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Total Unique Words", f"{len(frequencies):,}")
        table.add_row("Sources Analyzed", f"{len(self.frequencies)}")
        
        for size in sorted(word_lists.keys()):
            table.add_row(f"Top {size:,} Words", f"{len(word_lists[size]):,}")
        
        console.print("\n", table)
        
        # Show top 20 words
        top_words = list(frequencies.keys())[:20]
        console.print("\n[bold]Top 20 Most Frequent Words:[/bold]")
        for i, word in enumerate(top_words, 1):
            console.print(f"{i:2d}. {word} ({frequencies[word]:.4f})")
    
    def integrate_with_corpus_processor(
        self, 
        corpus_processor_output: Path
    ) -> dict[str, Any]:
        """Integrate with corpus processor results."""
        # Load lemma mappings
        mappings_path = corpus_processor_output / "inflection_mappings.json"
        base_forms_path = corpus_processor_output / "base_forms.txt"
        
        if not mappings_path.exists() or not base_forms_path.exists():
            console.print("[red]Corpus processor output not found[/red]")
            return {}
        
        with open(mappings_path, "r") as f:
            inflection_map = json.load(f)
        
        with open(base_forms_path, "r") as f:
            base_forms = set(line.strip() for line in f)
        
        # Create frequency-ordered base form list
        ordered_base_forms = []
        seen_bases: set[str] = set()
        
        for word in sorted(self.combined_frequencies.keys(), 
                          key=lambda x: self.combined_frequencies[x], 
                          reverse=True):
            # Check if it's a base form
            if word in base_forms and word not in seen_bases:
                ordered_base_forms.append(word)
                seen_bases.add(word)
            # Check if it maps to a base form
            else:
                for base, inflections in inflection_map.items():
                    if word in inflections and base not in seen_bases:
                        ordered_base_forms.append(base)
                        seen_bases.add(base)
                        break
        
        # Save ordered base forms
        output_path = self.output_dir / "frequency_ordered_base_forms.txt"
        with open(output_path, "w") as f:
            for word in ordered_base_forms:
                f.write(f"{word}\n")
        
        console.print(f"[green]Saved {len(ordered_base_forms)} frequency-ordered base forms[/green]")
        
        return {
            "total_base_forms": len(ordered_base_forms),
            "coverage": len(seen_bases) / len(base_forms) * 100,
        }


async def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze word frequencies for corpus prioritization"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/frequency_sources"),
        help="Directory for frequency data (default: data/frequency_sources)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/frequency_lists"),
        help="Output directory (default: data/frequency_lists)",
    )
    parser.add_argument(
        "--weights",
        type=json.loads,
        help="Custom source weights as JSON (e.g., '{\"google_10k\": 3.0}')",
    )
    parser.add_argument(
        "--integrate",
        type=Path,
        help="Integrate with corpus processor output directory",
    )
    
    args = parser.parse_args()
    
    analyzer = FrequencyAnalyzer(args.data_dir, args.output_dir)
    
    console.print("[bold cyan]Starting frequency analysis...[/bold cyan]")
    
    # Analyze frequencies
    frequencies, stats = await analyzer.analyze(args.weights)
    
    # Generate word lists
    word_lists = analyzer.generate_word_lists(frequencies)
    
    # Save results
    analyzer.save_results(frequencies, word_lists, stats)
    
    # Display statistics
    analyzer.display_statistics(frequencies, word_lists)
    
    # Integrate with corpus processor if requested
    if args.integrate:
        console.print("\n[cyan]Integrating with corpus processor...[/cyan]")
        integration_stats = analyzer.integrate_with_corpus_processor(args.integrate)
        if integration_stats:
            console.print(f"[green]Coverage: {integration_stats['coverage']:.1f}%[/green]")
    
    console.print("\n[bold green]Frequency analysis complete![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())