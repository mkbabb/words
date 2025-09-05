"""Tests for granular corpus rebuild functionality."""

from unittest.mock import MagicMock, patch

import pytest

from floridify.caching.manager import TreeCorpusManager
from floridify.caching.models import CorpusMetadata
from floridify.corpus.loaders.language import CorpusLanguageLoader
from floridify.corpus.loaders.literature import LiteratureCorpusLoader
from floridify.corpus.sources import LexiconSourceConfig
from floridify.models.dictionary import CorpusType, Language
from floridify.providers.literature.models import Author, LiteraryWork


class TestLanguageCorpusGranularRebuild:
    """Test granular rebuild for Language corpus."""
    
    @pytest.mark.asyncio
    async def test_rebuild_specific_sources(
        self, test_db, tree_corpus_manager: TreeCorpusManager
    ):
        """Test rebuilding specific sources within a language corpus."""
        loader = CorpusLanguageLoader()
        loader.tree_manager = tree_corpus_manager
        
        # Mock language sources
        source1 = LexiconSourceConfig(
            name="frequency_5000",
            url="http://example.com/freq5000.txt",
            description="Top 5000 words",
        )
        source2 = LexiconSourceConfig(
            name="academic_vocab",
            url="http://example.com/academic.txt",
            description="Academic vocabulary",
        )
        source3 = LexiconSourceConfig(
            name="technical_terms",
            url="http://example.com/technical.txt",
            description="Technical terms",
        )
        
        # Mock initial vocabulary for each source
        initial_vocabs = {
            "frequency_5000": ["word1", "word2", "word3"],
            "academic_vocab": ["academic1", "academic2"],
            "technical_terms": ["tech1", "tech2"],
        }
        
        # Mock updated vocabulary for specific sources
        updated_vocabs = {
            "frequency_5000": ["word1", "word2", "word3", "word4", "word5"],  # Added words
            "academic_vocab": ["academic1", "academic2", "academic3"],  # Added word
        }
        
        with patch.object(loader, '_load_source') as mock_load_source:
            # Setup initial load
            async def initial_load_side_effect(source, force_download=False):
                return initial_vocabs.get(source.name, [])
            
            mock_load_source.side_effect = initial_load_side_effect
            
            # Create initial corpus
            corpus = await loader.load_corpus(
                language=Language.ENGLISH,
                sources=[source1, source2, source3],
                force_rebuild=False,
            )
            
            assert corpus is not None
            initial_content = await corpus.get_content()
            initial_vocab = set(initial_content.get("vocabulary", []))
            
            # Should have all initial vocabularies
            expected_initial = set()
            for vocab_list in initial_vocabs.values():
                expected_initial.update(vocab_list)
            assert initial_vocab == expected_initial
            
            # Now setup rebuild of specific sources
            async def rebuild_load_side_effect(source, force_download=False):
                if force_download and source.name in updated_vocabs:
                    # Return updated vocabulary for rebuilt sources
                    return updated_vocabs[source.name]
                else:
                    # Return original vocabulary for non-rebuilt sources
                    return initial_vocabs.get(source.name, [])
            
            mock_load_source.side_effect = rebuild_load_side_effect
            
            # Rebuild only specific sources
            rebuilt_corpus = await loader.load_corpus(
                language=Language.ENGLISH,
                sources=[source1, source2, source3],
                rebuild_sources=["frequency_5000", "academic_vocab"],  # Only rebuild these
                force_rebuild=False,
            )
            
            assert rebuilt_corpus is not None
            rebuilt_content = await rebuilt_corpus.get_content()
            rebuilt_vocab = set(rebuilt_content.get("vocabulary", []))
            
            # Should have updated vocabulary for rebuilt sources
            # and original vocabulary for non-rebuilt source
            expected_rebuilt = set()
            expected_rebuilt.update(updated_vocabs["frequency_5000"])
            expected_rebuilt.update(updated_vocabs["academic_vocab"])
            expected_rebuilt.update(initial_vocabs["technical_terms"])  # Not rebuilt
            
            assert rebuilt_vocab == expected_rebuilt
            
            # Verify force_download was called only for rebuilt sources
            force_download_calls = [
                call for call in mock_load_source.call_args_list
                if call[1].get('force_download', False)
            ]
            # Should have force_download for the 2 sources we're rebuilding
            assert len([c for c in force_download_calls if c[1].get('force_download')]) >= 2
    
    @pytest.mark.asyncio
    async def test_preserve_non_rebuilt_sources(
        self, test_db, tree_corpus_manager: TreeCorpusManager
    ):
        """Test that non-rebuilt sources preserve their vocabulary."""
        loader = CorpusLanguageLoader()
        loader.tree_manager = tree_corpus_manager
        
        sources = [
            LexiconSourceConfig(name="source_a", url="http://a.com", description="A"),
            LexiconSourceConfig(name="source_b", url="http://b.com", description="B"),
            LexiconSourceConfig(name="source_c", url="http://c.com", description="C"),
        ]
        
        vocabs = {
            "source_a": ["alpha", "apple", "arrow"],
            "source_b": ["banana", "berry", "butter"],
            "source_c": ["carrot", "cherry", "cheese"],
        }
        
        with patch.object(loader, '_load_source') as mock_load:
            async def mock_load_func(s, **kwargs):
                return vocabs[s.name]
            mock_load.side_effect = mock_load_func
            
            # Create initial corpus
            initial = await loader.load_corpus(
                language=Language.ENGLISH,
                sources=sources,
            )
            
            # Rebuild only source_b with new vocabulary
            new_vocab_b = ["banana", "berry", "butter", "bread", "biscuit"]
            
            async def selective_load(source, force_download=False):
                if source.name == "source_b" and force_download:
                    return new_vocab_b
                return vocabs[source.name]
            
            mock_load.side_effect = selective_load
            
            # Rebuild only source_b
            rebuilt = await loader.load_corpus(
                language=Language.ENGLISH,
                sources=sources,
                rebuild_sources=["source_b"],
            )
            
            content = await rebuilt.get_content()
            final_vocab = set(content.get("vocabulary", []))
            
            # Should have original a and c, but updated b
            expected = set()
            expected.update(vocabs["source_a"])  # Original
            expected.update(new_vocab_b)  # Updated
            expected.update(vocabs["source_c"])  # Original
            
            assert final_vocab == expected
    
    @pytest.mark.asyncio
    async def test_granular_rebuild_with_versioning(
        self, test_db, tree_corpus_manager: TreeCorpusManager
    ):
        """Test that granular rebuild creates new versions correctly."""
        loader = CorpusLanguageLoader()
        loader.tree_manager = tree_corpus_manager
        
        source = LexiconSourceConfig(
            name="versioned_source",
            url="http://example.com/words.txt",
            description="Versioned vocabulary",
        )
        
        with patch.object(loader, '_load_source') as mock_load:
            # Version 1
            async def mock_v1():
                return ["v1_word1", "v1_word2"]
            mock_load.return_value = mock_v1()
            
            v1_corpus = await loader.load_corpus(
                language=Language.ENGLISH,
                sources=[source],
            )
            
            assert v1_corpus is not None
            v1_content = await v1_corpus.get_content()
            assert set(v1_content["vocabulary"]) == {"v1_word1", "v1_word2"}
            
            # Version 2 - granular rebuild
            async def mock_v2():
                return ["v2_word1", "v2_word2", "v2_word3"]
            mock_load.return_value = mock_v2()
            
            v2_corpus = await loader.load_corpus(
                language=Language.ENGLISH,
                sources=[source],
                rebuild_sources=["versioned_source"],
            )
            
            assert v2_corpus is not None
            v2_content = await v2_corpus.get_content()
            assert set(v2_content["vocabulary"]) == {"v2_word1", "v2_word2", "v2_word3"}
            
            # Versions should be different
            assert v1_corpus.id != v2_corpus.id
            assert v1_corpus.version_info.version != v2_corpus.version_info.version


