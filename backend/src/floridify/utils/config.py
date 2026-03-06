"""Configuration management for Floridify."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

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
class MerriamWebsterConfig:
    """Merriam-Webster Dictionary API configuration."""

    api_key: str


@dataclass
class RateLimits:
    """Rate limiting configuration."""

    oxford_rps: float = 10.0
    wiktionary_rps: float = 50.0
    openai_bulk_max_concurrent: int = 5


@dataclass
class DatabaseConfig:
    """Database configuration with strict target URLs.

    In production (Docker), containers talk directly to MongoDB via the Docker
    network using ``runtime_url`` / ``test_url``.

    For local development, an optional ``tunnel_url`` / ``tunnel_test_url`` can
    point at an SSH-tunnelled port (e.g. ``localhost:27018``).  When present
    **and** not running inside Docker, the tunnel URLs take precedence.
    """

    runtime_url: str
    test_url: str
    runtime_tls_required: bool
    name: str = "floridify"
    timeout: int = 120
    max_pool_size: int = 100
    tunnel_url: str | None = None
    tunnel_test_url: str | None = None

    @staticmethod
    def _in_docker() -> bool:
        return os.path.exists("/.dockerenv")

    def get_url(self, target: str = "runtime") -> str:
        """Return the best URL for a target database.

        Prefers the tunnel URL when running outside Docker.
        """
        if target == "runtime":
            if self.tunnel_url and not self._in_docker():
                return self.tunnel_url
            url = self.runtime_url
        elif target == "test":
            if self.tunnel_test_url and not self._in_docker():
                return self.tunnel_test_url
            url = self.test_url
        else:
            raise ValueError(f"Unsupported database target: {target}")

        if not url:
            raise ValueError(f"Database URL for target '{target}' is empty")
        return url

    @staticmethod
    def _extract_hosts(connection_string: str) -> list[str]:
        """Extract hostnames from MongoDB URI netloc."""
        parsed = urlparse(connection_string)
        netloc = parsed.netloc.rsplit("@", 1)[-1]
        if not netloc:
            return []
        hosts: list[str] = []
        for host_part in netloc.split(","):
            host = host_part.strip()
            if not host:
                continue
            if host.startswith("["):
                hosts.append(host.split("]", 1)[0].strip("[]").lower())
            else:
                hosts.append(host.split(":", 1)[0].lower())
        return hosts

    @classmethod
    def _is_local_host(cls, host: str) -> bool:
        local_hosts = {
            "localhost",
            "127.0.0.1",
            "::1",
            "mongodb",
            "floridify-mongodb",
            "host.docker.internal",
        }
        return host in local_hosts or host.endswith(".local")

    def validate_runtime_target(self) -> None:
        """Fail fast when runtime URL points at local Mongo hosts."""
        hosts = self._extract_hosts(self.runtime_url)
        if not hosts:
            raise ValueError("Invalid database.runtime_url: no hosts parsed from URI")
        local_hosts = [host for host in hosts if self._is_local_host(host)]
        if local_hosts:
            raise ValueError(
                "database.runtime_url must point to remote MongoDB hosts; "
                f"found local hosts: {', '.join(local_hosts)}"
            )

    def validate_test_target(self) -> None:
        """Fail fast when test URL points at local Mongo hosts."""
        hosts = self._extract_hosts(self.test_url)
        if not hosts:
            raise ValueError("Invalid database.test_url: no hosts parsed from URI")
        local_hosts = [host for host in hosts if self._is_local_host(host)]
        if local_hosts:
            raise ValueError(
                "database.test_url must point to remote MongoDB hosts; "
                f"found local hosts: {', '.join(local_hosts)}"
            )

    @property
    def cert_path(self) -> Path | None:
        """Optional CA certificate path for TLS connections."""
        project_root = get_project_root()
        preferred = project_root / "auth" / "mongodb-ca.pem"
        if preferred.exists():
            return preferred
        legacy = project_root / "auth" / "rds-ca-2019-root.pem"
        return legacy if legacy.exists() else None


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
class SemanticSearchConfig:
    """Semantic search optimization configuration."""

    use_hnsw: bool = True  # Enable HNSW for MASSIVE corpus tier
    hnsw_m: int = 32  # HNSW connections per node
    hnsw_ef_construction: int = 200  # HNSW build-time search depth
    hnsw_ef_search: int = 64  # HNSW query-time search depth


@dataclass
class Config:
    """Main configuration class."""

    openai: OpenAIConfig
    oxford: OxfordConfig
    database: DatabaseConfig
    rate_limits: RateLimits
    processing: ProcessingConfig
    merriam_webster: MerriamWebsterConfig | None = None
    google_cloud: GoogleCloudConfig | None = None
    semantic_search: SemanticSearchConfig | None = None

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
                f"Please create {config_path} with your API keys and database configuration.",
            )

        data = toml.load(config_path)

        # Validate required sections exist
        if "openai" not in data:
            raise ValueError(
                f"Missing [openai] section in {config_path}\n"
                f"Please add OpenAI configuration with api_key field.",
            )

        # Load OpenAI config with explicit validation
        openai_data = data["openai"]
        if "api_key" not in openai_data or not openai_data["api_key"]:
            raise ValueError(
                f"OpenAI API key missing in {config_path}\n"
                f"Please set 'api_key' in the [openai] section.",
            )

        models_data = data.get("models", {})
        openai_config = OpenAIConfig(
            api_key=openai_data["api_key"],
            model=models_data.get("openai_model", "gpt-4o"),
            reasoning_effort=models_data.get("reasoning_effort", "high"),
            embedding_model=models_data.get("embedding_model", "text-embedding-3-large"),
        )

        # Load Oxford config (optional for some features)
        oxford_data = data.get("oxford", {})
        oxford_config = OxfordConfig(
            app_id=oxford_data.get("app_id", ""),
            api_key=oxford_data.get("api_key", ""),
        )

        # Load Merriam-Webster config (optional)
        merriam_webster_config = None
        if "merriam_webster" in data:
            mw_data = data["merriam_webster"]
            if "api_key" in mw_data and mw_data["api_key"]:
                merriam_webster_config = MerriamWebsterConfig(api_key=mw_data["api_key"])

        # Load database config with validation
        if "database" not in data:
            raise ValueError(
                f"Missing [database] section in {config_path}\nPlease add database configuration.",
            )

        db_data = data["database"]
        required_keys = ["runtime_url", "test_url", "runtime_tls_required"]
        missing_keys = [key for key in required_keys if key not in db_data]
        if missing_keys:
            raise ValueError(
                f"Missing required [database] keys in {config_path}: {', '.join(missing_keys)}",
            )

        legacy_keys = [
            "production_url",
            "development_url",
            "docker_development_url",
            "local_mongodb_url",
            "native_local_url",
        ]
        present_legacy = [key for key in legacy_keys if key in db_data]
        if present_legacy:
            raise ValueError(
                "Legacy [database] keys are not supported anymore. "
                f"Remove: {', '.join(present_legacy)}"
            )

        runtime_tls_required = db_data["runtime_tls_required"]
        if not isinstance(runtime_tls_required, bool):
            raise ValueError("database.runtime_tls_required must be a boolean")

        # Optional tunnel URLs for local development (SSH tunnel)
        tunnel_url = db_data.get("tunnel_url")
        tunnel_test_url = db_data.get("tunnel_test_url")
        if tunnel_url:
            tunnel_url = str(tunnel_url).strip()
        if tunnel_test_url:
            tunnel_test_url = str(tunnel_test_url).strip()

        database_config = DatabaseConfig(
            runtime_url=str(db_data["runtime_url"]).strip(),
            test_url=str(db_data["test_url"]).strip(),
            runtime_tls_required=runtime_tls_required,
            name=db_data.get("name", "floridify"),
            timeout=db_data.get("timeout", 120),
            max_pool_size=db_data.get("max_pool_size", 100),
            tunnel_url=tunnel_url,
            tunnel_test_url=tunnel_test_url,
        )
        # Skip local-host validation in production Docker (MongoDB is co-located)
        if os.environ.get("ENVIRONMENT") != "production":
            database_config.validate_runtime_target()
            database_config.validate_test_target()

        # Load rate limits with explicit defaults (not silent fallbacks)
        rate_limits_data = data.get("rate_limits", {})
        rate_limits = RateLimits(
            oxford_rps=rate_limits_data.get("oxford_rps", 10.0),
            wiktionary_rps=rate_limits_data.get("wiktionary_rps", 50.0),
            openai_bulk_max_concurrent=rate_limits_data.get("openai_bulk_max_concurrent", 5),
        )

        # Load processing config with explicit defaults
        processing_data = data.get("processing", {})
        processing = ProcessingConfig(
            max_concurrent_words=processing_data.get("max_concurrent_words", 100),
            batch_size=processing_data.get("batch_size", 50),
            retry_attempts=processing_data.get("retry_attempts", 3),
            cache_ttl_hours=processing_data.get("cache_ttl_hours", 24),
            verbose=processing_data.get("verbose", False),
        )

        # Load Google Cloud config (optional)
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

        # Load Semantic Search config (optional)
        semantic_search = None
        if "semantic_search" in data:
            ss_data = data["semantic_search"]
            semantic_search = SemanticSearchConfig(
                use_hnsw=ss_data.get("use_hnsw", True),
                hnsw_m=ss_data.get("hnsw_m", 32),
                hnsw_ef_construction=ss_data.get("hnsw_ef_construction", 200),
                hnsw_ef_search=ss_data.get("hnsw_ef_search", 64),
            )

        return cls(
            openai=openai_config,
            oxford=oxford_config,
            merriam_webster=merriam_webster_config,
            database=database_config,
            rate_limits=rate_limits,
            processing=processing,
            google_cloud=google_cloud,
            semantic_search=semantic_search,
        )
