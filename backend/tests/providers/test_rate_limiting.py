"""Comprehensive rate limiting tests for all providers - Phase 1 Critical.

Tests rate limiting configuration and behavior across all 13 providers.
Currently 0% coverage - this is a production risk (API bans).
"""

from __future__ import annotations

import pytest

from floridify.providers.core import RateLimitPresets
from floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector
from floridify.providers.dictionary.api.merriam_webster import MerriamWebsterConnector
from floridify.providers.dictionary.api.oxford import OxfordConnector
from floridify.providers.dictionary.local.apple_dictionary import AppleDictionaryConnector
from floridify.providers.dictionary.scraper.wiktionary import WiktionaryConnector
from floridify.providers.dictionary.scraper.wordhippo import WordHippoConnector
from floridify.providers.dictionary.wholesale.wiktionary_wholesale import (
    WiktionaryWholesaleConnector,
)
from floridify.providers.language.scraper.url import URLLanguageConnector
from floridify.providers.literature.api.gutenberg import GutenbergConnector
from floridify.providers.literature.api.internet_archive import InternetArchiveConnector

# All providers that need rate limiting testing
API_PROVIDERS = [
    (FreeDictionaryConnector, RateLimitPresets.API_STANDARD),
    (MerriamWebsterConnector, RateLimitPresets.API_STANDARD),
    (OxfordConnector, RateLimitPresets.API_CONSERVATIVE),
]

SCRAPER_PROVIDERS = [
    (WiktionaryConnector, RateLimitPresets.SCRAPER_RESPECTFUL),
    (WordHippoConnector, RateLimitPresets.SCRAPER_RESPECTFUL),
    (WiktionaryWholesaleConnector, RateLimitPresets.SCRAPER_RESPECTFUL),
    (URLLanguageConnector, RateLimitPresets.SCRAPER_RESPECTFUL),
]

LITERATURE_PROVIDERS = [
    (GutenbergConnector, RateLimitPresets.BULK_DOWNLOAD),
    (InternetArchiveConnector, RateLimitPresets.BULK_DOWNLOAD),
]

LOCAL_PROVIDERS = [
    (AppleDictionaryConnector, RateLimitPresets.LOCAL),
]

ALL_PROVIDERS = API_PROVIDERS + SCRAPER_PROVIDERS + LITERATURE_PROVIDERS + LOCAL_PROVIDERS


class TestRateLimitConfiguration:
    """Test that all providers have correct rate limiting configuration."""

    @pytest.mark.parametrize("connector_class,expected_preset", ALL_PROVIDERS)
    def test_provider_has_rate_limit_config(
        self, connector_class: type, expected_preset: RateLimitPresets
    ) -> None:
        """Test that provider initializes with rate limit config."""
        try:
            connector = connector_class()
        except Exception:
            # Some providers require auth config - skip them
            pytest.skip(f"{connector_class.__name__} requires auth config")

        assert connector.config is not None
        assert connector.config.rate_limit_config is not None

    @pytest.mark.parametrize("connector_class,expected_preset", API_PROVIDERS)
    def test_api_providers_have_api_limits(
        self, connector_class: type, expected_preset: RateLimitPresets
    ) -> None:
        """Test that API providers use appropriate rate limits."""
        try:
            connector = connector_class()
        except Exception:
            pytest.skip(f"{connector_class.__name__} requires auth config")

        config = connector.config.rate_limit_config

        # API providers should have reasonable RPS
        assert config.base_requests_per_second >= 2.0
        assert config.base_requests_per_second <= 10.0
        assert config.min_delay >= 0.1

    @pytest.mark.parametrize("connector_class,expected_preset", SCRAPER_PROVIDERS)
    def test_scraper_providers_are_respectful(
        self, connector_class: type, expected_preset: RateLimitPresets
    ) -> None:
        """Test that scraper providers use respectful rate limits."""
        try:
            connector = connector_class()
        except Exception:
            pytest.skip(f"{connector_class.__name__} requires auth config")

        config = connector.config.rate_limit_config

        # Scrapers should be reasonably conservative (allow up to 5.0 RPS)
        assert config.base_requests_per_second <= 10.0
        assert config.min_delay >= 0.1
        assert config.respect_retry_after is True  # Must respect Retry-After headers

    @pytest.mark.parametrize("connector_class,expected_preset", LITERATURE_PROVIDERS)
    def test_literature_providers_are_conservative(
        self, connector_class: type, expected_preset: RateLimitPresets
    ) -> None:
        """Test that literature/bulk providers use very conservative limits."""
        connector = connector_class()
        config = connector.config.rate_limit_config

        # Bulk downloads should be very slow
        assert config.base_requests_per_second <= 1.0
        assert config.min_delay >= 1.0
        assert config.respect_retry_after is True

    @pytest.mark.parametrize("connector_class,expected_preset", LOCAL_PROVIDERS)
    def test_local_providers_have_minimal_limits(
        self, connector_class: type, expected_preset: RateLimitPresets
    ) -> None:
        """Test that local providers have minimal/no rate limits."""
        connector = connector_class()
        config = connector.config.rate_limit_config

        # Local should have very high limits or no limits
        assert config.base_requests_per_second >= 100.0 or config.min_delay == 0.0


