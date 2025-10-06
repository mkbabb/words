#!/usr/bin/env python3
"""Verify French words and expressions exist in the English language corpus.

This script:
1. Loads the English language corpus
2. Searches for specific French words/expressions
3. Reports presence and search results
4. Provides fallback verification methods
"""

import asyncio
import sys

from floridify.corpus.core import Corpus
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.models.base import Language
from floridify.search.constants import SearchMethod
from floridify.search.core import Search
from floridify.storage.mongodb import get_storage
from floridify.text.normalize import batch_normalize
from floridify.utils.logging import get_logger

logger = get_logger(__name__)

# Target French words to verify
TARGET_FRENCH_WORDS = [
    "en coulisse",
    "en coulisses",
    "recueillement",
    "au contraire",
    "raison d'être",
    "vis-à-vis",
]


async def get_english_corpus() -> Corpus | None:
    """Get the English language master corpus.

    Returns:
        English corpus or None if not found
    """
    print("🔍 Searching for English language corpus...")

    manager = get_tree_corpus_manager()

    # Try to find by common name patterns
    corpus_names = [
        "english_language_master",
        "english_master",
        "english",
    ]

    for name in corpus_names:
        corpus = await manager.get_corpus(corpus_name=name)
        if corpus:
            print(f"✅ Found corpus: {name}")
            return corpus

    # List all available corpora
    stats = await manager.get_stats()
    print(f"\n📊 Available corpora ({stats['total']}):")
    for corpus_name in stats.get('corpus_names', []):
        print(f"   - {corpus_name}")

    return None


async def check_direct_lookup(corpus: Corpus, words: list[str]) -> dict[str, bool]:
    """Check words using direct vocabulary lookup.

    Args:
        corpus: Corpus to search
        words: Words to check

    Returns:
        Dictionary mapping word to presence boolean
    """
    print("\n" + "=" * 80)
    print("METHOD 1: DIRECT VOCABULARY LOOKUP")
    print("=" * 80)

    # Normalize target words
    normalized_words = batch_normalize(words)
    normalized_vocab = set(corpus.vocabulary)

    results = {}
    for word, norm_word in zip(words, normalized_words, strict=False):
        exists = norm_word in normalized_vocab
        results[word] = exists
        status = "✅" if exists else "❌"
        print(f"{status} {word:20} (normalized: {norm_word:20}) -> {exists}")

    return results


async def check_search_methods(corpus: Corpus, words: list[str]) -> dict[str, dict]:
    """Check words using all search methods.

    Args:
        corpus: Corpus to search
        words: Words to check

    Returns:
        Dictionary mapping word to search results
    """
    print("\n" + "=" * 80)
    print("METHOD 2: SEARCH ENGINE LOOKUP (EXACT/FUZZY/SEMANTIC)")
    print("=" * 80)

    # Create search index
    print("\n🔎 Building search indices...")
    search = await Search.from_corpus(
        corpus_name=corpus.corpus_name,
        semantic=False,  # Start without semantic for speed
    )

    results = {}

    for word in words:
        print(f"\n🔍 Searching: {word}")
        word_results = {}

        # Exact search
        exact_results = await search.search(
            word,
            max_results=3,
            method=SearchMethod.EXACT
        )
        word_results["exact"] = exact_results
        if exact_results:
            print(f"   ✅ EXACT: {exact_results[0].word} (score: {exact_results[0].score})")
        else:
            print(f"   ❌ EXACT: No results")

        # Fuzzy search
        fuzzy_results = await search.search(
            word,
            max_results=5,
            method=SearchMethod.FUZZY,
            min_score=0.6
        )
        word_results["fuzzy"] = fuzzy_results
        if fuzzy_results:
            print(f"   ✅ FUZZY: Found {len(fuzzy_results)} results")
            for i, result in enumerate(fuzzy_results[:3]):
                print(f"      {i+1}. {result.word} (score: {result.score:.2f})")
        else:
            print(f"   ❌ FUZZY: No results")

        # Cascade (smart) search
        cascade_results = await search.search(word, max_results=5)
        word_results["cascade"] = cascade_results
        if cascade_results:
            print(f"   ✅ CASCADE: Found {len(cascade_results)} results")
            for i, result in enumerate(cascade_results[:3]):
                print(f"      {i+1}. {result.word} (score: {result.score:.2f}, method: {result.method.value})")
        else:
            print(f"   ❌ CASCADE: No results")

        results[word] = word_results

    return results


