"""
Lexicon Scrapers Module

Custom scrapers for generating lexicon data from various web sources.
Each scraper should be reproducible and return standardized data formats.
"""

from .wikipedia_french_expressions import scrape_french_expressions

__all__ = ["scrape_french_expressions"]
