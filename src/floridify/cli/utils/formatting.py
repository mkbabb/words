"""Rich formatting utilities for beautiful CLI output."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.text import Text

from ...models import DictionaryEntry

console = Console()


def format_word_display(
    entry: DictionaryEntry, show_examples: bool = True, show_synonyms: bool = True
) -> Panel:
    """Create a beautiful display panel for a dictionary entry."""
    pass


def format_search_results(results: list[tuple[float, str]], title: str = "Search Results") -> Table:
    """Format search results in a beautiful table."""
    table = Table(title=title, show_header=True, header_style="bold blue")
    table.add_column("Score", style="green", width=6)
    table.add_column("Word", style="bold")
    table.add_column("Pronunciation", style="italic dim")

    for score, word in results:
        # Format score as percentage
        score_text = f"{score:.0%}"
        table.add_row(score_text, word, f"/{word}/")  # Placeholder pronunciation

    return table


def format_similarity_results(
    results: list[tuple[float, str, str]], title: str = "Similar Words"
) -> Table:
    """Format semantic similarity results with explanations."""
    table = Table(title=title, show_header=True, header_style="bold blue")
    table.add_column("Score", style="green", width=6)
    table.add_column("Word", style="bold")
    table.add_column("Relationship", style="cyan")

    for score, word, explanation in results:
        score_text = f"{score:.0%}"
        table.add_row(score_text, word, explanation)

    return table


def format_anki_progress(current: int, total: int, current_word: str) -> Progress:
    """Create a beautiful progress bar for Anki deck creation."""
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("• Current: [bold]{current_word}[/bold]"),
        console=console,
    )

    task = progress.add_task("Creating Anki deck...", total=total, current_word=current_word)
    progress.update(task, completed=current)

    return progress


def format_processing_summary(
    processed: int, successful: int, failed: int, file_path: str
) -> Panel:
    """Format a summary of word list processing."""
    success_rate = (successful / processed * 100) if processed > 0 else 0

    content = Text()
    content.append(f"📄 File: {file_path}\n", style="bold")
    content.append(f"📊 Processed: {processed} words\n")
    content.append(f"✅ Successful: {successful}\n", style="green")
    content.append(f"❌ Failed: {failed}\n", style="red")
    content.append(
        f"📈 Success Rate: {success_rate:.1f}%",
        style="green" if success_rate >= 90 else "yellow" if success_rate >= 75 else "red",
    )

    return Panel(
        content,
        title="[bold green]Processing Complete[/bold green]",
        border_style="green",
        padding=(1, 2),
    )


def format_deck_summary(
    deck_name: str, total_cards: int, card_types: dict[str, int], file_size: str, output_path: str
) -> Panel:
    """Format Anki deck creation summary."""
    content_lines = [
        Text(f"🎴 Deck: {deck_name}", style="bold blue"),
        Text(f"📊 Total Cards: {total_cards}"),
        Text(""),
        Text("Card Types:", style="bold"),
    ]

    for card_type, count in card_types.items():
        content_lines.append(Text(f"  • {card_type.replace('_', ' ').title()}: {count}"))

    content_lines.extend(
        [
            Text(""),
            Text(f"📦 File Size: {file_size}"),
            Text(f"💾 Saved to: {output_path}", style="dim"),
            Text(""),
            Text("🎯 Ready to import into Anki!", style="bold green"),
        ]
    )

    content = Text()
    for i, line in enumerate(content_lines):
        if i > 0:
            content.append("\n")
        if isinstance(line, Text):
            content.append_text(line)
        else:
            content.append(str(line))

    return Panel(
        content,
        title="[bold green]Anki Deck Created[/bold green]",
        border_style="green",
        padding=(1, 2),
    )


def format_error(message: str, details: str | None = None) -> Panel:
    """Format error messages with optional troubleshooting details."""
    content = Text(f"❌ {message}", style="bold red")

    if details:
        content.append("\n\n")
        content.append(details, style="dim")

    return Panel(
        content,
        title="[bold red]Error[/bold red]",
        border_style="red",
        padding=(1, 2),
    )


def format_success(message: str, details: str | None = None) -> Panel:
    """Format success messages with optional details."""
    content = Text(f"✅ {message}", style="bold green")

    if details:
        content.append("\n\n")
        content.append(details, style="dim")

    return Panel(
        content,
        title="[bold green]Success[/bold green]",
        border_style="green",
        padding=(1, 2),
    )


def format_warning(message: str, details: str | None = None) -> Panel:
    """Format warning messages with optional details."""
    content = Text(f"⚠️  {message}", style="bold yellow")

    if details:
        content.append("\n\n")
        content.append(details, style="dim")

    return Panel(
        content,
        title="[bold yellow]Warning[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    )
