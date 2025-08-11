"""Corpus walker for systematic API querying of dictionary providers.

Walks through language corpora word by word, querying providers and
storing versioned results with resume capability.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from ...models import Word
from ...models.definition import Language
from ...models.provider import (
    BatchOperation,
    BatchStatus,
    VersionedProviderData,
)
from ...search.corpus.manager import CorpusManager
from ...utils.logging import get_logger
from ..base import DictionaryConnector

logger = get_logger(__name__)


class CorpusWalker:
    """Walks through a corpus, fetching definitions from providers.
    
    Features:
    - Systematic word-by-word processing
    - Resume capability for interrupted operations
    - Progress tracking and checkpointing
    - Versioned data storage
    - Rate limiting and error handling
    """
    
    def __init__(
        self,
        connector: DictionaryConnector,
        corpus_name: str = "english_common",
        language: Language = Language.ENGLISH,
        batch_size: int = 100,
    ) -> None:
        """Initialize corpus walker.
        
        Args:
            connector: Dictionary connector to use
            corpus_name: Name of corpus to walk
            language: Language of corpus
            batch_size: Number of words to process before checkpointing
        """
        self.connector = connector
        self.corpus_name = corpus_name
        self.language = language
        self.batch_size = batch_size
        self.corpus_manager = CorpusManager()
        
    async def walk_corpus(
        self,
        operation_id: str | None = None,
        resume: bool = True,
        max_words: int | None = None,
    ) -> BatchOperation:
        """Walk through corpus, fetching definitions for each word.
        
        Args:
            operation_id: Unique operation ID for tracking
            resume: Whether to resume from previous checkpoint
            max_words: Maximum number of words to process (None for all)
            
        Returns:
            BatchOperation with results
        """
        # Generate operation ID if not provided
        if not operation_id:
            operation_id = f"corpus_walk_{self.corpus_name}_{self.connector.provider_name.value}_{datetime.now(UTC).isoformat()}"
        
        # Check for existing operation to resume
        batch_op = None
        if resume:
            batch_op = await BatchOperation.find_one(
                {
                    "operation_id": operation_id,
                    "status": {"$in": [BatchStatus.IN_PROGRESS, BatchStatus.PARTIAL]},
                }
            )
        
        # Create new operation if not resuming
        if not batch_op:
            batch_op = BatchOperation(
                operation_id=operation_id,
                operation_type="corpus_walk",
                provider=self.connector.provider_name,
                status=BatchStatus.PENDING,
                corpus_name=self.corpus_name,
                corpus_language=self.language,
            )
            await batch_op.save()
        
        try:
            # Update status to in progress
            batch_op.status = BatchStatus.IN_PROGRESS
            batch_op.started_at = datetime.now(UTC)
            await batch_op.save()
            
            # Get corpus (existing corpus with vocabulary)
            corpus = await self.corpus_manager.get_corpus(
                corpus_name=self.corpus_name,
            )
            
            if not corpus or not corpus.vocabulary:
                raise ValueError(f"Corpus '{self.corpus_name}' not found or empty")
            
            # Get vocabulary to walk
            vocabulary = list(corpus.vocabulary)
            batch_op.total_items = len(vocabulary)
            
            # Apply max_words limit if specified
            if max_words:
                vocabulary = vocabulary[:max_words]
                batch_op.total_items = max_words
            
            # Resume from checkpoint if available
            start_index = 0
            if batch_op.checkpoint and "last_index" in batch_op.checkpoint:
                start_index = batch_op.checkpoint["last_index"] + 1
                logger.info(f"Resuming from index {start_index}")
            
            # Process words in batches
            for i in range(start_index, len(vocabulary), self.batch_size):
                batch_words = vocabulary[i:i + self.batch_size]
                
                await self._process_batch(
                    batch_words,
                    batch_op,
                    current_index=i,
                )
                
                # Update checkpoint
                batch_op.update_checkpoint({
                    "last_index": min(i + self.batch_size - 1, len(vocabulary) - 1),
                    "last_word": batch_words[-1],
                    "timestamp": datetime.now(UTC).isoformat(),
                })
                batch_op.processed_items = min(i + self.batch_size, len(vocabulary))
                await batch_op.save()
                
                # Log progress
                progress_pct = (batch_op.processed_items / batch_op.total_items) * 100
                logger.info(
                    f"Progress: {batch_op.processed_items}/{batch_op.total_items} "
                    f"({progress_pct:.1f}%) - Last word: {batch_words[-1]}"
                )
            
            # Mark as completed
            batch_op.status = BatchStatus.COMPLETED
            batch_op.completed_at = datetime.now(UTC)
            batch_op.statistics["duration_seconds"] = (
                batch_op.completed_at - batch_op.started_at
            ).total_seconds()
            await batch_op.save()
            
            logger.info(
                f"Corpus walk completed: {batch_op.processed_items} words processed, "
                f"{batch_op.failed_items} failed"
            )
            
        except Exception as e:
            logger.error(f"Corpus walk failed: {e}")
            batch_op.status = BatchStatus.FAILED if batch_op.processed_items == 0 else BatchStatus.PARTIAL
            batch_op.add_error("general", str(e))
            await batch_op.save()
            raise
        
        return batch_op
    
    async def _process_batch(
        self,
        words: list[str],
        batch_op: BatchOperation,
        current_index: int,
    ) -> None:
        """Process a batch of words.
        
        Args:
            words: List of words to process
            batch_op: Batch operation for tracking
            current_index: Current index in corpus
        """
        tasks = []
        
        for word_text in words:
            # Get or create Word object
            word_obj = await Word.find_one(
                {"text": word_text, "language": self.language}
            )
            
            if not word_obj:
                word_obj = Word(
                    text=word_text,
                    normalized=word_text.lower(),
                    language=self.language,
                )
                await word_obj.save()
            
            # Check if we already have latest data for this word
            existing = await VersionedProviderData.find_one(
                {
                    "word_id": word_obj.id,
                    "provider": self.connector.provider_name,
                    "version_info.is_latest": True,
                }
            )
            
            if existing and not batch_op.checkpoint.get("force_refresh", False):
                logger.debug(f"Skipping {word_text} - already have latest data")
                continue
            
            # Add to tasks for concurrent processing
            tasks.append(self._fetch_word(word_obj, batch_op))
        
        # Process tasks concurrently with semaphore for rate limiting
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count failures
            for result in results:
                if isinstance(result, Exception):
                    batch_op.failed_items += 1
    
    async def _fetch_word(
        self,
        word_obj: Word,
        batch_op: BatchOperation,
    ) -> VersionedProviderData | None:
        """Fetch a single word with error handling.
        
        Args:
            word_obj: Word to fetch
            batch_op: Batch operation for tracking
            
        Returns:
            VersionedProviderData or None if failed
        """
        try:
            # Use the connector's versioned fetch
            result = await self.connector.fetch_with_versioning(
                word_obj,
                force_fetch=True,
            )
            
            if result:
                # Update statistics
                if "definitions_fetched" not in batch_op.statistics:
                    batch_op.statistics["definitions_fetched"] = 0
                batch_op.statistics["definitions_fetched"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch {word_obj.text}: {e}")
            batch_op.add_error(word_obj.text, str(e))
            return None


class MultiProviderWalker:
    """Walks corpus with multiple providers in parallel."""
    
    def __init__(
        self,
        connectors: list[DictionaryConnector],
        corpus_name: str = "english_common",
        language: Language = Language.ENGLISH,
    ) -> None:
        """Initialize multi-provider walker.
        
        Args:
            connectors: List of dictionary connectors
            corpus_name: Name of corpus to walk
            language: Language of corpus
        """
        self.connectors = connectors
        self.corpus_name = corpus_name
        self.language = language
    
    async def walk_all_providers(
        self,
        resume: bool = True,
        max_words: int | None = None,
    ) -> list[BatchOperation]:
        """Walk corpus with all providers.
        
        Args:
            resume: Whether to resume from checkpoints
            max_words: Maximum words to process per provider
            
        Returns:
            List of BatchOperation results
        """
        walkers = [
            CorpusWalker(connector, self.corpus_name, self.language)
            for connector in self.connectors
        ]
        
        # Run all walkers in parallel
        tasks = [
            walker.walk_corpus(resume=resume, max_words=max_words)
            for walker in walkers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful operations
        operations = []
        for result in results:
            if isinstance(result, BatchOperation):
                operations.append(result)
            else:
                logger.error(f"Provider walk failed: {result}")
        
        return operations