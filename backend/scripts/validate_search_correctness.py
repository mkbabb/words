#!/usr/bin/env python3
"""
Validate search correctness after optimizations.
Tests semantic search quality with INT8 quantization and FAISS IVF-Flat.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from floridify.search.semantic.core import SemanticSearch
from floridify.search.semantic import constants as sem_constants
from floridify.corpus.core import Corpus
from floridify.caching.models import VersionConfig

# MongoDB initialization
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie


async def init_mongodb():
    """Initialize MongoDB connection and Beanie ODM."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")

    # Import all Beanie document models (NOT including Corpus which is BaseModel)
    from floridify.caching.models import BaseVersionedData
    from floridify.models.base import AudioMedia, ImageMedia
    from floridify.models.dictionary import (
        Definition,
        DictionaryEntry,
        Example,
        Fact,
        Pronunciation,
        Word,
    )
    from floridify.models.relationships import WordRelationship
    from floridify.providers.batch import BatchOperation
    from floridify.providers.dictionary.models import DictionaryProviderEntry
    from floridify.providers.language.models import LanguageEntry
    from floridify.providers.literature.models import LiteratureEntry
    from floridify.search.models import SearchIndex, TrieIndex
    from floridify.search.semantic.models import SemanticIndex
    from floridify.wordlist.models import WordList

    document_models = [
        Word,
        Definition,
        DictionaryEntry,
        Example,
        Fact,
        Pronunciation,
        WordRelationship,
        AudioMedia,
        ImageMedia,
        DictionaryProviderEntry,
        LanguageEntry,
        LiteratureEntry,
        SearchIndex,
        TrieIndex,
        SemanticIndex,
        WordList,
        BatchOperation,
        BaseVersionedData,
        # Note: Corpus is NOT a Beanie Document, it's BaseModel
    ]

    await init_beanie(database=client.floridify, document_models=document_models)
    return client


