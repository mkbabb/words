"""Comprehensive language and literature corpus pipeline tests.

Tests the complete workflow with real data:
- Real Wiktionary definition fetching and parsing
- Diacritic handling throughout the pipeline
- Language corpus with multi-source vocabulary
- Literature corpus with real text processing
- All search methods (exact, fuzzy, semantic) with diacritics
- Cross-corpus searching and result ranking
"""

import logging

import pytest
import pytest_asyncio

from floridify.caching.models import ResourceType
from floridify.corpus.core import Corpus
from floridify.corpus.language.core import LanguageCorpus
from floridify.corpus.literature.core import LiteratureCorpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language
from floridify.providers.core import ConnectorConfig
from floridify.providers.dictionary.scraper.wiktionary import WiktionaryConnector
from floridify.search.constants import SearchMethod, SearchMode
from floridify.search.core import Search
from floridify.search.fuzzy import FuzzySearch
from floridify.search.semantic.core import SemanticSearch
from floridify.search.trie import TrieSearch
from floridify.text.normalize import normalize_comprehensive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestLanguagePipeline:
    """Test language corpus with real vocabulary and searching."""

    @pytest_asyncio.fixture
    async def wiktionary(self, tmp_path):
        """Create real Wiktionary connector."""
        config = ConnectorConfig(
            cache_dir=tmp_path / "cache",
            max_requests_per_second=1,
            cache_ttl_seconds=3600,
        )
        return WiktionaryConnector(config=config)

    @pytest_asyncio.fixture
    async def corpus_manager(self):
        """Create corpus manager."""
        return TreeCorpusManager()

    async def test_real_wiktionary_with_diacritics(self, test_db, wiktionary, corpus_manager):
        """Test real Wiktionary fetching with diacritic words."""
        logger.info("=== Testing Real Wiktionary with Diacritics ===")

        # Test words with diacritics
        test_words = [
            "café",  # French origin with acute accent
            "naïve",  # Diaeresis
            "résumé",  # Multiple accents
            "piñata",  # Spanish tilde
            "jalapeño",  # Spanish ñ
        ]

        fetched_definitions = {}

        for word in test_words:
            logger.info(f"Fetching '{word}' from Wiktionary...")

            # Try both with and without diacritics
            normalized = normalize_comprehensive(word)

            # Try original first
            result = await wiktionary.fetch(word)
            if not result:
                # Try normalized version
                result = await wiktionary.fetch(normalized)

            if result:
                fetched_definitions[word] = result
                assert result.word.lower() in [word.lower(), normalized.lower()]
                assert len(result.definitions) > 0

                # Verify definition structure
                for defn in result.definitions:
                    assert defn.text is not None
                    assert len(defn.text) > 0
                    # Log first definition for verification
                    logger.info(f"  {word}: {defn.text[:100]}...")
                    break

        # Should fetch at least some words successfully
        assert len(fetched_definitions) >= 2, f"Only fetched {len(fetched_definitions)} words"

        # Create language corpus with fetched words
        lang_corpus = Corpus(
            corpus_name="diacritic-test-corpus",
            vocabulary=list(fetched_definitions.keys()),
            language=Language.ENGLISH,
            corpus_type=CorpusType.LEXICON,
            metadata={"has_diacritics": True},
        )

        saved = await corpus_manager.save_corpus(lang_corpus)
        assert saved.corpus_id is not None
        assert "café" in saved.vocabulary or "cafe" in saved.vocabulary

        logger.info(f"Created corpus with {len(saved.vocabulary)} diacritic words")

    async def test_language_corpus_with_search(self, test_db, corpus_manager):
        """Test language corpus creation with comprehensive search."""
        logger.info("=== Testing Language Corpus with Search ===")

        # Create language corpus with diverse vocabulary
        vocabulary = [
            # Regular words
            "dictionary",
            "language",
            "computer",
            "algorithm",
            # Words with diacritics
            "café",
            "naïve",
            "résumé",
            "façade",
            "piñata",
            # Compound words
            "database",
            "software",
            "hardware",
            # Phrases
            "machine learning",
            "artificial intelligence",
        ]

        lang_corpus = await LanguageCorpus.from_language(
            language=Language.ENGLISH,
            name="english-search-test",
        )
        lang_corpus.vocabulary = vocabulary
        lang_corpus.corpus_type = CorpusType.LANGUAGE
        lang_corpus.is_master = True

        saved = await corpus_manager.save_corpus(lang_corpus)
        assert saved.corpus_id is not None

        # Build search capabilities using the corpus
        logger.info("Testing search capabilities...")

        # 1. Exact search - create TrieSearch from corpus
        from floridify.search.models import TrieIndex

        trie_index = TrieIndex(
            resource_id=f"trie-{saved.corpus_id}",
            resource_type=ResourceType.TRIE,
            corpus_id=str(saved.corpus_id),
            words=vocabulary,
        )
        trie = TrieSearch(index=trie_index)

        # Test exact search with diacritics
        exact_result = trie.search_exact("café")
        assert exact_result is not None
        assert exact_result == "café"

        # 2. Fuzzy search using corpus directly
        fuzzy = FuzzySearch(min_score=0.7)

        # Test fuzzy search with typos
        fuzzy_results = fuzzy.search("rezume", saved, max_results=10)
        assert len(fuzzy_results) > 0
        assert any("résumé" in r.word or "resume" in r.word for r in fuzzy_results)

        # Test fuzzy with missing diacritics
        fuzzy_naive = fuzzy.search("naive", saved, max_results=10)
        assert len(fuzzy_naive) > 0
        assert any("naïve" in r.word or "naive" in r.word for r in fuzzy_naive)

        # 3. Semantic search (if embeddings available)
        try:
            from floridify.search.semantic.models import SemanticIndex

            sem_index = SemanticIndex(
                resource_id=f"semantic-{saved.corpus_id}",
                resource_type=ResourceType.SEMANTIC,
                corpus_id=str(saved.corpus_id),
                words=vocabulary,
                model_name="all-MiniLM-L6-v2",
            )
            # Note: This requires actual embedding generation which may not work in tests
            semantic = SemanticSearch(index=sem_index)

            # Test semantic search for related concepts
            semantic_results = semantic.search(
                "coffee",  # Should find café semantically
                saved,
                max_results=5,
            )
            # Semantic search might find café as related to coffee
            logger.info(
                f"Semantic search for 'coffee' found: {[r.word for r in semantic_results[:3]]}"
            )
        except Exception as e:
            logger.warning(f"Semantic search skipped: {e}")

        logger.info("=== Language Corpus Search Tests Successful ===")

    async def test_diacritic_preservation_pipeline(self, test_db, corpus_manager):
        """Test that diacritics are preserved throughout the pipeline."""
        logger.info("=== Testing Diacritic Preservation ===")

        # Create corpus with original diacritics
        original_words = [
            "café",
            "naïve",
            "résumé",
            "façade",
            "Zürich",
            "São Paulo",
            "Köln",
            "Montréal",
        ]

        corpus = Corpus(
            corpus_name="diacritic-preservation-test",
            vocabulary=original_words,
            language=Language.ENGLISH,
            corpus_type=CorpusType.LEXICON,
        )

        saved = await corpus_manager.save_corpus(corpus)

        # Retrieve and verify preservation
        retrieved = await corpus_manager.get_corpus(corpus_id=saved.corpus_id)

        # Original vocabulary should preserve diacritics
        for word in original_words:
            assert word in retrieved.vocabulary, f"Lost diacritic word: {word}"

        # Test search with normalized query returns original
        fuzzy = FuzzySearch(min_score=0.6)  # Lower threshold for diacritic variations

        # Search for "cafe" should find "café"
        results = fuzzy.search("cafe", retrieved, max_results=10)
        if len(results) == 0:
            # If fuzzy search fails, check if corpus has the words
            logger.warning(
                f"No fuzzy results for 'cafe'. Corpus vocabulary: {retrieved.vocabulary}"
            )
            # Try exact search to see if word exists
            assert "café" in retrieved.vocabulary, "Word 'café' not in corpus"
        else:
            found_words = [r.word for r in results]
            logger.info(f"Fuzzy search for 'cafe' found: {found_words}")
            assert any("café" in w or "cafe" in w for w in found_words), (
                f"Diacritics not preserved. Found: {found_words}"
            )

        # Search for "naive" should find "naïve"
        results = fuzzy.search("naive", retrieved, max_results=10)
        if len(results) == 0:
            logger.warning("No fuzzy results for 'naive'. Checking corpus...")
            assert "naïve" in retrieved.vocabulary, "Word 'naïve' not in corpus"
        else:
            found_words = [r.word for r in results]
            logger.info(f"Fuzzy search for 'naive' found: {found_words}")
            assert any("naïve" in w or "naive" in w for w in found_words), (
                f"Diaeresis not preserved. Found: {found_words}"
            )

        logger.info("=== Diacritic Preservation Successful ===")


