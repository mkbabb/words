"""Command-line interface for Floridify word processing."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from .ai import WordProcessingPipeline, simple_progress_callback
from .config import Config
from .prompts import PromptLoader
from .storage.mongodb import MongoDBStorage


async def process_word_command(word: str, config_path: str = "auth/config.toml") -> None:
    """Process a single word through the complete pipeline.

    Args:
        word: Word to process
        config_path: Path to configuration file
    """
    try:
        # Load configuration
        config = Config.from_file(config_path)

        # Initialize storage and connect
        storage = MongoDBStorage()
        await storage.connect()

        # Initialize pipeline
        pipeline = WordProcessingPipeline(config, storage)

        print(f"Processing word: {word}")
        print("=" * 50)

        # Process the word
        entry = await pipeline.process_word(word)

        if entry:
            print(f"✓ Successfully processed '{word}'")
            print(f"  Providers: {list(entry.providers.keys())}")
            print(f"  Definitions: {sum(len(p.definitions) for p in entry.providers.values())}")
            print(f"  Has AI synthesis: {'ai_synthesis' in entry.providers}")

            # Show AI synthesis if available
            if "ai_synthesis" in entry.providers:
                ai_data = entry.providers["ai_synthesis"]
                print(f"\\nAI Synthesis ({len(ai_data.definitions)} definitions):")
                for i, definition in enumerate(ai_data.definitions, 1):
                    print(f"  {i}. [{definition.word_type.value}] {definition.definition}")
                    if definition.examples.generated:
                        print("     Examples:")
                        for example in definition.examples.generated[:2]:
                            print(f"     - {example.sentence}")
        else:
            print(f"✗ Failed to process '{word}'")

        # Clean up
        await pipeline.close()

    except Exception as e:
        print(f"Error processing word '{word}': {e}")


async def process_word_list_command(file_path: str, config_path: str = "auth/config.toml") -> None:
    """Process a list of words from a file.

    Args:
        file_path: Path to file containing words (one per line)
        config_path: Path to configuration file
    """
    try:
        # Load word list
        words_file = Path(file_path)
        if not words_file.exists():
            print(f"Error: File '{file_path}' not found")
            return

        words = []
        with open(words_file) as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith("#"):  # Skip empty lines and comments
                    words.append(word)

        if not words:
            print(f"No words found in '{file_path}'")
            return

        print(f"Processing {len(words)} words from '{file_path}'")
        print("=" * 50)

        # Load configuration
        config = Config.from_file(config_path)

        # Initialize storage and connect
        storage = MongoDBStorage()
        await storage.connect()

        # Initialize pipeline
        pipeline = WordProcessingPipeline(config, storage)

        # Process words with progress callback
        entries = await pipeline.process_word_list(
            words, progress_callback=simple_progress_callback
        )

        print("=" * 50)
        print("Processing complete!")
        print(f"Successfully processed: {len(entries)}/{len(words)} words")

        # Show summary statistics
        total_definitions = sum(
            sum(len(p.definitions) for p in entry.providers.values()) for entry in entries
        )
        ai_syntheses = sum(1 for entry in entries if "ai_synthesis" in entry.providers)

        print(f"Total definitions: {total_definitions}")
        print(f"AI syntheses generated: {ai_syntheses}")

        # Clean up
        await pipeline.close()

    except Exception as e:
        print(f"Error processing word list: {e}")


def show_prompts_command() -> None:
    """Show available prompt templates and their information."""
    try:
        loader = PromptLoader()

        print("Available Prompt Templates")
        print("=" * 30)

        templates = loader.list_templates()

        for template_name in templates:
            try:
                info = loader.get_template_info(template_name)
                print(f"\n📝 {template_name}")
                print(f"   Variables: {', '.join(info['variables'])}")
                print(f"   AI Settings: {info['ai_settings']}")
                print(f"   Preview: {info['system_message_preview']}")
            except Exception as e:
                print(f"   Error loading template: {e}")

        print(f"\nTotal templates: {len(templates)}")

    except Exception as e:
        print(f"Error listing prompts: {e}")


def show_stats_command(config_path: str = "auth/config.toml") -> None:
    """Show processing pipeline statistics.

    Args:
        config_path: Path to configuration file
    """
    try:
        # Load configuration
        config = Config.from_file(config_path)

        # Initialize storage (no need to connect for stats)
        storage = MongoDBStorage()

        # Initialize pipeline
        pipeline = WordProcessingPipeline(config, storage)

        # Get and display stats
        stats = pipeline.get_processing_stats()

        print("Floridify Pipeline Statistics")
        print("=" * 30)
        print(f"Providers configured: {stats['providers_configured']}")
        print(f"Storage connected: {stats['storage_connected']}")
        print(f"AI model: {stats['ai_model']}")
        print(f"Embedding model: {stats['embedding_model']}")

    except Exception as e:
        print(f"Error getting stats: {e}")


def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Floridify Word Processing CLI")
        print("Usage:")
        print("  python -m floridify.cli word <word>")
        print("  python -m floridify.cli list <file_path>")
        print("  python -m floridify.cli stats")
        print("  python -m floridify.cli prompts")
        print("")
        print("Examples:")
        print("  python -m floridify.cli word serendipity")
        print("  python -m floridify.cli list words.txt")
        print("  python -m floridify.cli stats")
        print("  python -m floridify.cli prompts")
        return

    command = sys.argv[1].lower()

    if command == "word" and len(sys.argv) >= 3:
        word = sys.argv[2]
        asyncio.run(process_word_command(word))
    elif command == "list" and len(sys.argv) >= 3:
        file_path = sys.argv[2]
        asyncio.run(process_word_list_command(file_path))
    elif command == "stats":
        show_stats_command()
    elif command == "prompts":
        show_prompts_command()
    else:
        print(f"Unknown command: {command}")
        print("Use 'python -m floridify.cli' for help")


if __name__ == "__main__":
    main()
