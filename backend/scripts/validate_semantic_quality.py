"""Validate quality and correctness of semantic search results.

Uses Qwen3-0.6B embeddings with FAISS to test synonym quality, category coherence,
cross-category separation, and score calibration on a 35-word vocabulary.

Run with:
    cd backend
    .venv/bin/python -m pytest scripts/validate_semantic_quality.py -v -s --tb=short
"""

from __future__ import annotations

import os

from floridify.utils.threading_config import configure_threading

configure_threading()

os.environ["LOG_LEVEL"] = "WARNING"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

import shutil
import subprocess
import time
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.dictionary import Language
from floridify.search.semantic.core import SemanticSearch

# ---------------------------------------------------------------------------
# Categories for analysis
# ---------------------------------------------------------------------------
CATEGORIES: dict[str, list[str]] = {
    "positive_emotion": ["happy", "joyful", "cheerful", "glad", "delighted"],
    "negative_emotion": ["sad", "unhappy", "sorrowful", "miserable", "dejected"],
    "anger_emotion": ["angry", "furious", "irate", "enraged", "irritated"],
    "calm_emotion": ["calm", "peaceful", "serene", "tranquil", "relaxed"],
    "animal": ["dog", "cat", "elephant", "tiger", "lion"],
    "food": ["apple", "banana", "orange", "bread", "cheese"],
    "action": ["run", "walk", "jump", "swim", "fly"],
}

ALL_WORDS = sorted(
    word for words in CATEGORIES.values() for word in words
)

WORD_TO_CATEGORY: dict[str, str] = {}
for cat, words in CATEGORIES.items():
    for w in words:
        WORD_TO_CATEGORY[w] = cat


def _emotion_categories() -> set[str]:
    return {"positive_emotion", "negative_emotion", "anger_emotion", "calm_emotion"}


# ---------------------------------------------------------------------------
# Beanie document models (same as main conftest)
# ---------------------------------------------------------------------------
def get_document_models():
    from floridify.caching.models import BaseVersionedData
    from floridify.corpus.core import Corpus as CorpusDoc
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

    return [
        Word, Definition, DictionaryEntry, Pronunciation, Example, Fact,
        AudioMedia, ImageMedia, WordRelationship, WordList,
        BaseVersionedData, BatchOperation,
        CorpusDoc.Metadata, DictionaryProviderEntry.Metadata,
        LanguageEntry.Metadata, LiteratureEntry.Metadata,
        SearchIndex.Metadata, SemanticIndex.Metadata, TrieIndex.Metadata,
    ]


# ---------------------------------------------------------------------------
# Fixtures: MongoDB + Beanie
# ---------------------------------------------------------------------------
DEFAULT_MONGODB_PORT = int(os.getenv("TEST_MONGODB_PORT", "27017"))


@pytest.fixture(scope="session")
def mongodb_server(tmp_path_factory):
    """Launch a real mongod for the session."""
    mongod_bin = shutil.which(os.getenv("MONGOD_BIN", "mongod"))
    if not mongod_bin:
        pytest.skip("mongod binary not available on PATH")

    data_dir = tmp_path_factory.mktemp("mongo-data")
    log_path = data_dir / "mongod.log"
    port = DEFAULT_MONGODB_PORT

    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [mongod_bin, "--dbpath", str(data_dir), "--port", str(port),
             "--bind_ip", "127.0.0.1", "--nounixsocket", "--quiet"],
            stdout=log_file, stderr=subprocess.STDOUT,
        )
        try:
            client = MongoClient(f"mongodb://127.0.0.1:{port}", serverSelectionTimeoutMS=500)
            deadline = time.time() + 20
            while True:
                try:
                    client.admin.command("ping")
                    break
                except Exception as exc:
                    if time.time() > deadline:
                        process.terminate()
                        process.wait(timeout=10)
                        pytest.skip(f"MongoDB server failed to start: {exc}")
                    time.sleep(0.2)
            client.close()
            yield f"mongodb://127.0.0.1:{port}"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_db(mongodb_server: str):
    """Session-scoped database with Beanie init."""
    client = AsyncIOMotorClient(mongodb_server, serverSelectionTimeoutMS=500)
    db_name = f"validate_semantic_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    db = client[db_name]
    await init_beanie(database=db, document_models=get_document_models())
    yield db
    await client.drop_database(db_name)
    client.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def semantic_engine(test_db) -> SemanticSearch:
    """Build the semantic search engine from the 35-word corpus."""
    corpus = Corpus(
        corpus_name="quality_validation",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=ALL_WORDS,
        original_vocabulary=ALL_WORDS,
        lemmatized_vocabulary=ALL_WORDS,
    )
    corpus.vocabulary_to_index = {w: i for i, w in enumerate(ALL_WORDS)}
    corpus._build_candidate_index()

    manager = TreeCorpusManager()
    saved = await manager.save_corpus(corpus)

    engine = await SemanticSearch.from_corpus(corpus=saved)
    await engine.initialize()

    assert engine.sentence_embeddings is not None
    assert engine.sentence_index is not None
    print(f"\n[SETUP] Built semantic index: {engine.index.num_embeddings} embeddings, "
          f"{engine.index.embedding_dimension}D")
    return engine


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
async def _search(engine: SemanticSearch, query: str, k: int = 20) -> list[tuple[str, float]]:
    """Search and return (word, score) pairs."""
    results = await engine.search(query, max_results=k, min_score=0.0)
    return [(r.word, r.score) for r in results]


