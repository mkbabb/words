#!/usr/bin/env python3
"""Enhanced literature training with more examples and longer training."""

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
    """Enhanced training with 2x examples and longer training."""
    logger.info("🚀 Enhanced WOTD Training: More Examples + Longer Training")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    try:
        # Use supported authors with maximum vocabulary extraction
        authors = [
            "Shakespeare",  # Renaissance, complex, poetic, classical
            "Woolf",        # Modernist, psychological, stream-of-consciousness
        ]
        
        logger.info(f"📚 Enhanced training with {len(authors)} authors:")
        for i, author in enumerate(authors, 1):
            logger.info(f"  {i}. {author}")
        
        # Enhanced configuration with more samples and longer training
        config = TrainingConfig(
            # Efficient embedding model
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",  # 384D, fast, Apple Silicon optimized
            
            # Enhanced training parameters
            encoder_epochs=50,        # 2x longer training for better learning
            words_per_corpus=500,     # 2.5x more vocabulary per author  
            encoder_lr=0.0005,        # Lower learning rate for stability with more data
            
            # Model selection
            base_model="meta-llama/Llama-2-7b-hf",
        )
        
        logger.info("")
        logger.info("⚙️ Enhanced Training Configuration:")
        logger.info(f"  📊 Embedding Model: {config.embedding_model}")
        logger.info(f"  🔄 Encoder Epochs: {config.encoder_epochs} (2x longer)")
        logger.info(f"  📝 Words per Corpus: {config.words_per_corpus} (2.5x more)")
        logger.info(f"  🎯 Expected Base Words: {len(authors) * config.words_per_corpus}")
        logger.info(f"  🤖 With AI Augmentation: ~{len(authors) * config.words_per_corpus * 5} words")
        logger.info(f"  ⚡ Apple Silicon MPS: Enabled")
        
        # Create trainer
        trainer = WOTDTrainer(config)
        
        # Run enhanced literature training with AI augmentation
        logger.info("")
        logger.info("🚀 Starting enhanced literature training...")
        logger.info("   (More examples + longer training for superior quality)")
        
        results = await trainer.train_from_literature(
            authors=authors,
            output_dir="./models/wotd_literature_enhanced",
            use_lightweight_model=True,     # Use efficient model
            augment_with_ai=True,          # Generate variations
            max_words_per_author=500       # 2.5x more vocabulary
        )
        
        duration = time.time() - start_time
        
        logger.success("🎉 ENHANCED LITERATURE TRAINING COMPLETE!")
        logger.info("")
        logger.info("📊 Enhanced Training Results:")
        logger.info("=" * 30)
        
        logger.info(f"  ⏱️  Total Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"  📚 Base Authors: {len(authors)}")
        logger.info(f"  🏛️ Total Corpora: {results.num_corpora}")
        logger.info(f"  📝 Total Words: {results.total_words}")
        logger.info(f"  🔢 Semantic IDs: {len(results.semantic_ids)}")
        logger.info(f"  🤖 Augmentation Ratio: {results.num_corpora/len(authors):.1f}x")
        
        # Enhanced semantic diversity analysis
        logger.info("")
        logger.info("🎭 Enhanced Semantic Diversity Analysis:")
        logger.info("-" * 38)
        
        # Analyze semantic distribution
        style_dist = {}
        complexity_dist = {}
        era_dist = {}
        variation_dist = {}
        
        for corpus_id, semantic_id in results.semantic_ids.items():
            style, complexity, era, variation = semantic_id
            
            style_dist[style] = style_dist.get(style, 0) + 1
            complexity_dist[complexity] = complexity_dist.get(complexity, 0) + 1
            era_dist[era] = era_dist.get(era, 0) + 1
            variation_dist[variation] = variation_dist.get(variation, 0) + 1
        
        logger.info(f"  🎨 Style Coverage: {len(style_dist)} unique styles")
        for style, count in sorted(style_dist.items()):
            logger.info(f"    Style {style}: {count} corpora")
            
        logger.info(f"  📊 Complexity Coverage: {len(complexity_dist)} levels")
        for complexity, count in sorted(complexity_dist.items()):
            logger.info(f"    Complexity {complexity}: {count} corpora")
            
        logger.info(f"  🕰️ Era Coverage: {len(era_dist)} periods")
        for era, count in sorted(era_dist.items()):
            logger.info(f"    Era {era}: {count} corpora")
            
        logger.info(f"  🔄 Variation Coverage: {len(variation_dist)} variants")
        for variation, count in sorted(variation_dist.items()):
            logger.info(f"    Variation {variation}: {count} corpora")
        
        # Quality validation with enhanced metrics
        unique_ids = set(tuple(sid) for sid in results.semantic_ids.values())
        diversity_ratio = len(unique_ids) / len(results.semantic_ids)
        words_per_author = results.total_words // len(authors)
        
        logger.info("")
        logger.info("✅ Enhanced Quality Validation:")
        logger.info("-" * 32)
        logger.info(f"  📈 Total Words: {results.total_words}")
        logger.info(f"  📚 Words per Author: {words_per_author}")
        logger.info(f"  🎭 Semantic Diversity: {len(unique_ids)} unique IDs")
        logger.info(f"  🎯 Diversity Ratio: {diversity_ratio:.1%}")
        logger.info(f"  🤖 Augmentation Factor: {results.num_corpora/len(authors):.1f}x")
        logger.info(f"  📊 Coverage: {len(authors)} authors → {results.num_corpora} corpora")
        
        # Enhanced quality assertions
        assert results.total_words >= 800, f"Expected 800+ words, got {results.total_words}"
        assert words_per_author >= 400, f"Expected 400+ words per author, got {words_per_author}"
        assert len(unique_ids) >= 2, f"Expected 2+ unique semantic IDs, got {len(unique_ids)}"
        assert diversity_ratio >= 0.5, f"Low diversity ratio: {diversity_ratio:.1%}"
        
        logger.success("🎯 ALL ENHANCED VALIDATIONS PASSED!")
        logger.success(f"🚀 Enhanced Literature Training Complete: {results.total_words} words, {len(unique_ids)} semantic patterns!")
        
        # Show detailed corpus mapping
        logger.info("")
        logger.info("🔍 Enhanced Corpus → Semantic ID Mapping:")
        logger.info("-" * 41)
        
        for corpus_id, semantic_id in sorted(results.semantic_ids.items()):
            style, complexity, era, variation = semantic_id
            corpus_type = "Base" if corpus_id.endswith("_base") else "Augmented"
            author = corpus_id.split('_')[0].title()
            logger.info(f"  {corpus_id:28} → [{style},{complexity},{era},{variation}] ({corpus_type})")
        
        # Model files
        logger.info("")
        logger.info("💾 Enhanced Model Files:")
        logger.info("-" * 22)
        for model_type, path in results.model_paths.items():
            logger.info(f"  {model_type}: {path}")
        
        logger.info("")
        logger.info("🔄 Next: Comprehensive inference testing and reporting")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Enhanced literature training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)