async def test_semantic_search_correctness():
    """Test semantic search with realistic corpus and validate results."""

    print("=" * 80)
    print("SEMANTIC SEARCH CORRECTNESS VALIDATION")
    print("=" * 80)

    # Test corpus with clear semantic relationships
    test_corpus = [
        # Cluster 1: Emotions (positive)
        "happy", "joyful", "cheerful", "delighted", "pleased", "content", "glad",
        "elated", "jubilant", "ecstatic", "blissful", "merry", "jovial",

        # Cluster 2: Emotions (negative)
        "sad", "unhappy", "miserable", "sorrowful", "depressed", "melancholy",
        "gloomy", "dejected", "downcast", "dismal", "woeful",

        # Cluster 3: Size (large)
        "big", "large", "huge", "enormous", "gigantic", "massive", "immense",
        "colossal", "mammoth", "vast", "tremendous", "substantial",

        # Cluster 4: Size (small)
        "small", "tiny", "little", "minuscule", "microscopic", "diminutive",
        "petite", "compact", "minute", "miniature",

        # Cluster 5: Speed (fast)
        "fast", "quick", "rapid", "swift", "speedy", "hasty", "fleet",
        "brisk", "expeditious", "prompt",

        # Cluster 6: Speed (slow)
        "slow", "sluggish", "leisurely", "gradual", "unhurried", "dawdling",
        "lagging", "plodding",

        # Cluster 7: Temperature (hot)
        "hot", "warm", "heated", "scorching", "blazing", "burning", "fiery",
        "sweltering", "torrid", "boiling",

        # Cluster 8: Temperature (cold)
        "cold", "chilly", "freezing", "frigid", "icy", "frosty", "wintry",
        "arctic", "glacial", "frozen",
    ]

    print(f"\n📊 Test Corpus: {len(test_corpus)} words across 8 semantic clusters")
    print(f"   Quantization: {sem_constants.USE_QUANTIZATION}")
    print(f"   Precision: {sem_constants.QUANTIZATION_PRECISION}")
    print(f"   Corpus size: {len(test_corpus)} (threshold={sem_constants.SMALL_CORPUS_THRESHOLD})")

    # Create corpus
    print("\n🔄 Creating corpus...")
    from floridify.corpus.models import CorpusType
    from floridify.models.base import Language

    corpus = Corpus(
        corpus_name="validation_test",
        corpus_type=CorpusType.CUSTOM,
        language=Language.ENGLISH,
        vocabulary=test_corpus,
        original_vocabulary=test_corpus,
        lemmatized_vocabulary=test_corpus,
    )
    await corpus._rebuild_indices()

    # Initialize search engine
    print("🔄 Initializing semantic search engine...")
    engine = await SemanticSearch.from_corpus(
        corpus=corpus,
        model_name=sem_constants.DEFAULT_SENTENCE_MODEL,
        config=VersionConfig(),
    )

    # Check what index type was used
    if hasattr(engine, 'sentence_index'):
        index_type = type(engine.sentence_index).__name__
        print(f"   Index Type: {index_type}")
        if hasattr(engine.sentence_index, 'nprobe'):
            print(f"   nprobe: {engine.sentence_index.nprobe}")
        if hasattr(engine.sentence_index, 'nlist'):
            print(f"   nlist: {engine.sentence_index.nlist}")

    # Test queries with expected results
    test_cases = [
        {
            "query": "joyful",
            "expected_cluster": ["happy", "cheerful", "delighted", "pleased", "glad"],
            "description": "Positive emotion synonym"
        },
        {
            "query": "enormous",
            "expected_cluster": ["huge", "gigantic", "massive", "immense", "colossal"],
            "description": "Large size synonym"
        },
        {
            "query": "rapid",
            "expected_cluster": ["fast", "quick", "swift", "speedy", "brisk"],
            "description": "Fast speed synonym"
        },
        {
            "query": "freezing",
            "expected_cluster": ["cold", "chilly", "frigid", "icy", "frosty"],
            "description": "Cold temperature synonym"
        },
        {
            "query": "miserable",
            "expected_cluster": ["sad", "unhappy", "sorrowful", "depressed", "gloomy"],
            "description": "Negative emotion synonym"
        },
    ]

    print("\n" + "=" * 80)
    print("TESTING SEMANTIC SEARCH CORRECTNESS")
    print("=" * 80)

    total_tests = len(test_cases)
    passed_tests = 0
    failed_tests = []

    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = set(test_case["expected_cluster"])
        description = test_case["description"]

        print(f"\n[{i}/{total_tests}] Testing: {description}")
        print(f"   Query: '{query}'")

        # Get top 10 results
        results = await engine.search(query, max_results=10)

        # Check if expected words are in top results
        top_words = [r.word for r in results]
        top_5_words = set(top_words[:5])

        # Calculate precision: how many expected words in top 5?
        matches = expected.intersection(top_5_words)
        precision = len(matches) / len(expected)

        print(f"   Top 5 results: {top_words[:5]}")
        print(f"   Expected in cluster: {sorted(expected)}")
        print(f"   Matches in top 5: {sorted(matches)} ({len(matches)}/{len(expected)})")
        print(f"   Precision: {precision:.1%}")

        # Pass if at least 3/5 expected words in top 5
        if precision >= 0.6:
            print(f"   ✅ PASS (precision {precision:.1%} >= 60%)")
            passed_tests += 1
        else:
            print(f"   ❌ FAIL (precision {precision:.1%} < 60%)")
            failed_tests.append({
                "query": query,
                "description": description,
                "precision": precision,
                "top_results": top_words[:5],
                "expected": sorted(expected)
            })

    # Summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {passed_tests}/{total_tests} ({passed_tests/total_tests:.1%})")
    print(f"❌ Failed: {len(failed_tests)}/{total_tests}")

    if failed_tests:
        print("\n⚠️  FAILED TESTS:")
        for fail in failed_tests:
            print(f"\n   Query: '{fail['query']}' ({fail['description']})")
            print(f"   Precision: {fail['precision']:.1%}")
            print(f"   Got: {fail['top_results']}")
            print(f"   Expected cluster: {fail['expected']}")

    # Return success if all tests passed
    return passed_tests == total_tests