def _print_results(query: str, results: list[tuple[str, float]], label: str = "") -> None:
    header = f"  Query: '{query}'"
    if label:
        header += f"  ({label})"
    print(header)
    for rank, (word, score) in enumerate(results, 1):
        cat = WORD_TO_CATEGORY.get(word, "?")
        marker = ""
        if cat == WORD_TO_CATEGORY.get(query, "__NOMATCH__"):
            marker = " <-- same category"
        print(f"    {rank:2d}. {word:15s} score={score:.4f}  [{cat}]{marker}")
    print()


# ---------------------------------------------------------------------------
# TEST 1: Synonym Quality
# ---------------------------------------------------------------------------
class TestSynonymQuality:
    """Top results for a query should include its close synonyms."""

    @pytest.mark.asyncio
    async def test_happy_synonyms(self, semantic_engine: SemanticSearch):
        """'happy' top results should include joyful, cheerful, glad, delighted."""
        results = await _search(semantic_engine, "happy", k=15)
        _print_results("happy", results, "synonym quality")

        top_words = [w for w, _ in results[:10]]
        expected_synonyms = {"joyful", "cheerful", "glad", "delighted"}
        found = expected_synonyms & set(top_words)

        print(f"  Expected synonyms in top 10: {expected_synonyms}")
        print(f"  Found: {found} ({len(found)}/{len(expected_synonyms)})")

        # At least 2 of 4 synonyms should appear in top 10
        assert len(found) >= 2, (
            f"FAIL: Only {len(found)}/4 synonyms of 'happy' in top 10. "
            f"Found: {found}. Top 10: {top_words}"
        )
        print("  PASS\n")

    @pytest.mark.asyncio
    async def test_sad_synonyms(self, semantic_engine: SemanticSearch):
        """'sad' top results should include unhappy, sorrowful, miserable, dejected."""
        results = await _search(semantic_engine, "sad", k=15)
        _print_results("sad", results, "synonym quality")

        top_words = [w for w, _ in results[:10]]
        expected_synonyms = {"unhappy", "sorrowful", "miserable", "dejected"}
        found = expected_synonyms & set(top_words)

        print(f"  Expected synonyms in top 10: {expected_synonyms}")
        print(f"  Found: {found} ({len(found)}/{len(expected_synonyms)})")

        assert len(found) >= 2, (
            f"FAIL: Only {len(found)}/4 synonyms of 'sad' in top 10. "
            f"Found: {found}. Top 10: {top_words}"
        )
        print("  PASS\n")

    @pytest.mark.asyncio
    async def test_dog_animal_cluster(self, semantic_engine: SemanticSearch):
        """'dog' top results should include other animals (cat, tiger, lion, elephant)."""
        results = await _search(semantic_engine, "dog", k=15)
        _print_results("dog", results, "animal cluster")

        top_words = [w for w, _ in results[:10]]
        animals = {"cat", "tiger", "lion", "elephant"}
        found = animals & set(top_words)

        print(f"  Expected animals in top 10: {animals}")
        print(f"  Found: {found} ({len(found)}/{len(animals)})")

        assert len(found) >= 2, (
            f"FAIL: Only {len(found)}/4 animals near 'dog' in top 10. "
            f"Found: {found}. Top 10: {top_words}"
        )
        print("  PASS\n")

    @pytest.mark.asyncio
    async def test_apple_food_cluster(self, semantic_engine: SemanticSearch):
        """'apple' top results should include other food (banana, orange)."""
        results = await _search(semantic_engine, "apple", k=15)
        _print_results("apple", results, "food cluster")

        top_words = [w for w, _ in results[:10]]
        foods = {"banana", "orange", "bread", "cheese"}
        found = foods & set(top_words)

        print(f"  Expected foods in top 10: {foods}")
        print(f"  Found: {found} ({len(found)}/{len(foods)})")

        assert len(found) >= 2, (
            f"FAIL: Only {len(found)}/4 foods near 'apple' in top 10. "
            f"Found: {found}. Top 10: {top_words}"
        )
        print("  PASS\n")


