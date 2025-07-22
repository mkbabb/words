"""Configuration management for Floridify."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import toml

from .utils.paths import get_config_path


@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""

    api_key: str
    model: str = "gpt-4o"
    reasoning_effort: str = "high"
    embedding_model: str = "text-embedding-3-large"


@dataclass
class OxfordConfig:
    """Oxford Dictionary API configuration."""

    app_id: str
    api_key: str


@dataclass
class DictionaryComConfig:
    """Dictionary.com API configuration."""

    authorization: str


@dataclass
class RateLimits:
    """Rate limiting configuration."""

    oxford_rps: float = 10.0
    dictionary_com_rps: float = 20.0
    wiktionary_rps: float = 50.0
    openai_bulk_max_concurrent: int = 5


@dataclass
class DatabaseConfig:
    """Database configuration."""

    url: str = "mongodb://localhost:27017"
    name: str = "floridify"
    timeout: int = 30
    max_pool_size: int = 100


@dataclass
class ProcessingConfig:
    """Processing pipeline configuration."""

    max_concurrent_words: int = 100
    batch_size: int = 50
    retry_attempts: int = 3
    cache_ttl_hours: int = 24
    verbose: bool = False


@dataclass
class Config:
    """Main configuration class."""

    openai: OpenAIConfig
    oxford: OxfordConfig
    dictionary_com: DictionaryComConfig
    database: DatabaseConfig
    rate_limits: RateLimits
    processing: ProcessingConfig

    @classmethod
    def from_file(cls, config_path: str | Path | None = None) -> Config:
        """Load configuration from TOML file.

        Args:
            config_path: Path to configuration file (defaults to auth/config.toml)

        Returns:
            Loaded configuration
        """
        if config_path is None:
            config_path = get_config_path()
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        data = toml.load(config_path)

        # Load configurations with defaults
        openai_config = OpenAIConfig(
            api_key=data.get("openai", {}).get("api_key", ""),
            model=data.get("models", {}).get("openai_model", "gpt-4o"),
            reasoning_effort=data.get("models", {}).get("reasoning_effort", "high"),
            embedding_model=data.get("models", {}).get("embedding_model", "text-embedding-3-large"),
        )

        oxford_config = OxfordConfig(
            app_id=data.get("oxford", {}).get("app_id", ""),
            api_key=data.get("oxford", {}).get("api_key", ""),
        )

        dictionary_com_config = DictionaryComConfig(
            authorization=data.get("dictionary_com", {}).get("authorization", "")
        )

        database_config = DatabaseConfig(
            url=data.get("database", {}).get("url", "mongodb://localhost:27017"),
            name=data.get("database", {}).get("name", "floridify"),
            timeout=data.get("database", {}).get("timeout", 30),
            max_pool_size=data.get("database", {}).get("max_pool_size", 100),
        )

        rate_limits = RateLimits(
            oxford_rps=data.get("rate_limits", {}).get("oxford_rps", 10.0),
            dictionary_com_rps=data.get("rate_limits", {}).get("dictionary_com_rps", 20.0),
            wiktionary_rps=data.get("rate_limits", {}).get("wiktionary_rps", 50.0),
            openai_bulk_max_concurrent=data.get("rate_limits", {}).get(
                "openai_bulk_max_concurrent", 5
            ),
        )

        processing = ProcessingConfig(
            max_concurrent_words=data.get("processing", {}).get("max_concurrent_words", 100),
            batch_size=data.get("processing", {}).get("batch_size", 50),
            retry_attempts=data.get("processing", {}).get("retry_attempts", 3),
            cache_ttl_hours=data.get("processing", {}).get("cache_ttl_hours", 24),
            verbose=data.get("processing", {}).get("verbose", False),
        )

        return cls(
            openai=openai_config,
            oxford=oxford_config,
            dictionary_com=dictionary_com_config,
            database=database_config,
            rate_limits=rate_limits,
            processing=processing,
        )
