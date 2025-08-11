"""Bulk download system for wholesale dictionary providers.

Handles downloading and importing large data dumps from providers
that offer their entire dataset for download (e.g., Wiktionary).
"""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ...models import Word
from ...models.definition import DictionaryProvider, Language
from ...models.provider import (
    BatchOperation,
    BatchStatus,
    ProviderVersion,
    VersionedProviderData,
)
from ...utils.logging import get_logger

logger = get_logger(__name__)


class BulkDownloader:
    """Downloads and imports bulk dictionary data.
    
    Features:
    - Large file streaming with progress tracking
    - Compressed file support (gzip, bzip2)
    - Resume capability for interrupted downloads
    - Batch import with versioning
    - Memory-efficient processing
    """
    
    def __init__(
        self,
        provider: DictionaryProvider,
        download_url: str,
        data_dir: Path | None = None,
        chunk_size: int = 1024 * 1024,  # 1MB chunks
    ) -> None:
        """Initialize bulk downloader.
        
        Args:
            provider: Dictionary provider
            download_url: URL to download bulk data from
            data_dir: Directory to store downloaded files
            chunk_size: Size of chunks for streaming download
        """
        self.provider = provider
        self.download_url = download_url
        self.data_dir = data_dir or Path("/tmp/floridify/bulk_downloads")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self.session = httpx.AsyncClient(timeout=None)  # No timeout for large downloads
    
    async def __aenter__(self) -> BulkDownloader:
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.session.aclose()
    
    async def download_and_import(
        self,
        operation_id: str | None = None,
        resume: bool = True,
        batch_size: int = 1000,
    ) -> BatchOperation:
        """Download bulk data and import into database.
        
        Args:
            operation_id: Unique operation ID
            resume: Whether to resume interrupted operation
            batch_size: Number of items to import per batch
            
        Returns:
            BatchOperation with results
        """
        # Generate operation ID if not provided
        if not operation_id:
            operation_id = f"bulk_download_{self.provider.value}_{datetime.now(UTC).isoformat()}"
        
        # Check for existing operation
        batch_op = None
        if resume:
            batch_op = await BatchOperation.find_one(
                {
                    "operation_id": operation_id,
                    "status": {"$in": [BatchStatus.IN_PROGRESS, BatchStatus.PARTIAL]},
                }
            )
        
        # Create new operation if needed
        if not batch_op:
            batch_op = BatchOperation(
                operation_id=operation_id,
                operation_type="bulk_download",
                provider=self.provider,
                status=BatchStatus.PENDING,
            )
            await batch_op.save()
        
        try:
            # Update status
            batch_op.status = BatchStatus.IN_PROGRESS
            batch_op.started_at = datetime.now(UTC)
            await batch_op.save()
            
            # Download file
            file_path = await self._download_file(batch_op)
            
            # Import data
            await self._import_data(file_path, batch_op, batch_size)
            
            # Mark as completed
            batch_op.status = BatchStatus.COMPLETED
            batch_op.completed_at = datetime.now(UTC)
            batch_op.statistics["duration_seconds"] = (
                batch_op.completed_at - batch_op.started_at
            ).total_seconds()
            await batch_op.save()
            
            logger.info(
                f"Bulk download completed: {batch_op.processed_items} items imported, "
                f"{batch_op.failed_items} failed"
            )
            
        except Exception as e:
            logger.error(f"Bulk download failed: {e}")
            batch_op.status = BatchStatus.FAILED if batch_op.processed_items == 0 else BatchStatus.PARTIAL
            batch_op.add_error("general", str(e))
            await batch_op.save()
            raise
        
        return batch_op
    
    async def _download_file(self, batch_op: BatchOperation) -> Path:
        """Download file with progress tracking.
        
        Args:
            batch_op: Batch operation for tracking
            
        Returns:
            Path to downloaded file
        """
        # Determine file name from URL
        file_name = self.download_url.split("/")[-1]
        file_path = self.data_dir / file_name
        
        # Check if file already exists (for resume)
        if file_path.exists() and batch_op.checkpoint.get("download_complete"):
            logger.info(f"Using existing file: {file_path}")
            return file_path
        
        # Stream download with progress
        logger.info(f"Downloading from {self.download_url}")
        
        async with self.session.stream("GET", self.download_url) as response:
            response.raise_for_status()
            
            # Get total size if available
            total_size = int(response.headers.get("content-length", 0))
            batch_op.statistics["download_size_bytes"] = total_size
            
            # Download with progress tracking
            downloaded = 0
            with open(file_path, "wb") as f:
                async for chunk in response.aiter_bytes(self.chunk_size):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Update progress periodically
                    if total_size and downloaded % (10 * self.chunk_size) == 0:
                        progress_pct = (downloaded / total_size) * 100
                        logger.info(f"Download progress: {progress_pct:.1f}%")
                        
                        batch_op.update_checkpoint({
                            "download_progress": downloaded,
                            "download_total": total_size,
                        })
                        await batch_op.save()
            
            # Mark download as complete
            batch_op.update_checkpoint({"download_complete": True})
            await batch_op.save()
            
            logger.info(f"Download complete: {file_path}")
            return file_path
    
    async def _import_data(
        self,
        file_path: Path,
        batch_op: BatchOperation,
        batch_size: int,
    ) -> None:
        """Import data from downloaded file.
        
        Args:
            file_path: Path to data file
            batch_op: Batch operation for tracking
            batch_size: Number of items per import batch
        """
        # Determine file format and get appropriate parser
        from typing import Callable, Any
        open_func: Callable[..., Any]
        if file_path.suffix == ".gz":
            logger.info("Processing gzipped file")
            open_func = gzip.open
        else:
            open_func = open
        
        # Get starting position from checkpoint
        start_line = batch_op.checkpoint.get("last_line", 0)
        
        # Process file line by line (assuming JSONL format)
        current_line = 0
        batch_items = []
        
        with open_func(file_path, "rt", encoding="utf-8") as f:
            # Skip to checkpoint if resuming
            for _ in range(start_line):
                f.readline()
                current_line += 1
            
            for line in f:
                current_line += 1
                
                try:
                    # Parse line (assuming JSON)
                    data = json.loads(line.strip())
                    
                    # Convert to our format
                    versioned_data = await self._convert_to_versioned(
                        data,
                        batch_op.operation_id,
                    )
                    
                    if versioned_data:
                        batch_items.append(versioned_data)
                    
                    # Process batch when full
                    if len(batch_items) >= batch_size:
                        await self._save_batch(batch_items, batch_op)
                        batch_items = []
                        
                        # Update checkpoint
                        batch_op.update_checkpoint({"last_line": current_line})
                        batch_op.processed_items = current_line
                        await batch_op.save()
                        
                        # Log progress
                        if current_line % 10000 == 0:
                            logger.info(f"Imported {current_line} items")
                
                except Exception as e:
                    logger.error(f"Error processing line {current_line}: {e}")
                    batch_op.add_error(f"line_{current_line}", str(e))
                    batch_op.failed_items += 1
        
        # Process remaining items
        if batch_items:
            await self._save_batch(batch_items, batch_op)
            batch_op.processed_items = current_line
            await batch_op.save()
        
        logger.info(f"Import complete: {current_line} items processed")
    
    async def _convert_to_versioned(
        self,
        raw_data: dict[str, Any],
        operation_id: str,
    ) -> VersionedProviderData | None:
        """Convert raw data to versioned provider data.
        
        Args:
            raw_data: Raw data from bulk download
            operation_id: Operation ID for tracking
            
        Returns:
            VersionedProviderData or None if invalid
        """
        try:
            # Extract word text (format depends on provider)
            word_text = raw_data.get("word") or raw_data.get("title") or raw_data.get("term")
            if not word_text:
                return None
            
            # Get or create Word object
            word_obj = await Word.find_one(
                {"text": word_text, "language": Language.ENGLISH}
            )
            
            if not word_obj:
                word_obj = Word(
                    text=word_text,
                    normalized=word_text.lower(),
                    language=Language.ENGLISH,
                )
                await word_obj.save()
            
            # Check that word_obj has been saved and has an ID
            if not word_obj.id:
                raise ValueError(f"Word {word_text} must be saved before creating versioned data")
            
            # Compute data hash
            import hashlib
            data_str = json.dumps(raw_data, sort_keys=True)
            data_hash = hashlib.sha256(data_str.encode()).hexdigest()
            
            # Check if this exact data already exists
            existing = await VersionedProviderData.find_one(
                {"version_info.data_hash": data_hash}
            )
            if existing:
                return None  # Skip duplicate
            
            # Create versioned data
            versioned_data = VersionedProviderData(
                word_id=word_obj.id,
                word_text=word_text,
                language=Language.ENGLISH,
                provider=self.provider,
                version_info=ProviderVersion(
                    provider_version=operation_id,  # Use operation ID as version
                    schema_version="bulk_1.0",
                    data_hash=data_hash,
                    is_latest=True,
                ),
                raw_data=raw_data,
                provider_metadata={
                    "source": "bulk_download",
                    "operation_id": operation_id,
                },
            )
            
            return versioned_data
            
        except Exception as e:
            logger.error(f"Error converting data: {e}")
            return None
    
    async def _save_batch(
        self,
        items: list[VersionedProviderData],
        batch_op: BatchOperation,
    ) -> None:
        """Save a batch of versioned data.
        
        Args:
            items: List of VersionedProviderData to save
            batch_op: Batch operation for tracking
        """
        try:
            # Bulk insert
            if items:
                await VersionedProviderData.insert_many(items)
                
                # Update statistics
                if "items_saved" not in batch_op.statistics:
                    batch_op.statistics["items_saved"] = 0
                batch_op.statistics["items_saved"] += len(items)
                
        except Exception as e:
            logger.error(f"Error saving batch: {e}")
            batch_op.failed_items += len(items)


