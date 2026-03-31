"""Configuration management for Floridify."""

from __future__ import annotations

import functools
import os
from pathlib import Path
from urllib.parse import urlparse

import toml
from pydantic import BaseModel, ConfigDict, model_validator

from .paths import get_project_root


class AIGlobalConfig(BaseModel):
    """Global AI configuration."""

    model_config = ConfigDict(frozen=True)

    provider: str = "openai"
    effort: str = "medium"
    max_concurrent_requests: int = 10


class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""

    model_config = ConfigDict(frozen=True)

    api_key: str
    model: str = "gpt-5-mini"
    base_url: str | None = None  # None = api.openai.com; set for proxies
    embedding_model: str = "text-embedding-3-large"


class AnthropicConfig(BaseModel):
    """Anthropic API configuration."""

    model_config = ConfigDict(frozen=True)

    api_key: str
    model: str = "claude-sonnet-4-6"
    base_url: str | None = None  # None = api.anthropic.com
    max_tokens: int = 64000


class LocalModelConfig(BaseModel):
    """Configuration for a single local model endpoint (ollama, vLLM, llama.cpp, etc.)."""

    model_config = ConfigDict(frozen=True)

    model: str  # e.g., "qwen3:32b", "qwen3:8b"
    base_url: str = "http://localhost:11434/v1"  # ollama default
    api_key: str = "not-needed"
    max_tokens: int = 8192
    supports_structured_output: bool = True  # ollama v0.5+, vLLM w/ outlines
    timeout: int = 300


class LocalConfig(BaseModel):
    """Local model configuration with per-tier model routing.

    Allows different models for different capability tiers:
    e.g., Qwen3 32B for HIGH tasks, Qwen3 8B for LOW tasks.
    If medium/low are omitted, they fall back to the next higher tier.
    """

    model_config = ConfigDict(frozen=True)

    high: LocalModelConfig
    medium: LocalModelConfig | None = None
    low: LocalModelConfig | None = None

    def resolve(self, capability: str) -> LocalModelConfig:
        """Get the model config for a capability level, with fallback chain."""
        if capability == "high":
            return self.high
        elif capability == "medium":
            return self.medium or self.high
        else:
            return self.low or self.medium or self.high


class OxfordConfig(BaseModel):
    """Oxford Dictionary API configuration."""

    model_config = ConfigDict(frozen=True)

    app_id: str = ""
    api_key: str = ""


class MerriamWebsterConfig(BaseModel):
    """Merriam-Webster Dictionary API configuration."""

    model_config = ConfigDict(frozen=True)

    api_key: str


class RateLimits(BaseModel):
    """Rate limiting configuration."""

    model_config = ConfigDict(frozen=True)

    oxford_rps: float = 10.0
    wiktionary_rps: float = 50.0
    openai_bulk_max_concurrent: int = 5


class DatabaseConfig(BaseModel):
    """Database configuration.

    Docker containers connect to MongoDB via ``MONGODB_URL`` env var.
    The config file provides ``runtime_url`` and ``test_url`` as fallbacks.
    """

    model_config = ConfigDict(frozen=True)

    runtime_url: str
    test_url: str
    runtime_tls_required: bool
    name: str = "floridify"
    timeout: int = 120
    max_pool_size: int = 100

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_keys(cls, data: dict) -> dict:
        """Reject legacy database configuration keys."""
        if not isinstance(data, dict):
            return data
        legacy_keys = [
            "production_url",
            "development_url",
            "docker_development_url",
            "local_mongodb_url",
            "native_local_url",
            "tunnel_url",
            "tunnel_test_url",
        ]
        present_legacy = [key for key in legacy_keys if key in data]
        if present_legacy:
            raise ValueError(
                "Legacy [database] keys are not supported anymore. "
                f"Remove: {', '.join(present_legacy)}"
            )
        return data

    @staticmethod
    def _in_docker() -> bool:
        return os.path.exists("/.dockerenv")

    def get_url(self, target: str = "runtime") -> str:
        """Return the best URL for a target database.

        Priority: MONGODB_URL env var > config file URL.
        """
        env_url = os.environ.get("MONGODB_URL")
        if env_url and target == "runtime":
            return env_url

        if env_url and target == "test":
            # Derive the test URL from MONGODB_URL by swapping the database name.
            from urllib.parse import urlsplit, urlunsplit

            parts = urlsplit(env_url)
            test_db = self.test_url and urlsplit(self.test_url).path
            if test_db:
                test_parts = parts._replace(path=test_db)
                test_query = urlsplit(self.test_url).query if self.test_url else parts.query
                if test_query:
                    test_parts = test_parts._replace(query=test_query)
                return urlunsplit(test_parts)

        if target == "runtime":
            url = self.runtime_url
        elif target == "test":
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
        cert = project_root / "auth" / "mongodb-ca.pem"
        return cert if cert.exists() else None


