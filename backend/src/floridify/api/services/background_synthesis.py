"""Background synthesis deduplication service.

Ensures that only one background AI synthesis runs per word at a time,
preventing duplicate work when multiple requests arrive for the same
unsynthesized entry.
"""

from __future__ import annotations

import asyncio

from ...core.lookup_pipeline import lookup_word_pipeline
from ...models.parameters import LookupParams
from ...utils.logging import get_logger

logger = get_logger(__name__)


class BackgroundSynthesisService:
    """Deduplicates concurrent background synthesis requests per word."""

    def __init__(self) -> None:
        self._in_flight: set[str] = set()
        self._lock: asyncio.Lock = asyncio.Lock()

    async def synthesize(self, word: str, params: LookupParams) -> None:
        """Fire-and-forget AI synthesis using existing provider data in the DB."""
        async with self._lock:
            if word in self._in_flight:
                return
            self._in_flight.add(word)

        try:
            await lookup_word_pipeline(
                word=word,
                providers=params.providers,
                languages=params.languages,
                no_ai=False,
                skip_search=True,
                state_tracker=None,
            )
            logger.info(f"Background synthesis complete for '{word}'")
        except Exception as e:
            logger.warning(f"Background synthesis failed for '{word}': {e}")
        finally:
            async with self._lock:
                self._in_flight.discard(word)


_service: BackgroundSynthesisService | None = None


def get_background_synthesis_service() -> BackgroundSynthesisService:
    """Get or create the singleton BackgroundSynthesisService."""
    global _service
    if _service is None:
        _service = BackgroundSynthesisService()
    return _service
