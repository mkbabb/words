"""WOTD ML - Training and inference.

Commands for training and using the WOTD ML system with:
    - GTE-Qwen2 embeddings (4096D with Matryoshka)
    - Qwen-2.5/Phi-4 language models
    - FSQ/HVQ semantic encoders
    - Binary quantization support
"""

from __future__ import annotations

import asyncio
import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ...utils.logging import get_logger
from ...wotd.constants import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LANGUAGE_MODEL,
    E5_MULTILINGUAL,
    GTE_QWEN2_1B,
    GTE_QWEN2_7B,
    PHI_4,
    QWEN_25_3B,
    QWEN_25_7B,
)
from ...wotd.core import TrainingConfig
from ...wotd.generator import SyntheticGenerator
from ...wotd.trainer import train_from_literature, train_wotd_pipeline

console = Console()
logger = get_logger(__name__)


@click.group()
def wotd_ml():
    """WOTD ML System - Word generation with semantic learning."""


@wotd_ml.command()
@click.option(
    "--embedding-model",
    type=click.Choice(["gte-qwen2-7b", "gte-qwen2-1b", "e5-multilingual", "default"]),
    default="default",
    help="Embedding model to use",
)
@click.option(
    "--language-model",
    type=click.Choice(["qwen-2.5-7b", "qwen-2.5-3b", "phi-4", "default"]),
    default="default",
    help="Language model for generation",
)
@click.option(
    "--encoder",
    type=click.Choice(["fsq", "hvq"]),
    default="fsq",
    help="Semantic encoder type",
)
@click.option("--words-per-corpus", default=100, help="Words per semantic corpus")
@click.option("--num-corpora", default=12, help="Number of corpora to generate")
@click.option("--output-dir", default="./models/wotd", help="Output directory for models")
@click.option("--use-cache/--no-cache", default=True, help="Use cached corpora if available")
def train(
    embedding_model: str,
    language_model: str,
    encoder: str,
    words_per_corpus: int,
    num_corpora: int,
    output_dir: str,
    use_cache: bool,
):
    """Train WOTD system."""
    # Map model choices
    embedding_map = {
        "gte-qwen2-7b": GTE_QWEN2_7B,
        "gte-qwen2-1b": GTE_QWEN2_1B,
        "e5-multilingual": E5_MULTILINGUAL,
        "default": DEFAULT_EMBEDDING_MODEL,
    }

    language_map = {
        "qwen-2.5-7b": QWEN_25_7B,
        "qwen-2.5-3b": QWEN_25_3B,
        "phi-4": PHI_4,
        "default": DEFAULT_LANGUAGE_MODEL,
    }

    # Create config
    config = TrainingConfig(
        embedding_model=embedding_map[embedding_model],
        base_model=language_map[language_model],
        words_per_corpus=words_per_corpus,
        num_corpora=num_corpora,
    )

    # Display configuration
    console.print(
        Panel.fit(
            f"[bold cyan]WOTD Training Configuration[/bold cyan]\n\n"
            f"[yellow]Embedding:[/yellow] {config.embedding_model}\n"
            f"[yellow]Language:[/yellow] {config.base_model}\n"
            f"[yellow]Encoder:[/yellow] {encoder.upper()}\n"
            f"[yellow]Corpora:[/yellow] {num_corpora} × {words_per_corpus} words\n"
            f"[yellow]Output:[/yellow] {output_dir}",
            title="Training",
        ),
    )

    async def run_training():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Training WOTD pipeline...", total=None)

            # Update config for encoder type
            if encoder == "fsq":
                pass

            results = await train_wotd_pipeline(config, output_dir)

            progress.update(task, completed=True)

        # Display results
        table = Table(title="Training Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Duration", f"{results.duration_seconds:.2f}s")
        table.add_row("Corpora", str(results.num_corpora))
        table.add_row("Total Words", str(results.total_words))
        table.add_row("Semantic IDs", str(len(results.semantic_ids)))

        console.print(table)
        console.print("[bold green]✅ Training completed successfully![/bold green]")

    asyncio.run(run_training())


