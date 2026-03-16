"""Wiktionary wholesale data download and import.

Downloads complete Wiktionary XML dumps and imports entries in parallel
using the same robust wikitext parser as the regular Wiktionary scraper.

Usage (via CLI):
    floridify scrape wiktionary-wholesale --language en --download-all

Usage (programmatic):
    connector = WiktionaryWholesaleConnector(language=Language.ENGLISH)
    await connector.download_bulk_data("/tmp/wiktionary")
    count = await connector.import_bulk_data("/tmp/wiktionary")
"""

from __future__ import annotations

import bz2
import gzip
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ....models.base import Language, PydanticObjectId
from ....models.dictionary import (
    Definition,
    DictionaryEntry,
    DictionaryProvider,
    Etymology,
    Pronunciation,
    Word,
)
from ....storage.mongodb import get_storage
from ....utils.logging import get_logger
from ...batch import BatchOperation
from ...core import ConnectorConfig
from ...rate_limiting import RateLimitConfig
from ..core import DictionaryConnector
from ..scraper.wiktionary_parser import (
    extract_etymology,
    extract_pronunciation,
    extract_section_synonyms,
    find_language_section,
)

try:
    import wikitextparser as wtp  # type: ignore[import-untyped]
except ImportError:
    wtp = None

logger = get_logger(__name__)

# Concurrency controls
DB_CONCURRENCY = 200  # Max concurrent MongoDB write tasks
INSERT_BATCH_SIZE = 500  # Documents per insert_many call
LOG_INTERVAL = 1000  # Log progress every N entries

def _clean_wikitext(text: str) -> str:
    """Clean wikitext markup from a definition line.

    Handles templates, links, bold/italic, HTML tags, and common
    Wiktionary-specific patterns (labels, Wikidata IDs, etc.).
    """
    import re

    # Remove nested templates (greedy innermost-first, up to 3 levels)
    for _ in range(3):
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Convert wikilinks: [[link|display]] → display, [[word]] → word
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", text)

    # Remove bold/italic markers
    text = re.sub(r"'{2,}", "", text)

    # Remove Wikidata IDs (Q12345, q12345)
    text = re.sub(r"\bQ\d+\b", "", text)

    # Remove leftover template fragments (unclosed braces, pipes)
    text = re.sub(r"[{}|]", "", text)

    # Collapse multiple spaces and strip
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Remove leading/trailing punctuation artifacts
    text = text.strip(" ,;:.")

    return text


WIKTIONARY_SECTION_TITLES: dict[str, str] = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
}


