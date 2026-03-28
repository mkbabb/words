"""Wiktionary wholesale data download and import.

Downloads complete Wiktionary XML dumps and imports entries as a streaming
pipeline: XML pages are parsed and saved to MongoDB in batches without
materializing the full dump in memory.

Usage (via CLI):
    floridify scrape wiktionary-wholesale --language en

Usage (programmatic):
    connector = WiktionaryWholesaleConnector(language=Language.ENGLISH)
    await connector.download_bulk_data("/tmp/wiktionary")
    count = await connector.import_bulk_data("/tmp/wiktionary")
"""

from __future__ import annotations

import bz2
import io
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ....models.base import Language, PydanticObjectId
from ....models.dictionary import (
    DictionaryEntry,
    DictionaryProvider,
    Word,
)
from ....storage.mongodb import get_storage
from ....utils.logging import get_logger
from ...batch import BatchOperation
from ...core import ConnectorConfig
from ...rate_limiting import RateLimitConfig
from ..core import DictionaryConnector
from .batch import (
    ImportMode,
    find_complete_entries,
    flush_batch_insert,
    flush_batch_upsert,
)
from ..scraper.wikitext_cleaner import WikitextCleaner
from ..scraper.wiktionary_parser import (
    POS_MAPPINGS,
    extract_alternative_forms,
    extract_coordinate_terms,
    extract_derived_terms,
    extract_etymology,
    extract_hypernyms,
    extract_hyponyms,
    extract_inline_antonyms,
    extract_inline_synonyms,
    extract_pronunciation,
    extract_related_terms,
    extract_section_antonyms,
    extract_section_synonyms,
    extract_section_usage_notes,
    extract_wikilist_items,
    find_language_section,
)

try:
    import wikitextparser as wtp  # type: ignore[import-untyped]
except ImportError:
    wtp = None

logger = get_logger(__name__)

_DOWNLOAD_PROGRESS_CHUNK = 50 * 1024 * 1024  # Log every ~50MB

# ── Constants ─────────────────────────────────────────────────────────

INSERT_BATCH_SIZE = 500  # Documents per insert_many call
LOG_INTERVAL = 2000  # Log progress every N entries

WIKTIONARY_SECTION_TITLES: dict[str, str] = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
}

# Module-level cleaner instance (stateless, safe to share)
_cleaner = WikitextCleaner()


# ── Streaming helpers ─────────────────────────────────────────────────


