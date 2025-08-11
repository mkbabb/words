"""Versioned provider data models for persistent dictionary API storage."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from beanie import Document, Indexed, before_event, Insert, Replace
from pydantic import BaseModel, Field
from pydantic_core import PydanticCustomError

from .base import BaseMetadata, PydanticObjectId
from .definition import DictionaryProvider, Language


class BatchStatus(str, Enum):
    """Status of a batch download operation."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some items succeeded, some failed


class ProviderVersion(BaseModel):
    """Version information for provider data."""
    
    provider_version: str = Field(description="Provider's internal version (API version, data dump version, etc.)")
    schema_version: str = Field(default="1.0", description="Our internal schema version for this provider")
    data_hash: str = Field(description="Content hash for deduplication")
    is_latest: bool = Field(default=True, description="Whether this is the latest version for this word/provider combo")


class VersionedProviderData(Document, BaseMetadata):
    """Persistent storage for provider data with comprehensive versioning.
    
    This replaces ephemeral caching with permanent, versioned storage.
    Each API call or data import creates a versioned entry that can be
    retrieved by version, date, or as the latest available.
    """
    
    # Core identification
    word_id: PydanticObjectId = Field(description="Reference to the Word document")
    word_text: str = Field(description="Original word text for quick reference")
    language: Language = Field(default=Language.ENGLISH)
    provider: DictionaryProvider
    
    # Versioning
    version_info: ProviderVersion
    
    # Version chain (for tracking history)
    superseded_by: PydanticObjectId | None = Field(default=None, description="Link to newer version")
    supersedes: PydanticObjectId | None = Field(default=None, description="Link to older version")
    
    # Data storage
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw API response or scraped data")
    processed_data: dict[str, Any] | None = Field(default=None, description="Processed/normalized data if applicable")
    
    # Provider metadata
    provider_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific metadata (rate limits hit, response time, etc.)"
    )
    
    # Error tracking
    error: str | None = Field(default=None, description="Error message if fetch failed")
    error_code: str | None = Field(default=None, description="Error code if applicable")
    
    class Settings:
        name = "versioned_provider_data"
        indexes = [
            [("word_id", 1), ("provider", 1), ("version_info.is_latest", -1)],  # Quick latest lookup
            [("word_text", 1), ("language", 1), ("provider", 1)],  # Text-based lookup
            "version_info.data_hash",  # Deduplication
            [("created_at", -1)],  # Temporal queries
            "superseded_by",  # Version chain navigation
        ]
    
    @before_event([Insert, Replace])
    async def update_version_chain(self) -> None:
        """Update version chain when inserting new data."""
        if self.version_info.is_latest:
            # Mark previous versions as not latest
            await VersionedProviderData.find(
                {
                    "word_id": self.word_id,
                    "provider": self.provider,
                    "version_info.is_latest": True,
                    "_id": {"$ne": self.id}
                }
            ).update_many({"$set": {"version_info.is_latest": False, "superseded_by": self.id}})


class BatchOperation(Document, BaseMetadata):
    """Track batch download/processing operations for resume capability."""
    
    # Operation identification
    operation_id: str = Field(description="Unique operation identifier")
    operation_type: str = Field(description="Type of operation (corpus_walk, bulk_download, etc.)")
    provider: DictionaryProvider
    
    # Progress tracking
    status: BatchStatus = Field(default=BatchStatus.PENDING)
    total_items: int = Field(default=0)
    processed_items: int = Field(default=0)
    failed_items: int = Field(default=0)
    
    # Checkpoint data for resume
    checkpoint: dict[str, Any] = Field(
        default_factory=dict,
        description="State data for resuming (last processed word, page number, etc.)"
    )
    
    # Corpus information (for corpus walking)
    corpus_name: str | None = Field(default=None)
    corpus_language: Language = Field(default=Language.ENGLISH)
    
    # Timing
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    last_checkpoint_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Error tracking
    errors: list[dict[str, Any]] = Field(default_factory=list)
    
    # Statistics
    statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation statistics (requests made, data size, etc.)"
    )
    
    class Settings:
        name = "batch_operations"
        indexes = [
            "operation_id",
            [("provider", 1), ("status", 1)],
            [("operation_type", 1), ("status", 1)],
            "started_at",
        ]
    
    def update_checkpoint(self, data: dict[str, Any]) -> None:
        """Update checkpoint data for resume capability."""
        self.checkpoint.update(data)
        self.last_checkpoint_at = datetime.now(UTC)
    
    def add_error(self, word: str, error: str, error_code: str | None = None) -> None:
        """Add an error to the error log."""
        self.errors.append({
            "word": word,
            "error": error,
            "error_code": error_code,
            "timestamp": datetime.now(UTC)
        })
        self.failed_items += 1


class ProviderConfiguration(Document, BaseMetadata):
    """Store provider-specific configuration and metadata."""
    
    provider: DictionaryProvider = Field(description="Provider identifier")
    
    # API Configuration
    api_endpoint: str | None = Field(default=None)
    api_version: str | None = Field(default=None)
    requires_auth: bool = Field(default=False)
    auth_type: str | None = Field(default=None, description="Type of auth (api_key, oauth, etc.)")
    
    # Rate limiting
    rate_limit_requests: int | None = Field(default=None, description="Requests per time period")
    rate_limit_period: str | None = Field(default=None, description="Time period (second, minute, hour)")
    
    # Capabilities
    supports_batch: bool = Field(default=False)
    supports_etymology: bool = Field(default=True)
    supports_pronunciation: bool = Field(default=True)
    supports_examples: bool = Field(default=True)
    supports_synonyms: bool = Field(default=True)
    
    # Data format
    response_format: str = Field(default="json", description="Response format (json, xml, html, text)")
    requires_parsing: bool = Field(default=False, description="Whether response needs parsing (e.g., HTML scraping)")
    
    # Wholesale download
    supports_bulk_download: bool = Field(default=False)
    bulk_download_url: str | None = Field(default=None)
    bulk_download_format: str | None = Field(default=None, description="Format of bulk data (json, xml, sql, etc.)")
    last_bulk_download: datetime | None = Field(default=None)
    
    # Additional metadata
    notes: str | None = Field(default=None)
    active: bool = Field(default=True)
    
    class Settings:
        name = "provider_configurations"
        indexes = [
            "provider",
            "active",
        ]
