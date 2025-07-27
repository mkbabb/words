# Batch Processing Architecture

## System Overview

The batch processing system is designed to efficiently process the entire English language corpus (~55k base forms) using OpenAI's Batch API for 50% cost reduction.

## Key Components

### 1. Corpus Processing Pipeline
- **Input**: SOWPODS corpus (267,751 words)
- **Process**: NLTK WordNet lemmatization
- **Output**: ~55,000 base forms with inflection mappings
- **Reduction**: 79.5% through intelligent deduplication

### 2. Frequency Analysis System
- **Multi-source aggregation**: Google 10k, COCA, Wikipedia, Literary texts
- **Weighted scoring**: Configurable weights for each source
- **Integration**: Maps frequency rankings to base forms
- **Output**: Prioritized word lists (1k, 5k, 10k, 20k, 50k)

### 3. Batch Synthesis Engine
- **Batch API Integration**: 50% cost reduction via OpenAI Batch API
- **Checkpoint Recovery**: Resume from any interruption
- **Progress Monitoring**: Rich console UI with real-time metrics
- **Error Handling**: Tracks and logs failed words

## Cost Optimization

### Token Reduction (Achieved)
- **Prompt optimization**: 50-80% reduction across all prompts
- **Average tokens/word**: 20k → 12k (40% reduction)
- **Selective processing**: Only synthesize missing definitions

### API Cost Structure
- **GPT-4o Batch API**: $1.50/1M input, $5.00/1M output tokens
- **Total cost for 55k words**: ~$1,800 (vs $5,610 standard)
- **Processing time**: 3-5 days with batch API

### Alternative: GPT-4o-mini
- **Cost**: ~$90-120 for full corpus (95% cheaper)
- **Trade-off**: Lower quality definitions
- **Hybrid approach**: Use mini for secondary components

## Architecture Flow

```
1. Corpus Lemmatization
   SOWPODS (267k) → Lemmatizer → Base Forms (55k)
   
2. Frequency Analysis  
   Multiple Sources → Weighted Scoring → Priority Lists
   
3. Batch Processing
   Priority Words → Lookup Pipeline → Batch Synthesis → MongoDB
   
4. Progress Tracking
   Checkpoint File ← Progress Updates → Rich Console UI
```

## Implementation Details

### Checkpoint System
```json
{
  "processed_words": ["word1", "word2", ...],
  "failed_words": [{"word": "x", "error": "..."}],
  "metrics": {
    "words_successful": 1000,
    "words_failed": 5,
    "tokens_used": 12000000,
    "current_cost": 51.0
  },
  "last_position": 1005,
  "timestamp": "2025-01-27T12:00:00"
}
```

### Batch Processing Logic
1. Load words and check against existing entries
2. Group into batches (default: 50 words)
3. Process via `batch_synthesis` context manager
4. Collect futures and await batch completion
5. Update checkpoint every N words
6. Handle graceful shutdown

### Performance Metrics
- **Processing rate**: ~2-4 words/minute (with batch API)
- **Memory usage**: Minimal due to streaming design
- **Checkpoint interval**: Every 100 words
- **Batch size**: 50 words (configurable)

## Future Enhancements

1. **Distributed Processing**: Multiple workers with Redis queue
2. **Smart Prioritization**: ML-based importance scoring
3. **Incremental Updates**: Only process changed definitions
4. **Quality Validation**: Automated quality checks
5. **Cost Alerts**: Real-time cost threshold monitoring

## Usage Patterns

### Quick Test (1k words, ~$50)
```bash
python scripts/batch_synthesis_enhanced.py data/frequency_lists/frequency_list_1000.txt
```

### Production Run (10k words, ~$500)
```bash
python scripts/batch_synthesis_enhanced.py data/frequency_lists/frequency_list_10000.txt \
  --checkpoint production_checkpoint.json \
  --batch-size 100
```

### Full Corpus (55k words, ~$1,800)
```bash
python scripts/batch_synthesis_enhanced.py data/processed_corpus/base_forms.txt \
  --checkpoint full_corpus_checkpoint.json
```