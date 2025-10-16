"""Wiktionary wholesale data download and import.

Handles downloading and processing Wiktionary data dumps,
including full dictionary entries and definitions.
"""

from __future__ import annotations

import bz2
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import wikitextparser as wtp  # type: ignore[import-untyped]

from ....caching.models import VersionInfo
from ....models.base import Language
from ....models.dictionary import DictionaryEntry, DictionaryProvider, Word
from ....utils.logging import get_logger
from ...batch import BatchOperation
from ...core import ConnectorConfig
from ...utils import RateLimitConfig
from ..core import DictionaryConnector

logger = get_logger(__name__)


class WiktionaryWholesaleConnector(DictionaryConnector):
    """Downloads and processes complete Wiktionary data dumps.

    Supports:
    - Full XML dumps with all page content
    - Title lists for vocabulary building
    - Incremental updates
    - Multiple language editions
    """

    def __init__(
        self,
        language: Language = Language.ENGLISH,
        data_dir: Path | None = None,
        config: ConnectorConfig | None = None,
    ) -> None:
        """Initialize Wiktionary wholesale connector.

        Args:
            language: Language enum (defaults to English)
            data_dir: Directory for storing downloads
            config: Connector configuration

        """
        if config is None:
            config = ConnectorConfig(
                rate_limit_config=RateLimitConfig(base_requests_per_second=10.0),
            )
        super().__init__(provider=DictionaryProvider.WIKTIONARY, config=config)
        self.language = language
        self.data_dir = data_dir or Path("/tmp/floridify/wiktionary_wholesale")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize a regular Wiktionary connector for parsing
        from ..scraper import wiktionary as wiktionary_scraper

        class ParserProxy(wiktionary_scraper.WiktionaryConnector):
            def get_metadata_for_resource(self, resource_id: str) -> dict[str, Any]:
                return {}

            def model_dump(self, content: Any) -> Any:
                return content

            def model_load(self, content: Any) -> Any:
                return content

        self.parser = ParserProxy(config=config)

        # Wikimedia dump URLs
        self.dump_base_url = f"https://dumps.wikimedia.org/{language.value}wiktionary/latest"

    def get_provider_version(self) -> str:
        """Version includes language and date."""
        return f"{self.language}_wholesale_{datetime.now(UTC).strftime('%Y%m%d')}"

    async def __aenter__(self) -> WiktionaryWholesaleConnector:
        """Async context manager entry."""
        await super().__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        await super().__aexit__(*args)

    async def download_bulk_data(
        self,
        output_path: str,
        batch_operation: BatchOperation | None = None,
    ) -> bool:
        """Download Wiktionary data dump.

        Args:
            output_path: Path to save the downloaded data
            batch_operation: Optional batch operation for tracking

        Returns:
            True if download was successful

        """
        try:
            # Determine which dump to download
            dump_file = f"{self.language.value}wiktionary-latest-pages-articles.xml.bz2"
            url = f"{self.dump_base_url}/{dump_file}"

            output_file = Path(output_path) / dump_file

            # Check if already downloaded
            if output_file.exists():
                logger.info(f"Dump file already exists: {output_file}")
                return True

            logger.info(f"Downloading Wiktionary dump from {url}")

            # Stream download with progress
            session = self.api_client
            async with session.stream("GET", url) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(output_file, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size and batch_operation:
                            progress = (downloaded / total_size) * 100
                            batch_operation.update_checkpoint(
                                {
                                    "download_progress": progress,
                                    "downloaded_bytes": downloaded,
                                    "total_bytes": total_size,
                                },
                            )

                            if downloaded % (100 * 1024 * 1024) == 0:  # Log every 100MB
                                logger.info(f"Download progress: {progress:.1f}%")
                                await batch_operation.save()

            logger.info(f"Download complete: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Download failed: {e}")
            if batch_operation:
                batch_operation.add_error("download", str(e))
            return False

    async def import_bulk_data(
        self,
        data_path: str,
        batch_operation: BatchOperation | None = None,
    ) -> int:
        """Import Wiktionary dump into versioned storage.

        Args:
            data_path: Path to the dump file
            batch_operation: Optional batch operation for tracking

        Returns:
            Number of entries imported

        """
        data_file = Path(data_path)
        if not data_file.exists():
            # Try to find the dump file
            dump_file = f"{self.language.value}wiktionary-latest-pages-articles.xml.bz2"
            data_file = data_file / dump_file
            if not data_file.exists():
                raise FileNotFoundError(f"Data file not found: {data_file}")

        logger.info(f"Importing Wiktionary dump from {data_file}")

        # Determine file type and open appropriately

        open_func: Callable[..., Any]
        if data_file.suffix == ".bz2":
            open_func = bz2.open
        elif data_file.suffix == ".gz":
            open_func = gzip.open
        else:
            open_func = open

        imported_count = 0
        batch_size = 100
        batch_items = []

        # Parse XML dump
        with open_func(data_file, "rt", encoding="utf-8") as f:
            # Use iterative XML parsing for memory efficiency
            context = ET.iterparse(f, events=("start", "end"))
            context = iter(context)  # type: ignore[assignment]
            event, root = next(context)

            for event, elem in context:
                if event == "end" and elem.tag.endswith("page"):
                    # Process each page (word entry)
                    page_data = self._extract_page_data(elem)

                    if page_data and self._is_valid_entry(page_data):
                        # Convert to versioned data
                        versioned_data = await self._convert_page_to_versioned(
                            page_data,
                            batch_operation,
                        )

                        if versioned_data:
                            batch_items.append(versioned_data)

                            # Save batch when full
                            if len(batch_items) >= batch_size:
                                await self._save_batch(batch_items)
                                imported_count += len(batch_items)
                                batch_items = []

                                # Update progress
                                if batch_operation:
                                    batch_operation.processed_items = imported_count
                                    await batch_operation.save()

                                if imported_count % 1000 == 0:
                                    logger.info(f"Imported {imported_count} entries")

                    # Clear element to save memory
                    elem.clear()
                    root.clear()

        # Save remaining items
        if batch_items:
            await self._save_batch(batch_items)
            imported_count += len(batch_items)

        logger.info(f"Import complete: {imported_count} entries processed")
        return imported_count

    def _extract_page_data(self, page_elem: ET.Element) -> dict[str, Any] | None:
        """Extract data from a page element.

        Args:
            page_elem: XML page element

        Returns:
            Page data dictionary or None

        """
        try:
            ns = {"mw": "http://www.mediawiki.org/xml/export-0.10/"}

            title = page_elem.find(".//mw:title", ns)
            text = page_elem.find(".//mw:text", ns)

            if title is not None and text is not None:
                return {
                    "title": title.text,
                    "content": text.text,
                }

            return None

        except Exception as e:
            logger.debug(f"Error extracting page data: {e}")
            return None

    def _is_valid_entry(self, page_data: dict[str, Any]) -> bool:
        """Check if a page is a valid dictionary entry.

        Args:
            page_data: Page data from XML

        Returns:
            True if valid entry

        """
        title = page_data.get("title", "")
        content = page_data.get("content", "")

        # Skip special pages and templates
        if ":" in title:
            return False

        # Must have English section for English Wiktionary
        if self.language == Language.ENGLISH and "==English==" not in content:
            return False

        # Must have some definition content
        if not content or len(content) < 50:
            return False

        return True

    async def _convert_page_to_versioned(
        self,
        page_data: dict[str, Any],
        batch_operation: BatchOperation | None,
    ) -> DictionaryEntry | None:
        """Convert Wiktionary page to versioned provider data.

        Args:
            page_data: Page data from XML
            batch_operation: Optional batch operation

        Returns:
            DictionaryEntry or None

        """
        try:
            title = page_data["title"]
            content = page_data["content"]

            # Get or create Word object
            word_obj = await Word.find_one(
                {"text": title, "language": self.language},
            )

            if not word_obj:
                word_obj = Word(
                    text=title,
                    normalized=title.lower(),
                    language=self.language,
                )
                await word_obj.save()

            # Check that word_obj has been saved and has an ID
            if not word_obj.id:
                raise ValueError(f"Word {title} must be saved before creating versioned data")

            # Parse wikitext to extract structured data
            parsed_data = self._parse_wikitext(content)

            # Compute data hash

            data_str = json.dumps(parsed_data, sort_keys=True)
            data_hash = hashlib.sha256(data_str.encode()).hexdigest()

            # Check if this exact data already exists
            existing = await DictionaryEntry.find_one(
                {"version_info.data_hash": data_hash},
            )
            if existing:
                return None  # Skip duplicate

            # Create versioned data
            versioned_data = DictionaryEntry(
                word_id=word_obj.id,
                word_text=title,
                language=self.language,
                provider=self.provider,
                version_info=VersionInfo(
                    data_hash=data_hash,
                    is_latest=True,
                ),
                raw_data={
                    "title": title,
                    "parsed": parsed_data,
                    "source": "wholesale_dump",
                },
                provider_metadata={
                    "dump_date": datetime.now(UTC).isoformat(),
                    "language": self.language.value,
                },
            )

            return versioned_data

        except Exception as e:
            logger.error(f"Error converting page {page_data.get('title')}: {e}")
            if batch_operation:
                batch_operation.add_error(page_data.get("title", "unknown"), str(e))
            return None

    def _parse_wikitext(self, content: str) -> dict[str, Any]:
        """Parse wikitext content to extract structured data.

        Args:
            content: Raw wikitext content

        Returns:
            Parsed data dictionary

        """
        parsed = wtp.parse(content)
        data: dict[str, list[Any]] = {
            "definitions": [],
            "etymologies": [],
            "pronunciations": [],
            "synonyms": [],
            "antonyms": [],
        }

        # Extract sections
        for section in parsed.sections:
            if section.title and "Etymology" in section.title:
                data["etymologies"].append(section.plain_text())
            elif section.title and "Pronunciation" in section.title:
                data["pronunciations"].append(section.plain_text())
            elif section.title and section.title.strip().lower() in [
                "noun",
                "verb",
                "adjective",
                "adverb",
                "pronoun",
                "preposition",
                "conjunction",
                "interjection",
            ]:
                # Extract definitions
                for line in section.plain_text().split("\n"):
                    if line.strip().startswith("#") and not line.strip().startswith("##"):
                        definition = line.strip().lstrip("#").strip()
                        if definition:
                            data["definitions"].append(
                                {
                                    "part_of_speech": section.title.strip().lower(),
                                    "text": definition,
                                },
                            )

        return data

    async def _save_batch(self, items: list[DictionaryEntry]) -> None:
        """Save a batch of versioned data.

        Args:
            items: List of DictionaryEntry to save

        """
        if items:
            try:
                await DictionaryEntry.insert_many(items)
                logger.debug(f"Saved batch of {len(items)} items")
            except Exception as e:
                logger.error(f"Error saving batch: {e}")

    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: Any | None = None,
    ) -> Any | None:
        """Fetch definition from local wholesale data.

        This method checks if we have wholesale data for the word
        and returns it, otherwise falls back to the regular scraper.

        Args:
            word: Word text to look up
            state_tracker: Optional state tracker

        Returns:
            ProviderData or None

        """
        # First get or create word object
        word_obj = await Word.find_one({"text": word})
        if not word_obj:
            word_obj = Word(text=word)
            await word_obj.save()

        # First check if we have wholesale data
        wholesale_data = await DictionaryEntry.find_one(
            {
                "word_id": word_obj.id,
                "provider": DictionaryProvider.WIKTIONARY,
                "version_info.is_latest": True,
                "raw_data.source": "wholesale_dump",
            },
        )

        if wholesale_data and wholesale_data.raw_data:
            logger.debug(f"Using wholesale data for {word}")
            # Convert versioned data back to ProviderData format
            # This would need proper conversion logic
            return wholesale_data.raw_data.get("parsed")

        # Fall back to regular scraper
        logger.debug(f"No wholesale data for {word}, using scraper")
        return await self.parser._fetch_from_provider(word, state_tracker)


