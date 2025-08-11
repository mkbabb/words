# WOTD Model Research Query - January 2025

**Research Task**: Identify the optimal models for a Word of the Day ML system that learns semantic preferences and generates educational vocabulary using hierarchical semantic embeddings.

## Key Research Questions

1. **Best Embedding Model (replacing BAAI/bge-m3)**:
   - Latest multilingual embedding models with >1024 dimensions
   - Performance on semantic similarity and educational vocabulary tasks
   - Open-source models competitive with OpenAI text-embedding-3-large
   - Consider: Alibaba GTE, Salesforce SFR, Microsoft E5, Cohere v3.1

2. **Best Base Language Model (replacing microsoft/Phi-3.5-mini-instruct)**:
   - 3-8B parameter models optimized for instruction following
   - Strong performance on educational content generation
   - LoRA-friendly architecture for efficient fine-tuning
   - Consider: Qwen2.5, Mistral-Nemo, Llama 3.2/3.3, Phi-4

3. **Modern Semantic Encoding Architecture**:
   - Latest developments in vector quantization beyond RVQ
   - Hierarchical discrete representation learning 
   - Consider: FSQ, Neural Codecs, Matryoshka embeddings

## Current System Context

- **Goal**: Learn 4-level semantic hierarchy [Style, Complexity, Era, Variation] from word corpora
- **Training**: 12 synthetic corpora × 100 words using GPT-4o generation
- **Deployment**: AWS SageMaker with production requirements
- **Performance**: <500ms inference, >90% semantic consistency

## Search Constraints

- **Date**: January 2025+ papers/models only
- **License**: Commercial-friendly (Apache 2.0, MIT preferred)
- **Size**: Models deployable on single A10G/A100 GPU
- **Quality**: MTEB benchmark scores, educational domain performance

**Output**: Ranked recommendations with benchmarks, deployment considerations, and migration path from current BGE-M3 + Phi-3.5 setup.