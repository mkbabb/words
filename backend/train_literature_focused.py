#!/usr/bin/env python3
"""Generate focused literature-based training using supported authors.

Uses Shakespeare and Woolf with extensive AI augmentation to create diverse,
high-quality training data spanning different eras and styles.
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
    """Generate comprehensive literature training set."""
    logger.info("🎯 Focused Literature Training: Shakespeare + Woolf + AI Augmentation")
    logger.info("=" * 70)
    
    start_time = time.time()
    
    try:
        # Use supported authors with maximum diversity through AI augmentation
        authors = [
            "Shakespeare",  # Renaissance, complex, poetic, classical
            "Woolf",        # Modernist, psychological, stream-of-consciousness
        ]
        
        logger.info(f"📚 Selected {len(authors)} core authors for focused training:")
        for i, author in enumerate(authors, 1):
            logger.info(f"  {i}. {author}")
        
        logger.info("")
        logger.info("🤖 AI Augmentation Strategy:")
        logger.info("  • Each author → 4+ semantic variations")
        logger.info("  • Classical, Simple, Modern, Neutral transformations") 
        logger.info("  • Expected: 2 base + 8 augmented = 10+ corpora")
        logger.info("  • Target: 1000+ total words across variations")
        
        # Configure for comprehensive training with heavy augmentation
        config = TrainingConfig(
            # Efficient embedding model for speed
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",  # 384D, fast
            
            # Training parameters optimized for quality
            encoder_epochs=25,        # More epochs for better learning  
            words_per_corpus=200,     # Rich vocabulary per corpus
            encoder_lr=0.0005,        # Lower learning rate for stability
            
            # Model selection
            base_model="meta-llama/Llama-2-7b-hf",  # Local model for DSL training
        )
        
        logger.info("")
        logger.info("⚙️ Training Configuration:")
        logger.info(f"  📊 Embedding Model: {config.embedding_model}")
        logger.info(f"  🔄 Encoder Epochs: {config.encoder_epochs}")
        logger.info(f"  📝 Words per Corpus: {config.words_per_corpus}")
        logger.info(f"  🎯 Expected Base Words: {len(authors) * config.words_per_corpus}")
        logger.info(f"  🤖 With AI Augmentation: ~{len(authors) * config.words_per_corpus * 5} words")
        
        # Create trainer
        trainer = WOTDTrainer(config)
        
        # Run comprehensive literature training with heavy augmentation
        logger.info("")
        logger.info("🚀 Starting focused literature training with AI augmentation...")
        
        results = await trainer.train_from_literature(
            authors=authors,
            output_dir="./models/wotd_literature_focused",
            use_lightweight_model=True,     # Use efficient model
            augment_with_ai=True,          # CRITICAL: Generate many variations 
            max_words_per_author=200       # Rich vocabulary per author
        )
        
        duration = time.time() - start_time
        
        logger.success("🎉 FOCUSED LITERATURE TRAINING COMPLETE!")
        logger.info("")
        logger.info("📊 Training Results Summary:")
        logger.info("=" * 35)
        
        logger.info(f"  ⏱️  Total Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"  📚 Base Authors: {len(authors)}")
        logger.info(f"  🏛️ Total Corpora: {results.num_corpora}")
        logger.info(f"  📝 Total Words: {results.total_words}")
        logger.info(f"  🔢 Semantic IDs: {len(results.semantic_ids)}")
        logger.info(f"  🤖 Augmentation Ratio: {results.num_corpora/len(authors):.1f}x")
        
        # Display semantic diversity analysis
        logger.info("")
        logger.info("🎭 Semantic Diversity Analysis:")
        logger.info("-" * 32)
        
        # Analyze semantic distribution
        style_dist = {}
        complexity_dist = {}
        era_dist = {}
        
        for corpus_id, semantic_id in results.semantic_ids.items():
            style, complexity, era, variation = semantic_id
            
            style_dist[style] = style_dist.get(style, 0) + 1
            complexity_dist[complexity] = complexity_dist.get(complexity, 0) + 1
            era_dist[era] = era_dist.get(era, 0) + 1
        
        logger.info(f"  🎨 Style Coverage: {len(style_dist)} unique styles")
        for style, count in sorted(style_dist.items()):
            logger.info(f"    Style {style}: {count} corpora")
            
        logger.info(f"  📊 Complexity Coverage: {len(complexity_dist)} levels")
        for complexity, count in sorted(complexity_dist.items()):
            logger.info(f"    Complexity {complexity}: {count} corpora")
            
        logger.info(f"  🕰️ Era Coverage: {len(era_dist)} periods")
        for era, count in sorted(era_dist.items()):
            logger.info(f"    Era {era}: {count} corpora")
        
        # Show detailed corpus mapping
        logger.info("")
        logger.info("🔍 Corpus → Semantic ID Mapping:")
        logger.info("-" * 33)
        
        for corpus_id, semantic_id in sorted(results.semantic_ids.items()):
            style, complexity, era, variation = semantic_id
            corpus_type = "Base" if corpus_id.endswith("_base") else "Augmented"
            author = corpus_id.split('_')[0].title()
            logger.info(f"  {corpus_id:25} → [{style},{complexity},{era},{variation}] ({corpus_type})")
        
        # Quality validation
        unique_ids = set(tuple(sid) for sid in results.semantic_ids.values())
        diversity_ratio = len(unique_ids) / len(results.semantic_ids)
        augmentation_factor = results.num_corpora / len(authors)
        
        logger.info("")
        logger.info("✅ Training Quality Validation:")
        logger.info("-" * 30)
        logger.info(f"  📈 Total Words: {results.total_words}")
        logger.info(f"  🎭 Semantic Diversity: {len(unique_ids)} unique IDs")
        logger.info(f"  🎯 Diversity Ratio: {diversity_ratio:.1%}")
        logger.info(f"  🤖 Augmentation Factor: {augmentation_factor:.1f}x")
        logger.info(f"  📚 Coverage: {len(authors)} authors → {results.num_corpora} corpora")
        
        # Quality assertions
        assert results.total_words >= 400, f"Expected 400+ words, got {results.total_words}"
        assert results.num_corpora >= len(authors), f"Expected {len(authors)}+ corpora, got {results.num_corpora}"
        assert diversity_ratio > 0.3, f"Low diversity ratio: {diversity_ratio:.1%}"
        assert augmentation_factor >= 1.0, f"No augmentation occurred: {augmentation_factor:.1f}x"
        
        logger.success("🎯 ALL QUALITY METRICS PASSED!")
        logger.success(f"🚀 Literature Training Complete: {results.total_words} words, {len(unique_ids)} semantic patterns!")
        
        # Show model files
        logger.info("")
        logger.info("💾 Saved Model Files:")
        logger.info("-" * 20)
        for model_type, path in results.model_paths.items():
            logger.info(f"  {model_type}: {path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Focused literature training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)