#!/usr/bin/env python3
"""Generate 1k diverse literature-based training samples.

Uses multiple classical authors to create a rich, diverse training corpus
that spans different eras, styles, and complexity levels.
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
    logger.info("🎯 Generating 1K Literature-Based Training Samples")
    logger.info("=" * 55)
    
    start_time = time.time()
    
    try:
        # Select diverse authors across different periods and styles
        authors = [
            # Classical foundations
            "Shakespeare",    # Renaissance, complex, poetic
            "Dickens",        # Victorian, narrative, social
            "Austen",         # Regency, elegant, social
            
            # Modernist diversity  
            "Joyce",          # Modernist, experimental, complex
            "Woolf",          # Modernist, psychological, lyrical
            
            # Additional depth
            "Tolstoy",        # Russian, philosophical, epic
            "Cervantes",      # Spanish, adventurous, classical
            "Dante",          # Medieval, spiritual, poetic
        ]
        
        logger.info(f"📚 Selected {len(authors)} authors for diverse training:")
        for i, author in enumerate(authors, 1):
            logger.info(f"  {i}. {author}")
        
        # Configure for comprehensive training
        config = TrainingConfig(
            # Efficient embedding model for speed
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",  # 384D, fast
            
            # Training parameters optimized for quality and diversity
            encoder_epochs=20,        # More epochs for better learning
            words_per_corpus=150,     # More words per author for diversity
            encoder_lr=0.001,         # Learning rate for convergence
            
            # Model selection
            base_model="meta-llama/Llama-2-7b-hf",  # Local model for DSL training
        )
        
        logger.info("")
        logger.info("⚙️ Training Configuration:")
        logger.info(f"  📊 Embedding Model: {config.embedding_model}")
        logger.info(f"  🔄 Encoder Epochs: {config.encoder_epochs}")
        logger.info(f"  📝 Words per Author: {config.words_per_corpus}")
        logger.info(f"  🎯 Expected Total Words: {len(authors) * config.words_per_corpus}")
        
        # Create trainer
        trainer = WOTDTrainer(config)
        
        # Run comprehensive literature training
        logger.info("")
        logger.info("🚀 Starting comprehensive literature-based training...")
        
        results = await trainer.train_from_literature(
            authors=authors,
            output_dir="./models/wotd_literature_1k",
            use_lightweight_model=True,     # Use efficient model
            augment_with_ai=True,          # Generate variations for diversity
            max_words_per_author=150       # Rich vocabulary per author
        )
        
        duration = time.time() - start_time
        
        logger.success("🎉 COMPREHENSIVE LITERATURE TRAINING COMPLETE!")
        logger.info("")
        logger.info("📊 Training Results Summary:")
        logger.info("=" * 35)
        
        logger.info(f"  ⏱️  Total Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"  📚 Authors Processed: {len(authors)}")
        logger.info(f"  🏛️ Total Corpora: {results.num_corpora}")
        logger.info(f"  📝 Total Words: {results.total_words}")
        logger.info(f"  🔢 Semantic IDs: {len(results.semantic_ids)}")
        logger.info(f"  💾 Models Saved: {len(results.model_paths)}")
        
        # Display semantic diversity
        logger.info("")
        logger.info("🎭 Semantic Diversity Analysis:")
        logger.info("-" * 32)
        
        # Group by semantic characteristics
        style_counts = {}
        era_counts = {}
        complexity_counts = {}
        
        for corpus_id, semantic_id in results.semantic_ids.items():
            style, complexity, era, variation = semantic_id
            
            style_counts[style] = style_counts.get(style, 0) + 1
            era_counts[era] = era_counts.get(era, 0) + 1  
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        logger.info(f"  🎨 Style Distribution: {len(style_counts)} unique styles")
        for style, count in sorted(style_counts.items()):
            logger.info(f"    Style {style}: {count} corpora")
            
        logger.info(f"  📊 Complexity Distribution: {len(complexity_counts)} levels")
        for complexity, count in sorted(complexity_counts.items()):
            logger.info(f"    Complexity {complexity}: {count} corpora")
            
        logger.info(f"  🕰️ Era Distribution: {len(era_counts)} eras")  
        for era, count in sorted(era_counts.items()):
            logger.info(f"    Era {era}: {count} corpora")
        
        # Sample semantic IDs
        logger.info("")
        logger.info("🔍 Sample Semantic Mappings:")
        logger.info("-" * 28)
        
        sample_count = min(10, len(results.semantic_ids))
        for i, (corpus_id, semantic_id) in enumerate(list(results.semantic_ids.items())[:sample_count]):
            author = corpus_id.split('_')[0].title()
            style, complexity, era, variation = semantic_id
            logger.info(f"  {i+1:2d}. {author:12} → [{style},{complexity},{era},{variation}] = {corpus_id}")
        
        # Validate diversity
        unique_ids = set(tuple(sid) for sid in results.semantic_ids.values())
        diversity_ratio = len(unique_ids) / len(results.semantic_ids)
        
        logger.info("")
        logger.info("✅ Training Quality Metrics:")
        logger.info("-" * 27)
        logger.info(f"  📈 Semantic Diversity: {len(unique_ids)} unique IDs from {len(results.semantic_ids)} corpora")
        logger.info(f"  🎯 Diversity Ratio: {diversity_ratio:.1%}")
        logger.info(f"  📊 Coverage: {len(authors)} authors, {results.num_corpora} total variants")
        
        # Quality assertions
        assert results.total_words >= 1000, f"Expected 1k+ words, got {results.total_words}"
        assert len(results.semantic_ids) >= len(authors), f"Expected {len(authors)}+ corpora, got {len(results.semantic_ids)}"
        assert diversity_ratio > 0.5, f"Low diversity ratio: {diversity_ratio:.1%}"
        
        logger.success("🎯 ALL QUALITY METRICS PASSED!")
        logger.success("🚀 1K Literature Training Dataset Ready!")
        
        # Next steps
        logger.info("")
        logger.info("🔄 Next Steps:")
        logger.info("  1. Test inference quality on diverse literature samples")
        logger.info("  2. Evaluate semantic ID accuracy and consistency")
        logger.info("  3. Optimize model performance for production deployment")
        logger.info("  4. Validate robustness across different text types")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Literature training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)