"""Integration tests for the complete provider system."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from floridify.caching.core import GlobalCacheManager
from floridify.caching.models import CacheNamespace
from floridify.corpus.loaders.language import CorpusLanguageLoader
from floridify.corpus.loaders.literature import LiteratureCorpusLoader
from floridify.corpus.sources import LexiconSourceConfig
from floridify.models.dictionary import (
    DictionaryProvider,
    Language,
)
from floridify.models.versioned import ResourceType, VersionConfig
from floridify.providers.batch import BatchOperation, BatchStatus
from floridify.providers.core import ConnectorConfig, ProviderType
from floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector
from floridify.providers.dictionary.scraper.wiktionary import WiktionaryConnector
from floridify.providers.literature.models import Author, LiteraryWork


class TestEndToEndProviderFlow:
    """Test complete end-to-end provider workflows."""
    
    @pytest.mark.asyncio
    async def test_dictionary_lookup_with_caching_and_versioning(
        self, test_db, cache_manager, version_manager
    ):
        """Test complete dictionary lookup flow with all features."""
        # Setup
        config = ConnectorConfig(provider_type=ProviderType.DICTIONARY)
        connector = FreeDictionaryConnector(config)
        connector.cache_manager = cache_manager
        
        # Mock API response
        mock_response = {
            "word": "ubiquitous",
            "phonetic": "/juːˈbɪkwɪtəs/",
            "meanings": [
                {
                    "partOfSpeech": "adjective",
                    "definitions": [
                        {"definition": "present everywhere"}
                    ],
                }
            ],
        }
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = [mock_response]
            mock_client.get.return_value = response
            
            # First lookup - hits API
            result1 = await connector.lookup("ubiquitous")
            assert mock_client.get.call_count == 1
            
            # Save to versioned storage
            saved = await version_manager.save(
                resource_id="ubiquitous",
                resource_type=ResourceType.DICTIONARY,
                namespace=CacheNamespace.DICTIONARY,
                content=result1,
                config=VersionConfig(version="1.0.0"),
            )
            
            assert saved.version_info.version == "1.0.0"
            
            # Second lookup - hits cache
            result2 = await connector.lookup("ubiquitous")
            assert mock_client.get.call_count == 1  # No additional API call
            
            # Verify versioned retrieval
            retrieved = await version_manager.get_latest(
                "ubiquitous", ResourceType.DICTIONARY
            )
            assert retrieved is not None
            content = await retrieved.get_content()
            assert content == result1
    
    @pytest.mark.asyncio
    async def test_corpus_build_with_granular_rebuild(
        self, test_db, tree_corpus_manager
    ):
        """Test building corpus with granular rebuild capability."""
        loader = CorpusLanguageLoader()
        loader.tree_manager = tree_corpus_manager
        
        # Define sources
        sources = [
            LexiconSourceConfig(
                name="core_vocab",
                url="http://example.com/core.txt",
                description="Core vocabulary",
            ),
            LexiconSourceConfig(
                name="advanced_vocab",
                url="http://example.com/advanced.txt",
                description="Advanced vocabulary",
            ),
        ]
        
        # Mock vocabularies
        vocabs = {
            "core_vocab": ["the", "and", "of", "to", "a"],
            "advanced_vocab": ["ubiquitous", "ephemeral", "serendipity"],
        }
        
        with patch.object(loader, '_load_source') as mock_load:
            async def mock_load_func(s, **kwargs):
                return vocabs[s.name]
            
            mock_load.side_effect = mock_load_func
            
            # Build initial corpus
            corpus_v1 = await loader.load_corpus(
                language=Language.ENGLISH,
                sources=sources,
            )
            
            assert corpus_v1 is not None
            content_v1 = await corpus_v1.get_content()
            vocab_v1 = set(content_v1["vocabulary"])
            
            # Update advanced vocabulary
            vocabs["advanced_vocab"] = [
                "ubiquitous", "ephemeral", "serendipity", "perspicacious"
            ]
            
            # Rebuild only advanced vocabulary
            corpus_v2 = await loader.load_corpus(
                language=Language.ENGLISH,
                sources=sources,
                rebuild_sources=["advanced_vocab"],
            )
            
            content_v2 = await corpus_v2.get_content()
            vocab_v2 = set(content_v2["vocabulary"])
            
            # Core vocab unchanged, advanced vocab updated
            assert "perspicacious" in vocab_v2
            assert "perspicacious" not in vocab_v1
            
            # Core vocabulary preserved
            for word in vocabs["core_vocab"]:
                assert word in vocab_v2
    
    @pytest.mark.asyncio
    async def test_multi_provider_cascade_with_batch(self, test_db):
        """Test cascading through multiple providers in batch operations."""
        words = ["common", "rare", "nonexistent"]
        
        # Setup providers
        providers = [
            FreeDictionaryConnector(ConnectorConfig(provider_type=ProviderType.DICTIONARY)),
            WiktionaryConnector(ConnectorConfig(provider_type=ProviderType.DICTIONARY)),
        ]
        
        # Create batch operation
        batch = BatchOperation(
            operation_id="cascade_test",
            operation_type="multi_provider_lookup",
            provider=DictionaryProvider.FREE_DICTIONARY,
            total_items=len(words),
        )
        await batch.save()
        
        # Mock provider responses
        def get_mock_response(provider_index, word):
            if provider_index == 0:  # FreeDictionary
                if word == "common":
                    return {"word": word, "source": "free_dictionary"}
                return None
            elif provider_index == 1:  # Wiktionary
                if word in ["common", "rare"]:
                    return {"word": word, "source": "wiktionary"}
                return None
            return None
        
        results = {}
        batch.status = BatchStatus.IN_PROGRESS
        
        for word in words:
            result = None
            
            # Try each provider
            for i, provider in enumerate(providers):
                with patch.object(provider, 'lookup') as mock_lookup:
                    mock_lookup.return_value = get_mock_response(i, word)
                    result = await provider.lookup(word)
                    
                    if result:
                        results[word] = result
                        break
            
            if result:
                batch.processed_items += 1
            else:
                batch.failed_items += 1
                batch.add_error(word, "Not found in any provider", "NOT_FOUND")
        
        batch.status = BatchStatus.COMPLETED
        await batch.save()
        
        # Verify results
        assert "common" in results
        assert results["common"]["source"] == "free_dictionary"  # First provider
        assert "rare" in results
        assert results["rare"]["source"] == "wiktionary"  # Second provider
        assert "nonexistent" not in results  # Not found
        
        assert batch.processed_items == 2
        assert batch.failed_items == 1
    
    @pytest.mark.asyncio
    async def test_literature_corpus_with_versioning(
        self, test_db, tree_corpus_manager
    ):
        """Test literature corpus creation with versioning."""
        loader = LiteratureCorpusLoader()
        loader.tree_manager = tree_corpus_manager
        
        author = Author(
            name="Test Author",
            gutenberg_author_id=999,
            works=[
                LiteraryWork(title="Book One", gutenberg_id=1001),
                LiteraryWork(title="Book Two", gutenberg_id=1002),
            ],
        )
        
        with patch.object(loader, '_download_work') as mock_download:
            # Version 1 content
            async def mock_download_v1(w, c, **kwargs):
                return f"Content of {w.title} v1"
            
            mock_download.side_effect = mock_download_v1
            
            with patch.object(loader, '_get_connector') as mock_connector:
                mock_connector.return_value = MagicMock()
                
                corpus_v1 = await loader.load_author_corpus(author=author)
            
            assert corpus_v1 is not None
            assert corpus_v1.version_info.version
            
            # Version 2 with updated content
            async def mock_download_v2(w, c, **kwargs):
                return f"Updated content of {w.title} v2"
            
            mock_download.side_effect = mock_download_v2
            
            with patch.object(loader, '_get_connector') as mock_connector:
                mock_connector.return_value = MagicMock()
                
                corpus_v2 = await loader.load_author_corpus(
                    author=author,
                    force_rebuild=True,
                )
            
            assert corpus_v2 is not None
            assert corpus_v2.id != corpus_v1.id
            assert corpus_v2.version_info.version != corpus_v1.version_info.version


class TestCachingIntegration:
    """Test integrated caching across the system."""
    
    @pytest.mark.asyncio
    async def test_multi_tier_cache_flow(self):
        """Test complete multi-tier cache flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize global cache
            cache = GlobalCacheManager()
            await cache.initialize(
                l2_base_dir=Path(tmpdir),
                l1_max_size=10,
                l1_ttl=3600,
                l2_ttl=86400,
            )
            
            namespace = CacheNamespace.DICTIONARY
            test_data = {"word": "test", "definition": "a trial"}
            
            # Set value - goes to L1 and L2
            await cache.set(namespace, "test_key", test_data)
            
            # Get from L1 (fast)
            result_l1 = await cache.get(namespace, "test_key")
            assert result_l1 == test_data
            
            # Simulate L1 eviction
            await cache.l1_caches[namespace].clear()
            
            # Get from L2 (slower, but restores to L1)
            result_l2 = await cache.get(namespace, "test_key")
            assert result_l2 == test_data
            
            # Should be back in L1
            l1_restored = await cache.l1_caches[namespace].get("test_key")
            assert l1_restored == test_data
            
            # Test namespace isolation
            await cache.set(CacheNamespace.CORPUS, "test_key", {"different": "data"})
            
            dict_value = await cache.get(CacheNamespace.DICTIONARY, "test_key")
            corpus_value = await cache.get(CacheNamespace.CORPUS, "test_key")
            
            assert dict_value != corpus_value
            assert dict_value == test_data
            assert corpus_value == {"different": "data"}
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_corpus_rebuild(
        self, test_db, tree_corpus_manager, cache_manager
    ):
        """Test cache invalidation when corpus is rebuilt."""
        loader = CorpusLanguageLoader()
        loader.tree_manager = tree_corpus_manager
        
        source = LexiconSourceConfig(
            name="test_source",
            url="http://example.com/test.txt",
            description="Test source",
        )
        
        with patch.object(loader, '_load_source') as mock_load:
            # Initial load
            async def mock_load_initial():
                return ["word1", "word2"]
            
            mock_load.return_value = mock_load_initial()
            
            corpus_v1 = await loader.load_corpus(
                language=Language.ENGLISH,
                sources=[source],
            )
            
            # Cache the corpus
            await cache_manager.set(
                CacheNamespace.CORPUS,
                f"corpus:{corpus_v1.resource_id}",
                corpus_v1,
            )
            
            # Rebuild with new content
            async def mock_load_rebuild():
                return ["word1", "word2", "word3"]
            
            mock_load.return_value = mock_load_rebuild()
            
            corpus_v2 = await loader.load_corpus(
                language=Language.ENGLISH,
                sources=[source],
                force_rebuild=True,
            )
            
            # Old cache should be invalidated
            cached = await cache_manager.get(
                CacheNamespace.CORPUS,
                f"corpus:{corpus_v1.resource_id}",
            )
            
            # Should get new version or None (depending on implementation)
            if cached:
                content = await cached.get_content()
                assert "word3" in content.get("vocabulary", [])


