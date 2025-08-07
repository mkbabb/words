"""Rich formatting utilities for beautiful CLI output."""

from __future__ import annotations

import re
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table
from rich.text import Text

from ...models import Definition, SynthesizedDictionaryEntry
from ...models.definition import DictionaryProvider, Language
from ...search import SearchResult
from ...search.constants import SearchMethod


# CLI-specific text formatting functions
def clean_markdown(text: str) -> str:
    """
    Remove markdown formatting from text.

    Used for CLI display purposes.

    Args:
        text: Text with markdown formatting

    Returns:
        Plain text without formatting
    """
    if not text:
        return ""

    # Remove bold
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

    # Remove italic
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # Remove code
    text = re.sub(r"`(.*?)`", r"\1", text)

    # Remove links
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

    # Remove headers
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

    # Remove horizontal rules
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)

    # Clean up extra whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


def ensure_sentence_case(text: str) -> str:
    """
    Ensure text has proper sentence case.

    Used for CLI display purposes.

    Args:
        text: Text to format

    Returns:
        Text with proper sentence case
    """
    if not text:
        return ""

    text = text.strip()

    # Capitalize first letter
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    # Add period if missing
    if text and text[-1] not in ".!?":
        text = text + "."

    return text


def bold_word_in_text(text: str, word: str) -> list[tuple[str, str]]:
    """
    Return formatted parts for displaying text with a bold word.

    Used for highlighting search terms in CLI examples.

    Args:
        text: The full text
        word: The word to make bold

    Returns:
        List of (text_part, style) tuples for Rich Text formatting
    """
    if not text or not word:
        return [(text, "")]

    # Case-insensitive search
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    parts = []
    last_end = 0

    for match in pattern.finditer(text):
        # Add text before the match
        if match.start() > last_end:
            parts.append((text[last_end : match.start()], ""))
        # Add the matched word with bold style
        parts.append((text[match.start() : match.end()], "bold"))
        last_end = match.end()

    # Add any remaining text
    if last_end < len(text):
        parts.append((text[last_end:], ""))

    return parts if parts else [(text, "")]


# Unicode superscript mapping for meaning counters
SUPERSCRIPT_MAP = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
}


def format_meaning_cluster_name(meaning_id: str) -> str:
    """Convert snake_case meaning cluster ID to Title Case display format.

    Examples:
        bank_financial -> Bank Financial
        simple_uncomplicated -> Simple Uncomplicated
        word_general -> Word General
    """
    # Remove word prefix and convert to title case
    parts = meaning_id.split("_")
    if len(parts) > 1:
        # Skip the word part and format the meaning part
        meaning_parts = parts[1:]  # Skip word prefix like 'bank_'
        return " ".join(word.lower() for word in meaning_parts)
    else:
        # Fallback for single words
        return meaning_id.lower()


console = Console()


def format_word_display(
    entry: SynthesizedDictionaryEntry, show_examples: bool = True, show_synonyms: bool = True
) -> Panel:
    """Create a beautiful display panel for a dictionary entry."""
    # TODO: Implement word display formatting
    return Panel(Text("Not implemented"), title="Word Display")


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
        style=("green" if success_rate >= 90 else "yellow" if success_rate >= 75 else "red"),
    )

    return Panel(
        content,
        title="[bold green]Processing Complete[/bold green]",
        border_style="green",
        padding=(1, 2),
    )


def format_deck_summary(
    deck_name: str,
    total_cards: int,
    card_types: dict[str, int],
    file_size: str,
    output_path: str,
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


def format_search_results_table(query: str, results: list[SearchResult]) -> Table:
    """Format search results in a styled table."""
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

        # Determine type - all entries are now vocabulary items
        type_text = "Entry"

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

    return table


def format_statistics_table(title: str, stats: dict[str, Any]) -> Table:
    """Format general statistics in a table."""
    table = Table(title=title)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="magenta")

    for metric, value in stats.items():
        # Format large numbers with commas
        if isinstance(value, int) and value > 1000:
            value_str = f"{value:,}"
        else:
            value_str = str(value)
        table.add_row(metric.replace("_", " ").title(), value_str)

    return table


def format_performance_table(stats: dict[str, dict[str, Any]]) -> Table | None:
    """Format performance statistics table."""
    if not any(data["count"] > 0 for data in stats.values()):
        return None

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

    return table


