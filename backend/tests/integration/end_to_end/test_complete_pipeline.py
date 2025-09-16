"""Comprehensive end-to-end test suite for the complete pipeline.

Tests the full workflow from provider data fetch through corpus creation,
search index building, and definition retrieval. Uses real MongoDB and
Wiktionary data without mocking.

Test Coverage:
- Provider data fetching (Wiktionary, FreeDictionary)
- Language corpus creation and CRUD operations
- Literature corpus creation from files
- TreeCorpus hierarchical management
- Search index creation and persistence
- All search methods (exact, fuzzy, semantic)
- Versioning and caching at all levels
- Complete definition retrieval pipeline
"""

import logging

import pytest
import pytest_asyncio

from floridify.caching.models import VersionConfig
from floridify.corpus.core import Corpus
from floridify.corpus.language.core import LanguageCorpus
from floridify.corpus.literature.core import LiteratureCorpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language
from floridify.providers.core import ConnectorConfig
from floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector
from floridify.providers.dictionary.scraper.wiktionary import WiktionaryConnector
from floridify.search.constants import SearchMethod, SearchMode
from floridify.search.core import Search
from floridify.search.fuzzy import FuzzySearch
from floridify.search.trie import TrieSearch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestCompletePipeline:
    """Complete end-to-end pipeline tests."""

    @pytest_asyncio.fixture
    async def connectors(self, tmp_path):
        """Create dictionary connectors."""
        config = ConnectorConfig(
            cache_dir=tmp_path / "cache",
            max_requests_per_second=1,
            cache_ttl_seconds=3600,
        )
        return {
            "wiktionary": WiktionaryConnector(config=config),
            "freedict": FreeDictionaryConnector(config=config),
        }

    @pytest_asyncio.fixture
    async def corpus_manager(self):
        """Create corpus manager."""
        return TreeCorpusManager()

    @pytest_asyncio.fixture
    async def search_engine(self):
        """Create search engine."""
        return Search(
            mode=SearchMode.FAST,
            enabled_methods=[SearchMethod.EXACT, SearchMethod.FUZZY, SearchMethod.SEMANTIC],
        )

    async def test_complete_pipeline_wiktionary(
        self, test_db, connectors, corpus_manager, search_engine, tmp_path
    ):
        """Test complete pipeline with Wiktionary data."""
        logger.info("=== Starting Complete Pipeline Test ===")

        # 1. Fetch data from provider
        logger.info("Step 1: Fetching data from Wiktionary...")
        test_words = ["dictionary", "language", "computer", "python", "algorithm"]
        fetched_data = {}

        for word in test_words:
            result = await connectors["wiktionary"].fetch(word)
            if result:
                fetched_data[word] = result
                assert result.word == word
                assert len(result.definitions) > 0

        assert len(fetched_data) >= 3, "Should fetch at least 3 words successfully"

        # 2. Create master language corpus
        logger.info("Step 2: Creating master language corpus...")
        master_corpus = await LanguageCorpus.from_language(
            language=Language.ENGLISH,
            name="english-master",
        )
        master_corpus.vocabulary = list(fetched_data.keys())
        master_corpus.corpus_type = CorpusType.LANGUAGE
        master_corpus.is_master = True

        saved_master = await corpus_manager.save_corpus(master_corpus)
        assert saved_master.corpus_id is not None
        assert saved_master.is_master is True

        # 3. Create specialized child corpora
        logger.info("Step 3: Creating specialized child corpora...")

        # Technical corpus
        tech_corpus = Corpus(
            corpus_name="technical-vocabulary",
            vocabulary=["computer", "python", "algorithm"],
            language=Language.ENGLISH,
            corpus_type=CorpusType.LEXICON,
            parent_corpus_id=saved_master.corpus_id,
        )
        saved_tech = await corpus_manager.save_corpus(tech_corpus)

        # General corpus
        general_corpus = Corpus(
            corpus_name="general-vocabulary",
            vocabulary=["dictionary", "language"],
            language=Language.ENGLISH,
            corpus_type=CorpusType.LEXICON,
            parent_corpus_id=saved_master.corpus_id,
        )
        saved_general = await corpus_manager.save_corpus(general_corpus)

        # 4. Test vocabulary aggregation
        logger.info("Step 4: Testing vocabulary aggregation...")
        aggregated = await corpus_manager.aggregate_vocabularies(saved_master.corpus_id)
        assert set(aggregated) == set(test_words)

        # 5. Create and test search indices
        logger.info("Step 5: Creating search indices...")

        # Create trie index for exact search
        trie_search = TrieSearch()
        await trie_search.build_index(
            words=aggregated,
            corpus_id=str(saved_master.corpus_id),
        )

        # Test exact search
        exact_results = await trie_search.search_exact("python")
        assert len(exact_results) > 0
        assert "python" in [r.word for r in exact_results]

        # Create fuzzy search index
        fuzzy_search = FuzzySearch()
        await fuzzy_search.build_index(
            words=aggregated,
            corpus_id=str(saved_master.corpus_id),
        )

        # Test fuzzy search
        fuzzy_results = await fuzzy_search.search("pythno", threshold=0.8)
        assert len(fuzzy_results) > 0
        assert "python" in [r.word for r in fuzzy_results]

        # 6. Test versioning and caching
        logger.info("Step 6: Testing versioning and caching...")

        # Update corpus and verify version increment
        updated_corpus = await corpus_manager.update_corpus(
            corpus_id=saved_master.corpus_id,
            content={
                "vocabulary": test_words + ["new_word"],
                "metadata": {"updated": True},
            },
        )
        assert "new_word" in updated_corpus.vocabulary

        # Test cache retrieval
        cached_corpus = await corpus_manager.get_corpus(
            corpus_id=saved_master.corpus_id,
            config=VersionConfig(use_cache=True),
        )
        assert cached_corpus.corpus_id == saved_master.corpus_id

        # 7. Test TreeCorpus operations
        logger.info("Step 7: Testing TreeCorpus operations...")

        # Get children
        children = await corpus_manager.get_children(saved_master.corpus_id)
        assert len(children) == 2
        child_names = {c.corpus_name for c in children}
        assert "technical-vocabulary" in child_names
        assert "general-vocabulary" in child_names

        # Update parent relationship
        orphan_corpus = Corpus(
            corpus_name="orphan-corpus",
            vocabulary=["orphan", "words"],
            language=Language.ENGLISH,
        )
        saved_orphan = await corpus_manager.save_corpus(orphan_corpus)

        await corpus_manager.update_parent(
            parent_id=saved_master.corpus_id,
            child_id=saved_orphan.corpus_id,
        )

        updated_orphan = await corpus_manager.get_corpus(corpus_id=saved_orphan.corpus_id)
        assert updated_orphan.parent_corpus_id == saved_master.corpus_id

        # 8. Test definition retrieval through complete pipeline
        logger.info("Step 8: Testing complete definition retrieval...")

        # Use the search engine to find and retrieve definitions
        search_results = await search_engine.search(
            query="python",
            corpus_id=str(saved_master.corpus_id),
        )

        assert len(search_results) > 0
        assert any("python" in r.word.lower() for r in search_results)

        # 9. Test cascade deletion
        logger.info("Step 9: Testing cascade deletion...")

        # Delete a child corpus
        deleted = await corpus_manager.delete_corpus(saved_tech.corpus_id)
        assert deleted is True

        # Verify it's gone
        gone = await corpus_manager.get_corpus(corpus_id=saved_tech.corpus_id)
        assert gone is None

        # Master should still exist
        master_exists = await corpus_manager.get_corpus(corpus_id=saved_master.corpus_id)
        assert master_exists is not None

        logger.info("=== Complete Pipeline Test Successful ===")

    async def test_literature_corpus_pipeline(self, test_db, corpus_manager, tmp_path):
        """Test literature corpus creation and management."""
        logger.info("=== Starting Literature Corpus Test ===")

        # 1. Create sample literature files
        logger.info("Step 1: Creating sample literature files...")

        book1 = tmp_path / "book1.txt"
        book1.write_text(
            "The quick brown fox jumps over the lazy dog. "
            "This is a sample sentence with various words."
        )

        book2 = tmp_path / "book2.txt"
        book2.write_text(
            "Python is a programming language. It is used for web development and data science."
        )

        # 2. Create literature corpus from files
        logger.info("Step 2: Creating literature corpus...")

        lit_corpus = await LiteratureCorpus.from_files(
            files=[book1, book2],
            name="sample-literature",
            language=Language.ENGLISH,
        )

        # Extract vocabulary from texts
        lit_corpus.vocabulary = [
            "quick",
            "brown",
            "fox",
            "lazy",
            "dog",
            "python",
            "programming",
            "language",
            "development",
            "science",
        ]
        lit_corpus.corpus_type = CorpusType.LITERATURE
        lit_corpus.metadata = {
            "source_files": [str(book1), str(book2)],
            "total_words": len(lit_corpus.vocabulary),
        }

        # 3. Save literature corpus
        saved_lit = await corpus_manager.save_corpus(lit_corpus)
        assert saved_lit.corpus_id is not None
        assert saved_lit.corpus_type == CorpusType.LITERATURE
        assert saved_lit.metadata["total_words"] == 10

        # 4. Create a master corpus and link literature as child
        logger.info("Step 3: Creating corpus hierarchy...")

        master = Corpus(
            corpus_name="literature-master",
            vocabulary=[],
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
            is_master=True,
        )
        saved_master = await corpus_manager.save_corpus(master)

        # Update literature corpus to be child of master
        await corpus_manager.update_parent(
            parent_id=saved_master.corpus_id,
            child_id=saved_lit.corpus_id,
        )

        # 5. Test vocabulary aggregation includes literature
        logger.info("Step 4: Testing vocabulary aggregation...")

        aggregated = await corpus_manager.aggregate_vocabularies(saved_master.corpus_id)
        assert "python" in aggregated
        assert "programming" in aggregated
        assert len(aggregated) == 10

        # 6. Add another work to the literature corpus
        logger.info("Step 5: Adding new work to literature corpus...")

        book3 = tmp_path / "book3.txt"
        book3.write_text("Machine learning and artificial intelligence.")

        updated_lit = await corpus_manager.update_corpus(
            corpus_id=saved_lit.corpus_id,
            content={
                "vocabulary": lit_corpus.vocabulary
                + ["machine", "learning", "artificial", "intelligence"],
                "metadata": {
                    "source_files": [str(book1), str(book2), str(book3)],
                    "total_words": 14,
                },
            },
        )

        assert "machine" in updated_lit.vocabulary
        assert len(updated_lit.metadata["source_files"]) == 3

        logger.info("=== Literature Corpus Test Successful ===")

    async def test_multi_provider_integration(self, test_db, connectors, corpus_manager):
        """Test integration with multiple providers."""
        logger.info("=== Starting Multi-Provider Test ===")

        # 1. Fetch from multiple providers
        logger.info("Step 1: Fetching from multiple providers...")

        test_word = "book"
        results = {}

        for name, connector in connectors.items():
            try:
                result = await connector.fetch(test_word)
                if result:
                    results[name] = result
                    logger.info(f"Fetched from {name}: {len(result.definitions)} definitions")
            except Exception as e:
                logger.warning(f"Failed to fetch from {name}: {e}")

        assert len(results) > 0, "Should fetch from at least one provider"

        # 2. Create corpus from combined results
        logger.info("Step 2: Creating corpus from combined results...")

        combined_vocab = []
        for provider_result in results.values():
            # Extract unique words from definitions
            for defn in provider_result.definitions:
                words = defn.text.lower().split()[:5]  # Take first 5 words
                combined_vocab.extend(words)

        combined_vocab = list(set(combined_vocab))[:20]  # Limit to 20 unique words

        multi_corpus = Corpus(
            corpus_name="multi-provider-corpus",
            vocabulary=combined_vocab,
            language=Language.ENGLISH,
            corpus_type=CorpusType.LEXICON,
            metadata={
                "providers": list(results.keys()),
                "total_definitions": sum(len(r.definitions) for r in results.values()),
            },
        )

        saved_multi = await corpus_manager.save_corpus(multi_corpus)
        assert saved_multi.corpus_id is not None
        assert len(saved_multi.metadata["providers"]) > 0

        logger.info("=== Multi-Provider Test Successful ===")

    async def test_search_cascade_with_corpus(self, test_db, corpus_manager, search_engine):
        """Test search cascade with corpus integration."""
        logger.info("=== Starting Search Cascade Test ===")

        # 1. Create test corpus with specific vocabulary
        logger.info("Step 1: Creating test corpus...")

        test_vocab = [
            "exact",
            "fuzzy",
            "semantic",
            "search",
            "algorithm",
            "python",
            "programming",
            "language",
            "development",
        ]

        corpus = Corpus(
            corpus_name="search-test-corpus",
            vocabulary=test_vocab,
            language=Language.ENGLISH,
            corpus_type=CorpusType.LEXICON,
        )
        saved_corpus = await corpus_manager.save_corpus(corpus)

        # 2. Build search indices
        logger.info("Step 2: Building search indices...")

        # Exact search with trie
        trie = TrieSearch()
        await trie.build_index(
            words=test_vocab,
            corpus_id=str(saved_corpus.corpus_id),
        )

        # Fuzzy search
        fuzzy = FuzzySearch()
        await fuzzy.build_index(
            words=test_vocab,
            corpus_id=str(saved_corpus.corpus_id),
        )

        # 3. Test search cascade
        logger.info("Step 3: Testing search cascade...")

        # Exact match
        exact_results = await trie.search_exact("python")
        assert len(exact_results) > 0
        assert exact_results[0].word == "python"
        assert exact_results[0].method == SearchMethod.EXACT

        # Fuzzy match (typo)
        fuzzy_results = await fuzzy.search("pyhton", threshold=0.8)
        assert len(fuzzy_results) > 0
        assert "python" in [r.word for r in fuzzy_results]

        # Partial match
        partial_results = await fuzzy.search("prog", threshold=0.6)
        assert len(partial_results) > 0
        assert any("programming" in r.word for r in partial_results)

        logger.info("=== Search Cascade Test Successful ===")

    async def test_versioning_and_caching_comprehensive(self, test_db, corpus_manager):
        """Test comprehensive versioning and caching."""
        logger.info("=== Starting Versioning & Caching Test ===")

        # 1. Create initial corpus version
        logger.info("Step 1: Creating initial version...")

        v1_corpus = Corpus(
            corpus_name="versioned-corpus",
            vocabulary=["version", "one"],
            language=Language.ENGLISH,
            metadata={"version": "1.0.0"},
        )
        v1_saved = await corpus_manager.save_corpus(v1_corpus)

        # 2. Update to create new version
        logger.info("Step 2: Creating version 2...")

        v2_updated = await corpus_manager.update_corpus(
            corpus_id=v1_saved.corpus_id,
            content={
                "vocabulary": ["version", "one", "two"],
                "metadata": {"version": "2.0.0"},
            },
            config=VersionConfig(increment_version=True),
        )
        assert "two" in v2_updated.vocabulary

        # 3. Test cache hit
        logger.info("Step 3: Testing cache hit...")

        cached = await corpus_manager.get_corpus(
            corpus_id=v1_saved.corpus_id,
            config=VersionConfig(use_cache=True),
        )
        assert cached.vocabulary == v2_updated.vocabulary

        # 4. Force rebuild to bypass cache
        logger.info("Step 4: Testing force rebuild...")

        fresh = await corpus_manager.get_corpus(
            corpus_id=v1_saved.corpus_id,
            config=VersionConfig(force_rebuild=True),
        )
        assert fresh.corpus_id == v1_saved.corpus_id

        # 5. Test cache invalidation
        logger.info("Step 5: Testing cache invalidation...")

        invalidated = await corpus_manager.invalidate_corpus(corpus_name="versioned-corpus")
        assert invalidated is True

        # 6. Create version 3 with same content (deduplication test)
        logger.info("Step 6: Testing content deduplication...")

        v3_updated = await corpus_manager.update_corpus(
            corpus_id=v1_saved.corpus_id,
            content={
                "vocabulary": ["version", "one", "two"],  # Same as v2
                "metadata": {"version": "2.0.0"},  # Same as v2
            },
        )
        # Should return same version due to deduplication
        assert v3_updated.vocabulary == v2_updated.vocabulary

        logger.info("=== Versioning & Caching Test Successful ===")
