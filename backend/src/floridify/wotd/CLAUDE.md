# WOTD Module - Word of the Day

ML pipeline for personalized word-of-the-day selection.

## Components

**ML Pipeline** (`pipeline.py`):
- Semantic encoder (sentence transformer)
- DSL model (domain-specific language decoder)
- Semantic vocabulary IDs
- Training metadata

**Models Required**:
- `semantic_encoder.pt` - Embedding model
- `dsl_model/` - Decoder
- `semantic_ids.json` - Vocabulary mapping
- `training_metadata.json` - Training info

**Features**:
- Literature corpus analysis
- Semantic style/era/complexity encoding (4D: style/complexity/era/variation)
- Synthetic corpus generation for training
- Preference interpolation

**Integration**: Managed via `core/wotd_pipeline.py` with singleton pattern
