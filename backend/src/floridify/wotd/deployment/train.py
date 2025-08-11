#!/usr/bin/env python3
"""SageMaker training script for WOTD ML pipeline."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add code directory to Python path
sys.path.append('/opt/ml/code')

from wotd.core import TrainingConfig
from wotd.trainer import train_wotd_pipeline


def parse_args() -> argparse.Namespace:
    """Parse SageMaker training arguments."""
    parser = argparse.ArgumentParser(description="Train WOTD ML pipeline on SageMaker")
    
    # SageMaker directories
    parser.add_argument(
        '--model-dir', 
        type=str, 
        default=os.environ.get('SM_MODEL_DIR', '/opt/ml/model'),
        help='Model output directory'
    )
    parser.add_argument(
        '--train-dir', 
        type=str, 
        default=os.environ.get('SM_CHANNEL_TRAIN', '/opt/ml/input/data/train'),
        help='Training data directory'
    )
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default=os.environ.get('SM_OUTPUT_DIR', '/opt/ml/output'),
        help='Output data directory'
    )
    
    # Training hyperparameters
    parser.add_argument('--words-per-corpus', type=int, default=100)
    parser.add_argument('--num-corpora', type=int, default=12)
    parser.add_argument('--encoder-epochs', type=int, default=200)
    parser.add_argument('--encoder-lr', type=float, default=1e-3)
    parser.add_argument('--lm-epochs', type=int, default=10)
    parser.add_argument('--lm-lr', type=float, default=2e-5)
    
    # Model configuration
    parser.add_argument('--base-model', type=str, default='microsoft/Phi-3.5-mini-instruct')
    parser.add_argument('--embedding-model', type=str, default='BAAI/bge-m3')
    
    return parser.parse_args()


async def main() -> None:
    """Main training function for SageMaker."""
    args = parse_args()
    
    print(f"🚀 Starting SageMaker WOTD training")
    print(f"Model directory: {args.model_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Training configuration:")
    print(f"  Words per corpus: {args.words_per_corpus}")
    print(f"  Encoder epochs: {args.encoder_epochs}")
    print(f"  LM epochs: {args.lm_epochs}")
    print(f"  Base model: {args.base_model}")
    print(f"  Embedding model: {args.embedding_model}")
    
    # Create training configuration
    config = TrainingConfig(
        words_per_corpus=args.words_per_corpus,
        num_corpora=args.num_corpora,
        encoder_epochs=args.encoder_epochs,
        encoder_lr=args.encoder_lr,
        lm_epochs=args.lm_epochs,
        lm_lr=args.lm_lr,
        base_model=args.base_model,
        embedding_model=args.embedding_model
    )
    
    try:
        # Train pipeline
        results = await train_wotd_pipeline(config, args.model_dir)
        
        # Save training results for SageMaker
        results_data = {
            "training_time": results.duration_seconds,
            "num_corpora": results.num_corpora,
            "total_words": results.total_words,
            "model_paths": results.model_paths,
            "status": "completed"
        }
        
        # Write results to output directory  
        output_path = Path(args.output_dir) / "training_results.json"
        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"✅ Training completed successfully in {results.duration_seconds:.2f}s")
        print(f"📊 Results: {results.num_corpora} corpora, {results.total_words} words")
        print(f"💾 Models saved to: {args.model_dir}")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        
        # Write failure info
        failure_path = Path(args.output_dir) / "training_results.json"
        with open(failure_path, 'w') as f:
            json.dump({"status": "failed", "error": str(e)}, f)
        
        raise


if __name__ == '__main__':
    asyncio.run(main())