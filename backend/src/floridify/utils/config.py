"""Configuration management for Floridify."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import toml

from .paths import get_project_root


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
class RateLimits:
    """Rate limiting configuration."""

    oxford_rps: float = 10.0
    wiktionary_rps: float = 50.0
    openai_bulk_max_concurrent: int = 5


@dataclass
class DatabaseConfig:
    """Database configuration with environment-specific URLs."""

    production_url: str = ""
    development_url: str = ""
    local_mongodb_url: str = ""
    name: str = "floridify"
    timeout: int = 120
    max_pool_size: int = 100

    def get_url(self) -> str:
        """Get appropriate database URL based on environment."""

        is_docker = os.path.exists("/.dockerenv")
        is_ec2 = os.path.exists("/var/lib/cloud")
        is_production = is_ec2 or os.getenv("ENVIRONMENT") == "production"

        # Get the appropriate URL
        if is_production:
            url = self.production_url
        else:
            # For development, prefer local MongoDB if available, fall back to SSH tunnel
            if self.local_mongodb_url:
                url = self.local_mongodb_url
            else:
                url = self.development_url

        if not url:
            raise ValueError(
                f"No database URL configured for environment "
                f"(production={is_production}, docker={is_docker}). "
                f"Please check auth/config.toml"
            )

        return url

    @property
    def cert_path(self) -> Path:
        """Certificate path is always at project_root/auth/."""
        return get_project_root() / "auth" / "rds-ca-2019-root.pem"


@dataclass
class GoogleCloudConfig:
    """Google Cloud configuration."""

    credentials_path: str | None = None
    project_id: str | None = None
    tts_american_voice: str = "en-US-Wavenet-D"
    tts_british_voice: str = "en-GB-Wavenet-B"
    tts_american_voice_female: str = "en-US-Wavenet-F"
    tts_british_voice_female: str = "en-GB-Wavenet-A"


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
    database: DatabaseConfig
    rate_limits: RateLimits
    processing: ProcessingConfig
    google_cloud: GoogleCloudConfig | None = None

    @classmethod
    def from_file(cls, config_path: str | Path | None = None) -> Config:
        """Load configuration from TOML file.

        Args:
            config_path: Path to configuration file (defaults to auth/config.toml)

        Returns:
            Loaded configuration
        """
        if config_path is None:
            # Get config path with environment override
            env_path = os.getenv("FLORIDIFY_CONFIG_PATH")
            if env_path:
                config_path = Path(env_path)
            else:
                # Standard location
                project_root = get_project_root()
                config_path = project_root / "auth" / "config.toml"

                # In Docker, check alternative location
                if os.path.exists("/.dockerenv") and not config_path.exists():
                    docker_config = Path("/app/auth/config.toml")
                    if docker_config.exists():
                        config_path = docker_config
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Please create {config_path} with your API keys and database configuration."
            )

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


        db_data = data.get("database", {})
        database_config = DatabaseConfig(
            production_url=db_data.get("production_url", ""),
            development_url=db_data.get("development_url", ""),
            local_mongodb_url=db_data.get("local_mongodb_url", ""),
            name=db_data.get("name", "floridify"),
            timeout=db_data.get("timeout", 120),
            max_pool_size=db_data.get("max_pool_size", 100),
        )

        rate_limits = RateLimits(
            oxford_rps=data.get("rate_limits", {}).get("oxford_rps", 10.0),
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

        # Load Google Cloud config if present
        google_cloud = None
        if "google_cloud" in data:
            gc_data = data["google_cloud"]
            google_cloud = GoogleCloudConfig(
                credentials_path=gc_data.get("credentials_path"),
                project_id=gc_data.get("project_id"),
                tts_american_voice=gc_data.get("tts_american_voice", "en-US-Wavenet-D"),
                tts_british_voice=gc_data.get("tts_british_voice", "en-GB-Wavenet-B"),
                tts_american_voice_female=gc_data.get(
                    "tts_american_voice_female", "en-US-Wavenet-F"
                ),
                tts_british_voice_female=gc_data.get("tts_british_voice_female", "en-GB-Wavenet-A"),
            )

        config = cls(
            openai=openai_config,
            oxford=oxford_config,
            database=database_config,
            rate_limits=rate_limits,
            processing=processing,
            google_cloud=google_cloud,
        )

        # Validate required fields
        if not config.openai.api_key:
            raise ValueError(
                f"OpenAI API key missing in {config_path}\n"
                f"Please update the 'api_key' field in the [openai] section."
            )

        return config