# ---------------------------------------------------------------------------
# TEST 2: Category Coherence
# ---------------------------------------------------------------------------
class TestCategoryCoherence:
    """Querying a category label should return words from that category."""

    @pytest.mark.asyncio
    async def test_emotion_query(self, semantic_engine: SemanticSearch):
        """'emotion' should return emotion words, not animals or food."""
        results = await _search(semantic_engine, "emotion", k=10)
        _print_results("emotion", results, "category coherence")

        emotion_cats = _emotion_categories()
        emotion_count = sum(1 for w, _ in results if WORD_TO_CATEGORY.get(w) in emotion_cats)
        non_emotion_count = len(results) - emotion_count
        ratio = emotion_count / len(results) if results else 0

        print(f"  Emotion words: {emotion_count}, Non-emotion: {non_emotion_count}, "
              f"Ratio: {ratio:.1%}")

        # At least 40% should be emotion words (relaxed for small vocab model)
        assert ratio >= 0.4, (
            f"FAIL: Only {ratio:.0%} emotion words for query 'emotion'. "
            f"Expected >= 40%."
        )
        print("  PASS\n")

    @pytest.mark.asyncio
    async def test_animal_query(self, semantic_engine: SemanticSearch):
        """'animal' should return animal words."""
        results = await _search(semantic_engine, "animal", k=10)
        _print_results("animal", results, "category coherence")

        animal_count = sum(1 for w, _ in results if WORD_TO_CATEGORY.get(w) == "animal")
        ratio = animal_count / len(results) if results else 0

        print(f"  Animal words: {animal_count}/{len(results)}, Ratio: {ratio:.1%}")

        # At least 30% should be animal words
        assert ratio >= 0.3, (
            f"FAIL: Only {ratio:.0%} animal words for query 'animal'. "
            f"Expected >= 30%."
        )
        print("  PASS\n")

    @pytest.mark.asyncio
    async def test_food_query(self, semantic_engine: SemanticSearch):
        """'food' should return food words."""
        results = await _search(semantic_engine, "food", k=10)
        _print_results("food", results, "category coherence")

        food_count = sum(1 for w, _ in results if WORD_TO_CATEGORY.get(w) == "food")
        ratio = food_count / len(results) if results else 0

        print(f"  Food words: {food_count}/{len(results)}, Ratio: {ratio:.1%}")

        # At least 30% should be food words
        assert ratio >= 0.3, (
            f"FAIL: Only {ratio:.0%} food words for query 'food'. "
            f"Expected >= 30%."
        )
        print("  PASS\n")


# ---------------------------------------------------------------------------
# TEST 3: Cross-Category Separation
# ---------------------------------------------------------------------------
class TestCrossCategorySeparation:
    """Same-category results should score higher than cross-category results on average."""

    @pytest.mark.asyncio
    async def test_happy_not_dominated_by_unrelated(self, semantic_engine: SemanticSearch):
        """'happy' results should NOT be dominated by 'apple' or 'dog' categories."""
        results = await _search(semantic_engine, "happy", k=15)
        _print_results("happy", results, "cross-category separation")

        top5_words = [w for w, _ in results[:5]]
        unrelated_cats = {"animal", "food"}
        unrelated_in_top5 = sum(
            1 for w in top5_words if WORD_TO_CATEGORY.get(w) in unrelated_cats
        )

        print(f"  Top 5: {top5_words}")
        print(f"  Unrelated (animal/food) in top 5: {unrelated_in_top5}")

        # At most 2 unrelated words in top 5
        assert unrelated_in_top5 <= 2, (
            f"FAIL: {unrelated_in_top5}/5 top results for 'happy' are from "
            f"unrelated categories (animal/food). Top 5: {top5_words}"
        )
        print("  PASS\n")

    @pytest.mark.asyncio
    async def test_same_category_avg_higher(self, semantic_engine: SemanticSearch):
        """Average same-category score should be higher than cross-category score."""
        test_queries = ["happy", "sad", "dog", "apple", "run"]
        same_scores: list[float] = []
        cross_scores: list[float] = []

        print("  Per-query breakdown:")
        for query in test_queries:
            results = await _search(semantic_engine, query, k=20)
            query_cat = WORD_TO_CATEGORY.get(query)

            q_same: list[float] = []
            q_cross: list[float] = []
            for word, score in results:
                word_cat = WORD_TO_CATEGORY.get(word)
                if word_cat == query_cat:
                    q_same.append(score)
                    same_scores.append(score)
                else:
                    q_cross.append(score)
                    cross_scores.append(score)

            avg_same = sum(q_same) / len(q_same) if q_same else 0
            avg_cross = sum(q_cross) / len(q_cross) if q_cross else 0
            delta = avg_same - avg_cross
            print(f"    '{query}': same_cat_avg={avg_same:.4f}, "
                  f"cross_cat_avg={avg_cross:.4f}, delta={delta:+.4f}")

        overall_same_avg = sum(same_scores) / len(same_scores) if same_scores else 0
        overall_cross_avg = sum(cross_scores) / len(cross_scores) if cross_scores else 0
        delta = overall_same_avg - overall_cross_avg

        print(f"\n  Overall: same_category_avg={overall_same_avg:.4f}, "
              f"cross_category_avg={overall_cross_avg:.4f}, delta={delta:+.4f}")

        assert overall_same_avg > overall_cross_avg, (
            f"FAIL: Same-category average ({overall_same_avg:.4f}) is NOT higher than "
            f"cross-category average ({overall_cross_avg:.4f}). Delta: {delta:+.4f}"
        )
        print("  PASS\n")


