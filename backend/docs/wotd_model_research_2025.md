# WOTD ML Model Research - August 2025

## Executive Summary

Comprehensive research on state-of-the-art models for Word of the Day (WOTD) semantic preference learning as of August 2025.

## Current System Issues

1. **Outdated Models**: Using GPT-2 (2019) and BERT (2018) 
2. **Poor Training Data**: Dummy/simple word lists
3. **Suboptimal Architecture**: Basic vector quantization
4. **Limited Deployment**: RunPod over AWS

## Latest Model Landscape - August 2025

### Language Models (Replacing GPT-2)

**Tier 1 - Production Ready**
- **Microsoft Phi-3.5-mini (3.8B)**: Excellent instruction following, efficient, commercial friendly
- **Meta Llama 3.1-8B-Instruct**: Strong reasoning, multilingual, good for fine-tuning  
- **Google Gemma-2-9B-it**: Efficient, safety-aligned, good performance
- **Mistral-Nemo-12B-Instruct**: Multilingual, Apache 2.0 license

**Tier 2 - High Performance**  
- **Meta Llama 3.1-70B-Instruct**: State-of-the-art reasoning for open models
- **Qwen2.5-32B-Instruct**: Excellent coding and reasoning
- **DeepSeek-V2.5**: Strong performance, mixture-of-experts

**Tier 3 - Cutting Edge**
- **OpenAI GPT-4o/o1**: Best commercial performance (API only)
- **Anthropic Claude 3.5 Sonnet**: Excellent reasoning and safety
- **Meta Llama 3.1-405B**: Largest open model, research compute intensive

### Embedding Models (Replacing BERT)

**Production Tier**
- **OpenAI text-embedding-3-large**: 3072-dim, state-of-the-art retrieval
- **OpenAI text-embedding-3-small**: 1536-dim, efficient, cost-effective
- **Cohere embed-english-v3.0**: Optimized for English, good performance

**Open Source Tier**
- **BAAI/bge-large-en-v1.5**: 1024-dim, excellent open-source option
- **sentence-transformers/all-mpnet-base-v2**: 768-dim, widely adopted
- **intfloat/e5-large-v2**: 1024-dim, multilingual capabilities
- **Voyage AI voyage-large-2**: 1536-dim, strong retrieval performance

### Semantic Encoding Architecture

**Modern Approaches**
1. **Vector Quantized VAEs (VQ-VAE2)**: Better than basic VQ, hierarchical
2. **Residual Vector Quantization (RVQ)**: State-of-the-art discrete representations  
3. **Finite Scalar Quantization (FSQ)**: Simpler, more robust than VQ
4. **Neural Codecs**: From audio processing, applicable to embeddings

## Recommended Architecture - 2025

### 1. Embedding Pipeline
```
Words → OpenAI text-embedding-3-large → 3072-dim vectors → L2 normalize
```

### 2. Semantic Encoder  
```
Embeddings → Residual Vector Quantizer → 4-level hierarchical codes
- Level 0: Style (32 codes)
- Level 1: Complexity (32 codes) 
- Level 2: Era (32 codes)
- Level 3: Variation (64 codes)
```

### 3. Language Model
```
Base: Microsoft Phi-3.5-mini-instruct (3.8B)
Training: LoRA fine-tuning on synthetic DSL corpus
Context: 4K tokens, optimized for instruction following
```

### 4. Deployment
```
Platform: AWS SageMaker JumpStart
Container: Custom Docker with PyTorch 2.4+
Infrastructure: ml.g5.xlarge (A10G GPU, 24GB RAM)
Scaling: SageMaker Multi-Model Endpoints
```

## Training Data Strategy

### Synthetic Corpus Generation
- **Generator**: OpenAI GPT-4o via API
- **Structure**: 12 corpora × 100 words = 1,200 high-quality training words
- **Categories**: All combinations of Style × Complexity × Era
- **Quality**: Etymological accuracy, semantic consistency, educational value

### Augmentation Techniques
1. **Paraphrase Generation**: Varied definitions for robustness
2. **Context Expansion**: Multiple example sentences per word
3. **Difficulty Calibration**: CEFR-aligned complexity assessment  
4. **Semantic Validation**: Cross-referenced with educational word lists

## Production Deployment - AWS SageMaker

### Model Registry
- **Semantic Encoder**: Custom PyTorch model with RVQ
- **Language Model**: HuggingFace Transformers with LoRA adapters
- **Embeddings**: OpenAI API integration with caching

### Infrastructure
- **Training**: ml.g5.2xlarge (A10G × 2, distributed training)
- **Inference**: ml.g5.xlarge (A10G × 1, real-time endpoints)  
- **Storage**: S3 for models, EFS for training data
- **Monitoring**: CloudWatch, SageMaker Model Monitor

### Cost Optimization
- **Spot Training**: 60-70% cost reduction for training jobs
- **Multi-Model Endpoints**: Shared infrastructure for multiple model versions
- **Auto-scaling**: Scale to zero during low usage
- **Caching**: Redis cluster for embedding and generation caching

## Performance Expectations

### Training Metrics
- **Semantic Encoder**: <0.01 reconstruction loss, >95% codebook utilization
- **Language Model**: <1.5 perplexity on DSL tasks, >90% format adherence
- **End-to-End**: <500ms generation latency, >0.85 semantic consistency

### Quality Metrics  
- **Corpus Coherence**: >0.8 intra-corpus similarity
- **Cross-Corpus Distinction**: >0.3 inter-corpus distance
- **Educational Value**: >0.9 human evaluation score
- **Linguistic Accuracy**: >95% etymological correctness

## Implementation Timeline

**Phase 1 (Week 1)**
- Synthetic corpus generation with GPT-4o
- Modern embedding pipeline with text-embedding-3-large
- Residual vector quantization implementation

**Phase 2 (Week 2)**  
- Phi-3.5-mini fine-tuning with LoRA
- AWS SageMaker containerization
- Training pipeline automation

**Phase 3 (Week 3)**
- Production deployment and testing
- Performance optimization and monitoring
- API integration and documentation

## Risk Mitigation

**Model Risks**
- **Embedding Dependency**: Fallback to sentence-transformers if OpenAI unavailable
- **LLM Performance**: Multiple model size options (3.8B → 8B → 70B)
- **Training Instability**: Gradient clipping, learning rate scheduling

**Infrastructure Risks**
- **AWS Costs**: Spot instances, auto-scaling, cost alerts
- **Latency**: Edge caching, model optimization, batching
- **Availability**: Multi-AZ deployment, health checks, fallback models

This architecture represents a 2025-era approach that is both cutting-edge and production-ready, with significant improvements over the 2019-era GPT-2/BERT baseline.