class ProcessingConfig(BaseModel):
    """Processing pipeline configuration."""

    model_config = ConfigDict(frozen=True)

    max_concurrent_words: int = 100
    batch_size: int = 50
    retry_attempts: int = 3
    cache_ttl_hours: int = 24
    verbose: bool = False


class SemanticSearchConfig(BaseModel):
    """Semantic search optimization configuration."""

    model_config = ConfigDict(frozen=True)

    use_hnsw: bool = True
    hnsw_m: int = 32
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 64


class Config(BaseModel):
    """Main configuration class."""

    model_config = ConfigDict(frozen=True)

    openai: OpenAIConfig
    oxford: OxfordConfig
    database: DatabaseConfig
    rate_limits: RateLimits
    processing: ProcessingConfig
    ai: AIGlobalConfig | None = None
    anthropic: AnthropicConfig | None = None
    local: LocalConfig | None = None
    merriam_webster: MerriamWebsterConfig | None = None
    semantic_search: SemanticSearchConfig | None = None

    @classmethod
    def from_file(cls, config_path: str | Path | None = None) -> Config:
        """Load configuration from TOML file.

        Results are cached by resolved path — repeated calls with the same
        path (or None → default) return the same frozen Config instance
        without re-reading disk.
        """
        resolved = cls._resolve_config_path(config_path)
        return cls._load_cached(str(resolved))

    @staticmethod
    def _resolve_config_path(config_path: str | Path | None) -> Path:
        """Resolve config_path to an absolute Path, applying defaults."""
        if config_path is None:
            env_path = os.getenv("FLORIDIFY_CONFIG_PATH")
            if env_path:
                return Path(env_path)

            project_root = get_project_root()
            candidate = project_root / "auth" / "config.toml"

            if os.path.exists("/.dockerenv") and not candidate.exists():
                docker_config = Path("/app/auth/config.toml")
                if docker_config.exists():
                    return docker_config
            return candidate

        return Path(config_path)

    @classmethod
    @functools.lru_cache(maxsize=4)
    def _load_cached(cls, config_path_str: str) -> Config:
        """Load and cache Config from a resolved path string."""
        config_path = Path(config_path_str)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Please create {config_path} with your API keys and database configuration.",
            )

        data = toml.load(config_path)

        # Validate required sections
        if "openai" not in data:
            raise ValueError(
                f"Missing [openai] section in {config_path}\n"
                f"Please add OpenAI configuration with api_key field.",
            )

        openai_data = data["openai"]
        if "api_key" not in openai_data or not openai_data["api_key"]:
            raise ValueError(
                f"OpenAI API key missing in {config_path}\n"
                f"Please set 'api_key' in the [openai] section.",
            )

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

        runtime_tls_required = db_data["runtime_tls_required"]
        if not isinstance(runtime_tls_required, bool):
            raise ValueError("database.runtime_tls_required must be a boolean")

        # Pre-process: map [models] keys into openai config
        models_data = data.get("models", {})
        openai_data.setdefault("model", models_data.get("openai_model", "gpt-5-mini"))
        openai_data.setdefault(
            "embedding_model", models_data.get("embedding_model", "text-embedding-3-large")
        )

        # Strip whitespace from URL fields
        for key in ("runtime_url", "test_url"):
            if key in db_data and db_data[key]:
                db_data[key] = str(db_data[key]).strip()

        # Build config dict for model_validate
        config_data: dict = {
            "openai": openai_data,
            "oxford": data.get("oxford", {}),
            "database": db_data,
            "rate_limits": data.get("rate_limits", {}),
            "processing": data.get("processing", {}),
        }

        # Optional sections
        if "ai" in data:
            config_data["ai"] = data["ai"]

        if "anthropic" in data:
            anth_data = data["anthropic"]
            if anth_data.get("api_key"):
                config_data["anthropic"] = anth_data

        if "merriam_webster" in data:
            mw_data = data["merriam_webster"]
            if mw_data.get("api_key"):
                config_data["merriam_webster"] = mw_data

        if "semantic_search" in data:
            config_data["semantic_search"] = data["semantic_search"]

        config = cls.model_validate(config_data)

        # Post-load validation: skip local-host validation in production Docker
        if os.environ.get("ENVIRONMENT") != "production":
            config.database.validate_runtime_target()
            config.database.validate_test_target()

        return config
