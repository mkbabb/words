"""Provider status and monitoring endpoints (read-only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path

from ...caching.core import CacheNamespace, get_global_cache
from ...models.dictionary import DictionaryProvider
from ...models.parameters import ProviderStatusParams
from ...models.responses import ProviderListResponse, ProviderStatusResponse
from ...utils.logging import get_logger
import platform

logger = get_logger(__name__)
router = APIRouter()


def parse_provider_status_params(
    include_rate_limits: bool = True,
    include_cache_stats: bool = True,
) -> ProviderStatusParams:
    """Parse provider status parameters."""
    return ProviderStatusParams(
        provider=None,
        include_rate_limits=include_rate_limits,
        include_cache_stats=include_cache_stats,
    )


@router.get("/providers/status", response_model=ProviderListResponse)
async def get_all_providers_status(
    params: ProviderStatusParams = Depends(parse_provider_status_params),
) -> ProviderListResponse:
    """Get status of all dictionary providers.

    Returns:
    - Provider availability
    - Rate limit information (if enabled)
    - Cache statistics (if enabled)
    - Recent error rates

    Note: Write operations (scraping, configuration) are CLI-only.
    """
    try:
        providers_data = []

        for provider in DictionaryProvider:
            if provider in [
                DictionaryProvider.AI_FALLBACK,
                DictionaryProvider.SYNTHESIS,
            ]:
                # Skip meta-providers
                continue

            status = await _get_provider_status(provider, params)
            providers_data.append(status)

        return ProviderListResponse(
            items=providers_data,
            total=len(providers_data),
            offset=0,
            limit=len(providers_data),
            has_more=False,
        )

    except Exception as e:
        logger.error(f"Failed to get provider statuses: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get provider statuses: {e!s}",
        )


@router.get("/providers/{provider}/status", response_model=ProviderStatusResponse)
async def get_provider_status(
    provider: str = Path(..., description="Provider name"),
    params: ProviderStatusParams = Depends(parse_provider_status_params),
) -> ProviderStatusResponse:
    """Get status of a specific provider."""
    try:
        # Parse provider enum
        try:
            provider_enum = DictionaryProvider(provider.lower())
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

        return await _get_provider_status(provider_enum, params)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider status for {provider}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get provider status: {e!s}",
        )


async def _get_provider_status(
    provider: DictionaryProvider,
    params: ProviderStatusParams,
) -> ProviderStatusResponse:
    """Internal helper to get provider status."""
    # Determine availability based on provider type
    available = True
    if provider == DictionaryProvider.APPLE_DICTIONARY:
        # macOS only

        available = platform.system() == "Darwin"

    # Get cache statistics
    cache_stats = None
    if params.include_cache_stats:
        try:
            cache = await get_global_cache()
            # Get stats for dictionary namespace
            namespace_stats = cache.get_stats(CacheNamespace.DICTIONARY)

            cache_stats = {
                "namespace": CacheNamespace.DICTIONARY.value,
                "hits": namespace_stats.get("hits", 0),
                "misses": namespace_stats.get("misses", 0),
                "evictions": namespace_stats.get("evictions", 0),
                "memory_items": namespace_stats.get("memory_items", 0),
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats for {provider.value}: {e}")
            cache_stats = {"error": str(e)}

    # Rate limit information
    rate_limit = None
    if params.include_rate_limits:
        # Default rate limits by provider
        rate_limits_map = {
            DictionaryProvider.WIKTIONARY: {"requests_per_second": 5.0, "type": "API_STANDARD"},
            DictionaryProvider.OXFORD: {"requests_per_second": 2.0, "type": "API_CONSERVATIVE"},
            DictionaryProvider.MERRIAM_WEBSTER: {
                "requests_per_second": 2.0,
                "type": "API_CONSERVATIVE",
            },
            DictionaryProvider.FREE_DICTIONARY: {"requests_per_second": 10.0, "type": "API_FAST"},
            DictionaryProvider.WORDHIPPO: {
                "requests_per_second": 1.0,
                "type": "SCRAPER_RESPECTFUL",
            },
            DictionaryProvider.APPLE_DICTIONARY: {"requests_per_second": 100.0, "type": "LOCAL"},
        }
        rate_limit = rate_limits_map.get(provider, {"requests_per_second": 1.0, "type": "UNKNOWN"})

    return ProviderStatusResponse(
        provider=provider.value,
        available=available,
        rate_limit=rate_limit,
        cache_stats=cache_stats,
        last_request=None,  # Would need tracking system
        error_rate=None,  # Would need error tracking
    )
