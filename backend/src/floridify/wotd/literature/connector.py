"""Generalized Project Gutenberg connector for downloading literary texts.

Provides a clean, DRY interface for downloading, caching, and processing
texts from Project Gutenberg with intelligent text cleaning.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import aiohttp
import aiofiles

from ...utils.logging import get_logger
from ...utils.paths import get_cache_directory
from ..core import Author
from .models import LiteraryWork

logger = get_logger(__name__)


class GutenbergConnector:
    """Unified connector for Project Gutenberg texts with caching."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize with optional custom cache directory."""
        self.cache_dir = cache_dir or get_cache_directory("literature")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Text cleaning patterns
        self.header_patterns = [
            r'\*\*\* START OF .*? \*\*\*',
            r'Project Gutenberg.*?(?=\n\n)',
            r'This eBook is for the use of anyone.*?(?=\n\n)',
            r'Updated editions will replace.*?(?=\n\n)',
        ]
        
        self.footer_patterns = [
            r'\*\*\* END OF .*? \*\*\*.*',
            r'End of .*?Project Gutenberg.*',
        ]
        
        self.cleanup_patterns = [
            r'^\s*Transcriber.*?$',  # Transcriber notes
            r'^\s*\[Illustration.*?\].*?$',  # Illustration notes
            r'^\s*\[Pg \d+\].*?$',  # Page numbers
            r'^\s*\[.*?\].*?$',  # Other editorial notes in brackets
        ]
    
    async def download_work(self, work: LiteraryWork, force_refresh: bool = False) -> str:
        """Download a literary work, with caching.
        
        Args:
            work: LiteraryWork with URL and metadata
            force_refresh: If True, re-download even if cached
            
        Returns:
            Clean text content of the work
        """
        cache_file = self._get_cache_path(work)
        
        # Check cache first
        if not force_refresh and cache_file.exists():
            logger.debug(f"📋 Using cached text for {work.title}")
            async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
                return await f.read()
        
        # Download from Project Gutenberg
        logger.info(f"⬇️ Downloading {work.title} by {work.author.value}")
        
        try:
            raw_text = await self._fetch_url(work.url)
            clean_text = self._clean_gutenberg_text(raw_text, work)
            
            # Cache the cleaned text
            await self._cache_text(cache_file, clean_text)
            
            logger.info(f"✅ Downloaded and cached {work.title} ({len(clean_text)} chars)")
            return clean_text
            
        except Exception as e:
            logger.error(f"❌ Failed to download {work.title}: {e}")
            raise
    
    async def download_author_works(
        self, 
        author: Author, 
        works: list[LiteraryWork],
        max_works: Optional[int] = None
    ) -> dict[str, str]:
        """Download all works for an author.
        
        Args:
            author: Author enum
            works: List of LiteraryWork objects
            max_works: Maximum number of works to download (None = all)
            
        Returns:
            Dict mapping work titles to their text content
        """
        if max_works:
            works = works[:max_works]
            
        results = {}
        
        for work in works:
            try:
                text = await self.download_work(work)
                results[work.title] = text
                
            except Exception as e:
                logger.warning(f"⚠️ Skipped {work.title}: {e}")
                continue
        
        logger.info(f"📚 Downloaded {len(results)}/{len(works)} works for {author.value}")
        return results
    
    def _get_cache_path(self, work: LiteraryWork) -> Path:
        """Generate cache file path for a work."""
        safe_title = re.sub(r'[^\w\s-]', '', work.title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title).lower()
        filename = f"{work.author.value}_{safe_title}.txt"
        return self.cache_dir / filename
    
    async def _fetch_url(self, url: str) -> str:
        """Fetch text content from URL."""
        timeout = aiohttp.ClientTimeout(total=60)  # 1 minute timeout
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                # Try to get encoding from headers
                encoding = 'utf-8'
                if 'content-type' in response.headers:
                    content_type = response.headers['content-type']
                    if 'charset=' in content_type:
                        encoding = content_type.split('charset=')[1].split(';')[0]
                
                content = await response.read()
                
                # Decode with fallbacks
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    try:
                        return content.decode('utf-8', errors='ignore')
                    except UnicodeDecodeError:
                        return content.decode('latin-1', errors='ignore')
    
    def _clean_gutenberg_text(self, raw_text: str, work: LiteraryWork) -> str:
        """Clean Project Gutenberg text by removing headers, footers, and formatting."""
        text = raw_text
        
        # Remove headers
        for pattern in self.header_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL)
        
        # Remove footers  
        for pattern in self.footer_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL)
        
        # Remove editorial notes and formatting
        for pattern in self.cleanup_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Collapse multiple empty lines
        text = re.sub(r'[ \t]+', ' ', text)  # Normalize whitespace
        text = text.strip()
        
        # Minimum length check
        if len(text) < 1000:
            logger.warning(f"⚠️ {work.title} text seems very short ({len(text)} chars)")
        
        return text
    
    async def _cache_text(self, cache_file: Path, text: str) -> None:
        """Cache cleaned text to file."""
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
            await f.write(text)
    
    def get_cached_works(self, author: Author) -> list[str]:
        """Get list of cached work titles for an author."""
        cached_files = list(self.cache_dir.glob(f"{author.value}_*.txt"))
        return [self._extract_title_from_filename(f) for f in cached_files]
    
    def _extract_title_from_filename(self, filepath: Path) -> str:
        """Extract work title from cache filename."""
        filename = filepath.stem
        # Remove author prefix
        if '_' in filename:
            title_part = '_'.join(filename.split('_')[1:])
            # Convert back to readable title
            return title_part.replace('_', ' ').title()
        return filename
    
    async def get_work_stats(self, work: LiteraryWork) -> dict:
        """Get basic statistics for a work."""
        try:
            text = await self.download_work(work)
            
            # Basic stats
            word_count = len(text.split())
            char_count = len(text)
            line_count = len(text.splitlines())
            
            return {
                "word_count": word_count,
                "character_count": char_count,
                "line_count": line_count,
                "avg_words_per_line": word_count / line_count if line_count > 0 else 0,
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {work.title}: {e}")
            return {}


# Convenience functions
async def download_single_work(work: LiteraryWork) -> str:
    """Download a single work using default connector."""
    connector = GutenbergConnector()
    return await connector.download_work(work)


async def download_author_complete(author: Author, max_works: Optional[int] = None) -> dict[str, str]:
    """Download all available works for an author."""
    from .mappings import get_author_works
    
    connector = GutenbergConnector()
    works = get_author_works(author)
    return await connector.download_author_works(author, works, max_works)