class TestLiteratureCorpusGranularRebuild:
    """Test granular rebuild for Literature corpus."""
    
    @pytest.mark.asyncio
    async def test_rebuild_specific_works(
        self, test_db, tree_corpus_manager: TreeCorpusManager
    ):
        """Test rebuilding specific works within an author's corpus."""
        loader = LiteratureCorpusLoader()
        loader.tree_manager = tree_corpus_manager
        
        # Create mock author with works
        author = Author(
            name="Shakespeare, William",
            gutenberg_author_id=65,
            works=[
                LiteraryWork(
                    title="Hamlet",
                    gutenberg_id=1524,
                    year=1603,
                ),
                LiteraryWork(
                    title="Romeo and Juliet",
                    gutenberg_id=1513,
                    year=1595,
                ),
                LiteraryWork(
                    title="Macbeth",
                    gutenberg_id=1533,
                    year=1606,
                ),
            ],
        )
        
        # Mock initial vocabularies for each work
        initial_vocabs = {
            "Hamlet": ["to", "be", "or", "not"],
            "Romeo and Juliet": ["wherefore", "art", "thou"],
            "Macbeth": ["double", "toil", "trouble"],
        }
        
        # Mock updated vocabularies for specific works
        updated_vocabs = {
            "Hamlet": ["to", "be", "or", "not", "that", "is", "the", "question"],
            "Romeo and Juliet": ["wherefore", "art", "thou", "Romeo", "Juliet"],
        }
        
        with patch.object(loader, '_download_work') as mock_download:
            # Setup initial download
            async def initial_download(work, connector):
                text = " ".join(initial_vocabs.get(work.title, []))
                return text
            
            mock_download.side_effect = initial_download
            
            # Create initial corpus
            with patch.object(loader, '_get_connector') as mock_connector:
                mock_connector.return_value = MagicMock()
                
                initial_corpus = await loader.load_author_corpus(
                    author=author,
                    force_rebuild=False,
                )
            
            assert initial_corpus is not None
            initial_content = await initial_corpus.get_content()
            initial_vocab = set(initial_content.get("vocabulary", []))
            
            # Should have all initial vocabularies
            expected_initial = set()
            for vocab_list in initial_vocabs.values():
                expected_initial.update(vocab_list)
            assert initial_vocab == expected_initial
            
            # Setup rebuild of specific works
            async def rebuild_download(work, connector, force=False):
                if force and work.title in updated_vocabs:
                    text = " ".join(updated_vocabs[work.title])
                else:
                    text = " ".join(initial_vocabs.get(work.title, []))
                return text
            
            mock_download.side_effect = rebuild_download
            
            # Rebuild only specific works
            with patch.object(loader, '_get_connector') as mock_connector:
                mock_connector.return_value = MagicMock()
                
                rebuilt_corpus = await loader.load_author_corpus(
                    author=author,
                    rebuild_works=["Hamlet", "Romeo and Juliet"],  # Only rebuild these
                    force_rebuild=False,
                )
            
            assert rebuilt_corpus is not None
            rebuilt_content = await rebuilt_corpus.get_content()
            rebuilt_vocab = set(rebuilt_content.get("vocabulary", []))
            
            # Should have updated vocabulary for rebuilt works
            # and original vocabulary for non-rebuilt work
            expected_rebuilt = set()
            expected_rebuilt.update(updated_vocabs["Hamlet"])
            expected_rebuilt.update(updated_vocabs["Romeo and Juliet"])
            expected_rebuilt.update(initial_vocabs["Macbeth"])  # Not rebuilt
            
            assert rebuilt_vocab == expected_rebuilt
    
    @pytest.mark.asyncio
    async def test_preserve_non_rebuilt_works(
        self, test_db, tree_corpus_manager: TreeCorpusManager
    ):
        """Test that non-rebuilt works preserve their vocabulary."""
        loader = LiteratureCorpusLoader()
        loader.tree_manager = tree_corpus_manager
        
        author = Author(
            name="Dickens, Charles",
            gutenberg_author_id=37,
            works=[
                LiteraryWork(title="Oliver Twist", gutenberg_id=730),
                LiteraryWork(title="Great Expectations", gutenberg_id=1400),
                LiteraryWork(title="A Christmas Carol", gutenberg_id=46),
            ],
        )
        
        work_vocabs = {
            "Oliver Twist": ["please", "sir", "more"],
            "Great Expectations": ["great", "expectations", "pip"],
            "A Christmas Carol": ["bah", "humbug", "scrooge"],
        }
        
        with patch.object(loader, '_download_work') as mock_download:
            async def mock_download_func(w, c, **kwargs):
                return " ".join(work_vocabs[w.title])
            mock_download.side_effect = mock_download_func
            
            with patch.object(loader, '_get_connector') as mock_connector:
                mock_connector.return_value = MagicMock()
                
                # Create initial corpus
                initial = await loader.load_author_corpus(author=author)
                
                # Update only Great Expectations
                new_vocab_ge = ["great", "expectations", "pip", "estella", "havisham"]
                
                async def selective_download(work, connector, force=False):
                    if work.title == "Great Expectations" and force:
                        return " ".join(new_vocab_ge)
                    return " ".join(work_vocabs[work.title])
                
                mock_download.side_effect = selective_download
                
                # Rebuild only Great Expectations
                rebuilt = await loader.load_author_corpus(
                    author=author,
                    rebuild_works=["Great Expectations"],
                )
            
            content = await rebuilt.get_content()
            final_vocab = set(content.get("vocabulary", []))
            
            # Should have original Oliver Twist and Christmas Carol, but updated Great Expectations
            expected = set()
            expected.update(work_vocabs["Oliver Twist"])  # Original
            expected.update(new_vocab_ge)  # Updated
            expected.update(work_vocabs["A Christmas Carol"])  # Original
            
            assert final_vocab == expected
    
    @pytest.mark.asyncio
    async def test_granular_rebuild_creates_child_corpora(
        self, test_db, tree_corpus_manager: TreeCorpusManager
    ):
        """Test that granular rebuild properly creates child corpora for works."""
        loader = LiteratureCorpusLoader()
        loader.tree_manager = tree_corpus_manager
        
        author = Author(
            name="Joyce, James",
            gutenberg_author_id=1039,
            works=[
                LiteraryWork(title="Ulysses", gutenberg_id=4300),
                LiteraryWork(title="Dubliners", gutenberg_id=2814),
            ],
        )
        
        with patch.object(loader, '_download_work') as mock_download:
            async def mock_download_text(w, c, **kwargs):
                return f"Text of {w.title}"
            mock_download.side_effect = mock_download_text
            
            with patch.object(loader, '_get_connector') as mock_connector:
                mock_connector.return_value = MagicMock()
                
                # Create corpus
                corpus = await loader.load_author_corpus(author=author)
                
                assert corpus is not None
                assert corpus.is_master is True
                assert len(corpus.child_corpus_ids) == 2  # One for each work
                
                # Load child corpora
                for child_id in corpus.child_corpus_ids:
                    child = await CorpusMetadata.get(child_id)
                    assert child is not None
                    assert child.parent_corpus_id == corpus.id
                    assert child.corpus_type == CorpusType.LITERATURE.value
    
    @pytest.mark.asyncio
    async def test_selective_work_rebuild_updates_master(
        self, test_db, tree_corpus_manager: TreeCorpusManager
    ):
        """Test that rebuilding specific works updates the master corpus vocabulary."""
        loader = LiteratureCorpusLoader()
        loader.tree_manager = tree_corpus_manager
        
        author = Author(
            name="Tolstoy, Leo",
            gutenberg_author_id=136,
            works=[
                LiteraryWork(title="War and Peace", gutenberg_id=2600),
                LiteraryWork(title="Anna Karenina", gutenberg_id=1399),
            ],
        )
        
        # Initial vocabularies
        initial_vocabs = {
            "War and Peace": ["war", "peace", "napoleon"],
            "Anna Karenina": ["anna", "karenina", "train"],
        }
        
        with patch.object(loader, '_download_work') as mock_download:
            async def mock_download_initial(w, c, **kwargs):
                return " ".join(initial_vocabs[w.title])
            mock_download.side_effect = mock_download_initial
            
            with patch.object(loader, '_get_connector') as mock_connector:
                mock_connector.return_value = MagicMock()
                
                # Create initial corpus
                initial_corpus = await loader.load_author_corpus(author=author)
                
                initial_content = await initial_corpus.get_content()
                initial_master_vocab = set(initial_content.get("vocabulary", []))
                
                # Update War and Peace vocabulary
                updated_wp_vocab = ["war", "peace", "napoleon", "pierre", "natasha"]
                
                async def selective_download(work, connector, force=False):
                    if work.title == "War and Peace" and force:
                        return " ".join(updated_wp_vocab)
                    return " ".join(initial_vocabs[work.title])
                
                mock_download.side_effect = selective_download
                
                # Rebuild only War and Peace
                rebuilt_corpus = await loader.load_author_corpus(
                    author=author,
                    rebuild_works=["War and Peace"],
                )
                
                rebuilt_content = await rebuilt_corpus.get_content()
                rebuilt_master_vocab = set(rebuilt_content.get("vocabulary", []))
                
                # Master should have updated War and Peace vocab + original Anna Karenina
                expected_master = set()
                expected_master.update(updated_wp_vocab)
                expected_master.update(initial_vocabs["Anna Karenina"])
                
                assert rebuilt_master_vocab == expected_master
                assert rebuilt_master_vocab != initial_master_vocab  # Should be different


