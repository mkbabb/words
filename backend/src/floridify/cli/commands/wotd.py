"""WOTD ML training and inference CLI commands."""

import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ...utils.logging import get_logger
from ...wotd import (
    Complexity,
    Era,
    Style,
    SyntheticGenerator,
    TrainingConfig,
    WOTDTrainer,
    get_wotd_storage,
    train_wotd_pipeline,
)

console = Console()
logger = get_logger(__name__)


@click.group()
def wotd():
    """Word of the Day ML system commands."""
    pass


@wotd.command()
@click.option("--words-per-corpus", default=100, help="Number of words per semantic corpus")
@click.option("--encoder-epochs", default=200, help="Semantic encoder training epochs")
@click.option("--lm-epochs", default=10, help="Language model training epochs")
@click.option("--output-dir", type=click.Path(), help="Output directory for trained models")
def train(
    words_per_corpus: int,
    encoder_epochs: int,
    lm_epochs: int,
    output_dir: Optional[str],
):
    """Train the complete WOTD ML pipeline using BGE embeddings."""
    
    async def _train():
        console.print(Panel.fit(
            "🚀 Starting WOTD ML Training Pipeline",
            style="bold blue"
        ))
        
        # Create training configuration
        config = TrainingConfig(
            words_per_corpus=words_per_corpus,
            encoder_epochs=encoder_epochs,
            lm_epochs=lm_epochs,
        )
        
        # Display configuration
        config_table = Table(title="Training Configuration")
        config_table.add_column("Parameter", style="cyan")
        config_table.add_column("Value", style="green")
        
        config_table.add_row("Words per corpus", str(config.words_per_corpus))
        config_table.add_row("Encoder epochs", str(config.encoder_epochs))
        config_table.add_row("LM epochs", str(config.lm_epochs))
        config_table.add_row("Base model", config.base_model)
        config_table.add_row("Embedding model", config.embedding_model)
        config_table.add_row("Output directory", output_dir or "./models/wotd")
        
        console.print(config_table)
        console.print()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Training WOTD pipeline...", total=None)
            
            try:
                results = await train_wotd_pipeline(config, output_dir)
                progress.update(task, description="✅ Training completed!")
                
                # Display results
                results_table = Table(title="Training Results")
                results_table.add_column("Metric", style="cyan")
                results_table.add_column("Value", style="green")
                
                results_table.add_row("Total time", f"{results.duration_seconds:.2f}s")
                results_table.add_row("Corpora generated", str(results.num_corpora))
                results_table.add_row("Total words", str(results.total_words))
                results_table.add_row("Embedding model", config.embedding_model)
                results_table.add_row("Language model", config.base_model)
                
                console.print()
                console.print(results_table)
                
                console.print(Panel.fit(
                    f"🎯 Training completed successfully!\n"
                    f"Models saved to: {output_dir or './models/wotd'}",
                    style="bold green"
                ))
                
            except Exception as e:
                progress.update(task, description="❌ Training failed!")
                console.print(Panel.fit(
                    f"Training failed: {e}",
                    style="bold red"
                ))
                raise click.ClickException(str(e))
    
    asyncio.run(_train())