class WiktionaryTitleListDownloader:
    """Downloads and processes Wiktionary title lists for corpus building."""

    def __init__(self, language: Language = Language.ENGLISH, data_dir: Path | None = None) -> None:
        """Initialize title list downloader.

        Args:
            language: Language enum
            data_dir: Directory for downloads

        """
        self.language = language
        self.data_dir = data_dir or Path("/tmp/floridify/wiktionary_titles")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.dump_url = (
            f"https://dumps.wikimedia.org/{language.value}wiktionary/latest/"
            f"{language.value}wiktionary-latest-all-titles-in-ns0.gz"
        )

    async def download_titles(self) -> Path:
        """Download title list.

        Returns:
            Path to downloaded file

        """
        output_file = self.data_dir / f"{self.language.value}_titles.gz"

        if output_file.exists():
            logger.info(f"Title list already exists: {output_file}")
            return output_file

        logger.info(f"Downloading title list from {self.dump_url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(self.dump_url)
            response.raise_for_status()

            with open(output_file, "wb") as f:
                f.write(response.content)

        logger.info(f"Download complete: {output_file}")
        return output_file

    async def extract_vocabulary(self, min_length: int = 2) -> list[str]:
        """Extract vocabulary from title list.

        Args:
            min_length: Minimum word length

        Returns:
            List of words

        """
        title_file = await self.download_titles()

        vocabulary = []

        with gzip.open(title_file, "rt", encoding="utf-8") as f:
            for line in f:
                title = line.strip()

                # Filter out special pages and short words
                if ":" not in title and len(title) >= min_length:
                    vocabulary.append(title)

        logger.info(f"Extracted {len(vocabulary)} words from title list")
        return vocabulary
