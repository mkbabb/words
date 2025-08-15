"""Corpus scrapers module."""

from .default import ScraperFunc, default_scraper
from .wikipedia_french_expressions import scrape_french_expressions

__all__ = [
    "ScraperFunc",
    "default_scraper",
    "scrape_french_expressions",
]