class WiktionaryBulkDownloader(BulkDownloader):
    """Specialized downloader for Wiktionary data dumps."""
    
    def __init__(self, language: Language = Language.ENGLISH, data_dir: Path | None = None) -> None:
        """Initialize Wiktionary downloader.
        
        Args:
            language: Language enum (defaults to English)
            data_dir: Directory for downloads
        """
        # Wiktionary dump URL pattern
        base_url = f"https://dumps.wikimedia.org/{language.value}wiktionary/latest/"
        dump_file = f"{language.value}wiktionary-latest-all-titles-in-ns0.gz"
        
        super().__init__(
            provider=DictionaryProvider.WIKTIONARY,
            download_url=base_url + dump_file,
            data_dir=data_dir,
        )
        self.language = language
    
    async def _convert_to_versioned(
        self,
        raw_data: dict[str, Any],
        operation_id: str,
    ) -> VersionedProviderData | None:
        """Convert Wiktionary data to versioned format.
        
        Wiktionary-specific conversion logic.
        """
        # For Wiktionary, we might just have titles in the dump
        # Actual definitions would need to be fetched via API
        # This is a simplified example
        
        if isinstance(raw_data, str):
            # Simple title list format
            word_text = raw_data.strip()
        else:
            word_text = raw_data.get("title", "")
        
        if not word_text:
            return None
        
        # Create minimal versioned data for title
        # Real implementation would fetch full data
        return await super()._convert_to_versioned(
            {"word": word_text, "source": "wiktionary_dump"},
            operation_id,
        )