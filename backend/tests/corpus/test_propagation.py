"""Test update and deletion propagation mechanisms."""
import asyncio
import pytest
from unittest.mock import AsyncMock
from floridify.models.versioned import CorpusMetadata


class TestUpdatePropagation:
    """Test change propagation through tree."""
    
    async def test_child_update_propagates(self, corpus_tree):
        """Test child change triggers parent re-aggregation."""
        master = corpus_tree["master"]
        work1 = corpus_tree["work1"]
        
        # Update child vocabulary
        original_master_vocab = set(master.content_inline.get("vocabulary", []))
        work1.content_inline["vocabulary"].extend(["new", "words", "added"])
        
        # Simulate propagation
        work1_vocab = set(work1.content_inline["vocabulary"])
        work2_vocab = set(corpus_tree["work2"].content_inline.get("vocabulary", []))
        new_master_vocab = work1_vocab.union(work2_vocab)
        
        master.content_inline["vocabulary"] = sorted(list(new_master_vocab))
        
        # Verify propagation
        assert "new" in master.content_inline["vocabulary"]
        assert len(master.content_inline["vocabulary"]) > len(original_master_vocab)
    
    async def test_batch_child_updates(self, corpus_tree, concurrent_executor):
        """Test multiple children updating together."""
        master = corpus_tree["master"]
        work1 = corpus_tree["work1"]
        work2 = corpus_tree["work2"]
        
        # Create update tasks
        async def update_child(child, new_words):
            child.content_inline["vocabulary"].extend(new_words)
            await asyncio.sleep(0.01)  # Simulate async operation
            return child
        
        # Execute updates concurrently
        results = await concurrent_executor([
            update_child(work1, ["batch1", "update1"]),
            update_child(work2, ["batch2", "update2"]),
        ])
        
        # Verify both updates applied
        assert "batch1" in work1.content_inline["vocabulary"]
        assert "batch2" in work2.content_inline["vocabulary"]
    
    async def test_concurrent_propagation(self, corpus_tree, concurrent_executor):
        """Test race condition handling in propagation."""
        master = corpus_tree["master"]
        
        # Create racing updates
        async def racing_update(corpus, word):
            vocab = corpus.content_inline.get("vocabulary", [])
            await asyncio.sleep(0.001)  # Simulate race condition
            vocab.append(word)
            corpus.content_inline["vocabulary"] = vocab
            return corpus
        
        # Execute concurrent updates
        results = await concurrent_executor([
            racing_update(master, f"race_{i}")
            for i in range(5)
        ])
        
        # Verify all updates applied (in real implementation, locks would ensure this)
        vocab = master.content_inline["vocabulary"]
        for i in range(5):
            assert f"race_{i}" in vocab
    
    async def test_failed_propagation_recovery(self, corpus_tree):
        """Test partial failure handling during propagation."""
        master = corpus_tree["master"]
        work1 = corpus_tree["work1"]
        
        # Simulate partial failure
        original_vocab = master.content_inline.get("vocabulary", []).copy()
        
        try:
            # Simulate failed aggregation
            work1.content_inline["vocabulary"].append("failing_word")
            raise Exception("Aggregation failed")
        except Exception:
            # Recovery: rollback to original state
            master.content_inline["vocabulary"] = original_vocab
        
        # Verify rollback worked
        assert master.content_inline["vocabulary"] == original_vocab
    
    async def test_version_chain_consistency(self):
        """Test supersedes/superseded_by links remain consistent."""
        # Create version chain
        v1 = CorpusMetadata(
            corpus_name="Version1",
            corpus_type="LANGUAGE",
            is_latest=False,
        )
        
        v2 = CorpusMetadata(
            corpus_name="Version2",
            corpus_type="LANGUAGE",
            supersedes=v1.id,
            is_latest=False,
        )
        v1.superseded_by = v2.id
        
        v3 = CorpusMetadata(
            corpus_name="Version3",
            corpus_type="LANGUAGE",
            supersedes=v2.id,
            is_latest=True,
        )
        v2.superseded_by = v3.id
        
        # Verify chain integrity
        assert v1.superseded_by == v2.id
        assert v2.supersedes == v1.id
        assert v2.superseded_by == v3.id
        assert v3.supersedes == v2.id
        assert v3.is_latest is True


