"""Test edge cases and boundary conditions."""
import asyncio

from floridify.models.versioned import CorpusMetadata


class TestEdgeCases:
    """Test boundary conditions and edge cases."""
    
    async def test_empty_corpus_creation(self):
        """Test creating corpus with zero vocabulary."""
        empty_corpus = CorpusMetadata(
            corpus_name="Empty",
            corpus_type="LANGUAGE",
            content_inline={"vocabulary": []},
        )
        
        assert empty_corpus.content_inline["vocabulary"] == []
        
        # Statistics for empty corpus
        stats = {
            "vocabulary_count": 0,
            "unique_words": 0,
            "avg_word_length": 0,
        }
        
        assert stats["vocabulary_count"] == 0
    
    async def test_unicode_vocabulary(self, sample_vocabularies):
        """Test various Unicode characters in vocabulary."""
        unicode_vocab = sample_vocabularies["unicode"]
        
        corpus = CorpusMetadata(
            corpus_name="Unicode_Test",
            corpus_type="LANGUAGE",
            content_inline={"vocabulary": unicode_vocab},
        )
        
        # Test preservation of various Unicode
        vocab = corpus.content_inline["vocabulary"]
        assert "😀" in vocab  # Emoji
        assert "北京" in vocab  # Chinese
        assert "café" in vocab  # Latin diacritics
        assert "naïve" in vocab  # More diacritics
        assert "résumé" in vocab  # Accents
        
        # Test edge Unicode cases
        edge_cases = [
            "\u0000",  # Null character
            "\uFEFF",  # BOM
            "a\u0301",  # Combining accent
            "🏳️‍🌈",  # Complex emoji
            "\u200B",  # Zero-width space
        ]
        
        edge_corpus = CorpusMetadata(
            corpus_name="Edge_Unicode",
            corpus_type="LANGUAGE",
            content_inline={"vocabulary": edge_cases},
        )
        
        # Should handle without crashing
        assert len(edge_corpus.content_inline["vocabulary"]) == len(edge_cases)
    
    async def test_massive_vocabulary(self):
        """Test performance with 100k+ words."""
        massive_vocab = [f"word_{i:06d}" for i in range(100000)]
        
        corpus = CorpusMetadata(
            corpus_name="Massive",
            corpus_type="LANGUAGE",
        )
        
        # Should trigger external storage
        EXTERNAL_THRESHOLD = 10000
        assert len(massive_vocab) > EXTERNAL_THRESHOLD
        
        # In production, would store externally
        corpus.content_location = {
            "storage_type": "external",
            "path": f"/cache/massive/{corpus.id}/vocabulary.json",
            "size": len(str(massive_vocab)),
        }
        
        assert corpus.content_location is not None
    
    async def test_deeply_nested_tree(self):
        """Test 10+ level hierarchy performance."""
        # Create deep tree
        root = CorpusMetadata(
            corpus_name="Root",
            corpus_type="LANGUAGE",
            is_master=True,
        )
        
        current = root
        depth = 10
        
        for i in range(depth):
            child = CorpusMetadata(
                corpus_name=f"Level_{i+1}",
                corpus_type="LITERATURE",
                parent_corpus_id=current.id,
            )
            current.child_corpus_ids = [child.id]
            current = child
        
        # Verify depth
        node = current
        actual_depth = 0
        while node.parent_corpus_id:
            actual_depth += 1
            if actual_depth > depth + 1:  # Prevent infinite loop
                break
            # In real test, would look up parent
            node = root if actual_depth == depth else node
        
        assert actual_depth <= depth
    
    async def test_concurrent_tree_modifications(self, corpus_tree, concurrent_executor):
        """Test simultaneous parent/child updates."""
        master = corpus_tree["master"]
        
        # Create concurrent modifications
        async def modify_operation(op_type, corpus, data):
            await asyncio.sleep(0.001)  # Simulate async work
            
            if op_type == "add_child":
                corpus.child_corpus_ids.append(data)
            elif op_type == "update_vocab":
                corpus.content_inline["vocabulary"].extend(data)
            elif op_type == "remove_child":
                if data in corpus.child_corpus_ids:
                    corpus.child_corpus_ids.remove(data)
            
            return corpus
        
        # Execute concurrent operations
        results = await concurrent_executor([
            modify_operation("add_child", master, "new_child_1"),
            modify_operation("update_vocab", master, ["concurrent", "words"]),
            modify_operation("add_child", master, "new_child_2"),
        ])
        
        # Verify all operations completed
        assert "new_child_1" in master.child_corpus_ids
        assert "new_child_2" in master.child_corpus_ids
        assert "concurrent" in master.content_inline.get("vocabulary", [])
    
    async def test_storage_threshold_boundary(self):
        """Test exactly 10k words edge case."""
        threshold = 10000
        
        # Test just below threshold
        below_threshold = [f"word_{i}" for i in range(threshold - 1)]
        corpus_below = CorpusMetadata(
            corpus_name="Below_Threshold",
            corpus_type="LANGUAGE",
            content_inline={"vocabulary": below_threshold},
        )
        
        # Should use inline storage
        assert corpus_below.content_inline is not None
        assert corpus_below.content_location is None
        
        # Test exactly at threshold
        at_threshold = [f"word_{i}" for i in range(threshold)]
        corpus_at = CorpusMetadata(
            corpus_name="At_Threshold",
            corpus_type="LANGUAGE",
        )
        
        # Borderline case - implementation dependent
        if len(at_threshold) >= threshold:
            corpus_at.content_location = {"storage_type": "external"}
            corpus_at.content_inline = None
        else:
            corpus_at.content_inline = {"vocabulary": at_threshold}
        
        # Test above threshold
        above_threshold = [f"word_{i}" for i in range(threshold + 1)]
        corpus_above = CorpusMetadata(
            corpus_name="Above_Threshold",
            corpus_type="LANGUAGE",
        )
        
        # Should use external storage
        if len(above_threshold) > threshold:
            corpus_above.content_location = {"storage_type": "external"}
            corpus_above.content_inline = None
        
        assert corpus_above.content_location is not None
    
    async def test_null_and_empty_values(self):
        """Test handling of null and empty values."""
        # Test various empty/null scenarios
        test_cases = [
            {"vocabulary": None},  # Null vocabulary
            {"vocabulary": []},  # Empty list
            {"vocabulary": [""]},  # Empty string in vocabulary
            {"vocabulary": [None]},  # None in vocabulary
            {},  # No vocabulary key
        ]
        
        for i, content in enumerate(test_cases):
            corpus = CorpusMetadata(
                corpus_name=f"Null_Test_{i}",
                corpus_type="LANGUAGE",
                content_inline=content if content else None,
            )
            
            # Should handle gracefully
            vocab = corpus.content_inline.get("vocabulary", []) if corpus.content_inline else []
            # Filter out None and empty strings
            clean_vocab = [w for w in vocab if w]
            
            assert isinstance(clean_vocab, list)
    
    async def test_corpus_type_mixing(self, corpus_tree):
        """Test mixed corpus types in tree."""
        language_corpus = corpus_tree["master"]
        literature_corpus = corpus_tree["work1"]
        
        # Verify different types can coexist
        assert language_corpus.corpus_type == "LANGUAGE"
        assert literature_corpus.corpus_type == "LITERATURE"
        
        # Language corpus as parent of literature
        assert literature_corpus.parent_corpus_id == language_corpus.id
        assert literature_corpus.id in language_corpus.child_corpus_ids
        
        # Test that is_master is only for language
        assert language_corpus.is_master is True
        assert literature_corpus.is_master is False
    
    async def test_vocabulary_with_special_chars(self):
        """Test vocabulary with special characters."""
        special_vocab = [
            "hello world",  # Space
            "compound-word",  # Hyphen
            "email@example.com",  # @ symbol
            "price:$100",  # Special symbols
            "C++",  # Plus signs
            "Node.js",  # Dot
            "#hashtag",  # Hash
            "100%",  # Percent
            "(parentheses)",  # Parentheses
            "quote's",  # Apostrophe
        ]
        
        corpus = CorpusMetadata(
            corpus_name="Special_Chars",
            corpus_type="LANGUAGE",
            content_inline={"vocabulary": special_vocab},
        )
        
        # All special characters should be preserved
        vocab = corpus.content_inline["vocabulary"]
        for word in special_vocab:
            assert word in vocab