async def check_child_corpora(corpus: Corpus, words: list[str]) -> dict[str, list[str]]:
    """Check if words exist in child corpora.

    Args:
        corpus: Master corpus with children
        words: Words to check

    Returns:
        Dictionary mapping word to list of corpora containing it
    """
    print("\n" + "=" * 80)
    print("METHOD 3: CHILD CORPORA SEARCH")
    print("=" * 80)

    if not corpus.child_corpus_ids:
        print("⚠️  No child corpora found")
        return {}

    print(f"\n📊 Checking {len(corpus.child_corpus_ids)} child corpora...")

    manager = get_tree_corpus_manager()
    results = {word: [] for word in words}

    for child_id in corpus.child_corpus_ids:
        child = await manager.get_corpus(corpus_id=child_id)
        if not child:
            continue

        print(f"\n   Checking: {child.corpus_name} ({len(child.vocabulary):,} words)")

        # Normalize and check
        normalized_words = batch_normalize(words)
        child_vocab_set = set(child.vocabulary)

        for word, norm_word in zip(words, normalized_words, strict=False):
            if norm_word in child_vocab_set:
                results[word].append(child.corpus_name)
                print(f"      ✅ Found: {word} in {child.corpus_name}")

    # Summary
    print(f"\n📋 Summary:")
    for word, corpora in results.items():
        if corpora:
            print(f"   ✅ {word}: found in {len(corpora)} corpora")
            for corpus_name in corpora:
                print(f"      - {corpus_name}")
        else:
            print(f"   ❌ {word}: not found in any child corpus")

    return results


async def check_french_expressions_source(corpus: Corpus, words: list[str]) -> bool:
    """Check if French expressions source exists in child corpora.

    Args:
        corpus: Master corpus
        words: Words to verify (not used, but kept for consistency)

    Returns:
        True if French expressions source exists
    """
    print("\n" + "=" * 80)
    print("METHOD 4: FRENCH EXPRESSIONS SOURCE VERIFICATION")
    print("=" * 80)

    if not corpus.child_corpus_ids:
        print("⚠️  No child corpora found")
        return False

    manager = get_tree_corpus_manager()

    # Look for French expressions child corpus
    french_expr_pattern = "french_expressions"

    for child_id in corpus.child_corpus_ids:
        child = await manager.get_corpus(corpus_id=child_id)
        if not child:
            continue

        if french_expr_pattern in child.corpus_name.lower():
            print(f"✅ Found French expressions corpus: {child.corpus_name}")
            print(f"   - Corpus ID: {child.corpus_id}")
            print(f"   - Vocabulary size: {len(child.vocabulary):,} words")
            print(f"   - Language: {child.language.value if hasattr(child.language, 'value') else child.language}")

            # Check if our target words are in this specific corpus
            normalized_words = batch_normalize(words)
            child_vocab_set = set(child.vocabulary)

            print(f"\n   🔍 Checking target words in this corpus:")
            found_count = 0
            for word, norm_word in zip(words, normalized_words, strict=False):
                exists = norm_word in child_vocab_set
                status = "✅" if exists else "❌"
                print(f"      {status} {word} ({norm_word})")
                if exists:
                    found_count += 1

            print(f"\n   📊 Found {found_count}/{len(words)} target words in French expressions corpus")
            return True

    print("❌ No French expressions corpus found")
    return False


