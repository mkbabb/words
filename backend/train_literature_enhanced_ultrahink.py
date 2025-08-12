#!/usr/bin/env python3
"""Ultrahink literature-based WOTD training with GPT-5 analysis.

Enhanced training pipeline using literature from Shakespeare, Woolf, Dante, and Joyce
with GPT-5 analysis for semantic classification and large-scale training datasets.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from floridify.wotd.trainer import WOTDTrainer
from floridify.wotd.core import TrainingConfig, Author
from floridify.wotd.literature import build_literature_training_set
from floridify.utils.logging import get_logger
from floridify.utils.paths import get_cache_directory

logger = get_logger(__name__)


async def generate_literature_training_data():
    """Generate comprehensive literature-based training data using GPT-5."""
    logger.info("🎭 Generating literature training data with GPT-5 analysis")
    logger.info("📚 Authors: Shakespeare, Woolf, Dante, Joyce")
    
    # Target authors for training
    target_authors = [
        Author.SHAKESPEARE,  # Renaissance drama/poetry
        Author.WOOLF,       # Modernist novel/essay  
        Author.DANTE,       # Medieval epic poetry
        Author.JOYCE,       # Modernist experimental fiction
    ]
    
    # Build literature corpora with AI analysis
    logger.info("🔍 Building author corpora with GPT-5 semantic analysis...")
    corpora = await build_literature_training_set(
        authors=target_authors,
        max_works_per_author=3  # Focus on major works per author
    )
    
    # Convert to training format expected by trainer
    training_corpora = []
    semantic_ids = {}
    
    for author_name, corpus in corpora.items():
        # Extract semantic ID from corpus metadata
        style_idx = list(corpus.style.__class__).index(corpus.style)
        complexity_idx = list(corpus.complexity.__class__).index(corpus.complexity) 
        era_idx = list(corpus.era.__class__).index(corpus.era)
        variation_idx = corpus.metadata.get("semantic_variation", 0)
        
        # Create corpus data structure
        corpus_data = {
            "id": corpus.id,
            "style": corpus.style.value,
            "complexity": corpus.complexity.value,
            "era": corpus.era.value,
            "words": [
                {"word": word.word, "frequency": word.frequency} 
                for word in corpus.words
            ],
            "metadata": corpus.metadata
        }
        
        training_corpora.append(corpus_data)
        semantic_ids[corpus.id] = [style_idx, complexity_idx, era_idx, variation_idx]
        
        logger.info(f"✅ {author_name}: {len(corpus.words)} words, semantic_id={semantic_ids[corpus.id]}")
    
    # Generate additional synthetic variations for scale
    logger.info("🎲 Generating synthetic variations for scale...")
    
    # Create variations of each corpus for more training data
    expanded_corpora = []
    expanded_semantic_ids = {}
    
    for corpus_data in training_corpora:
        base_id = corpus_data["id"]
        base_words = corpus_data["words"]
        
        # Create 3 variations per author for more training diversity
        for variation in range(3):
            variant_id = f"{base_id}_var_{variation}"
            
            # Select subset with slight variation
            start_idx = variation * 50
            variant_words = base_words[start_idx:start_idx + 150]  # 150 words per variant
            
            if len(variant_words) < 50:  # Skip if too few words
                continue
                
            variant_corpus = {
                "id": variant_id,
                "style": corpus_data["style"],
                "complexity": corpus_data["complexity"], 
                "era": corpus_data["era"],
                "words": variant_words,
                "metadata": {
                    **corpus_data["metadata"],
                    "variation": variation,
                    "source": "literature_variant"
                }
            }
            
            # Slight variation in semantic ID
            base_semantic = semantic_ids[base_id]
            variant_semantic = [
                base_semantic[0],  # Keep style
                base_semantic[1],  # Keep complexity
                base_semantic[2],  # Keep era
                (base_semantic[3] + variation) % 5  # Vary the variation dimension
            ]
            
            expanded_corpora.append(variant_corpus)
            expanded_semantic_ids[variant_id] = variant_semantic
    
    # Combine original and variants
    all_corpora = training_corpora + expanded_corpora
    all_semantic_ids = {**semantic_ids, **expanded_semantic_ids}
    
    logger.info(f"📊 Generated {len(all_corpora)} total training corpora")
    logger.info(f"🎭 Unique semantic IDs: {len(set(tuple(sid) for sid in all_semantic_ids.values()))}")
    
    return all_corpora, all_semantic_ids


async def main():
    """Ultrahink literature-based training with GPT-5 and scaled datasets."""
    logger.info("🚀 ULTRAHINK Literature WOTD Training")
    logger.info("=" * 50)
    logger.info("📚 Literature-based with GPT-5 semantic analysis")
    logger.info("🎯 Authors: Shakespeare, Woolf, Dante, Joyce")
    logger.info("⚡ Enhanced training optimization")
    
    start_time = time.time()
    
    try:
        # Generate literature training data
        logger.info("\n🎭 Stage 1: Literature Corpus Generation")
        corpora, semantic_ids = await generate_literature_training_data()
        
        # Save training data to cache directory
        cache_dir = get_cache_directory("wotd_literature_training")
        
        with open(cache_dir / "literature_corpora.json", "w") as f:
            json.dump(corpora, f, indent=2)
            
        with open(cache_dir / "literature_semantic_ids.json", "w") as f:
            json.dump(semantic_ids, f, indent=2)
            
        logger.info(f"💾 Saved training data to {cache_dir}")
        
        # Enhanced training configuration
        config = TrainingConfig(
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",  # Stable, tested model
            encoder_epochs=100,        # Extended training for better learning
            words_per_corpus=150,      # Rich vocabulary per corpus
            encoder_lr=0.0002,         # Optimized learning rate from previous experiments
            base_model="meta-llama/Llama-2-7b-hf",
        )
        
        logger.info("\n⚙️ Enhanced Training Configuration:")
        logger.info(f"  📊 Embedding Model: {config.embedding_model}")
        logger.info(f"  🔄 Encoder Epochs: {config.encoder_epochs}")
        logger.info(f"  📝 Words per Corpus: {config.words_per_corpus}")
        logger.info(f"  🧠 Learning Rate: {config.encoder_lr}")
        logger.info(f"  🎯 Total Training Words: {sum(len(c['words']) for c in corpora)}")
        logger.info(f"  📚 Total Corpora: {len(corpora)}")
        
        # Create trainer with enhanced configuration
        trainer = WOTDTrainer(config)
        
        # Run literature-based training
        logger.info("\n🚀 Stage 2: Enhanced Training Execution")
        logger.info("   📖 Literature-based semantic learning")
        logger.info("   🤖 GPT-5 semantic classification")
        logger.info("   ⚡ Optimized loss reduction")
        
        # Use the proper cache directory for model output
        output_dir = str(get_cache_directory("wotd_models") / "literature_ultrahink")
        
        results = await trainer.train_from_synthetic_data(
            corpora=corpora,
            semantic_ids=semantic_ids,
            output_dir=output_dir,
            use_lightweight_model=True
        )
        
        duration = time.time() - start_time
        
        logger.success("🎉 ULTRAHINK LITERATURE TRAINING COMPLETE!")
        logger.info("\n📊 Training Results:")
        logger.info("=" * 30)
        
        logger.info(f"  ⏱️  Duration: {duration:.2f}s ({duration/60:.1f} min)")
        logger.info(f"  📚 Authors Processed: 4 (Shakespeare, Woolf, Dante, Joyce)")
        logger.info(f"  🏛️ Total Corpora: {len(corpora)}")
        logger.info(f"  📝 Total Words: {sum(len(c['words']) for c in corpora)}")
        logger.info(f"  🎭 Unique Semantic IDs: {len(set(tuple(sid) for sid in semantic_ids.values()))}")
        
        # Analyze semantic coverage
        logger.info("\n🎭 Semantic Coverage Analysis:")
        logger.info("-" * 35)
        
        styles = set()
        complexities = set()
        eras = set()
        variations = set()
        
        for semantic_id in semantic_ids.values():
            style, complexity, era, variation = semantic_id
            styles.add(style)
            complexities.add(complexity)
            eras.add(era) 
            variations.add(variation)
        
        logger.info(f"  🎨 Style Coverage: {len(styles)} levels ({sorted(styles)})")
        logger.info(f"  📊 Complexity Coverage: {len(complexities)} levels ({sorted(complexities)})")
        logger.info(f"  🕰️ Era Coverage: {len(eras)} periods ({sorted(eras)})")
        logger.info(f"  🔄 Variation Coverage: {len(variations)} variants ({sorted(variations)})")
        
        # Quality metrics
        total_words = sum(len(c['words']) for c in corpora)
        unique_ids = len(set(tuple(sid) for sid in semantic_ids.values()))
        
        logger.info("\n✅ Quality Metrics:")
        logger.info("-" * 20)
        logger.info(f"  📈 Total Literature Words: {total_words}")
        logger.info(f"  🎭 Semantic Diversity: {unique_ids} unique patterns")
        logger.info(f"  🎯 Coverage Ratio: {unique_ids/len(semantic_ids):.1%}")
        logger.info(f"  📖 Avg Words/Corpus: {total_words//len(corpora)}")
        logger.info(f"  💾 Model Location: {output_dir}")
        
        # Enhanced validation
        assert total_words >= 2000, f"Expected 2000+ words, got {total_words}"
        assert unique_ids >= 8, f"Expected 8+ unique semantic IDs, got {unique_ids}" 
        assert len(corpora) >= 12, f"Expected 12+ corpora, got {len(corpora)}"
        assert len(styles) >= 3, f"Expected 3+ style variations, got {len(styles)}"
        assert len(eras) >= 3, f"Expected 3+ era variations, got {len(eras)}"
        
        logger.success("🎯 ALL ULTRAHINK VALIDATIONS PASSED!")
        logger.success(f"🚀 Literature Training Complete: {total_words} words from classic literature!")
        
        logger.info("\n🔄 Next Steps:")
        logger.info("  📊 Run inference testing with literature semantic IDs")
        logger.info("  🎭 Generate words from learned semantic patterns")
        logger.info("  📈 Compare with synthetic training approaches")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Literature training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)