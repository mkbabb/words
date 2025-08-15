"""WordHippo web scraper connector."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from bs4 import BeautifulSoup

from ....core.state_tracker import StateTracker
from ....models import (
    Definition,
    Etymology,
    Example,
    Pronunciation,
    Word,
)
from ....models.dictionary import DictionaryEntry, DictionaryProvider
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ...utils import respectful_scraper
from ..core import DictionaryConnector

logger = get_logger(__name__)


class WordHippoConnector(DictionaryConnector):
    """WordHippo dictionary scraper connector."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        """Initialize WordHippo connector.

        Args:
            config: Connector configuration

        """
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.SCRAPER_RESPECTFUL.value)
        super().__init__(provider=DictionaryProvider.WORDHIPPO, config=config)
        self.base_url = "https://www.wordhippo.com"
        self.rate_config = self.config.rate_limit_config

    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryEntry | None:
        """Fetch definition data for a word from WordHippo.

        Args:
            word: The word text to look up
            state_tracker: Optional state tracker for progress updates

        Returns:
            DictionaryEntry if successful, None if not found or error

        """
        try:
            # WordHippo URLs follow pattern: /what-is/the-meaning-of-the-word/WORD.html
            url = f"{self.base_url}/what-is/the-meaning-of-the-word/{word.lower()}.html"

            async with respectful_scraper("wordhippo", self.rate_config) as client:
                response = await client.get(url)

                if response.status_code == 404:
                    logger.debug(f"Word '{word}' not found on WordHippo")
                    return None

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Get or create word object to get ID
            word_obj = await Word.find_one({"text": word})
            if not word_obj:
                word_obj = Word(text=word)  # Language defaults to ENGLISH
                await word_obj.save()

            # Extract all components
            if word_obj.id is None:
                raise ValueError(f"Word {word} must be saved before processing")

            definitions = await self._extract_definitions(soup, word_obj.id)
            pronunciation = await self._extract_pronunciation(soup, word_obj.id)
            etymology = await self._extract_etymology(soup)

            # Fetch enhanced data from additional URLs (delays handled by RespectfulHttpClient)
            synonyms = await self._fetch_synonyms(word)
            antonyms = await self._fetch_antonyms(word)
            sentences = await self._fetch_sentences(word)

            # Enhance definitions with synonyms, antonyms, and additional examples
            await self._enhance_definitions_with_data(definitions, synonyms, antonyms, sentences)

            # Save pronunciation if found
            if pronunciation:
                await pronunciation.save()

            # Create raw data for storage
            raw_data = {
                "url": url,
                "html_length": len(response.text),
                "definitions_count": len(definitions),
                "synonyms_count": len(synonyms),
                "antonyms_count": len(antonyms),
                "sentences_count": len(sentences),
            }

            # word_obj.id is guaranteed to be not None after save()
            return DictionaryEntry(
                word_id=word_obj.id,
                provider=DictionaryProvider.WORDHIPPO,
                definition_ids=[d.id for d in definitions if d.id is not None],
                pronunciation_id=pronunciation.id if pronunciation else None,
                etymology=etymology,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.error(f"Error fetching {word} from WordHippo: {e}")
            return None

    async def _extract_definitions(
        self,
        soup: BeautifulSoup,
        word_id: PydanticObjectId,
    ) -> list[Definition]:
        """Extract definitions from WordHippo HTML.

        Args:
            soup: Parsed HTML content
            word_id: ID of the word these definitions belong to

        Returns:
            List of Definition objects

        """
        definitions = []

        try:
            # WordHippo structures definitions in div.relatedwords sections
            # Look for sections with class "wordtype" followed by definitions
            word_type_sections = soup.find_all("div", class_="wordtype")

            for section in word_type_sections:
                # Extract part of speech from the wordtype div
                part_of_speech_elem = section.find("span", class_="partofspeech")
                if not part_of_speech_elem:
                    continue

                pos_text = part_of_speech_elem.text.strip().lower()
                # Normalize common abbreviations directly
                pos_mappings = {
                    "n": "noun",
                    "v": "verb",
                    "adj": "adjective",
                    "adv": "adverb",
                    "prep": "preposition",
                    "conj": "conjunction",
                    "pron": "pronoun",
                    "interj": "interjection",
                    "exclamation": "interjection",
                }
                part_of_speech = pos_mappings.get(pos_text, pos_text)

                # Find definition list that follows this wordtype
                parent = section.parent
                if not parent:
                    continue

                # Look for definition divs within the parent container
                def_divs = parent.find_all("div", class_="defv2relatedwords")

                for idx, def_div in enumerate(def_divs):
                    def_text = def_div.text.strip()
                    if not def_text:
                        continue

                    # Create definition
                    definition = Definition(
                        word_id=word_id,
                        part_of_speech=part_of_speech,
                        text=def_text,
                        sense_number=f"{idx + 1}",
                        synonyms=[],
                        antonyms=[],
                        example_ids=[],
                    )

                    # Save definition to get ID
                    await definition.save()

                    # Look for examples in nearby elements
                    if definition.id is not None:
                        examples = await self._extract_examples_for_definition(
                            parent,
                            definition.id,
                        )
                        if examples:
                            definition.example_ids = [ex.id for ex in examples if ex.id]
                            await definition.save()

                    definitions.append(definition)

            # Fallback: if no structured definitions found, try simpler extraction
            if not definitions:
                # Look for any definition-like content
                meaning_divs = soup.find_all("div", class_=["defv2relatedwords", "wordDefinition"])
                for idx, div in enumerate(meaning_divs):
                    text = div.text.strip()
                    if text and len(text) > 10:  # Filter out very short text
                        definition = Definition(
                            word_id=word_id,
                            part_of_speech="noun",  # Default
                            text=text,
                            sense_number=f"{idx + 1}",
                            synonyms=[],
                            antonyms=[],
                            example_ids=[],
                        )
                        await definition.save()
                        definitions.append(definition)

        except Exception as e:
            logger.error(f"Error extracting definitions from WordHippo: {e}")

        return definitions

    async def _extract_examples_for_definition(
        self,
        parent_elem: Any,
        definition_id: PydanticObjectId,
    ) -> list[Example]:
        """Extract examples for a specific definition.

        Args:
            parent_elem: Parent HTML element containing examples
            definition_id: ID of the definition these examples belong to

        Returns:
            List of Example objects

        """
        examples = []

        try:
            # Look for example sentences in the parent element
            example_divs = parent_elem.find_all("div", class_=["examplesentence", "example"])

            for ex_div in example_divs[:3]:  # Limit to 3 examples
                ex_text = ex_div.text.strip()
                if ex_text and len(ex_text) > 5:
                    example = Example(
                        definition_id=definition_id,
                        text=ex_text,
                        type="literature",  # WordHippo uses real examples
                    )
                    await example.save()
                    examples.append(example)

        except Exception as e:
            logger.error(f"Error extracting examples: {e}")

        return examples

    async def _extract_pronunciation(
        self,
        soup: BeautifulSoup,
        word_id: PydanticObjectId,
    ) -> Pronunciation | None:
        """Extract pronunciation from WordHippo HTML.

        Args:
            soup: Parsed HTML content
            word_id: ID of the word this pronunciation belongs to

        Returns:
            Pronunciation if found, None otherwise

        """
        try:
            # WordHippo may have pronunciation in various formats
            # Look for common pronunciation indicators
            pron_elem = soup.find("span", class_=["pronunciation", "phonetic"])
            if not pron_elem:
                # Try alternative selectors
                pron_elem = soup.find("div", class_="pronunciation")

            if pron_elem:
                pron_text = pron_elem.text.strip()
                # Clean up pronunciation text
                pron_text = pron_text.replace("[", "").replace("]", "").strip()

                if pron_text:
                    return Pronunciation(
                        word_id=word_id,
                        phonetic=pron_text,
                        ipa=pron_text,  # Assume it's IPA format
                        syllables=[],
                        stress_pattern=None,
                    )

        except Exception as e:
            logger.error(f"Error extracting pronunciation from WordHippo: {e}")

        return None

    async def _extract_etymology(self, soup: BeautifulSoup) -> Etymology | None:
        """Extract etymology from WordHippo HTML.

        Args:
            soup: Parsed HTML content

        Returns:
            Etymology if found, None otherwise

        """
        try:
            # WordHippo may include etymology in various sections
            etym_elem = soup.find("div", class_=["etymology", "wordorigin"])
            if not etym_elem:
                # Try looking for sections with etymology keywords
                for elem in soup.find_all(["div", "p"]):
                    text = elem.text.lower()
                    if "origin" in text or "etymology" in text:
                        etym_elem = elem
                        break

            if etym_elem:
                etym_text = etym_elem.text.strip()
                # Clean up etymology text
                etym_text = etym_text.replace("Etymology:", "").replace("Origin:", "").strip()

                if etym_text and len(etym_text) > 20:  # Ensure meaningful content
                    return Etymology(
                        text=etym_text,
                        origin_language=None,
                        root_words=[],
                    )

        except Exception as e:
            logger.error(f"Error extracting etymology from WordHippo: {e}")

        return None

    async def _fetch_synonyms(self, word: str) -> list[str]:
        """Fetch synonyms from WordHippo synonym page.

        Args:
            word: The word to find synonyms for

        Returns:
            List of synonym strings

        """
        synonyms: list[str] = []

        try:
            url = f"{self.base_url}/what-is/another-word-for/{word.lower()}.html"
            async with respectful_scraper("wordhippo", self.rate_config) as client:
                response = await client.get(url)

            if response.status_code == 404:
                logger.debug(f"No synonyms page found for '{word}'")
                return synonyms

            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for synonym links - WordHippo uses specific classes for synonyms
            synonym_elements = soup.find_all(["a", "span"], class_=["relatedword", "synonym", "wb"])

            for elem in synonym_elements[:15]:  # Limit to top 15 synonyms
                text = elem.text.strip()
                if text and text.isalpha() and len(text) > 1:
                    synonyms.append(text)

            # Remove duplicates while preserving order
            seen = set()
            unique_synonyms = []
            for syn in synonyms:
                if syn.lower() not in seen and syn.lower() != word.lower():
                    seen.add(syn.lower())
                    unique_synonyms.append(syn)

            logger.debug(f"Found {len(unique_synonyms)} synonyms for '{word}'")
            return unique_synonyms

        except Exception as e:
            logger.error(f"Error fetching synonyms for '{word}': {e}")
            return synonyms

    async def _fetch_antonyms(self, word: str) -> list[str]:
        """Fetch antonyms from WordHippo antonym page.

        Args:
            word: The word to find antonyms for

        Returns:
            List of antonym strings

        """
        antonyms: list[str] = []

        try:
            url = f"{self.base_url}/what-is/the-opposite-of/{word.lower()}.html"
            async with respectful_scraper("wordhippo", self.rate_config) as client:
                response = await client.get(url)

            if response.status_code == 404:
                logger.debug(f"No antonyms page found for '{word}'")
                return antonyms

            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for antonym links - similar structure to synonyms
            antonym_elements = soup.find_all(["a", "span"], class_=["relatedword", "antonym", "wb"])

            for elem in antonym_elements[:10]:  # Limit to top 10 antonyms
                text = elem.text.strip()
                if text and text.isalpha() and len(text) > 1:
                    antonyms.append(text)

            # Remove duplicates while preserving order
            seen = set()
            unique_antonyms = []
            for ant in antonyms:
                if ant.lower() not in seen and ant.lower() != word.lower():
                    seen.add(ant.lower())
                    unique_antonyms.append(ant)

            logger.debug(f"Found {len(unique_antonyms)} antonyms for '{word}'")
            return unique_antonyms

        except Exception as e:
            logger.error(f"Error fetching antonyms for '{word}': {e}")
            return antonyms

    async def _fetch_sentences(self, word: str) -> list[str]:
        """Fetch example sentences from WordHippo sentences page.

        Args:
            word: The word to find sentences for

        Returns:
            List of example sentence strings

        """
        sentences: list[str] = []

        try:
            url = f"{self.base_url}/what-is/sentences-with-the-word/{word.lower()}.html"
            async with respectful_scraper("wordhippo", self.rate_config) as client:
                response = await client.get(url)

            if response.status_code == 404:
                logger.debug(f"No sentences page found for '{word}'")
                return sentences

            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for sentence examples - WordHippo typically uses specific classes
            sentence_elements = soup.find_all(
                ["div", "span"],
                class_=["sentence", "example", "examplesentence"],
            )

            # Also look for quote-like structures or list items
            if not sentence_elements:
                sentence_elements = soup.find_all(["li", "p"])

            for elem in sentence_elements[:8]:  # Limit to top 8 sentences
                text = elem.text.strip()
                # Filter for actual sentences (has the word, reasonable length, ends with punctuation)
                if (
                    text
                    and word.lower() in text.lower()
                    and 20 <= len(text) <= 200
                    and text[-1] in ".!?"
                ):
                    sentences.append(text)

            # Remove duplicates while preserving order
            seen = set()
            unique_sentences = []
            for sent in sentences:
                if sent not in seen:
                    seen.add(sent)
                    unique_sentences.append(sent)

            logger.debug(f"Found {len(unique_sentences)} sentences for '{word}'")
            return unique_sentences

        except Exception as e:
            logger.error(f"Error fetching sentences for '{word}': {e}")
            return sentences

    async def _enhance_definitions_with_data(
        self,
        definitions: list[Definition],
        synonyms: list[str],
        antonyms: list[str],
        sentences: list[str],
    ) -> None:
        """Enhance definitions with synonyms, antonyms, and additional examples.

        Args:
            definitions: List of definitions to enhance
            synonyms: List of synonyms to add
            antonyms: List of antonyms to add
            sentences: List of sentences to add as examples

        """
        try:
            # Distribute synonyms and antonyms across definitions
            for i, definition in enumerate(definitions):
                # Add synonyms (distribute evenly)
                start_idx = (i * len(synonyms)) // len(definitions) if definitions else 0
                end_idx = (
                    ((i + 1) * len(synonyms)) // len(definitions) if definitions else len(synonyms)
                )
                definition.synonyms = synonyms[start_idx:end_idx]

                # Add antonyms (distribute evenly)
                start_idx = (i * len(antonyms)) // len(definitions) if definitions else 0
                end_idx = (
                    ((i + 1) * len(antonyms)) // len(definitions) if definitions else len(antonyms)
                )
                definition.antonyms = antonyms[start_idx:end_idx]

                # Add sentences as examples (distribute evenly)
                start_idx = (i * len(sentences)) // len(definitions) if definitions else 0
                end_idx = (
                    ((i + 1) * len(sentences)) // len(definitions)
                    if definitions
                    else len(sentences)
                )

                for sentence in sentences[start_idx:end_idx]:
                    if definition.id is not None:
                        example = Example(
                            definition_id=definition.id,
                            text=sentence,
                            type="literature",  # WordHippo sentences are from real usage
                        )
                        await example.save()
                        if example.id is not None:
                            definition.example_ids.append(example.id)

                # Save updated definition
                await definition.save()

        except Exception as e:
            logger.error(f"Error enhancing definitions with additional data: {e}")

    async def close(self) -> None:
        """Close the HTTP session."""
        pass  # No persistent client to close