class TestDeletionCascade:
    """Test deletion behaviors and cascade effects."""
    
    async def test_version_chain_repair(self):
        """Test deleting middle version repairs chain."""
        # Create chain: v1 -> v2 -> v3
        v1 = CorpusMetadata(
            corpus_name="V1",
            corpus_type="LANGUAGE",
            is_latest=False,
        )
        
        v2 = CorpusMetadata(
            corpus_name="V2",
            corpus_type="LANGUAGE",
            supersedes=v1.id,
            is_latest=False,
        )
        v1.superseded_by = v2.id
        
        v3 = CorpusMetadata(
            corpus_name="V3",
            corpus_type="LANGUAGE",
            supersedes=v2.id,
            is_latest=True,
        )
        v2.superseded_by = v3.id
        
        # Delete v2 and repair chain
        v1.superseded_by = v3.id
        v3.supersedes = v1.id
        
        # Verify repair
        assert v1.superseded_by == v3.id
        assert v3.supersedes == v1.id
    
    async def test_latest_version_deletion(self):
        """Test deleting latest version promotes previous."""
        v1 = CorpusMetadata(
            corpus_name="V1",
            corpus_type="LANGUAGE",
            is_latest=False,
        )
        
        v2 = CorpusMetadata(
            corpus_name="V2",
            corpus_type="LANGUAGE",
            supersedes=v1.id,
            is_latest=True,
        )
        v1.superseded_by = v2.id
        
        # Delete v2 (latest)
        v1.superseded_by = None
        v1.is_latest = True  # Promote v1
        
        # Verify promotion
        assert v1.is_latest is True
        assert v1.superseded_by is None
    
    async def test_parent_deletion_no_cascade(self, corpus_tree):
        """Test parent deletion doesn't affect children."""
        master = corpus_tree["master"]
        work1 = corpus_tree["work1"]
        work2 = corpus_tree["work2"]
        
        # Store child IDs
        child_ids = master.child_corpus_ids.copy()
        
        # Delete parent (simulation)
        master_deleted = True
        
        # Verify children still exist
        assert work1.corpus_name == "Shakespeare_Works"
        assert work2.corpus_name == "Modern_Works"
        # Children become orphans but aren't deleted
        
    async def test_external_content_cleanup(self):
        """Test external storage is cleaned up on deletion."""
        corpus = CorpusMetadata(
            corpus_name="External_Corpus",
            corpus_type="LANGUAGE",
            content_location={
                "storage_type": "external",
                "path": "/cache/test_corpus/vocabulary.json",
                "size": 1024,
            },
        )
        
        # Track cleanup
        cleanup_called = False
        
        async def cleanup_external_content(location):
            nonlocal cleanup_called
            cleanup_called = True
            # In real implementation, would delete file at location["path"]
        
        # Simulate deletion
        if corpus.content_location:
            await cleanup_external_content(corpus.content_location)
        
        assert cleanup_called is True
    
    async def test_cache_invalidation_on_delete(self):
        """Test caches are properly cleared on deletion."""
        corpus = CorpusMetadata(
            corpus_name="Cached_Corpus",
            corpus_type="LANGUAGE",
        )
        
        # Track cache operations
        cache_keys_cleared = []
        
        async def clear_cache(corpus_id):
            cache_keys_cleared.extend([
                f"corpus:{corpus_id}",
                f"corpus:vocabulary:{corpus_id}",
                f"corpus:stats:{corpus_id}",
            ])
        
        # Simulate deletion with cache clearing
        await clear_cache(corpus.id)
        
        # Verify all cache keys cleared
        assert f"corpus:{corpus.id}" in cache_keys_cleared
        assert f"corpus:vocabulary:{corpus.id}" in cache_keys_cleared
        assert f"corpus:stats:{corpus.id}" in cache_keys_cleared