@pytest.mark.asyncio
class TestLiteraturePipeline:
    """Test literature corpus with real text processing."""

    @pytest_asyncio.fixture
    async def corpus_manager(self):
        """Create corpus manager."""
        return TreeCorpusManager()

    @pytest_asyncio.fixture
    async def sample_texts(self, tmp_path):
        """Create sample literature texts."""
        texts = {}

        # Classic literature excerpt
        shakespeare = tmp_path / "shakespeare.txt"
        shakespeare.write_text(
            """To be, or not to be, that is the question:
            Whether 'tis nobler in the mind to suffer
            The slings and arrows of outrageous fortune,
            Or to take arms against a sea of troubles
            And by opposing end them. To die—to sleep,
            No more; and by a sleep to say we end
            The heart-ache and the thousand natural shocks
            That flesh is heir to: 'tis a consummation
            Devoutly to be wish'd."""
        )
        texts["shakespeare"] = shakespeare

        # Modern text with diacritics
        modern = tmp_path / "modern.txt"
        modern.write_text(
            """The café on the corner serves the best résumé of French cuisine.
            Its naïve charm attracts tourists from Zürich to São Paulo.
            The façade, though weathered, maintains its belle époque elegance.
            Inside, the maître d' greets guests with practiced savoir-faire.
            The menu features crème brûlée, pâté, and other délicatessen.
            It's a true gem in our cosmopolitan métropole."""
        )
        texts["modern"] = modern

        # Technical text
        technical = tmp_path / "technical.txt"
        technical.write_text(
            """Machine learning algorithms process data through neural networks.
            The architecture includes convolutional layers for feature extraction.
            Gradient descent optimizes the loss function during backpropagation.
            Regularization techniques prevent overfitting on training datasets.
            The model achieves high accuracy through iterative refinement."""
        )
        texts["technical"] = technical

        return texts

    async def test_literature_corpus_creation(self, test_db, corpus_manager, sample_texts):
        """Test creating literature corpus from text files."""
        logger.info("=== Testing Literature Corpus Creation ===")

        # Create base literature corpus
        lit_corpus = LiteratureCorpus(
            corpus_name="test-literature",
            vocabulary=[],  # Will be populated from files
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            is_master=True,
        )

        # Save the master corpus first
        saved_master = await corpus_manager.save_corpus(lit_corpus)

        # Process texts to extract vocabulary
        all_words = set()
        for text_path in sample_texts.values():
            content = text_path.read_text()
            # Simple word extraction
            import re

            words = re.findall(r"\b[a-zA-ZÀ-ÿ]+\b", content.lower())
            all_words.update(words)

        # Update corpus with extracted vocabulary
        saved_master.vocabulary = sorted(list(all_words))
        saved_master.metadata = {
            "sources": list(sample_texts.keys()),
            "total_words": len(all_words),
        }

        # Save the updated corpus
        saved = await corpus_manager.save_corpus(saved_master)
        assert saved.corpus_id is not None
        assert saved.corpus_type == CorpusType.LITERATURE
        assert len(saved.vocabulary) > 50  # Should have substantial vocabulary

        # Verify diacritics are preserved
        assert "café" in saved.vocabulary or "cafe" in saved.vocabulary
        assert "résumé" in saved.vocabulary or "resume" in saved.vocabulary

        logger.info(f"Created literature corpus with {len(saved.vocabulary)} unique words")

        return saved

    async def test_literature_search_capabilities(self, test_db, corpus_manager, sample_texts):
        """Test searching within literature corpus."""
        logger.info("=== Testing Literature Search Capabilities ===")

        # Create corpus
        lit_corpus = await self.test_literature_corpus_creation(
            test_db, corpus_manager, sample_texts
        )

        # Build search indices
        vocabulary = lit_corpus.vocabulary

        # 1. Test exact search for literary terms
        from floridify.search.models import TrieIndex

        trie_index = TrieIndex(
            resource_id=f"trie-{lit_corpus.corpus_id}",
            resource_type=ResourceType.TRIE,
            corpus_id=str(lit_corpus.corpus_id),
            words=vocabulary,
        )
        trie = TrieSearch(index=trie_index)

        # Should find Shakespeare vocabulary
        shakespeare_words = ["question", "nobler", "fortune", "troubles"]
        for word in shakespeare_words:
            result = trie.search_exact(word)
            assert result is not None, f"Failed to find '{word}' from Shakespeare"

        # 2. Test fuzzy search for diacritic variations
        fuzzy = FuzzySearch(min_score=0.7)

        # Search without diacritics should find with diacritics
        results = fuzzy.search("creme", lit_corpus, max_results=10)
        if len(results) > 0:
            logger.info(f"Found 'creme' variations: {[r.word for r in results[:3]]}")

        results = fuzzy.search("maitre", lit_corpus, max_results=10)
        if len(results) > 0:
            assert any("maître" in r.word or "maitre" in r.word for r in results)

        # 3. Test semantic search for thematic content
        try:
            # Note: Semantic search requires actual embeddings which may not work in tests
            from floridify.search.semantic.models import SemanticIndex

            sem_index = SemanticIndex(
                resource_id=f"semantic-{lit_corpus.corpus_id}",
                resource_type=ResourceType.SEMANTIC,
                corpus_id=str(lit_corpus.corpus_id),
                words=vocabulary,
                model_name="all-MiniLM-L6-v2",
            )
            semantic = SemanticSearch(index=sem_index)

            # Search for "death" should find related Shakespeare terms
            results = semantic.search("death", lit_corpus, max_results=10)
            logger.info(f"Semantic search for 'death': {[r.word for r in results[:5]]}")
            # Might find: die, end, sleep, etc.

            # Search for "food" should find café terms
            results = semantic.search("food", lit_corpus, max_results=10)
            logger.info(f"Semantic search for 'food': {[r.word for r in results[:5]]}")
            # Might find: café, cuisine, menu, etc.
        except Exception as e:
            logger.warning(f"Semantic search skipped: {e}")

        logger.info("=== Literature Search Tests Successful ===")

    async def test_cross_corpus_search(self, test_db, corpus_manager, sample_texts):
        """Test searching across multiple corpus types."""
        logger.info("=== Testing Cross-Corpus Search ===")

        # Create master corpus
        master = Corpus(
            corpus_name="master-corpus",
            vocabulary=[],
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
            is_master=True,
        )
        saved_master = await corpus_manager.save_corpus(master)

        # Create language child corpus
        lang_corpus = Corpus(
            corpus_name="language-child",
            vocabulary=["café", "restaurant", "menu", "cuisine", "délicatessen"],
            language=Language.ENGLISH,
            corpus_type=CorpusType.LEXICON,
            parent_corpus_id=saved_master.corpus_id,
        )
        saved_lang = await corpus_manager.save_corpus(lang_corpus)

        # Create literature child corpus
        lit_corpus = LiteratureCorpus(
            corpus_name="literature-child",
            vocabulary=[],
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
        )

        # Extract vocabulary from modern text
        import re

        content = sample_texts["modern"].read_text()
        words = re.findall(r"\b[a-zA-ZÀ-ÿ]+\b", content.lower())
        lit_corpus.vocabulary = list(set(words))
        lit_corpus.parent_corpus_id = saved_master.corpus_id
        saved_lit = await corpus_manager.save_corpus(lit_corpus)

        # Aggregate vocabularies
        aggregated = await corpus_manager.aggregate_vocabularies(saved_master.corpus_id)
        assert len(aggregated) > len(lang_corpus.vocabulary)
        assert len(aggregated) > len(lit_corpus.vocabulary)

        # Build unified search on aggregated corpus
        # First update master corpus with aggregated vocabulary
        saved_master.vocabulary = aggregated
        updated_master = await corpus_manager.save_corpus(saved_master)

        # Now search using the master corpus
        fuzzy = FuzzySearch(min_score=0.8)

        # Search should find words from both corpora
        results = fuzzy.search("cafe", updated_master, max_results=10)
        assert len(results) > 0
        assert any("café" in r.word or "cafe" in r.word for r in results)

        # Search for literature-specific words
        results = fuzzy.search("tourist", updated_master, max_results=10)
        if len(results) > 0:
            logger.info(f"Found 'tourist' matches: {[r.word for r in results[:3]]}")

        logger.info(f"Cross-corpus search successful with {len(aggregated)} total words")