@wotd_ml.command()
@click.option("--words", default=100, help="Words per corpus")
@click.option("--save/--no-save", default=True, help="Save to storage")
def generate(words: int, save: bool):
    """Generate synthetic training corpora."""
    console.print(
        Panel.fit(
            f"[bold cyan]Generating Synthetic Corpora[/bold cyan]\n\n"
            f"[yellow]Words per corpus:[/yellow] {words}\n"
            f"[yellow]Save to storage:[/yellow] {'Yes' if save else 'No'}",
            title="Generation",
        ),
    )

    async def run_generation():
        generator = SyntheticGenerator()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating corpora...", total=None)

            corpora = await generator.generate_complete_training_set(
                words_per_corpus=words,
                save=save,
            )

            progress.update(task, completed=True)

        # Display results
        table = Table(title="Generated Corpora")
        table.add_column("ID", style="cyan")
        table.add_column("Style", style="yellow")
        table.add_column("Complexity", style="yellow")
        table.add_column("Era", style="yellow")
        table.add_column("Words", style="green")

        for corpus_id, corpus in list(corpora.items())[:10]:  # Show first 10
            table.add_row(
                corpus_id,
                corpus.style.value,
                corpus.complexity.value,
                corpus.era.value,
                str(len(corpus.words)),
            )

        console.print(table)
        console.print(f"[bold green]✅ Generated {len(corpora)} corpora![/bold green]")

    asyncio.run(run_generation())


@wotd_ml.command()
@click.option(
    "--corpus-id",
    default="classical_beautiful_shakespearean",
    help="Corpus to benchmark",
)
def benchmark(corpus_id: str):
    """Benchmark embedding and encoding performance."""
    console.print(
        Panel.fit(
            f"[bold cyan]Performance Benchmark[/bold cyan]\n\n[yellow]Corpus:[/yellow] {corpus_id}",
            title="Benchmark",
        ),
    )

    async def run_benchmark():

        from ...wotd.embeddings import EmbeddingMode, get_embedder
        from ...wotd.encoders import get_semantic_encoder
        from ...wotd.storage import get_wotd_storage

        storage = await get_wotd_storage()
        corpus = await storage.get_corpus(corpus_id)

        if not corpus:
            console.print(f"[red]Corpus {corpus_id} not found![/red]")
            return

        words = [w.word for w in corpus.words]

        # Test different configurations
        results = []

        # Test embedding models
        for model, name in [
            (GTE_QWEN2_1B, "GTE-Qwen2-1.5B"),
            (E5_MULTILINGUAL, "E5-Multilingual"),
            (GTE_QWEN2_7B, "GTE-Qwen2-7B"),
        ]:
            embedder = get_embedder(model_name=model)

            # Full embeddings
            start = time.time()
            full_emb = embedder.embed(words, mode=EmbeddingMode.FULL)
            full_time = time.time() - start

            # Binary embeddings
            start = time.time()
            embedder.embed(words, mode=EmbeddingMode.BINARY)
            binary_time = time.time() - start

            results.append(
                {
                    "model": name,
                    "full_time": full_time,
                    "binary_time": binary_time,
                    "full_dim": full_emb.shape[-1],
                    "speedup": full_time / binary_time,
                },
            )

        # Display results
        table = Table(title="Embedding Performance")
        table.add_column("Model", style="cyan")
        table.add_column("Full (ms)", style="yellow")
        table.add_column("Binary (ms)", style="yellow")
        table.add_column("Dimension", style="green")
        table.add_column("Speedup", style="magenta")

        for r in results:
            table.add_row(
                r["model"],
                f"{r['full_time'] * 1000:.1f}",
                f"{r['binary_time'] * 1000:.1f}",
                str(r["full_dim"]),
                f"{r['speedup']:.2f}x",
            )

        console.print(table)

        # Test encoders
        encoder_results = []

        for encoder_type in ["fsq", "hvq"]:
            encoder = get_semantic_encoder(use_fsq=(encoder_type == "fsq"))

            # Use first embedding for test
            test_emb = full_emb[0:1]  # Single embedding

            start = time.time()
            semantic_id = encoder.encode(test_emb)
            encode_time = time.time() - start

            encoder_results.append(
                {"type": encoder_type.upper(), "time": encode_time, "semantic_id": semantic_id},
            )

        # Display encoder results
        table2 = Table(title="Encoder Performance")
        table2.add_column("Type", style="cyan")
        table2.add_column("Time (ms)", style="yellow")
        table2.add_column("Semantic ID", style="green")

        for r in encoder_results:
            table2.add_row(r["type"], f"{r['time'] * 1000:.2f}", str(r["semantic_id"]))

        console.print(table2)

    asyncio.run(run_benchmark())


