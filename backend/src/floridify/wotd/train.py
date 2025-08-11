"""Main training script for WOTD system."""

import argparse
import json
import logging
import time
from pathlib import Path

from .inference import create_pipeline
from .language_model import train_dsl_model
from .semantic_encoder import (
    EncoderConfig,
    encode_words,
    learn_preference_vectors,
    save_encoder,
    train_semantic_encoder,
)

# Simple logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_word_corpora(data_dir: str) -> dict[str, list[str]]:
    """Load word corpora from data directory."""
    
    data_path = Path(data_dir)
    corpora = {}
    
    # Load built-in word list
    words_file = data_path.parent.parent / "data" / "words.txt"
    if words_file.exists():
        logger.info(f"Loading words from {words_file}")
        with open(words_file) as f:
            all_words = [line.strip().split('\t')[1] if '\t' in line else line.strip() 
                        for line in f if line.strip()]
        
        # Simple categorization based on word characteristics
        shakespeare_words = [w for w in all_words if any(c in w.lower() for c in ['th', 'doth', 'thou'])][:100]
        simple_words = [w for w in all_words if len(w) <= 6 and w.isalpha()][:100]
        complex_words = [w for w in all_words if len(w) >= 10][:100]
        beautiful_words = [w for w in all_words if any(pattern in w.lower() 
                          for pattern in ['ous', 'ful', 'ent', 'ine', 'escent'])][:100]
        
        corpora.update({
            'shakespeare': shakespeare_words or ['doth', 'thou', 'wherefore', 'beauteous'],
            'simple': simple_words or ['run', 'walk', 'see', 'think', 'good'],
            'complex': complex_words or ['extraordinary', 'magnificent', 'incomprehensible'],
            'beautiful': beautiful_words or ['luminous', 'ethereal', 'gossamer', 'efflorescent']
        })
    else:
        # Fallback data
        logger.warning("Using fallback word corpora")
        corpora = {
            'shakespeare': ['doth', 'thou', 'wherefore', 'beauteous', 'fair', 'sweet'],
            'modern': ['amazing', 'brilliant', 'fantastic', 'wonderful', 'great'],
            'simple': ['run', 'walk', 'see', 'think', 'good'],
            'complex': ['extraordinary', 'magnificent', 'incomprehensible', 'sophisticated'],
            'beautiful': ['luminous', 'ethereal', 'gossamer', 'efflorescent', 'radiant']
        }
    
    # Load additional corpora from JSON files if available
    for json_file in data_path.glob("*.json"):
        logger.info(f"Loading corpus from {json_file}")
        try:
            with open(json_file) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    corpora.update(data)
        except Exception as e:
            logger.warning(f"Failed to load {json_file}: {e}")
    
    logger.info(f"Loaded {len(corpora)} corpora with {sum(len(words) for words in corpora.values())} total words")
    return corpora


