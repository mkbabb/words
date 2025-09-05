"""Language scrapers implementations."""

from .default import default_scraper
from .wikipedia_french_expressions import scrape_french_expressions

__all__ = ["default_scraper", "scrape_french_expressions"]