@wotd_ml.command()
@click.option(
    "--authors",
    multiple=True,
    default=["Shakespeare", "Woolf"],
    help="Authors to train on (can specify multiple)",
)
@click.option(
    "--lightweight/--full",
    default=False,
    help="Use lightweight model for local training",
)
@click.option(
    "--augment/--no-augment",
    default=True,
    help="Augment with AI-generated variations",
)
@click.option(
    "--output-dir",
    default=None,
    help="Output directory for models",
)
@click.option(
    "--max-words",
    default=200,
    help="Maximum words per author",
)
def literature(
    authors: tuple[str, ...],
    lightweight: bool,
    augment: bool,
    output_dir: str | None,
    max_words: int,
):
    """Train WOTD from literary texts with AI augmentation.

    This command extracts vocabulary from real literature (Shakespeare, Woolf, etc.),
    augments it with AI-generated synthetic variations, and trains the semantic
    encoding pipeline using these real-world examples.

    Examples:
        # Train on default authors (Shakespeare and Woolf)
        floridify wotd-ml literature

        # Train on specific author with lightweight model
        floridify wotd-ml literature --authors Shakespeare --lightweight

        # Train without AI augmentation
        floridify wotd-ml literature --no-augment

    """
    authors_list = list(authors) if authors else ["Shakespeare", "Woolf"]

    console.print(
        Panel.fit(
            f"[bold cyan]Literature-Based WOTD Training[/bold cyan]\n\n"
            f"[yellow]Authors:[/yellow] {', '.join(authors_list)}\n"
            f"[yellow]Model:[/yellow] {'Lightweight (MiniLM)' if lightweight else 'Full (GTE-Qwen2)'}\n"
            f"[yellow]AI Augmentation:[/yellow] {'Enabled' if augment else 'Disabled'}\n"
            f"[yellow]Max Words/Author:[/yellow] {max_words}\n"
            f"[yellow]Output:[/yellow] {output_dir or 'auto-generated'}",
            title="Literature Training",
        ),
    )

    async def run_literature_training():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Add main task
            task = progress.add_task(
                f"Training on {', '.join(authors_list)}...",
                total=None,
            )

            # Run training
            results = await train_from_literature(
                authors=authors_list,
                config=None,  # Use defaults
                output_dir=output_dir,
                use_lightweight_model=lightweight,
                augment_with_ai=augment,
            )

            progress.update(task, completed=True)

        # Display results
        table = Table(title="Literature Training Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Duration", f"{results.duration_seconds:.2f}s")
        table.add_row("Authors", ", ".join(authors_list))
        table.add_row("Corpora", str(results.num_corpora))
        table.add_row("Total Words", str(results.total_words))
        table.add_row("Semantic IDs", str(len(results.semantic_ids)))

        # Show options used
        table.add_row("Model Type", "Lightweight" if lightweight else "Full")
        table.add_row("AI Augmented", "Yes" if augment else "No")

        console.print(table)

        # Show sample semantic IDs
        if results.semantic_ids:
            id_table = Table(title="Sample Semantic IDs")
            id_table.add_column("Corpus", style="cyan")
            id_table.add_column("Semantic ID", style="yellow")
            id_table.add_column("Interpretation", style="green")

            # Interpretation maps
            style_map = [
                "formal",
                "casual",
                "poetic",
                "dramatic",
                "archaic",
                "regional",
                "technical",
                "experimental",
            ]
            complexity_map = [
                "simple",
                "basic",
                "intermediate",
                "advanced",
                "erudite",
                "ornate",
                "dense",
                "esoteric",
            ]
            era_map = [
                "ancient",
                "medieval",
                "renaissance",
                "early_modern",
                "enlightenment",
                "romantic",
                "modernist",
                "contemporary",
            ]

            for corpus_id, sem_id in list(results.semantic_ids.items())[:5]:
                interpretation = (
                    f"{style_map[sem_id[0]] if sem_id[0] < len(style_map) else 'unknown'}, "
                    f"{complexity_map[sem_id[1]] if sem_id[1] < len(complexity_map) else 'unknown'}, "
                    f"{era_map[sem_id[2]] if sem_id[2] < len(era_map) else 'unknown'}"
                )
                id_table.add_row(
                    corpus_id[:30],
                    str(sem_id),
                    interpretation,
                )

            console.print(id_table)

        console.print("[bold green]✅ Literature training completed successfully![/bold green]")

        if results.model_paths:
            console.print(
                f"\n[yellow]Models saved to:[/yellow] {results.model_paths.get('models_directory')}",
            )

    asyncio.run(run_literature_training())