async def test_quantization_quality_loss():
    """Compare INT8 vs float32 results to measure quality loss."""

    print("\n" + "=" * 80)
    print("QUANTIZATION QUALITY LOSS ANALYSIS")
    print("=" * 80)

    test_words = [
        "happy", "joyful", "sad", "gloomy",
        "big", "enormous", "small", "tiny",
        "fast", "rapid", "slow", "sluggish"
    ]

    # Create corpus
    from floridify.corpus.models import CorpusType
    from floridify.models.base import Language

    corpus = Corpus(
        corpus_name="quant_test",
        corpus_type=CorpusType.CUSTOM,
        language=Language.ENGLISH,
        vocabulary=test_words,
        original_vocabulary=test_words,
        lemmatized_vocabulary=test_words,
    )
    await corpus._rebuild_indices()

    # Test with quantization
    print("\n🔄 Testing with INT8 quantization...")
    original_quant = sem_constants.USE_QUANTIZATION
    original_prec = sem_constants.QUANTIZATION_PRECISION

    # Temporarily enable quantization
    import floridify.search.semantic.constants as sem_consts
    sem_consts.USE_QUANTIZATION = True
    sem_consts.QUANTIZATION_PRECISION = "int8"

    engine_int8 = await SemanticSearch.from_corpus(
        corpus=corpus,
        model_name=sem_constants.DEFAULT_SENTENCE_MODEL,
        config=VersionConfig(),
    )

    results_int8 = {}
    for word in ["cheerful", "gigantic", "swift"]:
        results = await engine_int8.search(word, max_results=3)
        results_int8[word] = [(r.word, r.score) for r in results]

    # Test without quantization
    print("\n🔄 Testing with float32 (no quantization)...")
    sem_consts.USE_QUANTIZATION = False

    engine_float32 = await SemanticSearch.from_corpus(
        corpus=corpus,
        model_name=sem_constants.DEFAULT_SENTENCE_MODEL,
        config=VersionConfig(),
    )

    results_float32 = {}
    for word in ["cheerful", "gigantic", "swift"]:
        results = await engine_float32.search(word, max_results=3)
        results_float32[word] = [(r.word, r.score) for r in results]

    # Compare results
    print("\n📊 Comparison:")
    matches = 0
    total = 0
    for query in ["cheerful", "gigantic", "swift"]:
        print(f"\n   Query: '{query}'")
        print(f"   INT8:    {results_int8[query]}")
        print(f"   Float32: {results_float32[query]}")

        # Check if top result is the same
        if results_int8[query][0][0] == results_float32[query][0][0]:
            print(f"   ✅ Top result matches")
            matches += 1
        else:
            print(f"   ❌ Top result differs!")
        total += 1

    # Restore original settings
    sem_consts.USE_QUANTIZATION = original_quant
    sem_consts.QUANTIZATION_PRECISION = original_prec

    print(f"\n📊 Summary: {matches}/{total} queries had matching top results ({matches/total:.1%})")

    return matches == total


if __name__ == "__main__":
    async def main():
        client = None
        try:
            # Initialize MongoDB
            print("🔄 Initializing MongoDB connection...")
            client = await init_mongodb()
            print("✅ MongoDB connected\n")

            # Test correctness
            correctness_ok = await test_semantic_search_correctness()

            # Test quantization quality
            quant_ok = await test_quantization_quality_loss()

            if correctness_ok and quant_ok:
                print("\n✅ ALL VALIDATION TESTS PASSED")
                sys.exit(0)
            else:
                print("\n❌ VALIDATION FAILED")
                sys.exit(1)

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            if client:
                client.close()

    asyncio.run(main())