def train_complete_pipeline(
    data_dir: str = "data/wotd",
    output_dir: str = "models/wotd",
    encoder_epochs: int = 100,
    dsl_epochs: int = 10
) -> dict[str, str]:
    """Train the complete WOTD pipeline."""
    
    start_time = time.time()
    
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting WOTD training pipeline...")
    
    # Step 1: Load word corpora
    logger.info("Loading word corpora...")
    word_corpora = load_word_corpora(data_dir)
    
    # Step 2: Learn preference vectors
    logger.info("Learning preference vectors from corpora...")
    preference_vectors = learn_preference_vectors(word_corpora)
    
    # Step 3: Train semantic encoder
    logger.info(f"Training semantic encoder for {encoder_epochs} epochs...")
    encoder_config = EncoderConfig(num_epochs=encoder_epochs)
    encoder = train_semantic_encoder(preference_vectors, encoder_config)
    
    # Step 4: Encode words to Semantic IDs
    logger.info("Encoding preference vectors to Semantic IDs...")
    semantic_ids = encode_words(encoder, preference_vectors)
    
    # Log learned Semantic IDs
    logger.info("Learned Semantic IDs:")
    for name, semantic_id in semantic_ids.items():
        logger.info(f"  {name}: {semantic_id}")
    
    # Step 5: Train DSL model
    logger.info(f"Training DSL model for {dsl_epochs} epochs...")
    dsl_model = train_dsl_model(
        word_corpora,
        semantic_ids,
        output_dir=str(output_path / "dsl_model"),
        num_epochs=dsl_epochs
    )
    
    # Step 6: Save models
    logger.info("Saving trained models...")
    
    # Save semantic encoder
    encoder_path = output_path / "semantic_encoder.pt"
    save_encoder(encoder, str(encoder_path))
    
    # DSL model is already saved by train_dsl_model
    dsl_model_path = output_path / "dsl_model"
    
    # Save semantic IDs vocabulary
    vocab_path = output_path / "semantic_ids.json"
    with open(vocab_path, 'w') as f:
        json.dump(semantic_ids, f, indent=2)
    
    # Save training metadata
    metadata = {
        'training_time': time.time() - start_time,
        'encoder_epochs': encoder_epochs,
        'dsl_epochs': dsl_epochs,
        'num_corpora': len(word_corpora),
        'total_words': sum(len(words) for words in word_corpora.values()),
        'encoder_config': {
            'num_levels': encoder_config.num_levels,
            'codebook_size': encoder_config.codebook_size,
            'hidden_dim': encoder_config.hidden_dim
        }
    }
    
    metadata_path = output_path / "training_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Training completed in {metadata['training_time']:.2f} seconds")
    
    return {
        'encoder_path': str(encoder_path),
        'dsl_model_path': str(dsl_model_path),
        'semantic_ids_path': str(vocab_path),
        'metadata_path': str(metadata_path)
    }


def evaluate_pipeline(model_paths: dict[str, str]) -> dict[str, float]:
    """Simple evaluation of the trained pipeline."""
    
    logger.info("Evaluating trained pipeline...")
    
    # Load semantic IDs
    with open(model_paths['semantic_ids_path']) as f:
        semantic_ids = json.load(f)
    
    # Create pipeline
    pipeline = create_pipeline(
        model_paths['encoder_path'],
        model_paths['dsl_model_path'],
        semantic_ids
    )
    
    # Test queries
    test_queries = [
        "Generate [0,0,*,*] words",
        "Create beautiful words",
        "Simple modern words"
    ]
    
    results = {}
    total_time = 0.0
    
    for query in test_queries:
        logger.info(f"Testing query: '{query}'")
        result = pipeline.generate(query, num_words=5)
        
        logger.info(f"Generated: {result.words}")
        logger.info(f"Processing time: {result.processing_time:.3f}s")
        
        total_time += result.processing_time
        results[query] = len(result.words)
    
    # Simple metrics
    metrics = {
        'avg_processing_time': total_time / len(test_queries),
        'avg_words_generated': float(sum(results.values())) / len(results),
        'success_rate': float(len([r for r in results.values() if r > 0])) / len(results)
    }
    
    logger.info("Evaluation metrics:")
    for metric, value in metrics.items():
        logger.info(f"  {metric}: {value:.3f}")
    
    return metrics


def main() -> None:
    """Main training script entry point."""
    
    parser = argparse.ArgumentParser(description="Train WOTD ML pipeline")
    parser.add_argument("--data-dir", default="data/wotd", help="Data directory")
    parser.add_argument("--output-dir", default="models/wotd", help="Output directory")
    parser.add_argument("--encoder-epochs", type=int, default=50, help="Encoder training epochs")
    parser.add_argument("--dsl-epochs", type=int, default=5, help="DSL model training epochs")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate after training")
    
    args = parser.parse_args()
    
    try:
        # Train pipeline
        model_paths = train_complete_pipeline(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            encoder_epochs=args.encoder_epochs,
            dsl_epochs=args.dsl_epochs
        )
        
        logger.info("Training completed successfully!")
        logger.info("Model paths:")
        for name, path in model_paths.items():
            logger.info(f"  {name}: {path}")
        
        # Evaluate if requested
        if args.evaluate:
            metrics = evaluate_pipeline(model_paths)
            logger.info("Evaluation completed!")
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise


if __name__ == "__main__":
    main()