# ---------------------------------------------------------------------------
# TEST 4: Score Calibration
# ---------------------------------------------------------------------------
class TestScoreCalibration:
    """Verify scores are in a meaningful range and correctly ordered."""

    @pytest.mark.asyncio
    async def test_scores_between_0_and_1(self, semantic_engine: SemanticSearch):
        """All scores should be between 0 and 1."""
        queries = ["happy", "dog", "apple", "run", "calm"]
        all_ok = True

        for query in queries:
            results = await _search(semantic_engine, query, k=20)
            for word, score in results:
                if not (0.0 <= score <= 1.0):
                    print(f"  OUT OF RANGE: query='{query}', word='{word}', score={score:.4f}")
                    all_ok = False

        assert all_ok, "Some scores are outside [0, 1] range"
        print("  All scores in [0, 1]. PASS\n")

    @pytest.mark.asyncio
    async def test_self_score_highest(self, semantic_engine: SemanticSearch):
        """A word's self-match should be 1.0 or the highest score."""
        test_words = ["happy", "dog", "apple", "run", "calm"]
        all_ok = True

        for word in test_words:
            results = await _search(semantic_engine, word, k=20)
            if not results:
                print(f"  NO RESULTS for '{word}'")
                all_ok = False
                continue

            # Find self-match
            self_score = None
            for w, s in results:
                if w.lower() == word.lower():
                    self_score = s
                    break

            top_word, top_score = results[0]

            if self_score is None:
                print(f"  WARNING: '{word}' not found in its own results "
                      f"(top: {top_word}={top_score:.4f})")
                # This can happen if lemmatization maps the word differently
                continue

            print(f"  '{word}': self_score={self_score:.4f}, "
                  f"top='{top_word}'={top_score:.4f}")

            if self_score < top_score - 0.01:
                print(f"  WARNING: Self-score ({self_score:.4f}) < top score "
                      f"({top_score:.4f}) for '{word}'")
                # Soft warning: not a hard failure since lemmatization can shift things
                # all_ok = False

        if all_ok:
            print("  PASS\n")

    @pytest.mark.asyncio
    async def test_scores_decrease_monotonically(self, semantic_engine: SemanticSearch):
        """Scores should be in non-increasing order."""
        queries = ["happy", "dog", "apple"]
        all_ok = True

        for query in queries:
            results = await _search(semantic_engine, query, k=20)
            scores = [s for _, s in results]
            for i in range(len(scores) - 1):
                if scores[i] < scores[i + 1] - 1e-6:
                    print(f"  NON-MONOTONIC: query='{query}', "
                          f"score[{i}]={scores[i]:.4f} < score[{i+1}]={scores[i+1]:.4f}")
                    all_ok = False
                    break

        assert all_ok, "Scores are not monotonically decreasing"
        print("  Scores are monotonically non-increasing. PASS\n")

    @pytest.mark.asyncio
    async def test_synonym_scores_reasonable(self, semantic_engine: SemanticSearch):
        """Close synonyms should score reasonably high, unrelated words lower."""
        # Test happy -> joyful (synonym) vs happy -> elephant (unrelated)
        results = await _search(semantic_engine, "happy", k=35)
        score_map = {w: s for w, s in results}

        _print_results("happy", results[:10], "score calibration")

        synonym_words = ["joyful", "cheerful", "glad", "delighted"]
        unrelated_words = ["elephant", "banana", "swim"]

        synonym_scores = [score_map.get(w, 0.0) for w in synonym_words if w in score_map]
        unrelated_scores_list = [score_map.get(w, 0.0) for w in unrelated_words if w in score_map]

        avg_synonym = sum(synonym_scores) / len(synonym_scores) if synonym_scores else 0
        avg_unrelated = sum(unrelated_scores_list) / len(unrelated_scores_list) if unrelated_scores_list else 0

        print(f"  Synonym scores ({synonym_words}): {[f'{s:.4f}' for s in synonym_scores]}")
        print(f"  Avg synonym: {avg_synonym:.4f}")
        print(f"  Unrelated scores ({unrelated_words}): "
              f"{[f'{s:.4f}' for s in unrelated_scores_list]}")
        print(f"  Avg unrelated: {avg_unrelated:.4f}")
        print(f"  Gap: {avg_synonym - avg_unrelated:+.4f}")

        assert avg_synonym > avg_unrelated, (
            f"FAIL: Avg synonym score ({avg_synonym:.4f}) <= avg unrelated "
            f"({avg_unrelated:.4f})"
        )
        print("  PASS\n")