@wotd.command()
@click.option("--style", type=click.Choice([s.value for s in Style]), required=True, help="Word style")
@click.option("--complexity", type=click.Choice([c.value for c in Complexity]), required=True, help="Word complexity")
@click.option("--era", type=click.Choice([e.value for e in Era]), required=True, help="Historical era")
@click.option("--num-words", default=50, help="Number of words to generate")
@click.option("--theme", help="Optional thematic focus")
@click.option("--output", type=click.Path(), help="Save corpus to file")
def generate(
    style: str,
    complexity: str,
    era: str,
    num_words: int,
    theme: Optional[str],
    output: Optional[str],
):
    """Generate a synthetic training corpus with specific semantic parameters."""
    
    async def _generate():
        console.print(Panel.fit(
            f"🧬 Generating Synthetic Corpus\n"
            f"Style: {style} | Complexity: {complexity} | Era: {era}",
            style="bold blue"
        ))
        
        # Generate corpus
        generator = SyntheticGenerator()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating corpus...", total=None)
            
            try:
                corpus = await generator.generate_corpus(
                    Style(style),
                    Complexity(complexity),
                    Era(era),
                    num_words,
                    theme
                )
                progress.update(task, description="✅ Generation completed!")
                
                # Display sample words
                words_table = Table(title=f"Generated Corpus: {corpus.id}")
                words_table.add_column("Word", style="cyan")
                words_table.add_column("Definition", style="white")
                words_table.add_column("POS", style="green")
                
                # Show first 10 words
                for word_entry in corpus.words[:10]:
                    definition = word_entry.definition
                    if len(definition) > 60:
                        definition = definition[:57] + "..."
                    words_table.add_row(
                        word_entry.word,
                        definition,
                        word_entry.pos
                    )
                
                if len(corpus.words) > 10:
                    words_table.add_row("...", f"... and {len(corpus.words) - 10} more", "...")
                
                console.print()
                console.print(words_table)
                
                # Save if requested
                if output:
                    output_path = Path(output)
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(corpus.model_dump_json(indent=2))
                    
                    console.print(Panel.fit(
                        f"📁 Corpus saved to: {output_path}",
                        style="bold green"
                    ))
                else:
                    # Save to storage automatically
                    storage = await get_wotd_storage()
                    await storage.save_corpus(corpus)
                    
                    console.print(Panel.fit(
                        f"✨ Generated {len(corpus.words)} words successfully!",
                        style="bold green"
                    ))
                
            except Exception as e:
                progress.update(task, description="❌ Generation failed!")
                console.print(Panel.fit(
                    f"Generation failed: {e}",
                    style="bold red"
                ))
                raise click.ClickException(str(e))
    
    asyncio.run(_generate())


@wotd.command()
def status():
    """Check status of WOTD models and training artifacts."""
    
    async def _status():
        console.print(Panel.fit(
            "📊 WOTD System Status",
            style="bold blue"
        ))
        
        try:
            storage = await get_wotd_storage()
            
            # Check storage and cache stats
            cache_stats = await storage.get_cache_stats()
            
            stats_table = Table(title="Storage & Cache Status")
            stats_table.add_column("Component", style="cyan")
            stats_table.add_column("Status", style="white")
            stats_table.add_column("Details", style="dim")
            
            # Cache status
            if cache_stats:
                stats_table.add_row(
                    "Unified Cache",
                    "✅ Connected",
                    f"Architecture: {cache_stats.get('architecture', 'N/A')}"
                )
            else:
                stats_table.add_row(
                    "Unified Cache", 
                    "❌ Not Available",
                    "Cache system not responding"
                )
            
            # Check for corpora
            corpora = await storage.list_corpora(limit=50)
            if corpora:
                total_words = sum(len(c.words) for c in corpora)
                stats_table.add_row(
                    "Training Corpora",
                    f"✅ {len(corpora)} Available",
                    f"{total_words} total words"
                )
            else:
                stats_table.add_row(
                    "Training Corpora",
                    "❌ None Found",
                    "Run 'wotd generate' to create corpora"
                )
            
            # Check for training results
            latest_results = await storage.get_latest_training_results()
            if latest_results:
                stats_table.add_row(
                    "Latest Training",
                    "✅ Available",
                    f"Completed {latest_results.created_at}"
                )
            else:
                stats_table.add_row(
                    "Latest Training",
                    "❌ None Found",
                    "Run 'wotd train' to train models"
                )
            
            # Check semantic IDs
            semantic_ids = await storage.get_semantic_ids()
            if semantic_ids:
                stats_table.add_row(
                    "Semantic IDs",
                    f"✅ {len(semantic_ids)} Available",
                    "Ready for inference"
                )
            else:
                stats_table.add_row(
                    "Semantic IDs",
                    "❌ None Found",
                    "Complete training to generate IDs"
                )
            
            console.print(stats_table)
            
            # Show latest training results if available
            if latest_results:
                console.print()
                
                results_table = Table(title="Latest Training Results")
                results_table.add_column("Metric", style="cyan")
                results_table.add_column("Value", style="green")
                
                results_table.add_row("Duration", f"{latest_results.duration_seconds:.2f}s")
                results_table.add_row("Corpora", str(latest_results.num_corpora))
                results_table.add_row("Total Words", str(latest_results.total_words))
                results_table.add_row("Embedding Model", latest_results.config.embedding_model)
                results_table.add_row("Language Model", latest_results.config.base_model)
                results_table.add_row("Created", str(latest_results.created_at))
                
                console.print(results_table)
                
        except Exception as e:
            console.print(Panel.fit(
                f"Status check failed: {e}",
                style="bold red"
            ))
            raise click.ClickException(str(e))
    
    asyncio.run(_status())


if __name__ == "__main__":
    wotd()