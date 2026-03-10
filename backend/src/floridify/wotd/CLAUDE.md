# wotd/

Word-of-the-Day ML pipeline.

```
wotd/
├── __init__.py
├── constants.py            # Training hyperparameters
├── core.py                 # Style/Complexity/Era/Author enums, WOTDWord, TrainingConfig
├── embeddings.py           # SentenceTransformer management
├── encoders.py             # FSQEncoder, HierarchicalVQEncoder, UnifiedSemanticEncoder
├── generator.py            # SyntheticGenerator—training data generation
├── inference.py            # ML scoring
├── sagemaker.py            # AWS SageMaker integration (optional)
├── storage.py              # WOTD storage layer
├── storage_minimal.py      # Minimal storage fallback
├── training/
│   ├── __init__.py
│   ├── dsl_trainer.py      # DSLTrainer
│   ├── embedder.py         # WOTDEmbedder
│   └── pipeline.py         # WOTDTrainer, train_wotd_pipeline(), train_from_literature()
└── deployment/
    ├── inference.py         # Inference server
    ├── local.py             # Local deployment
    └── train.py             # Training script
```

4D encoding: style, complexity, era, variation. Literature corpus analysis. Synthetic corpus generation. Preference interpolation. Managed via `core/wotd_pipeline.py` singleton.
