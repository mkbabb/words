#!/usr/bin/env python3
"""Process SOWPODS corpus with lemmatization to create reduced base form corpus."""

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

# Ensure NLTK data is downloaded
for resource in ["wordnet", "averaged_perceptron_tagger", "punkt"]:
    try:
        nltk.data.find(f"tokenizers/{resource}")
    except LookupError:
        nltk.download(resource, quiet=True)

console = Console()


class CorpusProcessor:
    """Process word corpus with lemmatization and inflection mapping."""
    
    def __init__(self, corpus_path: Path, output_dir: Path) -> None:
        self.corpus_path = corpus_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.lemmatizer = WordNetLemmatizer()
        self.base_forms: Set[str] = set()
        self.inflection_map: Dict[str, List[str]] = defaultdict(list)
        self.stats: Dict[str, Any] = {
            "total_words": 0,
            "unique_base_forms": 0,
            "reduction_percentage": 0.0,
            "inflection_types": defaultdict(int),
        }
    
    def get_wordnet_pos(self, word: str) -> str:
        """Get WordNet POS tag for better lemmatization."""
        # Simple heuristic - can be improved with actual POS tagging
        if word.endswith("ing") or word.endswith("ed"):
            return wordnet.VERB
        elif word.endswith("ly"):
            return wordnet.ADV
        elif word.endswith("er") or word.endswith("est"):
            return wordnet.ADJ
        else:
            return wordnet.NOUN
    
    def lemmatize_word(self, word: str) -> Tuple[str, str]:
        """Lemmatize a word and determine inflection type."""
        word_lower = word.lower()
        
        # Try each POS tag to find the best lemma
        pos_tags = [wordnet.NOUN, wordnet.VERB, wordnet.ADJ, wordnet.ADV]
        best_lemma = word_lower
        inflection_type = "base"
        
        for pos in pos_tags:
            lemma = self.lemmatizer.lemmatize(word_lower, pos=pos)
            if lemma != word_lower and len(lemma) < len(best_lemma):
                best_lemma = lemma
                
                # Determine inflection type
                if pos == wordnet.VERB:
                    if word_lower.endswith("ed"):
                        inflection_type = "past"
                    elif word_lower.endswith("ing"):
                        inflection_type = "present_participle"
                    else:
                        inflection_type = "verb_form"
                elif pos == wordnet.NOUN and word_lower.endswith("s"):
                    inflection_type = "plural"
                elif pos == wordnet.ADJ:
                    if word_lower.endswith("er"):
                        inflection_type = "comparative"
                    elif word_lower.endswith("est"):
                        inflection_type = "superlative"
                    else:
                        inflection_type = "adjective_form"
                elif pos == wordnet.ADV:
                    inflection_type = "adverb_form"
        
        return best_lemma, inflection_type
    
    async def process_corpus(self) -> None:
        """Process the entire corpus with progress tracking."""
        # Load all words
        console.print("[cyan]Loading corpus...[/cyan]")
        with open(self.corpus_path, "r") as f:
            all_words = [line.strip() for line in f if line.strip()]
        
        self.stats["total_words"] = len(all_words)
        console.print(f"[green]Loaded {len(all_words):,} words[/green]")
        
        # Process with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing words", total=len(all_words))
            
            for word in all_words:
                # Lemmatize
                base_form, inflection_type = self.lemmatize_word(word)
                
                # Track statistics
                self.base_forms.add(base_form)
                if word.lower() != base_form:
                    self.inflection_map[base_form].append(word)
                    self.stats["inflection_types"][inflection_type] += 1
                
                progress.update(task, advance=1)
        
        # Calculate final statistics
        self.stats["unique_base_forms"] = len(self.base_forms)
        self.stats["reduction_percentage"] = (
            (1 - len(self.base_forms) / len(all_words)) * 100
        )
    
    def save_results(self) -> None:
        """Save processed corpus and mappings."""
        # Save base forms
        base_forms_path = self.output_dir / "base_forms.txt"
        with open(base_forms_path, "w") as f:
            for word in sorted(self.base_forms):
                f.write(f"{word}\n")
        
        # Save inflection mappings
        mappings_path = self.output_dir / "inflection_mappings.json"
        with open(mappings_path, "w") as f:
            json.dump(dict(self.inflection_map), f, indent=2, sort_keys=True)
        
        # Save statistics
        stats_path = self.output_dir / "processing_stats.json"
        with open(stats_path, "w") as f:
            stats_dict = dict(self.stats)
            stats_dict["inflection_types"] = dict(self.stats["inflection_types"])
            json.dump(stats_dict, f, indent=2)
        
        console.print(f"\n[green]Results saved to {self.output_dir}[/green]")
    
    def display_statistics(self) -> None:
        """Display processing statistics."""
        # Create statistics table
        table = Table(title="Corpus Processing Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Total Words", f"{self.stats['total_words']:,}")
        table.add_row("Unique Base Forms", f"{self.stats['unique_base_forms']:,}")
        table.add_row(
            "Reduction", f"{self.stats['reduction_percentage']:.1f}%"
        )
        
        console.print("\n", table)
        
        # Inflection types breakdown
        if self.stats["inflection_types"]:
            inflection_table = Table(
                title="Inflection Types", show_header=True
            )
            inflection_table.add_column("Type", style="cyan")
            inflection_table.add_column("Count", style="green", justify="right")
            inflection_table.add_column("Percentage", style="yellow", justify="right")
            
            total_inflections = sum(self.stats["inflection_types"].values())
            for inflection_type, count in sorted(
                self.stats["inflection_types"].items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                percentage = (count / total_inflections) * 100
                inflection_table.add_row(
                    inflection_type,
                    f"{count:,}",
                    f"{percentage:.1f}%",
                )
            
            console.print("\n", inflection_table)


async def main() -> None:
    """Main entry point."""
    # Paths
    corpus_path = Path("data/search/lexicons/sowpods_scrabble_words.txt")
    output_dir = Path("data/processed_corpus")
    
    # Check if corpus exists
    if not corpus_path.exists():
        console.print(f"[red]Error: Corpus not found at {corpus_path}[/red]")
        return
    
    # Process corpus
    processor = CorpusProcessor(corpus_path, output_dir)
    
    console.print("[bold cyan]Starting corpus processing with lemmatization...[/bold cyan]")
    await processor.process_corpus()
    
    # Display statistics
    processor.display_statistics()
    
    # Save results
    processor.save_results()
    
    console.print("\n[bold green]Corpus processing complete![/bold green]")
    console.print(
        f"[yellow]Base forms:[/yellow] {output_dir}/base_forms.txt"
    )
    console.print(
        f"[yellow]Inflection mappings:[/yellow] {output_dir}/inflection_mappings.json"
    )


if __name__ == "__main__":
    asyncio.run(main())