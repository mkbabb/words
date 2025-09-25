"""Internet Archive literature connector."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ....models.literature import LiteratureProvider
from ....utils.logging import get_logger
from ...core import ConnectorConfig, RateLimitPresets
from ...utils import respectful_scraper
from ..core import LiteratureConnector

logger = get_logger(__name__)


class InternetArchiveConnector(LiteratureConnector):
    """Internet Archive literature connector."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.BULK_DOWNLOAD.value)
        super().__init__(provider=LiteratureProvider.INTERNET_ARCHIVE, config=config)
        self.api_base = "https://archive.org"
        self.search_url = "https://archive.org/advancedsearch.php"

    async def _fetch_from_provider(
        self,
        source_id: str,
        state_tracker: Any | None = None,
    ) -> Any:
        """Fetch work from Internet Archive.

        Args:
            source_id: Work ID
            state_tracker: Optional state tracker

        Returns:
            Work content or metadata

        """
        # This is a stub implementation as InternetArchive uses specific methods
        # like _fetch_work_content and _fetch_work_metadata for different operations
        try:
            metadata = await self._fetch_work_metadata(source_id)
            if metadata:
                content = await self._fetch_work_content(source_id, metadata)
                if content:
                    return {"metadata": metadata, "content": content}
            return None
        except Exception as e:
            if state_tracker:
                await state_tracker.update_error(f"Internet Archive fetch failed: {e}")
            return None

    async def search_works(
        self,
        author_name: str | None = None,
        title: str | None = None,
        subject: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search Internet Archive for texts."""
        # Build query for books
        query_parts = ["mediatype:texts"]

        if author_name:
            query_parts.append(f'creator:"{author_name}"')
        if title:
            query_parts.append(f'title:"{title}"')
        if subject:
            query_parts.append(f'subject:"{subject}"')

        params = {
            "q": " AND ".join(query_parts),
            "fl": "identifier,title,creator,date,subject,downloads",
            "sort": "downloads desc",
            "rows": limit,
            "page": 1,
            "output": "json",
        }

        works = []
        async with respectful_scraper("archive_org", self.config.rate_limit_config) as client:
            try:
                response = await client.get(self.search_url, params=params)
                data = response.json()

                for doc in data.get("response", {}).get("docs", []):
                    work_data = {
                        "source_id": doc.get("identifier", ""),
                        "title": doc.get("title", "Unknown Title"),
                        "author": doc.get("creator", ["Unknown Author"])[0]
                        if doc.get("creator")
                        else "Unknown Author",
                        "url": f"{self.api_base}/details/{doc.get('identifier', '')}",
                        "date": doc.get("date"),
                        "subjects": doc.get("subject", []),
                        "downloads": doc.get("downloads", 0),
                    }
                    works.append(work_data)

            except Exception as e:
                logger.error(f"Error searching Internet Archive: {e}")

        return works

    async def _fetch_work_metadata(
        self,
        source_id: str,
        title: str | None = None,
        author_name: str | None = None,
    ) -> dict[str, Any]:
        """Fetch metadata from Internet Archive."""
        metadata_url = f"{self.api_base}/metadata/{source_id}"

        async with respectful_scraper("archive_org", self.config.rate_limit_config) as client:
            try:
                response = await client.get(metadata_url)
                metadata_json = response.json()
                return self._parse_archive_metadata(metadata_json, source_id, title, author_name)
            except Exception as e:
                logger.warning(f"Could not fetch metadata for {source_id}: {e}")
                return self._create_minimal_metadata(source_id, title, author_name)

    async def _fetch_work_content(self, source_id: str, metadata: dict[str, Any]) -> str | None:
        """Download text content from Internet Archive."""
        files_url = f"{self.api_base}/download/{source_id}"

        async with respectful_scraper("archive_org", self.config.rate_limit_config) as client:
            try:
                files_response = await client.get(files_url)
                files_soup = BeautifulSoup(files_response.text, "html.parser")

                # Look for text files in order of preference
                text_formats = [".txt", ".pdf", ".epub"]

                for format_ext in text_formats:
                    links = files_soup.find_all("a", href=True)
                    for link in links:
                        href = link["href"]
                        if href.endswith(format_ext) and "original" not in href.lower():
                            file_url = urljoin(files_url + "/", href)

                            if format_ext == ".txt":
                                text_response = await client.get(file_url)
                                text_content = text_response.text
                                if len(text_content.strip()) > 500:
                                    return text_content
                            # For PDF/EPUB, we'd need additional processing

            except Exception as e:
                logger.error(f"Error downloading from Internet Archive: {e}")

        return None

    def _parse_archive_metadata(
        self,
        metadata: dict[str, Any],
        source_id: str,
        title: str | None,
        author_name: str | None,
    ) -> dict[str, Any]:
        """Parse Internet Archive metadata."""
        item_metadata = metadata.get("metadata", {})

        # Extract title and author
        parsed_title = title or item_metadata.get("title", f"Archive Work {source_id}")
        if isinstance(parsed_title, list):
            parsed_title = parsed_title[0]

        creator = author_name or item_metadata.get("creator", "Unknown Author")
        if isinstance(creator, list):
            creator = creator[0]

        result = {
            "title": parsed_title,
            "author": creator,
            "source_url": f"{self.api_base}/details/{source_id}",
            "external_ids": {"archive_id": source_id},
        }

        # Additional metadata
        if "date" in item_metadata:
            result["date"] = item_metadata["date"]
        if "subject" in item_metadata:
            subjects = item_metadata["subject"]
            if isinstance(subjects, list):
                result["subjects"] = subjects
            else:
                result["subjects"] = [subjects]

        return result

    def _create_minimal_metadata(
        self,
        source_id: str,
        title: str | None,
        author_name: str | None,
    ) -> dict[str, Any]:
        """Create minimal metadata for Archive.org."""
        return {
            "title": title or f"Archive Work {source_id}",
            "author": author_name or "Unknown Author",
            "source_url": f"{self.api_base}/details/{source_id}",
            "external_ids": {"archive_id": source_id},
        }