@wotd_ml.command()
def info():
    """Display system information and configuration."""
    from ...wotd.constants import (
        DEFAULT_EMBEDDING_MODEL,
        DEFAULT_LANGUAGE_MODEL,
        MATRYOSHKA_TRAINING,
        USE_BINARY_EMBEDDINGS,
        USE_FSQ,
        USE_INT8_EMBEDDINGS,
    )

    # Create info table
    table = Table(title="WOTD System Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Description", style="yellow")

    table.add_row("Embedding Model", DEFAULT_EMBEDDING_MODEL, "Default embedding model")
    table.add_row("Language Model", DEFAULT_LANGUAGE_MODEL, "Default generation model")
    table.add_row("Encoder Type", "FSQ" if USE_FSQ else "HVQ", "Semantic encoding method")
    table.add_row("Binary Embeddings", str(USE_BINARY_EMBEDDINGS), "Use binary quantization")
    table.add_row("INT8 Embeddings", str(USE_INT8_EMBEDDINGS), "Use int8 quantization")
    table.add_row("Matryoshka Training", str(MATRYOSHKA_TRAINING), "Hierarchical embeddings")

    console.print(table)

    # Model capabilities
    capabilities = Table(title="Model Capabilities")
    capabilities.add_column("Model", style="cyan")
    capabilities.add_column("Type", style="yellow")
    capabilities.add_column("Dimensions", style="green")
    capabilities.add_column("Features", style="magenta")

    capabilities.add_row("GTE-Qwen2-7B", "Embedding", "4096", "SOTA, Matryoshka, Multilingual")
    capabilities.add_row(
        "GTE-Qwen2-1.5B",
        "Embedding",
        "4096",
        "Efficient, Matryoshka, Multilingual",
    )
    capabilities.add_row("E5-Multilingual", "Embedding", "1024", "Fast, 100+ languages")
    capabilities.add_row(
        "Qwen-2.5-7B",
        "Language",
        "32K context",
        "SOTA generation, instruction-tuned",
    )
    capabilities.add_row("Phi-4", "Language", "128K context", "Reasoning-focused, efficient")

    console.print(capabilities)


if __name__ == "__main__":
    wotd_ml()