class TestErrorRecovery:
    """Test system-wide error recovery."""
    
    @pytest.mark.asyncio
    async def test_cascade_failure_recovery(self, test_db):
        """Test recovery from cascading failures."""
        # Create a chain of dependent operations
        operations = []
        
        for i in range(3):
            batch = BatchOperation(
                operation_id=f"chain_{i}",
                operation_type="dependent_operation",
                provider=DictionaryProvider.WIKTIONARY,
                total_items=10,
                checkpoint={"depends_on": f"chain_{i-1}" if i > 0 else None},
            )
            await batch.save()
            operations.append(batch)
        
        # Simulate failure in middle operation
        operations[1].status = BatchStatus.FAILED
        operations[1].errors.append({
            "error": "Critical failure",
            "timestamp": datetime.now(UTC),
        })
        await operations[1].save()
        
        # Downstream operations should handle upstream failure
        for op in operations[2:]:
            op.status = BatchStatus.PARTIAL
            op.checkpoint["upstream_failure"] = operations[1].operation_id
            await op.save()
        
        # Verify failure propagation
        assert operations[0].status != BatchStatus.FAILED  # Upstream unaffected
        assert operations[1].status == BatchStatus.FAILED
        assert operations[2].checkpoint.get("upstream_failure") == operations[1].operation_id
    
    @pytest.mark.asyncio
    async def test_partial_success_handling(self, test_db):
        """Test handling partial success scenarios."""
        words = ["success1", "success2", "failure1", "success3", "failure2"]
        
        batch = BatchOperation(
            operation_id="partial_test",
            operation_type="mixed_results",
            provider=DictionaryProvider.OXFORD,
            total_items=len(words),
        )
        await batch.save()
        
        batch.status = BatchStatus.IN_PROGRESS
        successful = []
        failed = []
        
        for word in words:
            if "failure" in word:
                batch.add_error(word, "Lookup failed", "API_ERROR")
                failed.append(word)
            else:
                batch.processed_items += 1
                successful.append(word)
        
        # Mark as partial success
        if failed and successful:
            batch.status = BatchStatus.PARTIAL
        elif not failed:
            batch.status = BatchStatus.COMPLETED
        else:
            batch.status = BatchStatus.FAILED
        
        await batch.save()
        
        assert batch.status == BatchStatus.PARTIAL
        assert batch.processed_items == 3
        assert batch.failed_items == 2
        assert len(batch.errors) == 2
        
        # Create retry batch for failed items
        retry_batch = BatchOperation(
            operation_id="partial_test_retry",
            operation_type="retry_failed",
            provider=DictionaryProvider.OXFORD,
            total_items=len(failed),
            checkpoint={"retry_words": failed},
        )
        await retry_batch.save()
        
        assert retry_batch.checkpoint["retry_words"] == failed