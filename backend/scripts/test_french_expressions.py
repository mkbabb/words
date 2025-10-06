#!/usr/bin/env python3
"""Test French expressions Wikipedia scraper."""

import asyncio

from floridify.providers.language.scraper.scrapers import scrape_french_expressions


async def test_french_scraper():
    """Test French expressions scraper."""
    print("Testing French Wikipedia expressions scraper...")
    print("=" * 80)

    url = "https://en.wikipedia.org/wiki/Glossary_of_French_words_and_expressions_in_English"

    # Scrape expressions
    print(f"\n📥 Fetching from: {url}")
    result = await scrape_french_expressions(url)

    expressions = result["data"]
    metadata = result["metadata"]

    print(f"\n✅ Extracted {metadata['total_expressions']} French expressions")

    # Extract just the expression text
    expression_texts = [expr["expression"] for expr in expressions]

    # Check for specific words
    target_words = ["en coulisse", "recueillement", "au contraire", "bon mot"]
    print(f"\n🔍 Checking for target words:")
    for target in target_words:
        found = target in expression_texts
        status = "✅" if found else "❌"
        print(f"   {status} {target}: {found}")

    # Show first 20 expressions
    print(f"\n📝 First 20 expressions:")
    for i, expr in enumerate(expressions[:20]):
        print(f"   {i+1:2d}. {expr['expression']}")

    # Show some that might match our targets
    print(f"\n🔎 Expressions containing 'coulisse':")
    coulisse_words = [expr for expr in expressions if "coulisse" in expr["expression"].lower()]
    for expr in coulisse_words[:5]:
        print(f"   - {expr['expression']}: {expr['definition'][:60]}...")

    print(f"\n🔎 Expressions containing 'recueil':")
    recueil_words = [expr for expr in expressions if "recueil" in expr["expression"].lower()]
    for expr in recueil_words[:5]:
        print(f"   - {expr['expression']}: {expr['definition'][:60]}...")


if __name__ == "__main__":
    asyncio.run(test_french_scraper())
