"""Rich formatting utilities for beautiful CLI output."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.text import Text

from ...models import DictionaryEntry
from ...search import SearchResult
from ...search.constants import SearchMethod


def format_meaning_cluster_name(meaning_id: str) -> str:
    """Convert snake_case meaning cluster ID to Title Case display format.
    
    Examples:
        bank_financial -> Bank Financial
        simple_uncomplicated -> Simple Uncomplicated
        word_general -> Word General
    """
    # Remove word prefix and convert to title case
    parts = meaning_id.split('_')
    if len(parts) > 1:
        # Skip the word part and format the meaning part
        meaning_parts = parts[1:]  # Skip word prefix like 'bank_' 
        return ' '.join(word.capitalize() for word in meaning_parts)
    else:
        # Fallback for single words
        return meaning_id.capitalize()


def ensure_sentence_case(text: str) -> str:
    """Ensure text has proper sentence case: capital first letter, period at end."""
    if not text:
        return text
    
    # Strip whitespace and ensure first letter is capitalized
    text = text.strip()
    if not text:
        return text
        
    # Capitalize first letter
    text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    # Ensure ends with period if it doesn't end with punctuation
    if not text.endswith(('.', '!', '?', ':', ';')):
        text += '.'
    
    return text


console = Console()


def format_word_display(
    entry: DictionaryEntry, show_examples: bool = True, show_synonyms: bool = True
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
        table.add_row(metric.replace('_', ' ').title(), value_str)
    
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


def format_ai_definition(entry: Any, sources: list[str] | None = None) -> Panel:
    """Format AI-generated definition with beautiful styling."""
    # Clean markdown formatting from text
    def clean_markdown(text: str) -> str:
        # Remove markdown formatting
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic  
        text = re.sub(r'`(.*?)`', r'\1', text)        # Code
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # Links
        return text
    
    # Header with word and pronunciation (word always lowercase)
    header = Text()
    header.append(entry.word.text.lower(), style="bold bright_blue")
    if hasattr(entry, 'pronunciation') and entry.pronunciation.phonetic:
        header.append(f" /{entry.pronunciation.phonetic.lower()}/", style="dim cyan")
    
    # Main content
    content = Text()
    
    # Add definitions by word type
    for i, definition in enumerate(entry.definitions):
        if i > 0:
            content.append("\n\n")
        
        # Word type
        content.append(f"{definition.word_type.value}", style="bold yellow")
        content.append("\n")
        
        # Clean and format definition with proper sentence case
        clean_def = clean_markdown(definition.definition)
        clean_def = ensure_sentence_case(clean_def)
        content.append(f"  {clean_def}", style="white")
        
        # Examples with special formatting
        if hasattr(definition, 'examples') and definition.examples.generated:
            for example in definition.examples.generated[:2]:  # Show max 2 examples
                content.append("\n\n")
                
                # Clean example text and ensure proper sentence case
                clean_example = clean_markdown(example.sentence)
                clean_example = ensure_sentence_case(clean_example)
                
                # Handle multi-word phrases properly
                import re
                
                content.append("  ", style="cyan")  # Indent
                
                # For multi-word phrases, try to bold any part that appears
                word_parts = entry.word.text.lower().split()
                example_lower = clean_example.lower()
                
                # Simple approach: bold if any significant word from the phrase appears
                found_word = False
                for word_part in word_parts:
                    # Skip short words like "en", "a", "the"
                    if len(word_part) > 3 and word_part in example_lower:
                        # Bold the specific word part found
                        pattern = re.compile(re.escape(word_part), re.IGNORECASE)
                        if pattern.search(clean_example):
                            found_word = True
                            break
                
                if found_word:
                    # Split and bold the found word
                    pattern = re.compile(re.escape(word_part), re.IGNORECASE)
                    parts = pattern.split(clean_example)
                    matches = pattern.findall(clean_example)
                    
                    for j, part in enumerate(parts):
                        if j > 0 and j <= len(matches):
                            content.append(matches[j-1], style="bold cyan")
                        content.append(part, style="italic cyan")
                else:
                    # No word found to bold, just show in italic
                    content.append(clean_example, style="italic cyan")
    
    # Sources section
    if sources:
        content.append("\n\n")
        source_text = Text()
        source_text.append("✨ Sources: ", style="dim")
        source_text.append(", ".join(sources), style="dim")
        content.append_text(source_text)
    
    # Wrap everything in a double panel
    inner_panel = Panel(
        content,
        title_align="left",
        border_style="bright_blue",
        padding=(0, 1)
    )
    
    outer_panel = Panel(
        inner_panel,
        title=header,
        title_align="left", 
        border_style="blue",
        padding=(1, 1)
    )
    
    return outer_panel


def format_meaning_based_definition(
    entry: Any, meaning_groups: dict[str, list[Any]], sources: list[str] | None = None
) -> Panel:
    """Format AI-generated definition grouped by meanings with separate panels for multiple meanings."""
    from rich.console import Group
    
    # Clean markdown formatting from text
    def clean_markdown(text: str) -> str:
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic  
        text = re.sub(r'`(.*?)`', r'\1', text)        # Code
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # Links
        return text
    
    def format_meaning_panel(meaning_id: str, definitions: list[Any], counter: int, use_superscripts: bool) -> Panel:
        """Create a panel for a single meaning group."""
        # Unicode superscript mapping
        superscript_map = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', 
                           '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}
        
        # Create panel title with superscript if needed
        if use_superscripts:
            superscript = ''.join(superscript_map.get(d, d) for d in str(counter))
            meaning_display = format_meaning_cluster_name(meaning_id)
            panel_title = Text()
            panel_title.append(f"{entry.word.text.lower()}", style="bold bright_blue")
            panel_title.append(superscript, style="bold bright_blue")
            panel_title.append(f" ({meaning_display})", style="dim cyan")
        else:
            panel_title = None
        
        # Create content for this meaning
        content = Text()
        
        # Add definitions for this meaning
        for i, definition in enumerate(definitions):
            if i > 0:
                content.append("\n\n")
            
            # Word type
            content.append(f"{definition.word_type.value}", style="bold yellow")
            content.append("\n")
            
            # Clean and format definition with proper sentence case
            clean_def = clean_markdown(definition.definition)
            clean_def = ensure_sentence_case(clean_def)
            content.append(f"  {clean_def}", style="white")
            
            # Examples with special formatting
            if hasattr(definition, 'examples') and definition.examples.generated:
                for example in definition.examples.generated[:1]:  # Show 1 example per definition
                    content.append("\n\n")
                    
                    # Clean example text and ensure proper sentence case
                    clean_example = clean_markdown(example.sentence)
                    clean_example = ensure_sentence_case(clean_example)
                    content.append("  ", style="cyan")  # Indent
                    
                    # Bold the entire phrase in examples (fix for multi-word phrases)
                    import re
                    full_word = entry.word.text.lower()
                    example_lower = clean_example.lower()
                    
                    # Try to find the complete phrase first
                    if full_word in example_lower:
                        # Found complete phrase - bold it
                        pattern = re.compile(re.escape(full_word), re.IGNORECASE)
                        parts = pattern.split(clean_example)
                        matches = pattern.findall(clean_example)
                        
                        for j, part in enumerate(parts):
                            if j > 0 and j <= len(matches):
                                content.append(matches[j-1], style="bold cyan")
                            content.append(part, style="italic cyan")
                    else:
                        # Fallback: try individual words only if phrase is long
                        word_parts = full_word.split()
                        if len(word_parts) > 1:
                            # For multi-word phrases, just show italic if we can't find the full phrase
                            content.append(clean_example, style="italic cyan")
                        else:
                            # Single word - try to bold it
                            found_word = False
                            for word_part in word_parts:
                                if len(word_part) > 3 and word_part in example_lower:
                                    pattern = re.compile(re.escape(word_part), re.IGNORECASE)
                                    if pattern.search(clean_example):
                                        found_word = True
                                        parts = pattern.split(clean_example)
                                        matches = pattern.findall(clean_example)
                                        
                                        for j, part in enumerate(parts):
                                            if j > 0 and j <= len(matches):
                                                content.append(matches[j-1], style="bold cyan")
                                            content.append(part, style="italic cyan")
                                        break
                            
                            if not found_word:
                                content.append(clean_example, style="italic cyan")
        
        return Panel(
            content,
            title=panel_title,
            title_align="left",
            border_style="bright_blue",
            padding=(0, 1)
        )
    
    # Header with word and pronunciation (word always lowercase)
    header = Text()
    header.append(entry.word.text.lower(), style="bold bright_blue")
    if hasattr(entry, 'pronunciation') and entry.pronunciation.phonetic:
        header.append(f" /{entry.pronunciation.phonetic.lower()}/", style="dim cyan")
    
    # Check if we need superscripts and separate panels (more than 1 meaning)
    use_superscripts = len(meaning_groups) > 1
    
    if use_superscripts:
        # Create separate panels for each meaning
        panels = []
        meaning_counter = 1
        for meaning_id, definitions in meaning_groups.items():
            meaning_panel = format_meaning_panel(meaning_id, definitions, meaning_counter, True)
            panels.append(meaning_panel)
            meaning_counter += 1
        
        # Add sources
        if sources:
            source_text = Text()
            source_text.append("✨ Sources: ", style="dim")
            source_text.append(", ".join(sources), style="dim")
            source_panel = Panel(source_text, style="dim", border_style="dim")
            panels.append(source_panel)
        
        # Group all panels
        content_group = Group(*panels)
    else:
        # Single meaning - use simple format without sub-panels (just direct content)
        meaning_id, definitions = next(iter(meaning_groups.items()))
        
        # Create content directly without sub-panel
        content = Text()
        
        # Add definitions for this single meaning
        for i, definition in enumerate(definitions):
            if i > 0:
                content.append("\n\n")
            
            # Word type
            content.append(f"{definition.word_type.value}", style="bold yellow")
            content.append("\n")
            
            # Clean and format definition with proper sentence case
            clean_def = clean_markdown(definition.definition)
            clean_def = ensure_sentence_case(clean_def)
            content.append(f"  {clean_def}", style="white")
            
            # Examples with special formatting
            if hasattr(definition, 'examples') and definition.examples.generated:
                for example in definition.examples.generated[:1]:  # Show 1 example per definition
                    content.append("\n\n")
                    
                    # Clean example text and ensure proper sentence case
                    clean_example = clean_markdown(example.sentence)
                    clean_example = ensure_sentence_case(clean_example)
                    content.append("  ", style="cyan")  # Indent
                    
                    # Bold the entire phrase in examples (fix for multi-word phrases)
                    import re
                    full_word = entry.word.text.lower()
                    example_lower = clean_example.lower()
                    
                    # Try to find the complete phrase first
                    if full_word in example_lower:
                        # Found complete phrase - bold it
                        pattern = re.compile(re.escape(full_word), re.IGNORECASE)
                        parts = pattern.split(clean_example)
                        matches = pattern.findall(clean_example)
                        
                        for j, part in enumerate(parts):
                            if j > 0 and j <= len(matches):
                                content.append(matches[j-1], style="bold cyan")
                            content.append(part, style="italic cyan")
                    else:
                        # Fallback: try individual words only if phrase is long
                        word_parts = full_word.split()
                        if len(word_parts) > 1:
                            # For multi-word phrases, just show italic if we can't find the full phrase
                            content.append(clean_example, style="italic cyan")
                        else:
                            # Single word - try to bold it
                            found_word = False
                            for word_part in word_parts:
                                if len(word_part) > 3 and word_part in example_lower:
                                    pattern = re.compile(re.escape(word_part), re.IGNORECASE)
                                    if pattern.search(clean_example):
                                        found_word = True
                                        parts = pattern.split(clean_example)
                                        matches = pattern.findall(clean_example)
                                        
                                        for j, part in enumerate(parts):
                                            if j > 0 and j <= len(matches):
                                                content.append(matches[j-1], style="bold cyan")
                                            content.append(part, style="italic cyan")
                                        break
                            
                            if not found_word:
                                content.append(clean_example, style="italic cyan")
        
        # Add sources
        if sources:
            content.append("\n\n")
            content.append("✨ Sources: ", style="dim")
            content.append(", ".join(sources), style="dim")
        
        content_group = Group(content)
    
    # Wrap everything in outer panel
    outer_panel = Panel(
        content_group,
        title=header,
        title_align="left", 
        border_style="blue",
        padding=(1, 1)
    )
    
    return outer_panel
