"""Provider configuration management."""

from datetime import datetime

from beanie import Document
from pydantic import Field

from ..models.base import BaseMetadata
from ..models.dictionary import DictionaryProvider


class ProviderConfiguration(Document, BaseMetadata):
    """Store provider-specific configuration and metadata."""

    provider: DictionaryProvider = Field(description="Provider identifier")

    # API Configuration
    api_endpoint: str | None = None
    api_version: str | None = None
    requires_auth: bool = False
    auth_type: str | None = None

    # Rate limiting
    rate_limit_requests: int | None = None
    rate_limit_period: str | None = None

    # Capabilities
    supports_batch: bool = False
    supports_etymology: bool = True
    supports_pronunciation: bool = True
    supports_examples: bool = True
    supports_synonyms: bool = True

    # Data format
    response_format: str = "json"
    requires_parsing: bool = False

    # Wholesale download
    supports_bulk_download: bool = False
    bulk_download_url: str | None = None
    bulk_download_format: str | None = None
    last_bulk_download: datetime | None = None

    # Additional metadata
    notes: str | None = None
    active: bool = True

    class Settings:
        name = "provider_configurations"
        indexes = [
            "provider",
            "active",
        ]