class TestCrossCorpusGranularRebuild:
    """Test granular rebuild across both Language and Literature corpus types."""
    
    @pytest.mark.asyncio
    async def test_both_loaders_support_granular_rebuild(self):
        """Verify both loaders have granular rebuild methods."""
        lang_loader = LanguageCorpusLoader()
        lit_loader = LiteratureCorpusLoader()
        
        # Check Language loader has the method
        assert hasattr(lang_loader, '_rebuild_specific_sources')
        assert callable(getattr(lang_loader, '_rebuild_specific_sources', None))
        
        # Check Literature loader has the method
        assert hasattr(lit_loader, '_rebuild_specific_works')
        assert callable(getattr(lit_loader, '_rebuild_specific_works', None))
        
        # Check both accept rebuild parameters in load methods
        import inspect
        
        # Language loader should accept rebuild_sources
        lang_sig = inspect.signature(lang_loader.load_corpus)
        assert 'rebuild_sources' in lang_sig.parameters
        
        # Literature loader should accept rebuild_works
        lit_sig = inspect.signature(lit_loader.load_author_corpus)
        assert 'rebuild_works' in lit_sig.parameters
    
    @pytest.mark.asyncio
    async def test_mixed_corpus_tree_with_granular_rebuild(
        self, test_db, tree_corpus_manager: TreeCorpusManager
    ):
        """Test a corpus tree with both language and literature corpora."""
        lang_loader = LanguageCorpusLoader()
        lit_loader = LiteratureCorpusLoader()
        
        lang_loader.tree_manager = tree_corpus_manager
        lit_loader.tree_manager = tree_corpus_manager
        
        # Create language corpus
        lang_source = LexiconSourceConfig(
            name="common_words",
            url="http://example.com/common.txt",
            description="Common words",
        )
        
        with patch.object(lang_loader, '_load_source') as mock_lang_load:
            async def mock_lang_func():
                return ["the", "and", "of", "to"]
            mock_lang_load.return_value = mock_lang_func()
            
            lang_corpus = await lang_loader.load_corpus(
                language=Language.ENGLISH,
                sources=[lang_source],
            )
        
        # Create literature corpus
        author = Author(
            name="Test Author",
            gutenberg_author_id=999,
            works=[LiteraryWork(title="Test Work", gutenberg_id=9999)],
        )
        
        with patch.object(lit_loader, '_download_work') as mock_lit_download:
            async def mock_lit_func():
                return "once upon a time"
            mock_lit_download.return_value = mock_lit_func()
            
            with patch.object(lit_loader, '_get_connector') as mock_connector:
                mock_connector.return_value = MagicMock()
                
                lit_corpus = await lit_loader.load_author_corpus(author=author)
        
        # Create master corpus combining both
        master = await tree_corpus_manager.create_tree(
            master_name="combined_corpus",
            language=Language.ENGLISH,
            children=[
                {
                    "id": f"lang_{lang_corpus.resource_id}",
                    "content": await lang_corpus.get_content(),
                    "metadata": {"source_type": "language"},
                },
                {
                    "id": f"lit_{lit_corpus.resource_id}",
                    "content": await lit_corpus.get_content(),
                    "metadata": {"source_type": "literature"},
                },
            ],
        )
        
        assert master is not None
        assert master.is_master is True
        assert len(master.child_corpus_ids) == 2
        
        # Master should have combined vocabulary
        master_content = await master.get_content()
        master_vocab = set(master_content.get("vocabulary", []))
        
        # Should contain words from both sources
        assert "the" in master_vocab  # From language
        assert "once" in master_vocab  # From literature