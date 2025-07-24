"""Apple Dictionary batch extractor for comprehensive definition extraction."""

from __future__ import annotations

import asyncio
import platform
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from ..connectors.apple_dictionary import AppleDictionaryConnector
from ..models.models import ProviderData, SynthesizedDictionaryEntry
from ..storage.mongodb import MongoDBStorage
from ..utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


@dataclass 
class ExtractionStats:
    """Statistics for Apple Dictionary extraction."""
    
    words_processed: int = 0
    definitions_found: int = 0
    definitions_stored: int = 0
    errors: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    
    @property
    def duration(self) -> float:
        """Get extraction duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.words_processed == 0:
            return 0.0
        return (self.definitions_found / self.words_processed) * 100


@dataclass
class ExtractionConfig:
    """Configuration for Apple Dictionary extraction."""
    
    batch_size: int = 100  # Process this many words at once
    max_concurrent: int = 10  # Maximum concurrent extractions
    output_file: Path | None = None  # Optional output file for results
    include_metadata: bool = True  # Include extraction metadata
    save_to_mongodb: bool = True  # Save results to MongoDB
    rate_limit: float = 20.0  # Requests per second (higher for local API)
    log_progress: bool = True  # Show progress information


class AppleDictionaryBatchExtractor:
    """Batch extractor for Apple Dictionary definitions."""
    
    def __init__(
        self,
        config: ExtractionConfig,
        mongodb: MongoDBStorage | None = None
    ) -> None:
        """Initialize the batch extractor.
        
        Args:
            config: Extraction configuration
            mongodb: MongoDB storage instance (optional)
        """
        self.config = config
        self.mongodb = mongodb
        self.connector = AppleDictionaryConnector(rate_limit=config.rate_limit)
        self.stats = ExtractionStats()
        
        # Check platform compatibility
        if not self._check_platform_compatibility():
            raise RuntimeError(
                "Apple Dictionary batch extraction requires macOS (Darwin). "
                f"Current platform: {platform.system()}"
            )
    
    def _check_platform_compatibility(self) -> bool:
        """Check if running on macOS."""
        return platform.system() == 'Darwin'
    
    async def extract_word_list(self, words: list[str]) -> list[ProviderData]:
        """Extract definitions for a list of words.
        
        Args:
            words: List of words to extract definitions for
            
        Returns:
            List of ProviderData objects with definitions
        """
        logger.info(f"Starting Apple Dictionary batch extraction for {len(words)} words")
        
        self.stats = ExtractionStats()
        results: list[ProviderData] = []
        
        # Create progress tracker if enabled
        progress = None
        task_id = None
        if self.config.log_progress:
            progress = Progress()
            progress.start()
            task_id = progress.add_task(
                "[green]Extracting Apple Dictionary definitions...", 
                total=len(words)
            )
        
        try:
            # Process words in batches
            for i in range(0, len(words), self.config.batch_size):
                batch = words[i:i + self.config.batch_size]
                batch_results = await self._process_batch(batch)
                results.extend(batch_results)
                
                # Update progress
                if progress and task_id is not None:
                    progress.update(task_id, advance=len(batch))
            
            self.stats.end_time = datetime.now()
            
            # Log final statistics
            self._log_extraction_summary()
            
            # Save to file if requested
            if self.config.output_file:
                await self._save_results_to_file(results)
            
            return results
            
        finally:
            if progress:
                progress.stop()
    
    async def _process_batch(self, words: list[str]) -> list[ProviderData]:
        """Process a batch of words with concurrent extraction.
        
        Args:
            words: Batch of words to process
            
        Returns:
            List of ProviderData objects
        """
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        async def process_word(word: str) -> ProviderData | None:
            async with semaphore:
                return await self._extract_single_word(word)
        
        # Process all words in batch concurrently
        tasks = [process_word(word) for word in words]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter results and handle exceptions
        valid_results: list[ProviderData] = []
        for word, result in zip(words, batch_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to extract '{word}': {result}")
                self.stats.errors += 1
            elif result is not None:
                valid_results.append(result)
                self.stats.definitions_found += 1
                
                # Save to MongoDB if configured
                if self.config.save_to_mongodb and self.mongodb:
                    await self._save_to_mongodb(word, result)
                    self.stats.definitions_stored += 1
            
            self.stats.words_processed += 1
        
        return valid_results
    
    async def _extract_single_word(self, word: str) -> ProviderData | None:
        """Extract definition for a single word.
        
        Args:
            word: Word to extract definition for
            
        Returns:
            ProviderData if successful, None otherwise
        """
        try:
            result = await self.connector.fetch_definition(word)
            if result and result.definitions:
                logger.debug(f"Extracted {len(result.definitions)} definitions for '{word}'")
                return result
            else:
                logger.debug(f"No definitions found for '{word}'")
                return None
        except Exception as e:
            logger.error(f"Error extracting '{word}': {e}")
            raise
    
    async def _save_to_mongodb(self, word: str, provider_data: ProviderData) -> None:
        """Save provider data to MongoDB.
        
        Args:
            word: The word being saved
            provider_data: Provider data to save
        """
        if not self.mongodb:
            return
        
        try:
            # Create a synthesized entry with just the Apple Dictionary data
            from ..models import ModelInfo
            entry = SynthesizedDictionaryEntry(
                word_id=provider_data.word_id,
                definition_ids=provider_data.definition_ids,
                model_info=ModelInfo(
                    name="apple_dictionary_batch",
                    generation_count=1,
                    confidence=1.0,
                ),
                source_provider_data_ids=[str(provider_data.id)] if provider_data.id else [],
            )
            
            # Save to MongoDB
            await entry.save()
                
        except Exception as e:
            logger.error(f"Error saving '{word}' to MongoDB: {e}")
    
    async def _save_results_to_file(self, results: list[ProviderData]) -> None:
        """Save extraction results to file.
        
        Args:
            results: List of provider data to save
        """
        if not self.config.output_file:
            return
        
        try:
            output_data = {
                "extraction_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "platform": platform.system(),
                    "platform_version": platform.mac_ver()[0],
                    "total_words": self.stats.words_processed,
                    "definitions_found": self.stats.definitions_found,
                    "success_rate": self.stats.success_rate,
                    "duration_seconds": self.stats.duration
                },
                "results": [result.model_dump() for result in results]
            }
            
            # Ensure output directory exists
            self.config.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write results to file
            with open(self.config.output_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved extraction results to {self.config.output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save results to file: {e}")
    
    def _log_extraction_summary(self) -> None:
        """Log summary of extraction process."""
        if not self.config.log_progress:
            return
        
        table = Table(title="Apple Dictionary Extraction Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Words Processed", str(self.stats.words_processed))
        table.add_row("Definitions Found", str(self.stats.definitions_found))
        table.add_row("Definitions Stored", str(self.stats.definitions_stored))
        table.add_row("Errors", str(self.stats.errors))
        table.add_row("Success Rate", f"{self.stats.success_rate:.1f}%")
        table.add_row("Duration", f"{self.stats.duration:.2f}s")
        
        console.print(table)
        
        logger.info(
            f"Apple Dictionary extraction completed: "
            f"{self.stats.definitions_found}/{self.stats.words_processed} words "
            f"({self.stats.success_rate:.1f}% success rate) "
            f"in {self.stats.duration:.2f}s"
        )
    
    async def extract_from_word_list(self, word_list_path: Path) -> list[ProviderData]:
        """Extract definitions from a word list file.
        
        Args:
            word_list_path: Path to file containing words (one per line)
            
        Returns:
            List of ProviderData objects
        """
        if not word_list_path.exists():
            raise FileNotFoundError(f"Word list file not found: {word_list_path}")
        
        # Read words from file
        words = []
        with open(word_list_path, encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith('#'):  # Skip empty lines and comments
                    words.append(word)
        
        logger.info(f"Loaded {len(words)} words from {word_list_path}")
        return await self.extract_word_list(words)
    
    async def get_available_dictionaries(self) -> dict[str, Any]:
        """Get information about available Apple dictionaries.
        
        Returns:
            Dictionary with information about available dictionaries
        """
        service_info = self.connector.get_service_info()
        
        # Add extraction-specific information
        service_info.update({
            "batch_extractor_version": "1.0.0",
            "extraction_capabilities": {
                "batch_processing": True,
                "concurrent_extraction": True,
                "mongodb_integration": self.config.save_to_mongodb,
                "file_output": self.config.output_file is not None
            },
            "recommended_batch_size": self.config.batch_size,
            "max_concurrent": self.config.max_concurrent,
            "rate_limit": self.config.rate_limit
        })
        
        return service_info


# Convenience functions for common extraction tasks

async def extract_common_words(
    word_count: int = 1000,
    output_file: Path | None = None,
    mongodb: MongoDBStorage | None = None
) -> list[ProviderData]:
    """Extract definitions for the most common English words.
    
    Args:
        word_count: Number of common words to extract
        output_file: Optional output file for results
        mongodb: Optional MongoDB storage
        
    Returns:
        List of ProviderData objects
    """
    # TODO: Integrate with actual word frequency data from corpus/database
    # This is placeholder data for testing
    common_words = [
        "apple", "banana", "car", "dog", "elephant", "fire", "green", "house",
        "ice", "jump", "king", "lion", "moon", "nice", "ocean", "peace",
        "queen", "red", "sun", "tree", "umbrella", "voice", "water", "x-ray",
        "yellow", "zebra"
    ][:word_count]
    
    config = ExtractionConfig(
        output_file=output_file,
        save_to_mongodb=mongodb is not None
    )
    
    extractor = AppleDictionaryBatchExtractor(config, mongodb)
    return await extractor.extract_word_list(common_words)


async def extract_from_search_engine(
    search_limit: int = 1000,
    mongodb: MongoDBStorage | None = None
) -> list[ProviderData]:
    """Extract definitions for words from the search engine corpus.
    
    Args:
        search_limit: Maximum number of words to extract
        mongodb: Optional MongoDB storage
        
    Returns:
        List of ProviderData objects
    """
    # This would integrate with the existing search engine
    # For now, returning a placeholder
    logger.warning("Search engine integration not yet implemented")
    return []