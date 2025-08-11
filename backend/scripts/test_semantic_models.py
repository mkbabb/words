#!/usr/bin/env python3
"""Test script to verify both semantic models work correctly."""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from floridify.models.definition import Language
from floridify.search.language import LanguageSearch
from floridify.search.semantic.constants import BGE_M3_MODEL, MINI_LM_MODEL
from floridify.utils.logging import get_logger

logger = get_logger(__name__)

# Test words with various characteristics
TEST_WORDS = [
    # English words
    "hello", "world", "computer", "beautiful", "running",
    # Words with diacritics (for multilingual test)
    "café", "naïve", "résumé", "piñata",
    # Misspellings
    "compter", "beautful", "wrld",
    # Phrases
    "hello world", "artificial intelligence",
]

async def test_model(model_name: str, languages: list[Language]):
    """Test a specific semantic model."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {model_name}")
    logger.info(f"{'='*60}")
    
    start_time = time.time()
    
    # Initialize search with specific model
    search = LanguageSearch(
        languages=languages,
        semantic=True,
        semantic_model=model_name,
        force_rebuild=False  # Use cache if available
    )
    
    await search.initialize()
    
    init_time = time.time() - start_time
    logger.info(f"✅ Initialization complete in {init_time:.2f}s")
    
    # Test searches
    logger.info("\n📝 Testing searches:")
    for word in TEST_WORDS[:5]:  # Test subset
        results = await search.search(word, max_results=3)
        if results:
            top_result = results[0]
            logger.info(f"  '{word}' → '{top_result.word}' (score: {top_result.score:.3f}, method: {top_result.method})")
        else:
            logger.info(f"  '{word}' → No results")
    
    # Get stats
    stats = search.get_stats()
    logger.info(f"\n📊 Stats: {stats}")
    
    return init_time

async def main():
    """Test both semantic models."""
    logger.info("🚀 Testing Semantic Models")
    
    # Test BGE-M3 (multilingual)
    bge_time = await test_model(
        BGE_M3_MODEL, 
        [Language.ENGLISH, Language.FRENCH]
    )
    
    # Small delay to separate logs
    await asyncio.sleep(1)
    
    # Test MiniLM (English-only)
    minilm_time = await test_model(
        MINI_LM_MODEL,
        [Language.ENGLISH]
    )
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("📈 Performance Summary:")
    logger.info(f"  BGE-M3 (1024D): {bge_time:.2f}s")
    logger.info(f"  MiniLM (384D): {minilm_time:.2f}s")
    logger.info(f"  Speedup: {bge_time/minilm_time:.2f}x")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())