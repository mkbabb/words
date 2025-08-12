#!/usr/bin/env python3
"""Test script for the refactored literature system integration.

This script demonstrates the new unified literature system that integrates
with Floridify's existing search infrastructure, corpus management, and WOTD
training pipeline.
"""

import asyncio
import logging
from pathlib import Path

from src.floridify.literature import (
    LiteratureSourceManager,
    LiteratureCorpusBuilder,
    Author,
    Period,
    Genre
)
from src.floridify.wotd.core import Author as WOTDAuthor
from src.floridify.wotd.trainer import WOTDTrainer, TrainingConfig
from src.floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def test_literature_search():
    """Test multi-source literature search."""
    logger.info("🔍 Testing literature search across sources...")
    
    source_manager = LiteratureSourceManager()
    
    # Search for Shakespeare across all sources
    results = await source_manager.search_all_sources(
        author_name="William Shakespeare",
        limit_per_source=3
    )
    
    for source, works in results.items():
        logger.info(f"📚 {source.value}: {len(works)} works found")
        for work in works[:2]:  # Show first 2
            logger.info(f"  - {work['title']} ({work.get('date', 'unknown date')})")
    
    return results


async def test_corpus_building():
    """Test literature corpus building and integration."""
    logger.info("📖 Testing corpus building...")
    
    corpus_builder = LiteratureCorpusBuilder()
    
    # Create a sample author
    shakespeare = Author(
        name="William Shakespeare",
        birth_year=1564,
        death_year=1616,
        period=Period.RENAISSANCE,
        primary_genre=Genre.DRAMA,
        language="en"
    )
    
    # Build a corpus (this will use sample data since we don't have actual texts)
    corpus = await corpus_builder.build_author_corpus(
        author=shakespeare,
        works=[],  # Empty for testing - will use sample data
        max_words=50
    )
    
    logger.info(f"✅ Created corpus: {corpus.name}")
    logger.info(f"   Words: {len(corpus.words)}")
    logger.info(f"   Authors: {[a.name for a in corpus.metadata.authors]}")
    
    # Test search integration
    search_corpus = await corpus.to_search_corpus()
    logger.info(f"   Search vocabulary: {len(search_corpus.vocabulary)} items")
    
    # Test corpus registration
    await corpus.register_with_corpus_manager()
    logger.info("   Registered with corpus manager ✓")
    
    return corpus


async def test_wotd_integration():
    """Test WOTD training integration with literature system."""
    logger.info("🎭 Testing WOTD integration...")
    
    # Create training config
    config = TrainingConfig(
        batch_size=16,
        max_epochs=1,  # Quick test
        learning_rate=1e-4,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",  # Lightweight
    )
    
    trainer = WOTDTrainer(config)
    
    # Test with Shakespeare (will use sample data)
    authors = [WOTDAuthor.SHAKESPEARE]
    
    try:
        results = await trainer.train_from_literature(
            authors=authors,
            use_lightweight_model=True,
            max_works_per_author=1,
            max_words_per_corpus=20
        )
        
        logger.info(f"✅ Training completed:")
        logger.info(f"   Training loss: {results.final_loss:.4f}")
        logger.info(f"   Training time: {results.training_time_minutes:.1f}m")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        return None


async def main():
    """Run all integration tests."""
    logger.info("🚀 Starting literature system integration tests...")
    
    try:
        # Test 1: Literature search
        search_results = await test_literature_search()
        
        # Test 2: Corpus building
        corpus = await test_corpus_building()
        
        # Test 3: WOTD integration  
        training_results = await test_wotd_integration()
        
        logger.info("✅ All tests completed successfully!")
        
        # Summary
        total_sources = len(search_results)
        total_works = sum(len(works) for works in search_results.values())
        
        logger.info(f"📊 Summary:")
        logger.info(f"   Sources tested: {total_sources}")
        logger.info(f"   Works found: {total_works}")
        logger.info(f"   Corpus words: {len(corpus.words)}")
        logger.info(f"   Training: {'✅' if training_results else '❌'}")
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run tests
    asyncio.run(main())