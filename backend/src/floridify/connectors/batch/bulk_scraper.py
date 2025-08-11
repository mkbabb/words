"""
Bulk scraping module for systematically processing entire language corpora.

Provides comprehensive scraping capabilities with progress tracking, resume functionality,
and respectful rate limiting across different dictionary providers.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from ...models import Word
from ...models.definition import DictionaryProvider, Language
from ...models.provider import BatchOperation, VersionedProviderData
from ...search.corpus.language_loader import CorpusLanguageLoader
from ...utils.logging import get_logger
from ..base import DictionaryConnector
from ..config import VersionConfig

logger = get_logger(__name__)


class BulkScrapingConfig(BaseModel):
    """Configuration for bulk scraping operations."""
    
    provider: DictionaryProvider = Field(..., description="Dictionary provider to scrape")
    language: Language = Field(..., description="Language to scrape")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Words to process per batch")
    max_concurrent: int = Field(default=5, ge=1, le=20, description="Maximum concurrent operations")
    checkpoint_interval: int = Field(default=50, ge=1, description="Checkpoint every N words")
    error_threshold: int = Field(default=10, ge=1, description="Max consecutive errors before stopping")
    
    # Resume functionality
    resume_from_word: str | None = Field(default=None, description="Word to resume from")
    skip_existing: bool = Field(default=True, description="Skip words already in database")
    
    # Storage configuration
    save_versioned: bool = Field(default=True, description="Save to versioned storage")
    force_refresh: bool = Field(default=False, description="Force refresh even if data exists")
    
    model_config = {"frozen": True}


class BulkScrapingProgress(BaseModel):
    """Progress tracking for bulk scraping operations."""
    
    session_id: str = Field(..., description="Unique session identifier")
    config: BulkScrapingConfig = Field(..., description="Scraping configuration")
    
    # Progress tracking
    total_words: int = Field(default=0, ge=0)
    processed_words: int = Field(default=0, ge=0)
    successful_words: int = Field(default=0, ge=0)
    failed_words: int = Field(default=0, ge=0)
    skipped_words: int = Field(default=0, ge=0)
    
    # Current state
    current_word: str | None = Field(default=None)
    current_batch: int = Field(default=0, ge=0)
    
    # Timing
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_checkpoint: datetime = Field(default_factory=lambda: datetime.now(UTC))
    estimated_completion: datetime | None = Field(default=None)
    
    # Error tracking
    consecutive_errors: int = Field(default=0, ge=0)
    error_messages: list[str] = Field(default_factory=list, max_items=100)
    
    # Statistics
    words_per_second: float = Field(default=0.0, ge=0.0)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    
    def update_statistics(self) -> None:
        """Update calculated statistics."""
        elapsed = (datetime.now(UTC) - self.start_time).total_seconds()
        
        if elapsed > 0:
            self.words_per_second = self.processed_words / elapsed
            
        if self.processed_words > 0:
            self.success_rate = self.successful_words / self.processed_words
            
        if self.words_per_second > 0 and self.total_words > self.processed_words:
            remaining_words = self.total_words - self.processed_words
            remaining_seconds = remaining_words / self.words_per_second
            self.estimated_completion = datetime.now(UTC).timestamp() + remaining_seconds


class BulkScraper:
    """
    Bulk scraper for systematically processing entire language corpora.
    
    Features:
    - Resume from checkpoint functionality
    - Progress tracking with rich statistics
    - Respectful rate limiting
    - Error handling and recovery
    - Concurrent processing with backpressure
    - Comprehensive logging
    """
    
    def __init__(self, connector: DictionaryConnector, config: BulkScrapingConfig):
        """Initialize bulk scraper.
        
        Args:
            connector: Dictionary connector instance
            config: Scraping configuration
        """
        self.connector = connector
        self.config = config
        self.session_id = self._generate_session_id()
        
        # State
        self.progress = BulkScrapingProgress(
            session_id=self.session_id,
            config=config,
        )
        self.corpus_loader = CorpusLanguageLoader()
        self.vocabulary: list[str] = []
        self.should_stop = False
        
        # Concurrency control
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
        self.checkpoint_lock = asyncio.Lock()
        
        logger.info(f"Initialized bulk scraper for {config.provider.value} ({config.language.value})")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = str(int(time.time()))
        config_str = f"{self.config.provider.value}_{self.config.language.value}"
        session_data = f"{timestamp}_{config_str}"
        return hashlib.md5(session_data.encode()).hexdigest()[:16]
    
    async def start_scraping(self) -> BulkScrapingProgress:
        """Start the bulk scraping process.
        
        Returns:
            Final progress state
        """
        logger.info(f"Starting bulk scraping session {self.session_id}")
        
        try:
            # Load vocabulary
            await self._load_vocabulary()
            
            # Find resume point if specified
            start_index = await self._find_resume_point()
            
            # Process vocabulary
            await self._process_vocabulary(start_index)
            
            logger.info(f"Bulk scraping session {self.session_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Bulk scraping session {self.session_id} failed: {e}")
            self.progress.error_messages.append(str(e))
        
        self.progress.update_statistics()
        return self.progress
    
    async def _load_vocabulary(self) -> None:
        """Load vocabulary for the specified language."""
        logger.info(f"Loading {self.config.language.value} vocabulary...")
        
        # Load language corpus
        await self.corpus_loader.load_languages([self.config.language])
        self.vocabulary = self.corpus_loader.get_vocabulary_for_language(self.config.language)
        
        self.progress.total_words = len(self.vocabulary)
        logger.info(f"Loaded {len(self.vocabulary)} words for {self.config.language.value}")
    
    async def _find_resume_point(self) -> int:
        """Find the index to resume from."""
        if not self.config.resume_from_word:
            return 0
        
        try:
            resume_index = self.vocabulary.index(self.config.resume_from_word)
            logger.info(f"Resuming from word '{self.config.resume_from_word}' at index {resume_index}")
            return resume_index
        except ValueError:
            logger.warning(f"Resume word '{self.config.resume_from_word}' not found, starting from beginning")
            return 0
    
    async def _process_vocabulary(self, start_index: int = 0) -> None:
        """Process vocabulary starting from given index."""
        words_to_process = self.vocabulary[start_index:]
        
        # Process in batches
        for batch_start in range(0, len(words_to_process), self.config.batch_size):
            if self.should_stop:
                break
                
            batch_end = min(batch_start + self.config.batch_size, len(words_to_process))
            batch_words = words_to_process[batch_start:batch_end]
            
            self.progress.current_batch += 1
            logger.info(f"Processing batch {self.progress.current_batch} ({len(batch_words)} words)")
            
            # Process batch concurrently
            tasks = [self._process_word(word) for word in batch_words]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Checkpoint periodically
            if self.progress.processed_words % self.config.checkpoint_interval == 0:
                await self._create_checkpoint()
            
            # Check error threshold
            if self.progress.consecutive_errors >= self.config.error_threshold:
                logger.error(f"Exceeded error threshold ({self.config.error_threshold}), stopping")
                self.should_stop = True
                break
    
    async def _process_word(self, word_text: str) -> None:
        """Process a single word."""
        async with self.semaphore:
            self.progress.current_word = word_text
            
            try:
                # Check if already exists and skip if configured
                if self.config.skip_existing and not self.config.force_refresh:
                    existing = await self._check_existing_data(word_text)
                    if existing:
                        self.progress.skipped_words += 1
                        self.progress.processed_words += 1
                        logger.debug(f"Skipping existing word: {word_text}")
                        return
                
                # Create or get word object
                word_obj = await self._get_or_create_word(word_text)
                
                # Scrape definition using connector
                version_config = VersionConfig(
                    save_versioned=self.config.save_versioned,
                    force_api=self.config.force_refresh,
                )
                
                result = await self.connector.fetch_definition(word_obj, version_config=version_config)
                
                if result:
                    self.progress.successful_words += 1
                    self.progress.consecutive_errors = 0
                    logger.debug(f"Successfully processed: {word_text}")
                else:
                    self.progress.failed_words += 1
                    self.progress.consecutive_errors += 1
                    logger.debug(f"No data found for: {word_text}")
                
            except Exception as e:
                self.progress.failed_words += 1
                self.progress.consecutive_errors += 1
                error_msg = f"Error processing '{word_text}': {e}"
                self.progress.error_messages.append(error_msg)
                logger.error(error_msg)
            
            finally:
                self.progress.processed_words += 1
                self.progress.update_statistics()
    
    async def _check_existing_data(self, word_text: str) -> bool:
        """Check if data already exists for this word."""
        try:
            # Check if word exists
            word_obj = await Word.find_one(
                {"text": word_text, "language": self.config.language}
            )
            
            if not word_obj:
                return False
            
            # Check if versioned data exists
            existing = await VersionedProviderData.find_one(
                {
                    "word_id": word_obj.id,
                    "provider": self.config.provider,
                    "version_info.is_latest": True,
                }
            )
            
            return existing is not None
            
        except Exception as e:
            logger.debug(f"Error checking existing data for '{word_text}': {e}")
            return False
    
    async def _get_or_create_word(self, word_text: str) -> Word:
        """Get or create Word object."""
        # Try to find existing word
        word_obj = await Word.find_one(
            {"text": word_text, "language": self.config.language}
        )
        
        if word_obj:
            return word_obj
        
        # Create new word
        word_obj = Word(
            text=word_text,
            normalized=word_text.lower(),
            language=self.config.language,
        )
        await word_obj.save()
        return word_obj
    
    async def _create_checkpoint(self) -> None:
        """Create a checkpoint with current progress."""
        async with self.checkpoint_lock:
            self.progress.last_checkpoint = datetime.now(UTC)
            self.progress.update_statistics()
            
            logger.info(
                f"Checkpoint - Processed: {self.progress.processed_words}/{self.progress.total_words} "
                f"({self.progress.success_rate:.1%} success rate, "
                f"{self.progress.words_per_second:.2f} words/sec)"
            )
    
    def stop(self) -> None:
        """Signal the scraper to stop gracefully."""
        self.should_stop = True
        logger.info(f"Stop signal received for session {self.session_id}")
    
    def get_progress(self) -> BulkScrapingProgress:
        """Get current progress state."""
        self.progress.update_statistics()
        return self.progress


# Convenience functions for different providers

async def bulk_scrape_wordhippo(
    language: Language = Language.ENGLISH,
    **kwargs: Any
) -> BulkScrapingProgress:
    """Bulk scrape WordHippo for a language."""
    from ..scraper.wordhippo import WordHippoConnector
    
    config = BulkScrapingConfig(
        provider=DictionaryProvider.WORDHIPPO,
        language=language,
        **kwargs
    )
    
    connector = WordHippoConnector()
    scraper = BulkScraper(connector, config)
    
    try:
        return await scraper.start_scraping()
    finally:
        await connector.close()


async def bulk_scrape_dictionary_com(
    language: Language = Language.ENGLISH,
    **kwargs: Any
) -> BulkScrapingProgress:
    """Bulk scrape Dictionary.com for a language."""
    from ..scraper.dictionary_com import DictionaryComConnector
    
    config = BulkScrapingConfig(
        provider=DictionaryProvider.DICTIONARY_COM,
        language=language,
        **kwargs
    )
    
    connector = DictionaryComConnector()
    scraper = BulkScraper(connector, config)
    
    try:
        return await scraper.start_scraping()
    finally:
        await connector.close()


async def bulk_scrape_wiktionary_wholesale(
    language: Language = Language.ENGLISH,
    download_all: bool = False,
    **kwargs: Any
) -> BulkScrapingProgress:
    """Bulk scrape or download all Wiktionary data."""
    from ..wholesale.wiktionary_wholesale import WiktionaryWholesaleConnector
    
    config = BulkScrapingConfig(
        provider=DictionaryProvider.WIKTIONARY,
        language=language,
        batch_size=1000,  # Larger batches for wholesale
        **kwargs
    )
    
    wholesale = WiktionaryWholesaleConnector(language=language)
    
    if download_all:
        # Download complete Wiktionary dump
        logger.info(f"Starting wholesale Wiktionary download for {language.value}")
        
        batch_op = BatchOperation(
            operation_type="bulk_download",
            provider=DictionaryProvider.WIKTIONARY,
            language=language,
        )
        
        # Download dump
        download_success = await wholesale.download_bulk_data(
            str(wholesale.data_dir), 
            batch_op
        )
        
        if download_success:
            # Import dump
            imported_count = await wholesale.import_bulk_data(
                str(wholesale.data_dir),
                batch_op
            )
            logger.info(f"Wholesale import completed: {imported_count} entries")
        
        # Create mock progress for wholesale operation
        progress = BulkScrapingProgress(
            session_id="wholesale_" + str(int(time.time())),
            config=config,
            total_words=imported_count if download_success else 0,
            processed_words=imported_count if download_success else 0,
            successful_words=imported_count if download_success else 0,
        )
        progress.update_statistics()
        return progress
    
    else:
        # Use regular vocabulary-based scraping
        scraper = BulkScraper(wholesale, config)
        return await scraper.start_scraping()