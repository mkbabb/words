"""
Unified bulk scraping system for all dictionary providers.

Provides systematic scraping with progress tracking, resume functionality, and beautiful visualizations.
Supports all available providers: WordHippo, Dictionary.com, Wiktionary (API and wholesale).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..models.definition import DictionaryProvider, Language
from ..search.corpus.language_loader import CorpusLanguageLoader
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Global directory for storing scraping sessions
SESSIONS_DIR = Path.home() / ".floridify" / "scraping_sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class BulkScrapingConfig(BaseModel):
    """Configuration for bulk scraping operations."""
    
    provider: DictionaryProvider = Field(..., description="Dictionary provider to scrape")
    language: Language = Field(..., description="Language to scrape")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Words per batch")
    max_concurrent: int = Field(default=5, ge=1, le=20, description="Max concurrent operations")
    
    # Resume functionality
    resume_from_word: str | None = Field(default=None, description="Word to resume from")
    checkpoint_file: Path | None = Field(default=None, description="Checkpoint file path")
    
    # Processing options
    force_refresh: bool = Field(default=False, description="Force refresh existing data")
    skip_existing: bool = Field(default=True, description="Skip words with existing data")
    
    # Output options
    output_dir: Path | None = Field(default=None, description="Output directory for results")
    
    model_config = {"frozen": True}


class ScrapingSession(BaseModel):
    """Complete scraping session with persistence."""
    
    # Session identification
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_name: str | None = Field(default=None, description="Human-readable session name")
    provider: DictionaryProvider = Field(..., description="Provider being scraped")
    language: Language = Field(..., description="Language being scraped")
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    last_checkpoint_at: datetime | None = Field(default=None)
    
    # Configuration
    batch_size: int = Field(default=100, ge=1)
    max_concurrent: int = Field(default=5, ge=1)
    force_refresh: bool = Field(default=False)
    skip_existing: bool = Field(default=True)
    
    # Progress state
    vocabulary: list[str] = Field(default_factory=list, description="Full vocabulary list")
    processed_words: list[str] = Field(default_factory=list, description="Words already processed")
    failed_words: list[str] = Field(default_factory=list, description="Words that failed processing")
    current_position: int = Field(default=0, ge=0, description="Current index in vocabulary")
    
    # Statistics  
    total_words: int = Field(default=0, ge=0)
    successful_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    
    # Status
    status: str = Field(default="created", description="Session status: created, running, paused, completed, failed")
    error_message: str | None = Field(default=None)
    
    def get_session_file(self) -> Path:
        """Get the file path for this session."""
        safe_name = f"{self.provider.value}_{self.language.value}_{self.session_id[:8]}"
        return SESSIONS_DIR / f"{safe_name}.json"
    
    async def save(self) -> None:
        """Save session to disk."""
        session_file = self.get_session_file()
        try:
            with session_file.open('w', encoding='utf-8') as f:
                json.dump(self.model_dump(mode='json'), f, indent=2, default=str)
            logger.debug(f"Saved session {self.session_id[:8]} to {session_file}")
        except Exception as e:
            logger.error(f"Failed to save session {self.session_id}: {e}")
    
    @classmethod
    async def load(cls, session_id: str) -> ScrapingSession | None:
        """Load session from disk by ID."""
        # Find session file by ID prefix
        for session_file in SESSIONS_DIR.glob("*_*.json"):
            if session_id in session_file.stem:
                try:
                    with session_file.open('r', encoding='utf-8') as f:
                        data = json.load(f)
                    # Convert datetime strings back to datetime objects
                    for field in ['created_at', 'started_at', 'completed_at', 'last_checkpoint_at']:
                        if data.get(field):
                            data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                    return cls(**data)
                except Exception as e:
                    logger.error(f"Failed to load session from {session_file}: {e}")
        return None
    
    def get_remaining_vocabulary(self) -> list[str]:
        """Get vocabulary items that still need to be processed."""
        processed_set = set(self.processed_words)
        return [word for word in self.vocabulary[self.current_position:] if word not in processed_set]
    
    def mark_word_processed(self, word: str, success: bool) -> None:
        """Mark a word as processed."""
        if word not in self.processed_words:
            self.processed_words.append(word)
            
        if success:
            self.successful_count += 1
        else:
            self.failed_count += 1
            if word not in self.failed_words:
                self.failed_words.append(word)
    
    def get_progress_percentage(self) -> float:
        """Get completion percentage."""
        if self.total_words == 0:
            return 0.0
        return (len(self.processed_words) / self.total_words) * 100
    
    def get_statistics(self) -> dict[str, Any]:
        """Get session statistics."""
        elapsed_seconds = 0.0
        if self.started_at:
            end_time = self.completed_at or datetime.now(UTC)
            elapsed_seconds = (end_time - self.started_at).total_seconds()
        
        words_per_second = 0.0
        if elapsed_seconds > 0:
            words_per_second = len(self.processed_words) / elapsed_seconds
        
        success_rate = 0.0
        if len(self.processed_words) > 0:
            success_rate = self.successful_count / len(self.processed_words)
        
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "provider": self.provider.display_name,
            "language": self.language.value.title(),
            "status": self.status,
            "progress_percentage": self.get_progress_percentage(),
            "total_words": self.total_words,
            "processed_words": len(self.processed_words),
            "successful_words": self.successful_count,
            "failed_words": self.failed_count,
            "skipped_words": self.skipped_count,
            "success_rate": success_rate,
            "words_per_second": words_per_second,
            "elapsed_seconds": elapsed_seconds,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class BulkScrapingProgress(BaseModel):
    """Real-time progress tracking (for UI updates)."""
    
    # Basic info
    session_id: str = Field(..., description="Associated session ID")
    provider: DictionaryProvider = Field(..., description="Provider being scraped")
    language: Language = Field(..., description="Language being scraped")
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Progress tracking
    total_words: int = Field(default=0, ge=0)
    processed_words: int = Field(default=0, ge=0)
    successful_words: int = Field(default=0, ge=0)
    failed_words: int = Field(default=0, ge=0)
    skipped_words: int = Field(default=0, ge=0)
    
    # Current status
    current_batch: int = Field(default=0, ge=0)
    current_word: str | None = Field(default=None)
    is_running: bool = Field(default=False)
    is_completed: bool = Field(default=False)
    estimated_completion: datetime | None = Field(default=None)
    
    # Error tracking
    consecutive_errors: int = Field(default=0, ge=0)
    error_messages: list[str] = Field(default_factory=list)
    
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
            self.estimated_completion = datetime.now(UTC) + timedelta(seconds=remaining_seconds)

    def add_error(self, error_message: str) -> None:
        """Add an error message to tracking."""
        self.error_messages.append(error_message)
        # Keep only last 50 errors to prevent memory issues
        if len(self.error_messages) > 50:
            self.error_messages = self.error_messages[-50:]


class BulkScraper:
    """
    Unified bulk scraper for all dictionary providers.
    
    Supports:
    - WordHippo (comprehensive synonym/antonym data)
    - Dictionary.com + Thesaurus.com (definitions and synonyms)  
    - Wiktionary API (structured dictionary data)
    - Wiktionary Wholesale (complete dump processing)
    """

    def __init__(self, provider: DictionaryProvider, config: BulkScrapingConfig, session: ScrapingSession | None = None):
        """Initialize bulk scraper.
        
        Args:
            provider: Dictionary provider to use
            config: Scraping configuration
            session: Existing session to resume (optional)
        """
        self.provider = provider
        self.config = config
        self.session = session or ScrapingSession(
            provider=provider,
            language=config.language,
            batch_size=config.batch_size,
            max_concurrent=config.max_concurrent,
            force_refresh=config.force_refresh,
            skip_existing=config.skip_existing
        )
        self.progress = BulkScrapingProgress(
            session_id=self.session.session_id,
            provider=provider,
            language=config.language
        )
        self.should_stop = False
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        self._connector: Any = None
        self._checkpoint_interval = 50  # Save session every N words
        
    async def _get_connector(self) -> Any:
        """Get the appropriate connector for the provider."""
        if self._connector is not None:
            return self._connector
            
        if self.provider == DictionaryProvider.WORDHIPPO:
            from .scraper.wordhippo import WordHippoConnector
            self._connector = WordHippoConnector()
        elif self.provider == DictionaryProvider.DICTIONARY_COM:
            from .scraper.dictionary_com import DictionaryComConnector
            self._connector = DictionaryComConnector()
        elif self.provider == DictionaryProvider.WIKTIONARY:
            from .scraper.wiktionary import WiktionaryConnector
            self._connector = WiktionaryConnector()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
            
        return self._connector

    async def _get_corpus_vocabulary(self) -> list[str]:
        """Get normalized vocabulary from corpus for the target language."""
        logger.info(f"Loading vocabulary corpus for {self.config.language.value}")
        
        # Use the enhanced language loader with normalized vocabulary
        corpus_loader = CorpusLanguageLoader(force_rebuild=False)
        corpus = await corpus_loader.get_or_create_corpus(
            languages=[self.config.language],
            force_rebuild=False
        )
        
        vocabulary = corpus_loader.get_vocabulary_normalized()
        logger.info(f"Loaded {len(vocabulary)} normalized vocabulary items")
        return vocabulary

    async def start_scraping(self) -> BulkScrapingProgress:
        """Start or resume the bulk scraping process."""
        logger.info(f"Starting bulk scraping: {self.provider.display_name} ({self.config.language.value})")
        
        try:
            # Initialize or load vocabulary
            if not self.session.vocabulary:
                vocabulary = await self._get_corpus_vocabulary()
                if not vocabulary:
                    raise ValueError(f"No vocabulary available for {self.config.language.value}")
                
                self.session.vocabulary = vocabulary
                self.session.total_words = len(vocabulary)
                logger.info(f"Loaded {len(vocabulary)} words for scraping")
            else:
                logger.info(f"Resuming session with {len(self.session.vocabulary)} words")
            
            # Update progress tracking
            self.progress.total_words = self.session.total_words
            self.progress.successful_words = self.session.successful_count
            self.progress.failed_words = self.session.failed_count
            self.progress.processed_words = len(self.session.processed_words)
            self.progress.is_running = True
            
            # Mark session as started
            self.session.status = "running"
            self.session.started_at = datetime.now(UTC)
            await self.session.save()
            
            # Get remaining vocabulary to process
            remaining_vocabulary = self.session.get_remaining_vocabulary()
            
            if not remaining_vocabulary:
                logger.info("All words already processed, session complete")
                await self._complete_session()
                return self.progress
            
            logger.info(f"Processing {len(remaining_vocabulary)} remaining words")
            
            # Get connector
            connector = await self._get_connector()
            
            # Process in batches
            await self._process_batches(remaining_vocabulary, connector)
            
            # Mark as completed
            await self._complete_session()
            
        except Exception as e:
            logger.error(f"Bulk scraping failed: {e}")
            self.progress.add_error(str(e))
            self.progress.is_running = False
            self.session.status = "failed"
            self.session.error_message = str(e)
            await self.session.save()
            raise
        finally:
            # Clean up connector
            if self._connector and hasattr(self._connector, 'close'):
                await self._connector.close()
        
        return self.progress
    
    async def _complete_session(self) -> None:
        """Mark session as completed and save final state."""
        self.session.status = "completed"
        self.session.completed_at = datetime.now(UTC)
        self.progress.is_completed = True
        self.progress.is_running = False
        
        await self.session.save()
        
        logger.info(
            f"Bulk scraping completed: {self.session.successful_count}/{self.session.total_words} successful "
            f"({self.session.successful_count/max(1, self.session.total_words):.1%} success rate)"
        )
    
    async def _process_batches(self, vocabulary: list[str], connector: Any) -> None:
        """Process vocabulary in batches with concurrent processing."""
        batch_size = self.config.batch_size
        
        for i in range(0, len(vocabulary), batch_size):
            if self.should_stop:
                logger.info("Stopping scraping due to user request")
                break
            
            batch = vocabulary[i:i + batch_size]
            self.progress.current_batch += 1
            
            logger.debug(f"Processing batch {self.progress.current_batch} ({len(batch)} words)")
            
            # Process batch concurrently
            batch_tasks = [self._process_word(word, connector) for word in batch]
            await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Update progress
            self.progress.update_statistics()
            
            # Small delay between batches to be respectful
            if not self.should_stop:
                await asyncio.sleep(0.1)
    
    async def _process_word(self, word: str, connector: Any) -> None:
        """Process a single word with the connector."""
        async with self._semaphore:
            if self.should_stop:
                return
            
            self.progress.current_word = word
            success = False
            
            try:
                # Check if we should skip existing data
                if self.config.skip_existing and not self.config.force_refresh:
                    # For now, we'll implement basic existence checking later
                    # This could check MongoDB for existing entries
                    pass
                
                # Fetch definition using the connector
                result = await connector.fetch_definition(
                    word=word,
                    language=self.config.language
                )
                
                if result and hasattr(result, 'definitions') and result.definitions:
                    success = True
                    self.progress.successful_words += 1
                    self.progress.consecutive_errors = 0
                else:
                    self.progress.failed_words += 1
                    self.progress.consecutive_errors += 1
                    
            except Exception as e:
                logger.debug(f"Error processing word '{word}': {e}")
                self.progress.failed_words += 1
                self.progress.consecutive_errors += 1
                self.progress.add_error(f"{word}: {str(e)}")
                
                # Stop if too many consecutive errors
                if self.progress.consecutive_errors > 20:
                    logger.error("Too many consecutive errors, stopping scraping")
                    self.should_stop = True
            
            finally:
                self.progress.processed_words += 1
                
                # Update session progress
                self.session.mark_word_processed(word, success)
                
                # Checkpoint periodically
                if len(self.session.processed_words) % self._checkpoint_interval == 0:
                    self.session.last_checkpoint_at = datetime.now(UTC)
                    await self.session.save()
                    logger.debug(f"Checkpoint saved: {len(self.session.processed_words)} words processed")

    def stop(self) -> None:
        """Stop the scraping process gracefully."""
        logger.info("Stopping bulk scraping...")
        self.should_stop = True
        
    def get_progress(self) -> BulkScrapingProgress:
        """Get current progress information."""
        self.progress.update_statistics()
        return self.progress


# Specialized scraping functions for different modes

async def scrape_provider_corpus(
    provider: DictionaryProvider,
    language: Language,
    batch_size: int = 100,
    max_concurrent: int = 5,
    force_refresh: bool = False,
    skip_existing: bool = True,
) -> BulkScrapingProgress:
    """
    Scrape a provider using the vocabulary corpus for the language.
    
    Args:
        provider: Dictionary provider to scrape
        language: Language to scrape
        batch_size: Words per batch
        max_concurrent: Maximum concurrent operations
        force_refresh: Force refresh of existing data
        skip_existing: Skip words that already have data
        
    Returns:
        Final progress information
    """
    config = BulkScrapingConfig(
        provider=provider,
        language=language,
        batch_size=batch_size,
        max_concurrent=max_concurrent,
        force_refresh=force_refresh,
        skip_existing=skip_existing,
    )
    
    scraper = BulkScraper(provider, config)
    return await scraper.start_scraping()


async def scrape_wiktionary_wholesale(
    language: Language,
    download_all: bool = False,
) -> BulkScrapingProgress:
    """
    Scrape Wiktionary using wholesale dump processing.
    
    Args:
        language: Language to download
        download_all: If True, download complete dump; otherwise use vocabulary-based processing
        
    Returns:
        Final progress information
    """
    logger.info(f"Starting Wiktionary wholesale scraping for {language.value}")
    
    progress = BulkScrapingProgress(
        session_id=str(uuid.uuid4()),
        provider=DictionaryProvider.WIKTIONARY,
        language=language
    )
    
    try:
        if download_all:
            # Download complete Wiktionary dump
            logger.info("Downloading complete Wiktionary dump (this may take several hours)")
            # TODO: Implement wholesale dump downloading
            logger.warning("Wholesale dump download not yet implemented, falling back to vocabulary-based")
            download_all = False
        
        if not download_all:
            # Use vocabulary-based wholesale processing
            config = BulkScrapingConfig(
                provider=DictionaryProvider.WIKTIONARY,
                language=language,
                batch_size=50,  # Smaller batches for wholesale
                max_concurrent=3,  # Lower concurrency
            )
            
            scraper = BulkScraper(DictionaryProvider.WIKTIONARY, config)
            progress = await scraper.start_scraping()
        
        progress.is_completed = True
        logger.info(f"Wiktionary wholesale scraping completed: {progress.successful_words} entries processed")
        
    except Exception as e:
        logger.error(f"Wiktionary wholesale scraping failed: {e}")
        progress.add_error(str(e))
        raise
    
    return progress


# Session management functions

async def list_sessions() -> list[dict[str, Any]]:
    """List all scraping sessions with their statistics."""
    sessions = []
    
    for session_file in SESSIONS_DIR.glob("*.json"):
        try:
            session = await ScrapingSession.load(session_file.stem.split('_')[-1])
            if session:
                sessions.append(session.get_statistics())
        except Exception as e:
            logger.warning(f"Failed to load session from {session_file}: {e}")
    
    # Sort by creation date (newest first)
    sessions.sort(key=lambda x: x['created_at'], reverse=True)
    return sessions


async def get_session(session_id: str) -> ScrapingSession | None:
    """Get a specific session by ID."""
    return await ScrapingSession.load(session_id)


async def delete_session(session_id: str) -> bool:
    """Delete a session file."""
    session = await ScrapingSession.load(session_id)
    if session:
        try:
            session.get_session_file().unlink(missing_ok=True)
            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
    return False


async def cleanup_old_sessions(days: int = 30) -> int:
    """Clean up sessions older than specified days."""
    cutoff_date = datetime.now(UTC) - timedelta(days=days)
    cleaned_count = 0
    
    for session_file in SESSIONS_DIR.glob("*.json"):
        try:
            with session_file.open('r', encoding='utf-8') as f:
                data = json.load(f)
            
            created_at = datetime.fromisoformat(data.get('created_at', '').replace('Z', '+00:00'))
            
            if created_at < cutoff_date:
                session_file.unlink()
                cleaned_count += 1
                logger.debug(f"Cleaned up old session {session_file.name}")
                
        except Exception as e:
            logger.warning(f"Failed to process session file {session_file}: {e}")
    
    return cleaned_count


async def create_session(
    provider: DictionaryProvider,
    language: Language,
    session_name: str | None = None,
    **kwargs: Any
) -> ScrapingSession:
    """Create a new scraping session."""
    session = ScrapingSession(
        provider=provider,
        language=language,
        session_name=session_name,
        **kwargs
    )
    await session.save()
    logger.info(f"Created new session {session.session_id[:8]} for {provider.display_name} ({language.value})")
    return session


async def resume_session(session_id: str) -> tuple[BulkScraper, ScrapingSession] | None:
    """Resume a scraping session by ID."""
    session = await ScrapingSession.load(session_id)
    if not session:
        logger.error(f"Session {session_id} not found")
        return None
    
    if session.status == "completed":
        logger.info(f"Session {session_id} is already completed")
        return None
    
    # Create configuration from session
    config = BulkScrapingConfig(
        provider=session.provider,
        language=session.language,
        batch_size=session.batch_size,
        max_concurrent=session.max_concurrent,
        force_refresh=session.force_refresh,
        skip_existing=session.skip_existing,
    )
    
    # Create scraper with existing session
    scraper = BulkScraper(session.provider, config, session)
    
    logger.info(f"Resuming session {session_id[:8]} - {session.get_progress_percentage():.1f}% complete")
    return scraper, session