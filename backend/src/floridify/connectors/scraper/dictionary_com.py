"""Dictionary.com web scraper connector.

Scrapes dictionary data from Dictionary.com website.
No API key required, but respects rate limiting.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from beanie import PydanticObjectId
from bs4 import BeautifulSoup, Tag

from ...caching.decorators import cached_api_call
from ...core.state_tracker import Stages, StateTracker
from ...models import (
    Definition,
    Etymology,
    Example,
    Pronunciation,
    ProviderData,
    Word,
)
from ...models.definition import DictionaryProvider
from ...utils.logging import get_logger
from ..base import DictionaryConnector
from ..utils import RespectfulHttpClient

logger = get_logger(__name__)


class DictionaryComConnector(DictionaryConnector):
    """Connector for Dictionary.com web scraping.
    
    Dictionary.com provides:
    - Multiple definitions with usage notes
    - IPA and syllabic pronunciations
    - Etymology and word origin
    - Synonyms and antonyms
    - Example sentences
    - Word difficulty level
    """

    def __init__(self, rate_limit: float = 1.5) -> None:
        """Initialize Dictionary.com connector.
        
        Args:
            rate_limit: Maximum requests per second (default: 1.5, respectful for scraping)
        """
        super().__init__(rate_limit=rate_limit)
        self.base_url = "https://www.dictionary.com/browse"
        self.thesaurus_url = "https://www.thesaurus.com/browse"
        self.http_client = RespectfulHttpClient(
            base_url=self.base_url,
            rate_limit=rate_limit,
            timeout=30.0,
        )

    @property
    def provider_name(self) -> DictionaryProvider:
        """Return the provider name."""
        return DictionaryProvider.DICTIONARY_COM

    @property
    def provider_version(self) -> str:
        """Version of the Dictionary.com scraper implementation."""
        return "1.0.0"

    async def __aenter__(self) -> DictionaryComConnector:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.session.aclose()

    @cached_api_call(ttl_hours=168.0, key_prefix="dictionary_com")  # 7 days cache for scraped content
    async def _fetch_from_web(self, word: str) -> str | None:
        """Fetch word page from Dictionary.com.
        
        Args:
            word: The word to look up
            
        Returns:
            HTML content or None if not found
        """
        await self._enforce_rate_limit()
        
        url = f"{word}"
        
        try:
            response = await self.http_client.get(url)
            
            if response.status_code == 404:
                logger.debug(f"Word '{word}' not found on Dictionary.com")
                return None
            
            response.raise_for_status()
            return response.text
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Dictionary.com: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from Dictionary.com: {e}")
            return None

    def _parse_pronunciation(self, soup: BeautifulSoup, word_id: PydanticObjectId) -> Pronunciation | None:
        """Parse pronunciation data from page.
        
        Args:
            soup: BeautifulSoup parsed HTML
            
        Returns:
            Pronunciation object or None
        """
        try:
            # Look for IPA pronunciation
            ipa_elem = soup.find("span", class_="pron-ipa-content")
            ipa = ipa_elem.text.strip() if ipa_elem else None
            
            # Look for syllabic pronunciation
            syllabic_elem = soup.find("span", class_="pron-spell-content")
            phonetic = syllabic_elem.text.strip() if syllabic_elem else None
            
            # Extract syllables if available
            syllables = []
            if phonetic and "·" in phonetic:
                syllables = phonetic.split("·")
            elif phonetic and "-" in phonetic:
                syllables = phonetic.split("-")
            
            if ipa or phonetic:
                return Pronunciation(
                    word_id=word_id,
                    ipa=ipa or "..",
                    phonetic=phonetic or "..",
                    syllables=syllables,
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing pronunciation: {e}")
            return None

    def _parse_etymology(self, soup: BeautifulSoup) -> Etymology | None:
        """Parse etymology data from page.
        
        Args:
            soup: BeautifulSoup parsed HTML
            
        Returns:
            Etymology object or None
        """
        try:
            # Look for origin section
            origin_section = soup.find("section", {"data-type": "word-origin"})
            if not origin_section:
                # Alternative: look for etymology in definition sections
                origin_elem = soup.find("div", class_="etymology-root")
                if origin_elem and isinstance(origin_elem, Tag):
                    origin_text = origin_elem.get_text(separator=" ", strip=True)
                    return Etymology(
                        text=origin_text,
                        origin_language="en",
                        root_words=[],
                    )
                return None
            
            # Extract origin text
            if isinstance(origin_section, Tag):
                origin_content = origin_section.find("div", class_="default-content")
            else:
                origin_content = None
            if origin_content is not None and isinstance(origin_content, Tag):
                origin_text = origin_content.get_text(separator=" ", strip=True)
                
                # Clean up the text
                origin_text = re.sub(r"\s+", " ", origin_text)
                origin_text = origin_text.replace("ORIGIN OF", "").strip()
                
                if origin_text:
                    return Etymology(
                        text=origin_text,
                        origin_language="en",
                        root_words=[],
                    )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing etymology: {e}")
            return None

    async def _parse_definitions(self, soup: BeautifulSoup, word_id: PydanticObjectId) -> list[Definition]:
        """Parse definitions from page.
        
        Args:
            soup: BeautifulSoup parsed HTML
            word_id: ID of the word being defined
            
        Returns:
            List of Definition objects
        """
        definitions = []
        
        try:
            # Find all definition sections
            def_sections = soup.find_all("section", {"data-type": "word-definitions"})
            
            for section in def_sections:
                # Get part of speech
                pos_elem = section.find("span", class_="luna-pos")
                if not pos_elem:
                    continue
                    
                pos_raw = pos_elem.text.strip()
                # Clean and normalize part of speech directly
                part_of_speech = pos_raw.lower().strip()
                part_of_speech = re.sub(r"[,;].*", "", part_of_speech)  # Remove trailing info
                if not part_of_speech:
                    part_of_speech = "unknown"
                
                # Find definition groups
                def_groups = section.find_all("div", class_="css-1o58fj8")
                
                for idx, def_group in enumerate(def_groups, 1):
                    # Get definition text
                    def_content = def_group.find("div", class_="default-content")
                    if not def_content:
                        continue
                    
                    definition_text = def_content.get_text(separator=" ", strip=True)
                    if not definition_text:
                        continue
                    
                    # Clean definition text
                    definition_text = re.sub(r"\s+", " ", definition_text)
                    definition_text = re.sub(r"^\d+\.", "", definition_text).strip()
                    
                    # Extract example texts (will create Example objects after definition is saved)
                    example_texts = []
                    example_elems = def_group.find_all("div", class_="luna-example")
                    for ex_elem in example_elems:
                        ex_text = ex_elem.get_text(strip=True)
                        if ex_text:
                            example_texts.append(ex_text)
                    
                    # Extract synonyms
                    synonyms = []
                    syn_section = def_group.find("div", class_="css-1gyuw4i")
                    if syn_section:
                        syn_links = syn_section.find_all("a")
                        synonyms = [link.text.strip() for link in syn_links if link.text.strip()]
                    
                    # Create definition
                    definition = Definition(
                        word_id=word_id,
                        part_of_speech=part_of_speech,
                        text=definition_text,
                        sense_number=str(idx),
                        synonyms=synonyms[:10],  # Limit to 10 synonyms
                    )
                    
                    # Save definition to get ID
                    await definition.save()
                    
                    # Now create and save examples with the definition ID
                    example_ids = []
                    if definition.id is not None:
                        for ex_text in example_texts[:3]:  # Limit to 3 examples
                            example = Example(
                                definition_id=definition.id,
                                text=ex_text,
                                type="literature",
                            )
                            await example.save()
                            if example.id is not None:
                                example_ids.append(example.id)
                    
                    # Update definition with example IDs
                    definition.example_ids = example_ids
                    await definition.save()
                    
                    definitions.append(definition)
            
        except Exception as e:
            logger.error(f"Error parsing definitions: {e}")
        
        return definitions

    async def _fetch_from_provider(
        self,
        word_obj: Word,
        state_tracker: StateTracker | None = None,
    ) -> ProviderData | None:
        """Fetch definition from Dictionary.com.
        
        Args:
            word_obj: Word object to look up
            state_tracker: Optional state tracker for progress
            
        Returns:
            ProviderData with definitions, pronunciation, and etymology
        """
        try:
            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_START)
            
            # Fetch HTML from website
            html_content = await self._fetch_from_web(word_obj.text)
            if not html_content:
                return None
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Check that word_obj has been saved and has an ID
            if not word_obj.id:
                raise ValueError(f"Word {word_obj.text} must be saved before processing")
            
            # Parse components
            definitions = await self._parse_definitions(soup, word_obj.id)
            if not definitions:
                logger.warning(f"No definitions parsed for '{word_obj.text}'")
                return None
            
            pronunciation = self._parse_pronunciation(soup, word_obj.id)
            etymology = self._parse_etymology(soup)
            
            # Enhance with thesaurus.com data (delays handled by RespectfulHttpClient)
            thesaurus_synonyms, thesaurus_antonyms = await self._fetch_thesaurus_data(word_obj.text)
            await self._enhance_definitions_with_thesaurus(definitions, thesaurus_synonyms, thesaurus_antonyms)
            
            # Get definition IDs (already saved in parsing)
            definition_ids = [definition.id for definition in definitions if definition.id is not None]
            
            # Save pronunciation if exists
            pronunciation_id = None
            if pronunciation:
                await pronunciation.save()
                pronunciation_id = pronunciation.id
            
            # Create provider data
            provider_data = ProviderData(
                word_id=word_obj.id,
                provider=self.provider_name,
                definition_ids=definition_ids,
                pronunciation_id=pronunciation_id,
                etymology=etymology,
                raw_data={"url": f"{self.base_url}/{word_obj.text}"},
            )
            
            if state_tracker:
                await state_tracker.update_stage(Stages.PROVIDER_FETCH_COMPLETE)
            
            return provider_data
            
        except Exception as e:
            logger.error(f"Error fetching from Dictionary.com: {e}")
            if state_tracker:
                await state_tracker.update_error(str(e), Stages.PROVIDER_FETCH_ERROR)
            return None

    async def _fetch_thesaurus_data(self, word: str) -> tuple[list[str], list[str]]:
        """Fetch synonyms and antonyms from thesaurus.com.
        
        Args:
            word: The word to look up
            
        Returns:
            Tuple of (synonyms, antonyms)
        """
        synonyms = []
        antonyms = []
        
        # Use a separate client for thesaurus.com to avoid rate limiting conflicts
        thesaurus_client = RespectfulHttpClient(
            base_url=self.thesaurus_url,
            rate_limit=self.rate_limit,
            timeout=30.0,
        )
        
        try:
            # Thesaurus.com URL pattern
            url = f"{word.lower()}"
            response = await thesaurus_client.get(url)
            
            if response.status_code == 404:
                logger.debug(f"Word '{word}' not found on thesaurus.com")
                return synonyms, antonyms
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find synonyms section
            # Thesaurus.com uses various structures, look for common ones
            synonym_containers = soup.find_all(["div", "section"], class_=[
                "css-1lc0dpe", "synonyms-container", "css-ixn2qe", "css-1gyuw4i"
            ])
            
            # Also look for synonym links directly
            synonym_links = soup.find_all("a", href=lambda x: x and "/browse/" in x)
            
            # Extract synonyms from containers
            for container in synonym_containers:
                links = container.find_all("a")
                for link in links[:12]:  # Limit to 12 synonyms per container
                    text = link.text.strip()
                    if text and text.isalpha() and len(text) > 1:
                        synonyms.append(text)
            
            # Extract synonyms from direct links
            for link in synonym_links[:15]:  # Limit to 15 total synonym links
                text = link.text.strip()
                if text and text.isalpha() and len(text) > 1 and text.lower() != word.lower():
                    synonyms.append(text)
            
            # Look for antonyms in text content for "Antonyms" sections
            for elem in soup.find_all(["h2", "h3", "div"]):
                if elem.text and "antonym" in elem.text.lower():
                    # Find links in the next siblings or parent
                    parent = elem.parent if elem.parent else elem
                    links = parent.find_all("a")[:8]  # Limit to 8 antonyms
                    for link in links:
                        text = link.text.strip()
                        if text and text.isalpha() and len(text) > 1:
                            antonyms.append(text)
            
            # Remove duplicates while preserving order
            synonyms = list(dict.fromkeys(synonyms))[:20]  # Top 20 synonyms
            antonyms = list(dict.fromkeys(antonyms))[:10]   # Top 10 antonyms
            
            logger.debug(f"Fetched {len(synonyms)} synonyms and {len(antonyms)} antonyms for '{word}' from thesaurus.com")
            return synonyms, antonyms
            
        except Exception as e:
            logger.error(f"Error fetching thesaurus data for '{word}': {e}")
            return synonyms, antonyms
        finally:
            await thesaurus_client.close()
    
    async def _enhance_definitions_with_thesaurus(
        self, 
        definitions: list[Definition], 
        thesaurus_synonyms: list[str], 
        thesaurus_antonyms: list[str]
    ) -> None:
        """Enhance definitions with thesaurus.com synonyms and antonyms.
        
        Args:
            definitions: List of definitions to enhance
            thesaurus_synonyms: Synonyms from thesaurus.com
            thesaurus_antonyms: Antonyms from thesaurus.com
        """
        try:
            for i, definition in enumerate(definitions):
                # Combine existing synonyms with thesaurus ones
                existing_synonyms = definition.synonyms or []
                
                # Distribute thesaurus synonyms across definitions
                start_idx = (i * len(thesaurus_synonyms)) // len(definitions) if definitions else 0
                end_idx = ((i + 1) * len(thesaurus_synonyms)) // len(definitions) if definitions else len(thesaurus_synonyms)
                additional_synonyms = thesaurus_synonyms[start_idx:end_idx]
                
                # Combine and deduplicate synonyms
                all_synonyms = existing_synonyms + additional_synonyms
                unique_synonyms = []
                seen = set()
                for syn in all_synonyms:
                    if syn.lower() not in seen:
                        seen.add(syn.lower())
                        unique_synonyms.append(syn)
                
                definition.synonyms = unique_synonyms[:15]  # Limit to 15 total
                
                # Add antonyms (distribute across definitions)
                start_idx = (i * len(thesaurus_antonyms)) // len(definitions) if definitions else 0
                end_idx = ((i + 1) * len(thesaurus_antonyms)) // len(definitions) if definitions else len(thesaurus_antonyms)
                definition.antonyms = thesaurus_antonyms[start_idx:end_idx]
                
                # Save updated definition
                await definition.save()
                
        except Exception as e:
            logger.error(f"Error enhancing definitions with thesaurus data: {e}")
    
    async def close(self) -> None:
        """Close the HTTP session."""
        await self.http_client.close()


