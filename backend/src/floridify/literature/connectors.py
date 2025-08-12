"""Literature download connectors for multiple sources.

This module provides connectors for downloading full literary texts from various
sources including Project Gutenberg, Internet Archive, Wikisource, and others.
These connectors use respectful scraping practices with rate limiting and caching.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from ..caching import get_unified
from ..models.base import BaseMetadata
from ..utils.logging import get_logger
from ..utils.paths import get_cache_directory
from ..utils.scraping import (
    ContentProcessor,
    RateLimitConfig,
    ScrapingSession,
    SessionManager,
    respectful_scraper,
)
from .models import Author, Genre, LiteraryWork, LiteratureSource, Period

logger = get_logger(__name__)


class LiteratureConnector:
    """Base class for literature download connectors."""
    
    def __init__(self, source: LiteratureSource, cache_hours: int = 168):
        self.source = source
        self.cache_hours = cache_hours
        self.cache_dir = get_cache_directory(f"literature_{source.value}")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting configuration - respectful defaults
        self.rate_config = RateLimitConfig(
            base_requests_per_second=1.0,  # Conservative base rate
            min_delay=1.0,
            max_delay=30.0,
            backoff_multiplier=2.0,
            success_speedup=1.05,  # Gradual speedup
            success_threshold=20,
            max_consecutive_errors=3,
        )
    
    async def download_work(
        self, 
        source_id: str, 
        title: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> Optional[LiteraryWork]:
        """Download a single literary work.
        
        Args:
            source_id: Source-specific ID (e.g., Gutenberg number, Archive identifier)
            title: Optional title for metadata
            author_name: Optional author name for metadata
            
        Returns:
            LiteraryWork object with downloaded text and metadata
        """
        raise NotImplementedError("Subclasses must implement download_work")
    
    async def search_works(
        self, 
        author_name: Optional[str] = None,
        title: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search for works by criteria.
        
        Args:
            author_name: Filter by author name
            title: Filter by title
            subject: Filter by subject/genre
            limit: Maximum number of results
            
        Returns:
            List of work metadata dictionaries
        """
        raise NotImplementedError("Subclasses must implement search_works")
    
    def _get_cache_key(self, source_id: str) -> str:
        """Generate cache key for a work."""
        return f"{self.source.value}_{source_id}"
    
    async def _cache_text_content(self, work: LiteraryWork, text: str) -> None:
        """Cache the full text content."""
        cache_key = work.cache_key
        async with get_unified() as cache:
            await cache.set(
                "literature_texts",
                cache_key,
                {
                    "text": text,
                    "metadata": work.model_dump(),
                    "cached_at": asyncio.get_event_loop().time(),
                },
                ttl_hours=self.cache_hours
            )
    
    async def _get_cached_text(self, work: LiteraryWork) -> Optional[str]:
        """Retrieve cached text content."""
        cache_key = work.cache_key
        async with get_unified() as cache:
            cached = await cache.get("literature_texts", cache_key)
            return cached.get("text") if cached else None


