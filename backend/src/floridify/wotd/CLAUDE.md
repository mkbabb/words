# wotd/

Word-of-the-Day ML pipeline.

```
wotd/
├── trainer.py (1,440)      # ML training pipeline
├── encoders.py (609)       # Semantic + metadata encoding
├── embeddings.py (600)     # SentenceTransformer management
├── generator.py (266)      # WordOfTheDayGenerator
├── inference.py (275)      # ML scoring
├── core.py (259)           # WOTD core logic
├── sagemaker.py (320)      # AWS SageMaker (optional)
├── constants.py (127)      # Training hyperparameters
├── storage.py (104)        # WOTD storage layer
├── storage_minimal.py (67) # Minimal storage fallback
└── deployment/
    ├── local.py             # Local deployment
    ├── inference.py          # Inference server
    ├── train.py              # Training script
    ├── Dockerfile.inference   # Inference container
    ├── Dockerfile.training    # Training container
    └── nginx.conf             # Inference proxy config
```

4D encoding: style, complexity, era, variation. Literature corpus analysis. Synthetic corpus generation. Preference interpolation. Managed via `core/wotd_pipeline.py` singleton.
