"""Project Gutenberg literature connector.

Downloads texts from Project Gutenberg using their API and file structure.
Supports both mirror.gutenberg.org and API access.
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from ....core.state_tracker import StateTracker
from ....models.literature import AuthorInfo, LiteratureProvider
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ...utils import respectful_scraper
from ..core import LiteratureConnector
from ..models import LiteratureEntry

logger = get_logger(__name__)


class GutenbergConnector(LiteratureConnector):
    """Project Gutenberg literature connector."""

    async def _fetch_from_provider(
        self,
        source_id: str,
        state_tracker: StateTracker | None = None,
    ) -> Any:
        """Fetch work from Gutenberg.

        Args:
            source_id: Work ID
            state_tracker: Optional state tracker

        Returns:
            Work content or metadata
        """
        # This is a stub implementation as Gutenberg uses specific methods
        # like download_work and search_works for different operations
        try:
            # Create a minimal work entry to download
            from ....models.literature import AuthorInfo, Genre, Period

            work = LiteratureEntry(
                title=f"Work {source_id}",
                author=AuthorInfo(
                    name="Unknown", period=Period.CONTEMPORARY, primary_genre=Genre.NOVEL
                ),
                gutenberg_id=source_id,
                work_id=source_id,
            )
            return await self.download_work(work, force_refresh=False)
        except Exception as e:
            if state_tracker:
                await state_tracker.update_error(f"Gutenberg fetch failed: {e}")
            return None

    def __init__(self, config: ConnectorConfig | None = None):
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.BULK_DOWNLOAD.value)
        super().__init__(provider=LiteratureProvider.GUTENBERG, config=config)
        self.api_base = "https://www.gutenberg.org"
        self.mirror_base = "https://mirror.gutenberg.org"
        self.catalog_url = "https://www.gutenberg.org/ebooks/"

        # Rate limiting is handled by parent class

        # Text cleaning patterns from wotd/literature
        self.header_patterns = [
            r"\*\*\* START OF .*? \*\*\*",
            r"Project Gutenberg.*?(?=\n\n)",
            r"This eBook is for the use of anyone.*?(?=\n\n)",
            r"Updated editions will replace.*?(?=\n\n)",
        ]

        self.footer_patterns = [
            r"\*\*\* END OF .*? \*\*\*.*",
            r"End of .*?Project Gutenberg.*",
        ]

        self.cleanup_patterns = [
            r"^\s*Transcriber.*?$",
            r"^\s*\[Illustration.*?\].*?$",
            r"^\s*\[Pg \d+\].*?$",
            r"^\s*\[.*?\].*?$",
        ]

    async def search_works(
        self,
        author_name: str | None = None,
        title: str | None = None,
        subject: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search Project Gutenberg catalog."""
        search_url = f"{self.api_base}/ebooks/search/"
        params = {"sort_order": "downloads", "query": ""}

        # Build search query
        query_parts = []
        if author_name:
            query_parts.append(f'author:"{author_name}"')
        if title:
            query_parts.append(f'title:"{title}"')
        if subject:
            query_parts.append(f'subject:"{subject}"')

        params["query"] = " AND ".join(query_parts) if query_parts else "*"

        works = []
        async with respectful_scraper("gutenberg", self.config.rate_limit_config) as client:
            try:
                response = await client.get(search_url, params=params)
                soup = BeautifulSoup(response.text, "html.parser")

                # Parse search results
                for book_item in soup.find_all("li", class_="booklink")[:limit]:
                    link = book_item.find("a", class_="link")
                    if not link:
                        continue

                    # Extract Gutenberg ID from URL
                    href = link.get("href", "")
                    match = re.search(r"/ebooks/(\d+)", href)
                    if not match:
                        continue

                    gutenberg_id = match.group(1)
                    title_elem = book_item.find("span", class_="title")
                    author_elem = book_item.find("span", class_="subtitle")

                    work_data = {
                        "source_id": gutenberg_id,
                        "title": title_elem.get_text().strip() if title_elem else "Unknown",
                        "author": author_elem.get_text().strip() if author_elem else "Unknown",
                        "url": urljoin(self.api_base, href),
                        "download_count": self._extract_download_count(book_item),
                    }
                    works.append(work_data)

            except Exception as e:
                logger.error(f"Error searching Gutenberg: {e}")

        return works

    async def _fetch_work_metadata(
        self,
        source_id: str,
        title: str | None = None,
        author_name: str | None = None,
    ) -> dict[str, Any]:
        """Fetch metadata from Gutenberg catalog page."""
        catalog_url = f"{self.catalog_url}{source_id}"

        async with respectful_scraper("gutenberg", self.config.rate_limit_config) as client:
            try:
                response = await client.get(catalog_url)
                return self._parse_gutenberg_metadata(response.text, source_id, title, author_name)
            except Exception as e:
                logger.warning(f"Could not fetch metadata for {source_id}: {e}")
                return self._create_minimal_metadata(source_id, title, author_name)

    async def _fetch_work_content(self, source_id: str, metadata: dict[str, Any]) -> str | None:
        """Download text content from Project Gutenberg."""
        # Try multiple text formats in order of preference
        formats = [
            f"files/{source_id}/{source_id}-0.txt",  # UTF-8 plain text
            f"files/{source_id}/{source_id}.txt",  # Plain text
            f"files/{source_id}/{source_id}-8.txt",  # ISO-8859-1 text
            f"files/{source_id}/{source_id}.zip",  # Zipped text
        ]

        async with respectful_scraper("gutenberg", self.config.rate_limit_config) as client:
            for format_path in formats:
                download_url = f"{self.mirror_base}/{format_path}"

                try:
                    logger.debug(f"Trying format: {download_url}")
                    response = await client.get(download_url)

                    if format_path.endswith(".zip"):
                        text_content = self._extract_from_zip(response.content)
                    else:
                        text_content = response.text

                    if text_content and len(text_content.strip()) > 500:
                        logger.info(f"✅ Downloaded text using format: {format_path}")
                        return self._clean_gutenberg_text(text_content)

                except Exception as e:
                    logger.debug(f"Failed format {format_path}: {e}")
                    continue

        return None

    def _parse_gutenberg_metadata(
        self,
        html: str,
        source_id: str,
        title: str | None = None,
        author_name: str | None = None,
    ) -> dict[str, Any]:
        """Parse metadata from Gutenberg catalog page."""
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        if not title:
            title_elem = soup.find("h1", itemprop="name")
            title = title_elem.get_text().strip() if title_elem else "Unknown Title"

        # Extract author
        if not author_name:
            author_elem = soup.find("a", itemprop="creator")
            if author_elem:
                author_name = author_elem.get_text().strip()
            else:
                author_name = "Unknown Author"

        # Extract other metadata
        metadata: dict[str, Any] = {
            "title": title,
            "author": author_name,
            "source_url": f"{self.catalog_url}{source_id}",
            "external_ids": {"gutenberg_id": source_id},
        }

        metadata_table = soup.find("table", class_="bibrec")
        if metadata_table and isinstance(metadata_table, Tag):
            for row in metadata_table.find_all("tr"):
                th = row.find("th")
                td = row.find("td")
                if th and td:
                    key = th.get_text().strip().lower()
                    value = td.get_text().strip()

                    if "language" in key:
                        metadata["language"] = value
                    elif "subject" in key:
                        metadata["subjects"] = value.split(", ")
                    elif "locc" in key or "classification" in key:
                        metadata["classification"] = value
                    elif "release date" in key:
                        # Try to extract year
                        year_match = re.search(r"\b(18|19|20)\d{2}\b", value)
                        if year_match:
                            metadata["publication_year"] = int(
                                year_match.group()
                            )  # Changed from "year" to avoid type confusion

        return metadata

    def _create_minimal_metadata(
        self,
        source_id: str,
        title: str | None,
        author_name: str | None,
    ) -> dict[str, Any]:
        """Create minimal metadata when catalog parsing fails."""
        return {
            "title": title or f"Gutenberg Work {source_id}",
            "author": author_name or "Unknown Author",
            "source_url": f"{self.catalog_url}{source_id}",
            "external_ids": {"gutenberg_id": source_id},
        }

    def _extract_download_count(self, book_item: Tag) -> int:
        """Extract download count from book listing."""
        try:
            downloads_elem = book_item.find("span", string=re.compile(r"downloads"))
            if downloads_elem:
                text = downloads_elem.get_text()
                match = re.search(r"(\d+)", text)
                return int(match.group(1)) if match else 0
        except Exception:
            pass
        return 0

    def _extract_from_zip(self, zip_content: bytes) -> str | None:
        """Extract text from ZIP file."""
        try:
            with zipfile.ZipFile(BytesIO(zip_content)) as zf:
                # Look for .txt files
                for filename in zf.namelist():
                    if filename.endswith(".txt") and not filename.startswith("__MACOSX"):
                        return zf.read(filename).decode("utf-8", errors="ignore")
        except Exception as e:
            logger.debug(f"Failed to extract from ZIP: {e}")
        return None

    def _clean_gutenberg_text(self, text: str, work: LiteratureEntry | None = None) -> str:
        """Clean Project Gutenberg text headers and footers.

        Enhanced version incorporating patterns from wotd/literature.
        """
        lines = text.split("\n")
        start_idx = 0
        end_idx = len(lines)

        # Find start of actual text (after Gutenberg header)
        for i, line in enumerate(lines):
            if any(
                marker in line.lower()
                for marker in [
                    "*** start of this project gutenberg",
                    "*** start of the project gutenberg",
                    "start of this project gutenberg ebook",
                ]
            ):
                start_idx = i + 1
                break

        # Find end of actual text (before Gutenberg footer)
        for i in range(len(lines) - 1, -1, -1):
            if any(
                marker in lines[i].lower()
                for marker in [
                    "*** end of this project gutenberg",
                    "*** end of the project gutenberg",
                    "end of this project gutenberg ebook",
                ]
            ):
                end_idx = i
                break

        # Extract main text
        main_text = "\n".join(lines[start_idx:end_idx])

        # Apply additional cleanup patterns
        for pattern in self.cleanup_patterns:
            main_text = re.sub(pattern, "", main_text, flags=re.MULTILINE)

        # Clean up whitespace and formatting
        main_text = re.sub(r"\n\s*\n\s*\n", "\n\n", main_text)  # Reduce multiple newlines
        main_text = re.sub(r"[ \t]+", " ", main_text)  # Normalize spaces
        main_text = main_text.strip()

        return main_text

    async def download_work(self, work: LiteratureEntry, force_refresh: bool = False) -> str:
        """Download a literary work with caching.

        Migrated from wotd/literature/connector.py.
        """
        # Fetch and clean the text
        logger.info(f"⬇️ Downloading {work.title} by {work.author.name}")

        try:
            # work.gutenberg_id might be None, so we need to check
            if not work.gutenberg_id:
                raise ValueError(f"Work {work.title} has no Gutenberg ID")

            raw_text = await self._fetch_work_content(work.gutenberg_id, {})
            if not raw_text:
                raise ValueError(f"Could not download text for {work.title}")

            clean_text = self._clean_gutenberg_text(raw_text, work)

            logger.info(f"✅ Downloaded {work.title} ({len(clean_text)} chars)")
            return clean_text

        except Exception as e:
            logger.error(f"❌ Failed to download {work.title}: {e}")
            raise

    async def download_author_works(
        self,
        author: AuthorInfo,
        works: list[LiteratureEntry],
        max_works: int | None = None,
    ) -> dict[str, str]:
        """Download all works for an author.

        Migrated from wotd/literature/connector.py.
        """
        results = {}
        works_to_download = works[:max_works] if max_works else works

        for work in works_to_download:
            try:
                text = await self.download_work(work)
                results[work.title] = text
            except Exception as e:
                logger.warning(f"Failed to download {work.title}: {e}")
                continue

        logger.info(
            f"✅ Downloaded {len(results)}/{len(works_to_download)} works for {author.name}"
        )
        return results

    async def _fetch_url(self, url: str) -> str:
        """Fetch content from URL."""
        async with respectful_scraper("gutenberg", self.config.rate_limit_config) as client:
            response = await client.get(url)
            return response.text