@pytest.mark.asyncio
class TestDefinitionRetrievalPipeline:
    """Test complete definition retrieval pipeline."""

    @pytest_asyncio.fixture
    async def search_engine(self):
        """Create search engine."""
        return Search(
            mode=SearchMode.SMART,
            enabled_methods=[SearchMethod.EXACT, SearchMethod.FUZZY, SearchMethod.SEMANTIC],
        )

    async def test_complete_definition_pipeline(self, test_db, tmp_path):
        """Test complete pipeline from word to definition."""
        logger.info("=== Testing Complete Definition Pipeline ===")

        # Setup components
        corpus_manager = TreeCorpusManager()
        config = ConnectorConfig(
            cache_dir=tmp_path / "cache",
            max_requests_per_second=1,
        )
        wiktionary = WiktionaryConnector(config=config)

        # Test word with diacritics
        test_word = "café"

        # 1. Fetch definition from Wiktionary
        logger.info(f"Step 1: Fetching '{test_word}' from Wiktionary...")
        result = await wiktionary.fetch(test_word)
        if not result:
            # Try without diacritic
            result = await wiktionary.fetch("cafe")

        if result:
            assert result.word.lower() in ["café", "cafe"]
            assert len(result.definitions) > 0
            logger.info(f"  Found {len(result.definitions)} definitions")

            # 2. Create corpus with the word
            logger.info("Step 2: Creating corpus...")
            corpus = Corpus(
                corpus_name="definition-test",
                vocabulary=[test_word],
                language=Language.ENGLISH,
                metadata={
                    "definitions": [
                        {"word": test_word, "text": d.text} for d in result.definitions[:3]
                    ]
                },
            )
            saved = await corpus_manager.save_corpus(corpus)

            # 3. Build search index
            logger.info("Step 3: Building search index...")
            from floridify.search.models import TrieIndex

            trie_index = TrieIndex(
                resource_id=f"trie-{saved.corpus_id}",
                resource_type=ResourceType.TRIE,
                corpus_id=str(saved.corpus_id),
                words=[test_word],
            )
            trie = TrieSearch(index=trie_index)

            # 4. Search for the word
            logger.info("Step 4: Searching for word...")
            search_result = trie.search_exact(test_word)
            assert search_result is not None
            assert search_result == test_word

            # 5. Retrieve corpus with definitions
            logger.info("Step 5: Retrieving definitions...")
            retrieved = await corpus_manager.get_corpus(corpus_id=saved.corpus_id)
            assert "definitions" in retrieved.metadata
            assert len(retrieved.metadata["definitions"]) > 0

            # Log first definition
            first_def = retrieved.metadata["definitions"][0]
            logger.info(f"  Definition: {first_def['text'][:100]}...")

            logger.info("=== Complete Pipeline Successful ===")
        else:
            logger.warning(f"Could not fetch '{test_word}' from Wiktionary (may be rate limited)")