class GutenbergConnector(LiteratureConnector):
    """Project Gutenberg literature connector.
    
    Downloads texts from Project Gutenberg using their API and file structure.
    Supports both mirror.gutenberg.org and API access.
    """
    
    def __init__(self):
        super().__init__(LiteratureSource.GUTENBERG, cache_hours=720)  # 30 days
        self.api_base = "https://www.gutenberg.org"
        self.mirror_base = "https://mirror.gutenberg.org"
        self.catalog_url = "https://www.gutenberg.org/ebooks/"
    
    async def search_works(
        self, 
        author_name: Optional[str] = None,
        title: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search Project Gutenberg catalog."""
        
        search_url = f"{self.api_base}/ebooks/search/"
        params = {
            "sort_order": "downloads",
            "query": ""
        }
        
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
        async with respectful_scraper("gutenberg", self.rate_config) as client:
            try:
                response = await client.get(search_url, params=params)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Parse search results
                for book_item in soup.find_all('li', class_='booklink')[:limit]:
                    link = book_item.find('a', class_='link')
                    if not link:
                        continue
                    
                    # Extract Gutenberg ID from URL
                    href = link.get('href', '')
                    match = re.search(r'/ebooks/(\d+)', href)
                    if not match:
                        continue
                    
                    gutenberg_id = match.group(1)
                    title_elem = book_item.find('span', class_='title')
                    author_elem = book_item.find('span', class_='subtitle')
                    
                    work_data = {
                        'source_id': gutenberg_id,
                        'title': title_elem.get_text().strip() if title_elem else "Unknown",
                        'author': author_elem.get_text().strip() if author_elem else "Unknown",
                        'url': urljoin(self.api_base, href),
                        'download_count': self._extract_download_count(book_item)
                    }
                    works.append(work_data)
                    
            except Exception as e:
                logger.error(f"Error searching Gutenberg: {e}")
        
        return works
    
    def _extract_download_count(self, book_item) -> int:
        """Extract download count from book listing."""
        try:
            downloads_elem = book_item.find('span', string=re.compile(r'downloads'))
            if downloads_elem:
                text = downloads_elem.get_text()
                match = re.search(r'(\d+)', text)
                return int(match.group(1)) if match else 0
        except:
            pass
        return 0
    
    async def download_work(
        self, 
        source_id: str, 
        title: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> Optional[LiteraryWork]:
        """Download work from Project Gutenberg."""
        
        logger.info(f"📚 Downloading Gutenberg work {source_id}")
        
        # Try multiple text formats in order of preference
        formats = [
            f"files/{source_id}/{source_id}-0.txt",  # UTF-8 plain text
            f"files/{source_id}/{source_id}.txt",    # Plain text
            f"files/{source_id}/{source_id}-8.txt",  # ISO-8859-1 text
            f"files/{source_id}/{source_id}.zip",    # Zipped text
        ]
        
        async with respectful_scraper("gutenberg", self.rate_config) as client:
            # Get metadata first
            catalog_url = f"{self.catalog_url}{source_id}"
            try:
                metadata_response = await client.get(catalog_url)
                work_metadata = self._parse_gutenberg_metadata(
                    metadata_response.text, 
                    source_id, 
                    title, 
                    author_name
                )
            except Exception as e:
                logger.warning(f"Could not fetch metadata for {source_id}: {e}")
                # Create minimal work metadata
                work_metadata = self._create_minimal_work(source_id, title, author_name)
            
            # Download text content
            text_content = None
            for format_path in formats:
                download_url = f"{self.mirror_base}/{format_path}"
                
                try:
                    logger.debug(f"Trying format: {download_url}")
                    response = await client.get(download_url)
                    
                    if format_path.endswith('.zip'):
                        text_content = self._extract_from_zip(response.content)
                    else:
                        text_content = response.text
                    
                    if text_content and len(text_content.strip()) > 500:
                        logger.info(f"✅ Downloaded text using format: {format_path}")
                        break
                        
                except Exception as e:
                    logger.debug(f"Failed format {format_path}: {e}")
                    continue
            
            if not text_content:
                logger.error(f"Could not download text for Gutenberg {source_id}")
                return None
            
            # Clean and process text
            cleaned_text = self._clean_gutenberg_text(text_content)
            if not ContentProcessor.validate_text_content(cleaned_text):
                logger.warning(f"Text quality validation failed for {source_id}")
                return None
            
            # Update work metadata with text info
            work_metadata.word_count = len(cleaned_text.split())
            work_metadata.character_count = len(cleaned_text)
            work_metadata.estimated_reading_time_minutes = work_metadata.word_count // 200
            work_metadata.text_hash = hashlib.sha256(cleaned_text.encode()).hexdigest()
            
            # Save work to database
            await work_metadata.save()
            
            # Cache text content separately
            await self._cache_text_content(work_metadata, cleaned_text)
            
            logger.info(f"✅ Successfully downloaded '{work_metadata.title}' "
                       f"({work_metadata.word_count:,} words)")
            
            return work_metadata
    
    def _parse_gutenberg_metadata(
        self, 
        html: str, 
        source_id: str, 
        title: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> LiteraryWork:
        """Parse metadata from Gutenberg catalog page."""
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        if not title:
            title_elem = soup.find('h1', itemprop='name')
            title = title_elem.get_text().strip() if title_elem else "Unknown Title"
        
        # Extract author
        author_obj = Author(
            name=author_name or "Unknown Author",
            period=Period.CONTEMPORARY,  # Default, will be updated if we can determine
            primary_genre=Genre.NOVEL,   # Default
        )
        
        if not author_name:
            author_elem = soup.find('a', itemprop='creator')
            if author_elem:
                author_obj.name = author_elem.get_text().strip()
        
        # Extract other metadata
        metadata_table = soup.find('table', class_='bibrec')
        metadata = BaseMetadata()
        
        if metadata_table:
            for row in metadata_table.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    key = th.get_text().strip().lower()
                    value = td.get_text().strip()
                    
                    if 'language' in key:
                        metadata.additional_metadata['original_language'] = value
                    elif 'subject' in key:
                        metadata.additional_metadata['subjects'] = value.split(', ')
                    elif 'locc' in key or 'classification' in key:
                        metadata.additional_metadata['classification'] = value
        
        return LiteraryWork(
            title=title,
            author=author_obj,
            source=LiteratureSource.GUTENBERG,
            source_id=source_id,
            source_url=f"{self.catalog_url}{source_id}",
            metadata=metadata,
        )
    
    def _create_minimal_work(
        self, 
        source_id: str, 
        title: Optional[str], 
        author_name: Optional[str]
    ) -> LiteraryWork:
        """Create minimal work metadata when catalog parsing fails."""
        return LiteraryWork(
            title=title or f"Gutenberg Work {source_id}",
            author=Author(
                name=author_name or "Unknown Author",
                period=Period.CONTEMPORARY,
                primary_genre=Genre.NOVEL,
            ),
            source=LiteratureSource.GUTENBERG,
            source_id=source_id,
            source_url=f"{self.catalog_url}{source_id}",
            metadata=BaseMetadata(),
        )
    
    def _extract_from_zip(self, zip_content: bytes) -> Optional[str]:
        """Extract text from ZIP file."""
        try:
            with zipfile.ZipFile(BytesIO(zip_content)) as zf:
                # Look for .txt files
                for filename in zf.namelist():
                    if filename.endswith('.txt') and not filename.startswith('__MACOSX'):
                        return zf.read(filename).decode('utf-8', errors='ignore')
        except Exception as e:
            logger.debug(f"Failed to extract from ZIP: {e}")
        return None
    
    def _clean_gutenberg_text(self, text: str) -> str:
        """Clean Project Gutenberg text headers and footers."""
        
        lines = text.split('\n')
        start_idx = 0
        end_idx = len(lines)
        
        # Find start of actual text (after Gutenberg header)
        for i, line in enumerate(lines):
            if any(marker in line.lower() for marker in [
                '*** start of this project gutenberg',
                '*** start of the project gutenberg',
                'start of this project gutenberg ebook'
            ]):
                start_idx = i + 1
                break
        
        # Find end of actual text (before Gutenberg footer)
        for i in range(len(lines) - 1, -1, -1):
            if any(marker in lines[i].lower() for marker in [
                '*** end of this project gutenberg',
                '*** end of the project gutenberg',
                'end of this project gutenberg ebook'
            ]):
                end_idx = i
                break
        
        # Extract main text
        main_text = '\n'.join(lines[start_idx:end_idx])
        
        # Clean up whitespace and formatting
        main_text = re.sub(r'\n\s*\n\s*\n', '\n\n', main_text)  # Reduce multiple newlines
        main_text = re.sub(r'[ \t]+', ' ', main_text)  # Normalize spaces
        main_text = main_text.strip()
        
        return main_text


class InternetArchiveConnector(LiteratureConnector):
    """Internet Archive literature connector."""
    
    def __init__(self):
        super().__init__(LiteratureSource.INTERNET_ARCHIVE, cache_hours=168)
        self.api_base = "https://archive.org"
        self.search_url = "https://archive.org/advancedsearch.php"
        
        # More conservative rate limiting for Archive.org
        self.rate_config.base_requests_per_second = 0.5
        self.rate_config.min_delay = 2.0
    
    async def search_works(
        self, 
        author_name: Optional[str] = None,
        title: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search Internet Archive for texts."""
        
        # Build query for books
        query_parts = ['mediatype:texts']
        
        if author_name:
            query_parts.append(f'creator:"{author_name}"')
        if title:
            query_parts.append(f'title:"{title}"')
        if subject:
            query_parts.append(f'subject:"{subject}"')
        
        params = {
            'q': ' AND '.join(query_parts),
            'fl': 'identifier,title,creator,date,subject,downloads',
            'sort': 'downloads desc',
            'rows': limit,
            'page': 1,
            'output': 'json'
        }
        
        works = []
        async with respectful_scraper("archive_org", self.rate_config) as client:
            try:
                response = await client.get(self.search_url, params=params)
                data = response.json()
                
                for doc in data.get('response', {}).get('docs', []):
                    work_data = {
                        'source_id': doc.get('identifier', ''),
                        'title': doc.get('title', 'Unknown Title'),
                        'author': doc.get('creator', ['Unknown Author'])[0] if doc.get('creator') else 'Unknown Author',
                        'url': f"{self.api_base}/details/{doc.get('identifier', '')}",
                        'date': doc.get('date'),
                        'subjects': doc.get('subject', []),
                        'downloads': doc.get('downloads', 0)
                    }
                    works.append(work_data)
                    
            except Exception as e:
                logger.error(f"Error searching Internet Archive: {e}")
        
        return works
    
    async def download_work(
        self, 
        source_id: str, 
        title: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> Optional[LiteraryWork]:
        """Download work from Internet Archive."""
        
        logger.info(f"📚 Downloading Internet Archive work {source_id}")
        
        async with respectful_scraper("archive_org", self.rate_config) as client:
            # Get metadata
            metadata_url = f"{self.api_base}/metadata/{source_id}"
            
            try:
                metadata_response = await client.get(metadata_url)
                metadata_json = metadata_response.json()
                work_metadata = self._parse_archive_metadata(
                    metadata_json, 
                    source_id, 
                    title, 
                    author_name
                )
            except Exception as e:
                logger.warning(f"Could not fetch metadata for {source_id}: {e}")
                work_metadata = self._create_minimal_archive_work(source_id, title, author_name)
            
            # Find text files
            files_url = f"{self.api_base}/download/{source_id}"
            
            try:
                files_response = await client.get(files_url)
                files_soup = BeautifulSoup(files_response.text, 'html.parser')
                
                # Look for text files in order of preference
                text_formats = ['.txt', '.pdf', '.epub']
                text_content = None
                
                for format_ext in text_formats:
                    links = files_soup.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        if href.endswith(format_ext) and 'original' not in href.lower():
                            file_url = urljoin(files_url + '/', href)
                            
                            if format_ext == '.txt':
                                text_response = await client.get(file_url)
                                text_content = text_response.text
                                if len(text_content.strip()) > 500:
                                    break
                            # For PDF/EPUB, we'd need additional processing
                    
                    if text_content:
                        break
                
                if not text_content:
                    logger.error(f"No suitable text format found for {source_id}")
                    return None
                
                # Validate and clean text
                if not ContentProcessor.validate_text_content(text_content):
                    logger.warning(f"Text quality validation failed for {source_id}")
                    return None
                
                # Update work metadata
                work_metadata.word_count = len(text_content.split())
                work_metadata.character_count = len(text_content)
                work_metadata.estimated_reading_time_minutes = work_metadata.word_count // 200
                work_metadata.text_hash = hashlib.sha256(text_content.encode()).hexdigest()
                
                # Save work
                await work_metadata.save()
                await self._cache_text_content(work_metadata, text_content)
                
                logger.info(f"✅ Successfully downloaded '{work_metadata.title}' from Archive.org")
                return work_metadata
                
            except Exception as e:
                logger.error(f"Error downloading from Internet Archive: {e}")
                return None
    
    def _parse_archive_metadata(
        self, 
        metadata: dict, 
        source_id: str, 
        title: Optional[str],
        author_name: Optional[str]
    ) -> LiteraryWork:
        """Parse Internet Archive metadata."""
        
        item_metadata = metadata.get('metadata', {})
        
        # Extract title and author
        parsed_title = title or item_metadata.get('title', f'Archive Work {source_id}')
        if isinstance(parsed_title, list):
            parsed_title = parsed_title[0]
        
        creator = author_name or item_metadata.get('creator', 'Unknown Author')
        if isinstance(creator, list):
            creator = creator[0]
        
        author_obj = Author(
            name=creator,
            period=Period.CONTEMPORARY,
            primary_genre=Genre.NOVEL,
        )
        
        # Build metadata
        base_metadata = BaseMetadata()
        if 'date' in item_metadata:
            base_metadata.additional_metadata['date'] = item_metadata['date']
        if 'subject' in item_metadata:
            subjects = item_metadata['subject']
            if isinstance(subjects, list):
                base_metadata.additional_metadata['subjects'] = subjects
            else:
                base_metadata.additional_metadata['subjects'] = [subjects]
        
        return LiteraryWork(
            title=parsed_title,
            author=author_obj,
            source=LiteratureSource.INTERNET_ARCHIVE,
            source_id=source_id,
            source_url=f"{self.api_base}/details/{source_id}",
            metadata=base_metadata,
        )
    
    def _create_minimal_archive_work(
        self, 
        source_id: str, 
        title: Optional[str], 
        author_name: Optional[str]
    ) -> LiteraryWork:
        """Create minimal work metadata for Archive.org."""
        return LiteraryWork(
            title=title or f"Archive Work {source_id}",
            author=Author(
                name=author_name or "Unknown Author",
                period=Period.CONTEMPORARY,
                primary_genre=Genre.NOVEL,
            ),
            source=LiteratureSource.INTERNET_ARCHIVE,
            source_id=source_id,
            source_url=f"{self.api_base}/details/{source_id}",
            metadata=BaseMetadata(),
        )


class WikisourceConnector(LiteratureConnector):
    """Wikisource literature connector."""
    
    def __init__(self):
        super().__init__(LiteratureSource.WIKISOURCE, cache_hours=168)
        self.api_base = "https://en.wikisource.org/w/api.php"
        self.base_url = "https://en.wikisource.org"
        
        # Respectful rate limiting for Wikimedia
        self.rate_config.base_requests_per_second = 1.0
        self.rate_config.min_delay = 1.0
    
    async def search_works(
        self, 
        author_name: Optional[str] = None,
        title: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search Wikisource using MediaWiki API."""
        
        search_terms = []
        if author_name:
            search_terms.append(author_name)
        if title:
            search_terms.append(title)
        if subject:
            search_terms.append(subject)
        
        if not search_terms:
            search_terms = ["literature"]
        
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': ' '.join(search_terms),
            'srnamespace': '0',  # Main namespace
            'srlimit': limit,
            'srprop': 'title|snippet|timestamp'
        }
        
        works = []
        async with respectful_scraper("wikisource", self.rate_config) as client:
            try:
                response = await client.get(self.api_base, params=params)
                data = response.json()
                
                for result in data.get('query', {}).get('search', []):
                    work_data = {
                        'source_id': result['title'].replace(' ', '_'),
                        'title': result['title'],
                        'author': 'Unknown Author',  # Would need additional parsing
                        'url': f"{self.base_url}/wiki/{result['title'].replace(' ', '_')}",
                        'snippet': result.get('snippet', ''),
                        'timestamp': result.get('timestamp', '')
                    }
                    works.append(work_data)
                    
            except Exception as e:
                logger.error(f"Error searching Wikisource: {e}")
        
        return works
    
    async def download_work(
        self, 
        source_id: str, 
        title: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> Optional[LiteraryWork]:
        """Download work from Wikisource."""
        
        logger.info(f"📚 Downloading Wikisource work {source_id}")
        
        async with respectful_scraper("wikisource", self.rate_config) as client:
            # Get page content using MediaWiki API
            params = {
                'action': 'query',
                'format': 'json',
                'titles': source_id.replace('_', ' '),
                'prop': 'extracts|info',
                'exintro': False,
                'explaintext': True,
                'inprop': 'url'
            }
            
            try:
                response = await client.get(self.api_base, params=params)
                data = response.json()
                
                pages = data.get('query', {}).get('pages', {})
                if not pages:
                    logger.error(f"No pages found for {source_id}")
                    return None
                
                page = next(iter(pages.values()))
                if 'missing' in page:
                    logger.error(f"Page {source_id} not found on Wikisource")
                    return None
                
                text_content = page.get('extract', '')
                if not text_content or len(text_content.strip()) < 500:
                    logger.error(f"Insufficient text content for {source_id}")
                    return None
                
                # Create work metadata
                work_title = title or page.get('title', source_id.replace('_', ' '))
                
                author_obj = Author(
                    name=author_name or "Unknown Author",
                    period=Period.CONTEMPORARY,
                    primary_genre=Genre.NOVEL,
                )
                
                work_metadata = LiteraryWork(
                    title=work_title,
                    author=author_obj,
                    source=LiteratureSource.WIKISOURCE,
                    source_id=source_id,
                    source_url=page.get('fullurl', f"{self.base_url}/wiki/{source_id}"),
                    word_count=len(text_content.split()),
                    character_count=len(text_content),
                    estimated_reading_time_minutes=len(text_content.split()) // 200,
                    text_hash=hashlib.sha256(text_content.encode()).hexdigest(),
                    metadata=BaseMetadata(),
                )
                
                # Save work
                await work_metadata.save()
                await self._cache_text_content(work_metadata, text_content)
                
                logger.info(f"✅ Successfully downloaded '{work_title}' from Wikisource")
                return work_metadata
                
            except Exception as e:
                logger.error(f"Error downloading from Wikisource: {e}")
                return None


class LiteratureSourceManager:
    """Manager for coordinating multiple literature sources."""
    
    def __init__(self):
        self.connectors = {
            LiteratureSource.GUTENBERG: GutenbergConnector(),
            LiteratureSource.INTERNET_ARCHIVE: InternetArchiveConnector(),
            LiteratureSource.WIKISOURCE: WikisourceConnector(),
        }
        self.session_manager = SessionManager()
    
    async def search_all_sources(
        self,
        author_name: Optional[str] = None,
        title: Optional[str] = None,
        subject: Optional[str] = None,
        limit_per_source: int = 20
    ) -> dict[LiteratureSource, list[dict[str, Any]]]:
        """Search across all available literature sources."""
        
        logger.info(f"🔍 Searching all sources for: author='{author_name}', title='{title}', subject='{subject}'")
        
        results = {}
        tasks = []
        
        for source, connector in self.connectors.items():
            task = asyncio.create_task(
                connector.search_works(author_name, title, subject, limit_per_source)
            )
            tasks.append((source, task))
        
        for source, task in tasks:
            try:
                source_results = await task
                results[source] = source_results
                logger.info(f"✅ {source.value}: {len(source_results)} results")
            except Exception as e:
                logger.error(f"❌ {source.value} search failed: {e}")
                results[source] = []
        
        total_results = sum(len(r) for r in results.values())
        logger.info(f"🔍 Search complete: {total_results} total results across {len(results)} sources")
        
        return results
    
    async def download_from_source(
        self,
        source: LiteratureSource,
        source_id: str,
        title: Optional[str] = None,
        author_name: Optional[str] = None
    ) -> Optional[LiteraryWork]:
        """Download a work from a specific source."""
        
        connector = self.connectors.get(source)
        if not connector:
            logger.error(f"No connector available for source: {source}")
            return None
        
        return await connector.download_work(source_id, title, author_name)
    
    async def bulk_download_author(
        self,
        author_name: str,
        max_works: int = 10,
        preferred_sources: Optional[list[LiteratureSource]] = None
    ) -> AsyncGenerator[LiteraryWork, None]:
        """Download multiple works by an author."""
        
        # Search for works by author
        search_results = await self.search_all_sources(author_name=author_name)
        
        # Prioritize sources if specified
        sources = preferred_sources or list(self.connectors.keys())
        
        downloaded_count = 0
        seen_titles = set()
        
        for source in sources:
            if downloaded_count >= max_works:
                break
                
            works = search_results.get(source, [])
            for work_data in works:
                if downloaded_count >= max_works:
                    break
                
                # Skip duplicates (same title)
                title_key = work_data['title'].lower().strip()
                if title_key in seen_titles:
                    continue
                
                try:
                    work = await self.download_from_source(
                        source,
                        work_data['source_id'],
                        work_data['title'],
                        work_data['author']
                    )
                    
                    if work:
                        seen_titles.add(title_key)
                        downloaded_count += 1
                        logger.info(f"📚 Downloaded {downloaded_count}/{max_works}: '{work.title}'")
                        yield work
                        
                        # Small delay between downloads
                        await asyncio.sleep(1.0)
                        
                except Exception as e:
                    logger.error(f"Failed to download {work_data['title']}: {e}")
                    continue
        
        logger.info(f"✅ Bulk download complete: {downloaded_count} works by {author_name}")