def _create_superscript(number: int) -> str:
    """Convert number to unicode superscript."""
    return "".join(SUPERSCRIPT_MAP.get(d, d) for d in str(number))


def _format_example_with_bold_word(
    content: Text, example_text: str, word: str, base_style: str = "italic cyan"
) -> None:
    """Add example text to content with word bolded."""
    content.append("  ", style="cyan")  # Indent

    text_parts = bold_word_in_text(example_text, word)

    for text_part, style_type in text_parts:
        if style_type == "bold":
            content.append(text_part, style="bold cyan")
        else:
            content.append(text_part, style=base_style)


def _add_definition_content(content: Text, definitions: list[Definition], word: str) -> None:
    """Add definition content with examples and synonyms to a Text object."""
    for i, definition in enumerate(definitions):
        if i > 0:
            content.append("\n\n")

        # Word type
        content.append(f"{definition.part_of_speech}", style="bold yellow")
        content.append("\n")

        # Clean and format definition with proper sentence case
        clean_def = clean_markdown(definition.definition)
        clean_def = ensure_sentence_case(clean_def)
        content.append(f"  {clean_def}", style="white")

        # Examples with special formatting
        # Note: Examples are stored separately in the new model structure
        # This would need to be loaded asynchronously, which is not possible in this sync function
        # For now, we'll skip examples in the CLI formatting

        # Synonyms (limit to 10)
        if definition.synonyms:
            content.append("\n\n")
            content.append("  synonyms: ", style="dim italic")

            displayed_synonyms = definition.synonyms[:10]
            synonyms_text = ", ".join(displayed_synonyms)
            content.append(synonyms_text, style="cyan italic")


def _create_meaning_panel(
    entry: SynthesizedDictionaryEntry,
    meaning_id: str,
    definitions: list[Definition],
    counter: int,
    use_superscripts: bool,
) -> Panel:
    """Create a panel for a single meaning group."""
    # Create panel title with superscript if needed
    if use_superscripts:
        superscript = _create_superscript(counter)
        meaning_display = format_meaning_cluster_name(meaning_id)
        panel_title = Text()
        panel_title.append(f"{entry.word.lower()}", style="bold bright_blue")
        panel_title.append(superscript, style="bold bright_blue")
        panel_title.append(f" ({meaning_display})", style="dim cyan")
    else:
        panel_title = None

    # Create content for this meaning
    content = Text()
    _add_definition_content(content, definitions, entry.word.lower())

    return Panel(
        content,
        title=panel_title,
        title_align="left",
        border_style="bright_blue",
        padding=(0, 1),
    )


def format_meaning_based_definition(
    entry: SynthesizedDictionaryEntry,
    languages: list[Language],
    providers: list[DictionaryProvider],
    meaning_groups: dict[str, list[Definition]],
) -> Panel:
    """Format AI-generated definition grouped by meanings with separate panels for multiple meanings."""

    # Header with word and pronunciation (word always lowercase)
    header = Text()

    header.append(entry.word, style="bold bright_blue")
    header.append(f" /{entry.pronunciation.phonetic.lower()}/", style="dim cyan")

    header.append("\n")
    header.append(", ".join(language.value for language in languages), style="dim")

    # Check if we need superscripts and separate panels (more than 1 meaning)
    use_superscripts = len(meaning_groups) > 1

    content_group: Group | Text = None  # type: ignore

    if use_superscripts:
        # Create separate panels for each meaning
        panels = []
        for meaning_counter, (meaning_id, definitions) in enumerate(meaning_groups.items(), 1):
            meaning_panel = _create_meaning_panel(
                entry, meaning_id, definitions, meaning_counter, True
            )
            panels.append(meaning_panel)

        content_group = Group(*panels)
    else:
        # Single meaning - use simple format without sub-panels
        meaning_id, definitions = next(iter(meaning_groups.items()))
        content = Text()

        _add_definition_content(content, definitions, entry.word)

        content_group = Group(content)

    # Add provider and language info
    provider_info = Text()
    provider_info.append("✨ source(s): ", style="dim")
    provider_info.append(", ".join(provider.name.lower() for provider in providers), style="dim")

    content_group = Group(
        content_group,
        provider_info,
    )

    # Wrap everything in outer panel
    return Panel(
        content_group,
        title=header,
        title_align="left",
        border_style="blue",
        padding=(1, 1, 0, 1),
    )
