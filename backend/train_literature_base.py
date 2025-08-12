#!/usr/bin/env python3
"""Generate literature training using base corpora only (no AI augmentation).

Uses Shakespeare and Woolf base corpora to create solid training foundation
without GPT-5 Mini API issues.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from floridify.wotd.trainer import WOTDTrainer
from floridify.wotd.core import TrainingConfig
from floridify.utils.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Generate base literature training set."""
    logger.info("🎯 Base Literature Training: Shakespeare + Woolf (No Augmentation)")
    logger.info("=" * 68)
    
    start_time = time.time()
    
    try:
        # Use supported authors with high word count per corpus
        authors = [
            "Shakespeare",  # Renaissance, complex, poetic, classical
            "Woolf",        # Modernist, psychological, stream-of-consciousness
        ]
        
        logger.info(f"📚 Base authors for robust training:")
        for i, author in enumerate(authors, 1):
            logger.info(f"  {i}. {author}")
        
        # Configure for comprehensive base training
        config = TrainingConfig(
            # Efficient embedding model
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",  # 384D, fast, Apple Silicon optimized
            
            # Training parameters for quality
            encoder_epochs=30,        # More epochs for better learning with limited data
            words_per_corpus=200,     # Maximum vocabulary per author
            encoder_lr=0.0008,        # Fine-tuned learning rate
            
            # Model selection
            base_model="meta-llama/Llama-2-7b-hf",
        )
        
        logger.info("")
        logger.info("⚙️ Optimized Training Configuration:")
        logger.info(f"  📊 Embedding Model: {config.embedding_model}")
        logger.info(f"  🔄 Encoder Epochs: {config.encoder_epochs}")
        logger.info(f"  📝 Words per Corpus: {config.words_per_corpus}")
        logger.info(f"  🎯 Expected Total Words: {len(authors) * config.words_per_corpus}")
        logger.info(f"  ⚡ Apple Silicon MPS: Enabled")
        
        # Create trainer
        trainer = WOTDTrainer(config)
        
        # Run base literature training (no AI augmentation)
        logger.info("")
        logger.info("🚀 Starting focused base literature training...")
        logger.info("   (Skipping AI augmentation to avoid GPT-5 Mini API issues)")
        
        results = await trainer.train_from_literature(
            authors=authors,
            output_dir="./models/wotd_literature_base",
            use_lightweight_model=True,     # Use MiniLM for efficiency
            augment_with_ai=False,          # Skip augmentation to avoid API issues
            max_words_per_author=200        # Rich vocabulary per base author
        )
        
        duration = time.time() - start_time
        
        logger.success("🎉 BASE LITERATURE TRAINING COMPLETE!")
        logger.info("")
        logger.info("📊 Training Results:")
        logger.info("=" * 25)
        
        logger.info(f"  ⏱️  Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"  📚 Authors: {len(authors)}")
        logger.info(f"  🏛️ Corpora: {results.num_corpora}")
        logger.info(f"  📝 Total Words: {results.total_words}")
        logger.info(f"  🔢 Semantic IDs: {len(results.semantic_ids)}")
        
        # Detailed corpus analysis
        logger.info("")
        logger.info("🔍 Corpus Analysis:")
        logger.info("-" * 20)
        
        for corpus_id, semantic_id in sorted(results.semantic_ids.items()):
            author = corpus_id.split('_')[0].title()
            style, complexity, era, variation = semantic_id
            logger.info(f"  {author:12} → [{style},{complexity},{era},{variation}] ({corpus_id})")
        
        # Quality validation
        unique_ids = set(tuple(sid) for sid in results.semantic_ids.values())
        
        logger.info("")
        logger.info("✅ Quality Metrics:")
        logger.info("-" * 17)
        logger.info(f"  📝 Words per Author: {results.total_words // len(authors)}")
        logger.info(f"  🎭 Unique Semantic IDs: {len(unique_ids)}")
        logger.info(f"  📊 Coverage Ratio: {len(unique_ids)/len(results.semantic_ids):.1%}")
        logger.info(f"  🏛️ Base Corpora: {results.num_corpora}")
        
        # Model files
        logger.info("")
        logger.info("💾 Model Files:")
        logger.info("-" * 13)
        for model_type, path in results.model_paths.items():
            logger.info(f"  {model_type}: {path}")
        
        # Quality assertions
        assert results.total_words >= 200, f"Expected 200+ words, got {results.total_words}"
        assert results.num_corpora >= len(authors), f"Expected {len(authors)}+ corpora, got {results.num_corpora}"
        assert len(unique_ids) >= 1, f"No unique semantic IDs generated"
        
        logger.success("🎯 ALL VALIDATIONS PASSED!")
        logger.success(f"🚀 Base Literature Training Ready: {results.total_words} words!")
        
        logger.info("")
        logger.info("🔄 Next Steps:")
        logger.info("  1. Test inference quality on this base model")
        logger.info("  2. Evaluate semantic ID accuracy and consistency")  
        logger.info("  3. Run development loop for optimization")
        logger.info("  4. Scale up with working augmentation later")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Base literature training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)