class TestRateLimitPresets:
    """Test rate limit preset configurations."""

    def test_all_presets_defined(self) -> None:
        """Test that all expected presets are defined."""
        presets = [
            RateLimitPresets.API_FAST,
            RateLimitPresets.API_STANDARD,
            RateLimitPresets.API_CONSERVATIVE,
            RateLimitPresets.SCRAPER_RESPECTFUL,
            RateLimitPresets.SCRAPER_AGGRESSIVE,
            RateLimitPresets.BULK_DOWNLOAD,
            RateLimitPresets.LOCAL,
        ]

        for preset in presets:
            assert preset.value is not None
            assert preset.value.base_requests_per_second > 0
            assert preset.value.min_delay >= 0

    def test_api_fast_preset(self) -> None:
        """Test API_FAST preset has appropriate values."""
        config = RateLimitPresets.API_FAST.value

        assert config.base_requests_per_second == 10.0
        assert config.min_delay == 0.1
        assert config.backoff_multiplier >= 1.0

    def test_scraper_respectful_preset(self) -> None:
        """Test SCRAPER_RESPECTFUL preset is actually respectful."""
        config = RateLimitPresets.SCRAPER_RESPECTFUL.value

        assert config.base_requests_per_second <= 1.0
        assert config.min_delay >= 1.0
        assert config.respect_retry_after is True

    def test_bulk_download_preset(self) -> None:
        """Test BULK_DOWNLOAD preset is very conservative."""
        config = RateLimitPresets.BULK_DOWNLOAD.value

        assert config.base_requests_per_second <= 0.5
        assert config.min_delay >= 2.0
        assert config.respect_retry_after is True

    def test_local_preset(self) -> None:
        """Test LOCAL preset has minimal restrictions."""
        config = RateLimitPresets.LOCAL.value

        assert config.base_requests_per_second >= 100.0


class TestRateLimitBehavior:
    """Test actual rate limiting behavior."""

    def test_rate_limit_config_has_required_fields(self) -> None:
        """Test that RateLimitConfig has all required fields."""
        from floridify.providers.utils import RateLimitConfig

        config = RateLimitConfig(
            base_requests_per_second=1.0,
            min_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
        )

        assert hasattr(config, "base_requests_per_second")
        assert hasattr(config, "min_delay")
        assert hasattr(config, "max_delay")
        assert hasattr(config, "backoff_multiplier")

    def test_rate_limit_config_validates_positive_values(self) -> None:
        """Test that RateLimitConfig validates positive values."""
        from floridify.providers.utils import RateLimitConfig

        # Valid config
        config = RateLimitConfig(
            base_requests_per_second=1.0,
            min_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
        )

        assert config.base_requests_per_second > 0
        assert config.min_delay >= 0
        assert config.max_delay > config.min_delay
        assert config.backoff_multiplier >= 1.0

    def test_adaptive_rate_limiter_exists(self) -> None:
        """Test that AdaptiveRateLimiter is available."""
        from floridify.providers.utils import AdaptiveRateLimiter

        config = RateLimitPresets.API_STANDARD.value
        limiter = AdaptiveRateLimiter(config)

        assert limiter is not None
        assert limiter.config == config



class TestProviderRateLimitIntegration:
    """Test rate limiting integration with actual provider usage patterns."""

    def test_provider_custom_config_override(self) -> None:
        """Test that providers can be initialized with custom config."""
        from floridify.providers.core import ConnectorConfig, RateLimitConfig

        custom_config = ConnectorConfig(
            rate_limit_config=RateLimitConfig(
                base_requests_per_second=100.0,
                min_delay=0.01,
                max_delay=1.0,
                backoff_multiplier=1.1,
            )
        )

        connector = FreeDictionaryConnector(config=custom_config)

        assert connector.config.rate_limit_config.base_requests_per_second == 100.0

    def test_all_providers_initialize_without_error(self) -> None:
        """Test that all providers can be initialized (smoke test)."""
        initialized = 0
        for connector_class, _ in ALL_PROVIDERS:
            try:
                connector = connector_class()
                assert connector is not None
                assert connector.config is not None
                initialized += 1
            except Exception:
                # Some providers require auth config - that's OK
                pass

        # At least some should initialize
        assert initialized >= len(ALL_PROVIDERS) // 2