async def generate_report(
    corpus: Corpus,
    direct_results: dict[str, bool],
    search_results: dict[str, dict],
    child_results: dict[str, list[str]],
    french_expr_exists: bool,
) -> None:
    """Generate comprehensive verification report.

    Args:
        corpus: English corpus
        direct_results: Direct lookup results
        search_results: Search method results
        child_results: Child corpora results
        french_expr_exists: Whether French expressions source exists
    """
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE VERIFICATION REPORT")
    print("=" * 80)

    print(f"\nCorpus: {corpus.corpus_name}")
    print(f"  - ID: {corpus.corpus_id}")
    print(f"  - Language: {corpus.language.value if hasattr(corpus.language, 'value') else corpus.language}")
    print(f"  - Total vocabulary: {len(corpus.vocabulary):,} words")
    print(f"  - Child corpora: {len(corpus.child_corpus_ids)}")
    print(f"  - Is master: {corpus.is_master}")

    print(f"\n{'Word':<25} {'Direct':<10} {'Exact':<10} {'Fuzzy':<10} {'Children':<20}")
    print("-" * 80)

    for word in TARGET_FRENCH_WORDS:
        direct = "✅" if direct_results.get(word, False) else "❌"
        exact = "✅" if search_results.get(word, {}).get("exact") else "❌"
        fuzzy = "✅" if search_results.get(word, {}).get("fuzzy") else "❌"
        children_list = child_results.get(word, [])
        children = f"{len(children_list)} found" if children_list else "❌"

        print(f"{word:<25} {direct:<10} {exact:<10} {fuzzy:<10} {children:<20}")

    print("\n📋 Summary:")
    total_words = len(TARGET_FRENCH_WORDS)
    direct_found = sum(1 for v in direct_results.values() if v)
    exact_found = sum(1 for v in search_results.values() if v.get("exact"))
    fuzzy_found = sum(1 for v in search_results.values() if v.get("fuzzy"))
    children_found = sum(1 for v in child_results.values() if v)

    print(f"   Direct lookup: {direct_found}/{total_words} found ({direct_found/total_words*100:.1f}%)")
    print(f"   Exact search:  {exact_found}/{total_words} found ({exact_found/total_words*100:.1f}%)")
    print(f"   Fuzzy search:  {fuzzy_found}/{total_words} found ({fuzzy_found/total_words*100:.1f}%)")
    print(f"   Child corpora: {children_found}/{total_words} found ({children_found/total_words*100:.1f}%)")
    print(f"   French expressions source: {'✅ Present' if french_expr_exists else '❌ Missing'}")

    # Recommendations
    print("\n💡 Recommendations:")
    if direct_found < total_words:
        print("   ⚠️  Some French words missing from master corpus vocabulary")
        print("      → Check if French expressions source is properly integrated")
        print("      → Verify vocabulary aggregation from child corpora")

    if not french_expr_exists:
        print("   ⚠️  French expressions source not found in child corpora")
        print("      → Run: python scripts/build_english_corpus.py")
        print("      → This will create the master corpus with all sources including French expressions")

    if fuzzy_found > exact_found:
        print("   ℹ️  Fuzzy search finds more results than exact search")
        print("      → This suggests normalization differences")
        print("      → French words may have diacritics/special characters")


async def main():
    """Main execution."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "FRENCH WORDS IN ENGLISH CORPUS VERIFICATION" + " " * 18 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Initialize database
    print("🔌 Initializing database connection...")
    await get_storage()
    print("   ✅ Database connected\n")

    # Get English corpus
    corpus = await get_english_corpus()

    if not corpus:
        print("\n❌ ERROR: English language corpus not found!")
        print("\n💡 To create the corpus, run:")
        print("   python scripts/build_english_corpus.py")
        sys.exit(1)

    print(f"\n📚 Corpus loaded: {corpus.corpus_name}")
    print(f"   - Vocabulary: {len(corpus.vocabulary):,} words")
    print(f"   - Children: {len(corpus.child_corpus_ids)}")

    # Run all verification methods
    direct_results = await check_direct_lookup(corpus, TARGET_FRENCH_WORDS)
    search_results = await check_search_methods(corpus, TARGET_FRENCH_WORDS)
    child_results = await check_child_corpora(corpus, TARGET_FRENCH_WORDS)
    french_expr_exists = await check_french_expressions_source(corpus, TARGET_FRENCH_WORDS)

    # Generate report
    await generate_report(
        corpus,
        direct_results,
        search_results,
        child_results,
        french_expr_exists,
    )

    print("\n" + "=" * 80)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(main())