class WiktionaryWholesaleConnector(DictionaryConnector):
    """Downloads and processes complete Wiktionary data dumps.

    Uses the same robust wikitext parser as the regular Wiktionary scraper
    (extract_definitions, extract_etymology, extract_pronunciation) but
    operates on local XML dumps for bulk throughput.

    Architecture (3-phase, like seed_apple_dictionary.py):
      Phase 1: Stream XML, extract raw (title, wikitext) pages
      Phase 2: Parse wikitext into structured definitions (CPU-bound)
      Phase 3: Save to MongoDB with high concurrency (semaphore-gated)
    """

    def __init__(
        self,
        language: Language = Language.ENGLISH,
        data_dir: Path | None = None,
        config: ConnectorConfig | None = None,
    ) -> None:
        if config is None:
            config = ConnectorConfig(
                rate_limit_config=RateLimitConfig(base_requests_per_second=10.0),
            )
        super().__init__(provider=DictionaryProvider.WIKTIONARY, config=config)
        self.language = language
        self.lang_code = language.value if hasattr(language, "value") else str(language)
        self.data_dir = data_dir or Path("/tmp/floridify/wiktionary_wholesale")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.dump_base_url = f"https://dumps.wikimedia.org/{self.lang_code}wiktionary/latest"

    def get_provider_version(self) -> str:
        return f"{self.lang_code}_wholesale_{datetime.now(UTC).strftime('%Y%m%d')}"

    async def __aenter__(self) -> WiktionaryWholesaleConnector:
        await super().__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        await super().__aexit__(*args)

    # ── Phase 0: Download ────────────────────────────────────────────

    async def download_bulk_data(
        self,
        output_path: str,
        batch_operation: BatchOperation | None = None,
    ) -> bool:
        """Download Wiktionary XML dump (bz2 compressed)."""
        try:
            dump_file = f"{self.lang_code}wiktionary-latest-pages-articles.xml.bz2"
            url = f"{self.dump_base_url}/{dump_file}"
            output_file = Path(output_path) / dump_file

            if output_file.exists():
                logger.info(f"Dump file already exists: {output_file}")
                return True

            output_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Downloading Wiktionary dump from {url}")

            session = self.api_client
            async with session.stream("GET", url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(output_file, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size and batch_operation and downloaded % (50 * 1024 * 1024) == 0:
                            progress = (downloaded / total_size) * 100
                            batch_operation.update_checkpoint(
                                {"download_progress": progress, "downloaded_bytes": downloaded}
                            )
                            logger.info(f"Download progress: {progress:.1f}%")
                            await batch_operation.save()

            logger.info(f"Download complete: {output_file} ({downloaded / 1024 / 1024:.0f} MB)")
            return True

        except Exception as e:
            logger.error(f"Download failed: {e}")
            if batch_operation:
                batch_operation.add_error("download", str(e))
            return False

    # ── Phase 1-3: Import ────────────────────────────────────────────

    async def import_bulk_data(
        self,
        data_path: str,
        batch_operation: BatchOperation | None = None,
        skip_existing: bool = True,
        limit: int = 0,
    ) -> int:
        """Import Wiktionary dump using robust parser + parallel writes.

        Args:
            data_path: Path to dump file or directory containing it
            batch_operation: Optional progress tracking
            skip_existing: Skip words already in DB
            limit: Max words to import (0 = unlimited)

        Returns:
            Number of entries imported
        """
        if wtp is None:
            raise ImportError("wikitextparser is required: pip install wikitextparser")

        await get_storage()

        data_file = self._resolve_data_file(data_path)
        section_title = WIKTIONARY_SECTION_TITLES.get(self.lang_code, "English")

        # Pre-load existing words for skip check
        existing_words: set[str] = set()
        if skip_existing:
            logger.info("Loading existing Wiktionary entries for skip check...")
            wikt_entries = await DictionaryEntry.find(
                {"provider": DictionaryProvider.WIKTIONARY.value}
            ).to_list()
            wikt_word_ids = {e.word_id for e in wikt_entries}
            if wikt_word_ids:
                existing = await Word.find({"_id": {"$in": list(wikt_word_ids)}}).to_list()
                existing_words = {w.text for w in existing}
            logger.info(f"Found {len(existing_words)} existing entries to skip")

        # Pre-load word index for fast lookup
        logger.info("Loading word index...")
        word_index: dict[str, Word] = {}
        async for w in Word.find_all():
            word_index[w.text] = w

        # Phase 1: Stream XML and extract raw pages
        logger.info(f"Phase 1: Streaming XML from {data_file}...")
        raw_pages = list(self._iter_valid_pages(data_file, section_title, existing_words, limit))
        logger.info(f"  {len(raw_pages)} valid pages extracted")

        if not raw_pages:
            return 0

        # Phase 2: Parse wikitext into structured data (CPU-bound)
        logger.info(f"Phase 2: Parsing {len(raw_pages)} pages...")
        parsed_entries: list[dict[str, Any]] = []
        for title, content in raw_pages:
            try:
                parsed = self._parse_page_robust(title, content, section_title)
                if parsed and parsed["definitions"]:
                    parsed_entries.append(parsed)
            except Exception as e:
                logger.debug(f"Parse error for '{title}': {e}")

        logger.info(f"  {len(parsed_entries)} pages with definitions")

        if not parsed_entries:
            return 0

        # Phase 3: Bulk save to MongoDB with insert_many batches
        logger.info(
            f"Phase 3: Saving {len(parsed_entries)} entries "
            f"(batch_size={INSERT_BATCH_SIZE}, concurrency={DB_CONCURRENCY})..."
        )
        imported = 0
        failed = 0

        for batch_start in range(0, len(parsed_entries), INSERT_BATCH_SIZE):
            batch = parsed_entries[batch_start : batch_start + INSERT_BATCH_SIZE]

            # Build all documents for this batch
            word_docs: list[Word] = []
            def_docs: list[Definition] = []
            entry_docs: list[DictionaryEntry] = []
            pron_docs: list[Pronunciation] = []

            for entry in batch:
                try:
                    title = entry["title"]

                    # Get or create Word — pre-assign ID so insert_many
                    # doesn't leave .id as None
                    word_obj = word_index.get(title)
                    if not word_obj:
                        word_obj = Word(
                            id=PydanticObjectId(),
                            text=title,
                            languages=[self.lang_code],
                        )
                        word_docs.append(word_obj)
                        word_index[title] = word_obj

                except Exception as e:
                    logger.debug(f"Prep error for '{entry.get('title')}': {e}")
                    failed += 1

            # Bulk insert new Words (IDs already assigned)
            if word_docs:
                await Word.insert_many(word_docs)

            # Now build definitions + entries with real word IDs
            for entry in batch:
                try:
                    title = entry["title"]
                    word_obj = word_index.get(title)
                    if not word_obj or not word_obj.id:
                        failed += 1
                        continue

                    # Create Definition documents (pre-assign IDs)
                    defs_for_entry: list[Definition] = []
                    for def_data in entry["definitions"]:
                        defs_for_entry.append(
                            Definition(
                                id=PydanticObjectId(),
                                word_id=word_obj.id,
                                part_of_speech=def_data["part_of_speech"],
                                text=def_data["text"],
                                synonyms=def_data.get("synonyms", [])[:10],
                                providers=[DictionaryProvider.WIKTIONARY],
                            )
                        )

                    if not defs_for_entry:
                        failed += 1
                        continue

                    def_docs.extend(defs_for_entry)

                    # Pronunciation
                    pron = entry.get("pronunciation")
                    pron_doc = None
                    if pron and hasattr(pron, "phonetic"):
                        pron_doc = Pronunciation(
                            id=PydanticObjectId(),
                            word_id=word_obj.id,
                            phonetic=pron.phonetic,
                            ipa=pron.ipa,
                            syllables=getattr(pron, "syllables", []),
                        )
                        pron_docs.append(pron_doc)

                    # Etymology
                    etym = entry.get("etymology")
                    etymology_obj = None
                    if etym and isinstance(etym, dict) and etym.get("text"):
                        etymology_obj = Etymology(
                            text=etym["text"],
                            origin_language=etym.get("origin_language"),
                            root_words=etym.get("root_words", []),
                            first_known_use=etym.get("first_known_use"),
                        )

                    # Stash entry data for after bulk insert (need def IDs)
                    entry_docs.append(
                        (word_obj, defs_for_entry, pron_doc, etymology_obj)
                    )

                except Exception as e:
                    logger.debug(f"Build error for '{entry.get('title')}': {e}")
                    failed += 1

            # Bulk insert all documents — wrapped in try/except per collection
            # so one bad batch doesn't kill the entire import
            try:
                if def_docs:
                    await Definition.insert_many(def_docs)
                if pron_docs:
                    await Pronunciation.insert_many(pron_docs)

                # Build DictionaryEntry documents
                dict_entries: list[DictionaryEntry] = []
                for word_obj, defs, pron_doc, etymology_obj in entry_docs:
                    def_ids = [d.id for d in defs if d.id]
                    dict_entries.append(
                        DictionaryEntry(
                            word_id=word_obj.id,
                            definition_ids=def_ids,
                            pronunciation_id=pron_doc.id if pron_doc and pron_doc.id else None,
                            provider=DictionaryProvider.WIKTIONARY,
                            languages=[self.lang_code],
                            etymology=etymology_obj,
                        )
                    )

                if dict_entries:
                    await DictionaryEntry.insert_many(dict_entries)
                    imported += len(dict_entries)
            except Exception as e:
                logger.warning(f"Batch save error (batch {batch_start}): {e}")
                failed += len(batch)

            if (batch_start + len(batch)) % LOG_INTERVAL < INSERT_BATCH_SIZE:
                logger.info(f"  Progress: {imported} imported, {failed} failed")
                if batch_operation:
                    batch_operation.processed_items = imported
                    await batch_operation.save()

        logger.info(f"Import complete: {imported} imported, {failed} failed")
        return imported

    # ── Internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _safe_iterparse(context):
        """Wrap ET.iterparse to gracefully handle truncated XML."""
        try:
            yield from context
        except ET.ParseError:
            # Truncated file or malformed XML at end — stop gracefully
            return

    def _resolve_data_file(self, data_path: str) -> Path:
        """Find the dump file from a path or directory.

        Prefers .xml (pre-decompressed) over .xml.bz2 for speed.
        Tip: pre-decompress with pbzip2 for ~10x faster streaming:
            pbzip2 -dk enwiktionary-latest-pages-articles.xml.bz2
        """
        data_file = Path(data_path)
        if data_file.is_dir():
            # Prefer pre-decompressed XML if available
            xml_file = data_file / f"{self.lang_code}wiktionary-latest-pages-articles.xml"
            bz2_file = data_file / f"{self.lang_code}wiktionary-latest-pages-articles.xml.bz2"
            if xml_file.exists():
                logger.info(f"Using pre-decompressed XML: {xml_file}")
                data_file = xml_file
            elif bz2_file.exists():
                data_file = bz2_file
            else:
                raise FileNotFoundError(f"No dump file found in {data_path}")
        if not data_file.exists():
            raise FileNotFoundError(f"Data file not found: {data_file}")
        return data_file

    def _iter_valid_pages(
        self,
        data_file: Path,
        section_title: str,
        existing_words: set[str],
        limit: int = 0,
    ):
        """Stream XML and yield (title, content) for valid dictionary pages."""
        open_func: Callable[..., Any]
        if data_file.suffix == ".bz2":
            open_func = bz2.open
        elif data_file.suffix == ".gz":
            open_func = gzip.open
        else:
            open_func = open

        count = 0
        with open_func(data_file, "rt", encoding="utf-8") as f:
            try:
                context = ET.iterparse(f, events=("end",))
            except ET.ParseError as e:
                logger.error(f"Failed to start XML parsing: {e}")
                return

            for event, elem in self._safe_iterparse(context):
                if not elem.tag.endswith("page"):
                    continue

                # Try multiple namespace versions (0.11, 0.10, none)
                title_el = None
                text_el = None
                for ns in (
                    "{http://www.mediawiki.org/xml/export-0.11/}",
                    "{http://www.mediawiki.org/xml/export-0.10/}",
                    "",  # no namespace
                ):
                    if title_el is None:
                        title_el = elem.find(f".//{ns}title")
                    if text_el is None:
                        text_el = elem.find(f".//{ns}text")

                if title_el is not None and title_el.text and text_el is not None and text_el.text:
                    title = title_el.text.strip()
                    content = text_el.text

                    # Skip special pages, short content, existing words
                    if (
                        ":" not in title
                        and len(content) >= 50
                        and f"=={section_title}==" in content
                        and title not in existing_words
                    ):
                        yield (title, content)
                        count += 1

                        if limit and count >= limit:
                            elem.clear()
                            break

                elem.clear()

    def _parse_page_robust(
        self,
        title: str,
        content: str,
        section_title: str,
    ) -> dict[str, Any] | None:
        """Parse wikitext using the robust Wiktionary parser.

        Uses the same extract_definitions/extract_etymology/extract_pronunciation
        functions as the regular WiktionaryConnector scraper.
        """
        parsed = wtp.parse(content)
        language_section = find_language_section(parsed, section_title)
        if language_section is None:
            return None

        # Extract section-level synonyms (shared across all definitions)
        section_syns = extract_section_synonyms(language_section)  # returns list[str]

        # Extract definitions synchronously (they don't need word_id yet)
        # We'll create a temporary ObjectId placeholder
        from bson import ObjectId

        temp_word_id = ObjectId()

        # extract_definitions is async — but we're in sync context here.
        # Store raw section data instead and parse async in save phase.
        definitions_raw: list[dict[str, Any]] = []
        pos_sections = [
            "noun", "verb", "adjective", "adverb", "pronoun",
            "preposition", "conjunction", "interjection", "determiner",
            "article", "participle", "numeral", "proper noun",
        ]

        for section in language_section.sections:
            if not section.title:
                continue
            pos = section.title.strip().lower()
            if pos not in pos_sections:
                continue

            # Use wikitext_cleaner-style extraction
            for line in section.contents.split("\n"):
                line = line.strip()
                if line.startswith("# ") or (line.startswith("#") and not line.startswith("##")):
                    text = line.lstrip("#").strip()
                    if text and len(text) > 5:
                        text = _clean_wikitext(text)
                        if text and len(text) > 5:
                            definitions_raw.append({
                                "part_of_speech": pos.replace("proper noun", "noun"),
                                "text": text,
                                "synonyms": section_syns,
                            })

        etymology = extract_etymology(language_section)
        pronunciation = None
        try:
            pronunciation = extract_pronunciation(language_section, temp_word_id)
        except Exception:
            pass

        return {
            "title": title,
            "definitions": definitions_raw,
            "etymology": etymology,
            "pronunciation": pronunciation,
        }

    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: Any | None = None,
    ) -> Any | None:
        """Not used for wholesale — see import_bulk_data instead."""
        return None


class WiktionaryTitleListDownloader:
    """Downloads and processes Wiktionary title lists for corpus building."""

    def __init__(self, language: Language = Language.ENGLISH, data_dir: Path | None = None) -> None:
        self.language = language
        self.lang_code = language.value if hasattr(language, "value") else str(language)
        self.data_dir = data_dir or Path("/tmp/floridify/wiktionary_titles")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.dump_url = (
            f"https://dumps.wikimedia.org/{self.lang_code}wiktionary/latest/"
            f"{self.lang_code}wiktionary-latest-all-titles-in-ns0.gz"
        )

    async def download_titles(self) -> Path:
        output_file = self.data_dir / f"{self.lang_code}_titles.gz"
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
        title_file = await self.download_titles()
        vocabulary = []
        with gzip.open(title_file, "rt", encoding="utf-8") as f:
            for line in f:
                title = line.strip()
                if ":" not in title and len(title) >= min_length:
                    vocabulary.append(title)

        logger.info(f"Extracted {len(vocabulary)} words from title list")
        return vocabulary
