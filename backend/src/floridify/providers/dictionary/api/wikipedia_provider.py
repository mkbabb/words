"""Wikipedia/DBpedia provider for encyclopedic enrichment.

Fetches structured extracts from Wikipedia via the MediaWiki API.
Not a traditional dictionary provider — enriches the Fact, Etymology,
and domain classification data. CC BY-SA 3.0 licensed.
"""

from __future__ import annotations

from typing import Any

import httpx

from ....core.state_tracker import StateTracker
from ....models.dictionary import DictionaryProvider, Word
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ..core import DictionaryConnector
from ..models import DictionaryProviderEntry

logger = get_logger(__name__)

_WIKI_API = "https://en.wikipedia.org/w/api.php"
_USER_AGENT = "Floridify/1.0 (https://github.com/user/floridify)"


class WikipediaConnector(DictionaryConnector):
    """Wikipedia enrichment provider — facts, domain, etymology cross-reference."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.API_STANDARD.value)
        super().__init__(provider=DictionaryProvider.WIKIPEDIA, config=config)

    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
        **kwargs: Any,
    ) -> DictionaryProviderEntry | None:
        """Fetch Wikipedia extract and categories for a word."""
        try:
            extract = await self._fetch_extract(word)
            if extract is None:
                return None

            text = extract.get("extract", "")
            title = extract.get("title", word)
            categories = await self._fetch_categories(title)

            # Build facts from the extract (first 2-3 sentences)
            facts = self._extract_facts(text, word)

            # Infer domain from categories
            domain = self._infer_domain(categories)

            return DictionaryProviderEntry(
                word=word,
                provider=DictionaryProvider.WIKIPEDIA.value,
                definitions=[],  # Wikipedia is not a dictionary — no definitions
                provider_metadata={
                    "wikipedia_title": title,
                    "extract": text[:2000],  # Truncate for storage
                    "categories": categories[:20],
                    "facts": facts,
                    "inferred_domain": domain,
                },
            )
        except Exception as e:
            logger.error(f"Wikipedia fetch failed for '{word}': {e}")
            return None

    async def _fetch_extract(self, word: str) -> dict[str, Any] | None:
        """Fetch the Wikipedia page extract via TextExtracts API."""
        params = {
            "action": "query",
            "titles": word,
            "prop": "extracts",
            "exintro": "true",  # Only the intro section
            "explaintext": "true",  # Plain text, no HTML
            "redirects": "1",
            "format": "json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                _WIKI_API,
                params=params,
                headers={"User-Agent": _USER_AGENT},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                return None  # Page not found
            return page

        return None

    async def _fetch_categories(self, title: str) -> list[str]:
        """Fetch Wikipedia categories for domain inference."""
        params = {
            "action": "query",
            "titles": title,
            "prop": "categories",
            "cllimit": "20",
            "clshow": "!hidden",  # Exclude hidden maintenance categories
            "format": "json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    _WIKI_API,
                    params=params,
                    headers={"User-Agent": _USER_AGENT},
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()

            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                cats = page.get("categories", [])
                return [
                    c["title"].replace("Category:", "")
                    for c in cats
                    if "title" in c
                ]
        except Exception as e:
            logger.debug(f"Failed to fetch Wikipedia categories: {e}")

        return []

    def _extract_facts(self, text: str, word: str) -> list[str]:
        """Extract interesting facts from the Wikipedia extract.

        Splits the intro text into sentences and selects the most
        informative ones (avoiding generic openings).
        """
        if not text:
            return []

        sentences = [s.strip() for s in text.split(".") if s.strip()]
        facts: list[str] = []

        for sentence in sentences[:5]:  # First 5 sentences max
            # Skip very short or generic sentences
            if len(sentence) < 20:
                continue
            # Ensure it ends with a period
            fact = sentence.rstrip(".") + "."
            facts.append(fact)

        return facts[:3]  # Max 3 facts

    def _infer_domain(self, categories: list[str]) -> str | None:
        """Infer subject domain from Wikipedia categories."""
        category_text = " ".join(categories).lower()

        domain_keywords: dict[str, list[str]] = {
            "biology": ["biology", "species", "organism", "genus", "animal", "plant"],
            "medicine": ["medicine", "disease", "medical", "health", "drug"],
            "computing": ["computing", "software", "programming", "computer", "algorithm"],
            "finance": ["financial", "banking", "investment", "economics", "stock", "fiscal"],
            "music": ["music", "musician", "album", "song", "composer"],
            "physics": ["physics", "quantum", "particle", "energy"],
            "chemistry": ["chemistry", "chemical", "element", "compound"],
            "mathematics": ["mathematics", "theorem", "algebra", "geometry"],
            "law": ["law", "legal", "court", "legislation"],
            "philosophy": ["philosophy", "philosopher", "ethics"],
            "linguistics": ["linguistics", "language", "grammar", "phonology"],
            "history": ["history", "historical", "century", "ancient"],
            "geography": ["geography", "country", "city", "region"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in category_text for kw in keywords):
                return domain

        return None

    async def _fetch_provider_entry(
        self,
        word: Word,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryProviderEntry | None:
        return await self._fetch_from_provider(word.text, state_tracker)

    async def close(self) -> None:
        pass