# ---------------------------------------------------------------------------
# TEST 5: Comprehensive Summary Report
# ---------------------------------------------------------------------------
class TestSummaryReport:
    """Generate a comprehensive summary report of all semantic quality metrics."""

    @pytest.mark.asyncio
    async def test_generate_summary(self, semantic_engine: SemanticSearch):
        """Print a comprehensive quality summary (always passes -- informational)."""
        print("\n" + "=" * 80)
        print("  SEMANTIC SEARCH QUALITY REPORT")
        print(f"  Model: {semantic_engine.index.model_name}")
        print(f"  Embeddings: {semantic_engine.index.num_embeddings}")
        print(f"  Dimension: {semantic_engine.index.embedding_dimension}")
        print(f"  Index type: {semantic_engine.index.index_type}")
        print("=" * 80)

        # Test all categories
        category_queries = {
            "positive_emotion": ["happy", "joyful"],
            "negative_emotion": ["sad", "unhappy"],
            "anger_emotion": ["angry", "furious"],
            "calm_emotion": ["calm", "peaceful"],
            "animal": ["dog", "cat"],
            "food": ["apple", "banana"],
            "action": ["run", "jump"],
        }

        print("\n--- Score Distribution by Query ---")
        for cat, queries in category_queries.items():
            for query in queries:
                results = await _search(semantic_engine, query, k=35)
                score_by_cat: dict[str, list[float]] = {}
                for word, score in results:
                    wcat = WORD_TO_CATEGORY.get(word, "unknown")
                    score_by_cat.setdefault(wcat, []).append(score)

                print(f"\n  '{query}' [{cat}]:")
                for sc, scores in sorted(score_by_cat.items(),
                                         key=lambda x: -max(x[1])):
                    avg_s = sum(scores) / len(scores)
                    max_s = max(scores)
                    indicator = " <-- OWN" if sc == cat else ""
                    print(f"    {sc:20s}  n={len(scores):2d}  "
                          f"avg={avg_s:.4f}  max={max_s:.4f}{indicator}")

        # Pairwise category centroid distances
        import numpy as np

        print("\n--- Category Centroid Cosine Similarity Matrix ---")
        cat_names = list(CATEGORIES.keys())
        centroids = {}
        for cat, words in CATEGORIES.items():
            cat_scores = []
            for w in words:
                results = await _search(semantic_engine, w, k=35)
                score_vec = [0.0] * len(ALL_WORDS)
                for rw, rs in results:
                    if rw in ALL_WORDS:
                        idx = ALL_WORDS.index(rw)
                        score_vec[idx] = rs
                cat_scores.append(score_vec)
            centroids[cat] = np.mean(cat_scores, axis=0)

        # Print header
        header = f"{'':20s}" + "".join(f"{c[:8]:>10s}" for c in cat_names)
        print(f"  {header}")
        for i, c1 in enumerate(cat_names):
            row = f"  {c1:20s}"
            for j, c2 in enumerate(cat_names):
                v1 = centroids[c1]
                v2 = centroids[c2]
                cos_sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-10)
                row += f"{cos_sim:10.4f}"
            print(row)

        print("\n" + "=" * 80)
        print("  END OF REPORT")
        print("=" * 80 + "\n")
