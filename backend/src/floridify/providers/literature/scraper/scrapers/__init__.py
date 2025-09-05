"""Literature scrapers implementations."""

from .default import (
    default_literature_scraper,
    scrape_archive_org,
    scrape_gutenberg,
    scrape_wikisource,
)

__all__ = [
    "default_literature_scraper",
    "scrape_gutenberg",
    "scrape_archive_org",
    "scrape_wikisource",
]
