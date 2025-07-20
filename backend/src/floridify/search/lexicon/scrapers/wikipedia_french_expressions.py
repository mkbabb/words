"""
Wikipedia French Expressions Scraper

Simple scraper for French words and expressions commonly used in English.
"""

from __future__ import annotations

from typing import Any

import httpx
from bs4 import BeautifulSoup

from ....utils.logging import get_logger

logger = get_logger(__name__)


async def scrape_french_expressions(url: str = "", **kwargs: Any) -> dict[str, Any]:
    """
    Scrape French expressions from Wikipedia glossary page.

    Returns:
        Dictionary with 'data' key containing expressions list
    """
    target_url = (
        url or "https://en.wikipedia.org/wiki/Glossary_of_French_words_and_expressions_in_English"
    )

    logger.info(f"Scraping French expressions from: {target_url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(target_url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    expressions = []

    # Find all dt/dd pairs in the main content
    content = soup.find("div", {"class": "mw-content-ltr"})
    if not content or not hasattr(content, "find_all"):
        logger.warning("Could not find main content")
        return {"data": []}

    # Get all dt elements (expression names)
    dt_elements = content.find_all("dt")
    logger.debug(f"Found {len(dt_elements)} dt elements")

    for dt in dt_elements:
        # Extract the expression text (clean it up)
        expression_text = dt.get_text().strip()
        if not expression_text:
            continue

        # Get the corresponding definition (next dd element)
        dd = dt.find_next_sibling("dd")
        definition = ""
        if dd:
            definition = dd.get_text().strip()

        # Only include multi-word expressions
        if len(expression_text.split()) > 1:
            expressions.append(
                {
                    "expression": expression_text,
                    "definition": definition,
                    "source": "wikipedia_glossary",
                }
            )

    logger.info(f"Extracted {len(expressions)} French expressions")

    return {
        "data": expressions,
        "metadata": {
            "source_url": target_url,
            "total_expressions": len(expressions),
            "scraper": "wikipedia_french_expressions",
        },
    }