def _open_bz2_stream(data_file: Path) -> tuple[Any, subprocess.Popen[bytes] | None]:
    """Open a bz2 file for streaming XML parsing.

    Tries pbzip2 first for parallel decompression (~5-10x faster).
    Falls back to Python's single-threaded bz2.open().

    Returns:
        (file_like_object, optional_process_to_cleanup)
    """
    if shutil.which("pbzip2"):
        logger.info("Using pbzip2 for parallel bz2 decompression")
        proc = subprocess.Popen(
            ["pbzip2", "-dc", str(data_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        # Wrap bytes pipe in a text-mode reader for ET.iterparse
        return io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace"), proc

    logger.warning(
        "pbzip2 not found — falling back to single-threaded bz2 decompression. "
        "Install pbzip2 for ~5-10x faster streaming: brew install pbzip2"
    )
    return bz2.open(data_file, "rt", encoding="utf-8"), None


class WiktionaryWholesaleConnector(DictionaryConnector):
    """Downloads and processes complete Wiktionary data dumps.

    Streaming pipeline architecture:
      1. Stream XML pages from dump (bz2 or plain XML)
      2. Parse each page's wikitext into structured definitions
      3. Flush to MongoDB in batches of INSERT_BATCH_SIZE

    Peak memory: O(batch_size + word_index), not O(total_pages).
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
        # Always use English Wiktionary dump — it contains ALL languages.
        # The `language` param controls which ==Section== to filter for.
        self.dump_base_url = "https://dumps.wikimedia.org/enwiktionary/latest"

    def get_provider_version(self) -> str:
        return f"{self.lang_code}_wholesale_{datetime.now(UTC).strftime('%Y%m%d')}"

    async def __aenter__(self) -> WiktionaryWholesaleConnector:
        await super().__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        await super().__aexit__(*args)

    # ── Download ──────────────────────────────────────────────────────

    async def download_bulk_data(
        self,
        output_path: str,
        batch_operation: BatchOperation | None = None,
    ) -> bool:
        """Download Wiktionary XML dump (bz2 compressed, ~1.5GB)."""
        try:
            dump_file = "enwiktionary-latest-pages-articles.xml.bz2"
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

                        if total_size and downloaded % _DOWNLOAD_PROGRESS_CHUNK < 1024 * 1024:
                            progress = (downloaded / total_size) * 100
                            logger.info(
                                f"Download progress: {progress:.1f}% ({downloaded // (1024 * 1024)} MB)"
                            )
                            if batch_operation:
                                batch_operation.update_checkpoint(
                                    {"download_progress": progress, "downloaded_bytes": downloaded}
                                )
                                await batch_operation.save()

            logger.info(f"Download complete: {output_file} ({downloaded // (1024 * 1024)} MB)")
            return True

        except Exception as e:
            logger.error(f"Download failed: {e}")
            if batch_operation:
                batch_operation.add_error("download", str(e))
            return False

    # ── Import (streaming pipeline) ───────────────────────────────────

    async def import_bulk_data(
        self,
        data_path: str,
        batch_operation: BatchOperation | None = None,
        skip_existing: bool = True,
        limit: int = 0,
        mode: ImportMode = ImportMode.INSERT,
    ) -> int:
        """Import Wiktionary dump as a streaming pipeline.

        Streams XML → parses wikitext → saves to MongoDB in batches.
        Never materializes the full dump in memory.

        Args:
            data_path: Path to dump file or directory containing it.
            batch_operation: Optional progress tracking with resume support.
            skip_existing: Skip words that already have Wiktionary entries (INSERT mode only).
            limit: Max words to import (0 = unlimited).
            mode: INSERT (skip existing, fast insert_many),
                  UPDATE (re-parse all, versioned upsert),
                  HYDRATE (re-parse incomplete, versioned upsert).

        Returns:
            Number of entries imported.
        """
        if wtp is None:
            raise ImportError("wikitextparser is required: pip install wikitextparser")

        await get_storage()

        data_file = self._resolve_data_file(data_path)
        section_title = WIKTIONARY_SECTION_TITLES.get(self.lang_code, "English")

        # Pre-load word index for dedup (needed throughout import)
        logger.info("Loading word index...")
        word_index: dict[str, Word] = {}
        async for w in Word.find_all():
            word_index[w.text] = w
        logger.info(f"  {len(word_index)} words in index")

        # Build skip set based on mode
        existing_words: set[str] = set()
        if mode == ImportMode.UPDATE:
            logger.info("  UPDATE mode: processing ALL entries")
        elif mode == ImportMode.HYDRATE:
            existing_words = await find_complete_entries(word_index)
            logger.info(f"  HYDRATE mode: skipping {len(existing_words)} complete entries")
        elif skip_existing:
            existing_word_ids: set[PydanticObjectId] = set()
            async for entry in DictionaryEntry.find(
                {"provider": DictionaryProvider.WIKTIONARY.value}
            ):
                existing_word_ids.add(entry.word_id)
            word_id_to_text = {w.id: text for text, w in word_index.items()}
            existing_words = {
                word_id_to_text[wid] for wid in existing_word_ids if wid in word_id_to_text
            }
            logger.info(f"  INSERT mode: skipping {len(existing_words)} existing entries")

        # Resume support
        resume_after: str | None = None
        if batch_operation and batch_operation.checkpoint.get("last_title"):
            resume_after = batch_operation.checkpoint["last_title"]
            logger.info(f"Resuming after: {resume_after}")

        # Select flush strategy based on mode
        flush_fn = flush_batch_upsert if mode != ImportMode.INSERT else flush_batch_insert

        # Streaming pipeline: parse + save in batches
        logger.info(f"Streaming import from {data_file} (mode={mode.value})...")
        batch_buffer: list[dict[str, Any]] = []
        imported = 0
        failed = 0
        parsed_count = 0
        last_title = ""

        for title, content in self._iter_valid_pages(
            data_file, section_title, existing_words, limit, resume_after
        ):
            try:
                parsed = self._parse_page(title, content, section_title)
                if parsed and parsed["definitions"]:
                    batch_buffer.append(parsed)
                    parsed_count += 1
            except Exception as e:
                logger.debug(f"Parse error for '{title}': {e}")
                failed += 1

            last_title = title

            # Flush batch when full
            if len(batch_buffer) >= INSERT_BATCH_SIZE:
                count = await flush_fn(batch_buffer, word_index, self.lang_code)
                imported += count
                failed += len(batch_buffer) - count
                batch_buffer.clear()

                if imported % LOG_INTERVAL < INSERT_BATCH_SIZE:
                    logger.info(
                        f"  Progress: {imported} imported, {failed} failed, {parsed_count} parsed"
                    )

                # Checkpoint for resume
                if batch_operation:
                    batch_operation.update_checkpoint(
                        {"last_title": last_title, "imported": imported}
                    )
                    batch_operation.processed_items = imported
                    await batch_operation.save()

        # Flush remaining
        if batch_buffer:
            count = await flush_fn(batch_buffer, word_index, self.lang_code)
            imported += count

        logger.info(
            f"Import complete: {imported} imported, {failed} failed, {parsed_count} parsed total"
        )
        return imported

    # ── XML streaming ─────────────────────────────────────────────────

    def _iter_valid_pages(
        self,
        data_file: Path,
        section_title: str,
        existing_words: set[str],
        limit: int = 0,
        resume_after: str | None = None,
    ) -> Generator[tuple[str, str]]:
        """Stream XML and yield (title, content) for valid dictionary pages."""
        # Open with pbzip2 (parallel) or fallback to stdlib bz2
        proc: subprocess.Popen[bytes] | None = None
        if data_file.suffix == ".bz2":
            f, proc = _open_bz2_stream(data_file)
        elif data_file.suffix == ".gz":
            import gzip

            f = gzip.open(data_file, "rt", encoding="utf-8")
        else:
            f = open(data_file, encoding="utf-8")

        try:
            context = ET.iterparse(f, events=("end",))
            count = 0
            skipping = resume_after is not None

            for _, elem in self._safe_iterparse(context):
                if not elem.tag.endswith("page"):
                    continue

                title_el, text_el = self._extract_page_elements(elem)

                if title_el is not None and title_el.text and text_el is not None and text_el.text:
                    title = title_el.text.strip()
                    content = text_el.text

                    # Resume: skip until past checkpoint
                    if skipping:
                        if title == resume_after:
                            skipping = False
                        elem.clear()
                        continue

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
        finally:
            f.close()
            if proc is not None:
                proc.wait()

    @staticmethod
    def _extract_page_elements(elem: ET.Element) -> tuple[ET.Element | None, ET.Element | None]:
        """Extract title and text elements, trying multiple MediaWiki namespace versions."""
        title_el = None
        text_el = None
        for ns in (
            "{http://www.mediawiki.org/xml/export-0.11/}",
            "{http://www.mediawiki.org/xml/export-0.10/}",
            "",
        ):
            if title_el is None:
                title_el = elem.find(f".//{ns}title")
            if text_el is None:
                text_el = elem.find(f".//{ns}text")
        return title_el, text_el

    @staticmethod
    def _safe_iterparse(context: Any) -> Generator[tuple[str, ET.Element]]:
        """Wrap ET.iterparse to gracefully handle truncated XML."""
        try:
            yield from context
        except ET.ParseError:
            return

    # ── Wikitext parsing ──────────────────────────────────────────────

    @staticmethod
    def _parse_page(
        title: str,
        content: str,
        section_title: str,
    ) -> dict[str, Any] | None:
        """Parse a single page's wikitext into structured data.

        Uses the shared WikitextCleaner and extract_wikilist_items from the
        scraper module — same parsing quality as live Wiktionary lookups.
        """
        parsed = wtp.parse(content)
        language_section = find_language_section(parsed, section_title)
        if language_section is None:
            return None

        # Extract etymology and pronunciation FIRST — before synonym/antonym
        # extraction modifies wtp Section objects (template.string = ...)
        etymology = extract_etymology(language_section)
        pronunciation = None
        try:
            from bson import ObjectId
            pronunciation = extract_pronunciation(language_section, ObjectId())
        except Exception:
            pass

        # Re-parse to get fresh section objects for template-modifying extractions
        parsed = wtp.parse(content)
        language_section = find_language_section(parsed, section_title)
        if language_section is None:
            return None

        section_syns = extract_section_synonyms(language_section)
        section_ants = extract_section_antonyms(language_section)

        definitions_raw: list[dict[str, Any]] = []
        for section in language_section.sections:
            if not section.title:
                continue
            pos = section.title.strip().lower()
            mapped_pos = POS_MAPPINGS.get(pos)
            if not mapped_pos:
                continue

            # Reuse shared definition extractor (handles multi-line, quote stripping)
            section_text = str(section)
            definition_texts = extract_wikilist_items(section_text)

            # Extract synonyms/antonyms from the full POS section text
            # (catches #: {{syn|...}} lines below definitions, not just section-level)
            pos_syns = extract_inline_synonyms(section_text)
            pos_ants = extract_inline_antonyms(section_text)
            all_syns = list(set(section_syns + pos_syns))
            all_ants = list(set(section_ants + pos_ants))

            for def_text in definition_texts:
                if not def_text or len(def_text.strip()) < 5:
                    continue
                clean_def = _cleaner.clean_text(def_text)
                if not clean_def or len(clean_def) < 5:
                    continue
                definitions_raw.append(
                    {
                        "part_of_speech": mapped_pos,
                        "text": clean_def,
                        "synonyms": all_syns,
                        "antonyms": all_ants,
                    }
                )

        # Extract additional structured data (re-parse again for clean state)
        parsed = wtp.parse(content)
        language_section = find_language_section(parsed, section_title)
        if language_section is None:
            return None

        derived = extract_derived_terms(language_section)
        related = extract_related_terms(language_section)
        hyper = extract_hypernyms(language_section)
        hypo = extract_hyponyms(language_section)
        coordinate = extract_coordinate_terms(language_section)
        alt_forms = extract_alternative_forms(language_section)
        usage_notes = extract_section_usage_notes(language_section)

        return {
            "title": title,
            "definitions": definitions_raw,
            "etymology": etymology,
            "pronunciation": pronunciation,
            "derived_terms": derived,
            "related_terms": related,
            "hypernyms": hyper,
            "hyponyms": hypo,
            "coordinate_terms": coordinate,
            "alternative_forms": alt_forms,
            "usage_notes": [{"type": n.type, "text": n.text} for n in usage_notes],
        }

    # ── File resolution ───────────────────────────────────────────────

    def _resolve_data_file(self, data_path: str) -> Path:
        """Find the dump file from a path or directory.

        Prefers .xml (pre-decompressed) over .xml.bz2.
        """
        data_file = Path(data_path)
        if data_file.is_dir():
            xml_file = data_file / "enwiktionary-latest-pages-articles.xml"
            bz2_file = data_file / "enwiktionary-latest-pages-articles.xml.bz2"
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

    async def _fetch_from_provider(
        self,
        word: str,
        state_tracker: Any | None = None,
    ) -> Any | None:
        """Not used for wholesale — see import_bulk_data instead."""
        return None
