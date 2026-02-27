# wotd/

Word-of-the-Day ML pipeline.

```
wotd/
├── trainer.py (1,440)      # ML training pipeline
├── encoders.py (609)       # Semantic + metadata encoding
├── embeddings.py (600)     # SentenceTransformer management
├── core.py (259)           # WOTD core logic
├── generator.py (266)      # WordOfTheDayGenerator
├── inference.py (275)      # ML scoring
├── sagemaker.py (320)      # AWS SageMaker (optional)
├── storage.py, storage_minimal.py
├── constants.py (127)      # Training hyperparameters
└── deployment/             # Local + SageMaker deployment
```

Models: semantic_encoder.pt, dsl_model/, semantic_ids.json, training_metadata.json.

4D encoding: style, complexity, era, variation. Literature corpus analysis. Synthetic corpus generation. Preference interpolation. Managed via `core/wotd_pipeline.py` singleton.
