# Semantic Search Memory Usage Guide

## Quick Reference: Memory Requirements by Corpus Size

### BGE-M3 Model (1024D embeddings)
| Corpus Size | Baseline (FP32) | Strategy | Actual Memory | Compression | Quality Loss |
|------------|-----------------|----------|---------------|-------------|--------------|
| 10k words | 40 MB | Exact | 40 MB | 100% | 0% |
| 25k words | 100 MB | FP16 | 50 MB | 50% | <0.5% |
| 50k words | 200 MB | INT8 | 50 MB | 25% | ~1-2% |
| 100k words | 400 MB | IVF-PQ | 40 MB | 10% | ~5-10% |
| 250k words | 1 GB | IVF-PQ | 100 MB | 10% | ~5-10% |
| 500k words | 2 GB | OPQ+PQ | 60 MB | 3% | ~10-15% |
| 1M words | 4 GB | OPQ+PQ | 120 MB | 3% | ~10-15% |

### MiniLM Model (384D embeddings)
| Corpus Size | Baseline (FP32) | Strategy | Actual Memory | Compression | Quality Loss |
|------------|-----------------|----------|---------------|-------------|--------------|
| 10k words | 15 MB | Exact | 15 MB | 100% | 0% |
| 25k words | 38 MB | FP16 | 19 MB | 50% | <0.5% |
| 50k words | 75 MB | INT8 | 19 MB | 25% | ~1-2% |
| 100k words | 150 MB | IVF-PQ | 15 MB | 10% | ~5-10% |
| 250k words | 375 MB | IVF-PQ | 38 MB | 10% | ~5-10% |
| 500k words | 750 MB | OPQ+PQ | 23 MB | 3% | ~10-15% |
| 1M words | 1.5 GB | OPQ+PQ | 45 MB | 3% | ~10-15% |

## Quantization Strategies Explained

### 1. **Exact Search (IndexFlatL2)**
- **When**: <10k vectors
- **Memory**: 100% of baseline (no compression)
- **Quality**: Perfect (0% loss)
- **Use case**: Small specialized dictionaries, high precision needed

### 2. **FP16 Scalar Quantization**
- **When**: 10k-25k vectors
- **Memory**: 50% of baseline (2x compression)
- **Quality**: Near-perfect (<0.5% loss)
- **Use case**: Medium dictionaries, good balance

### 3. **INT8 Scalar Quantization**
- **When**: 25k-50k vectors
- **Memory**: 25% of baseline (4x compression)
- **Quality**: Excellent (~1-2% loss)
- **Use case**: Large dictionaries, memory-conscious

### 4. **IVF-PQ (Inverted File + Product Quantization)**
- **When**: 50k-250k vectors
- **Memory**: ~10% of baseline (10x compression)
- **Quality**: Good (~5-10% loss)
- **Use case**: Very large dictionaries, production systems

### 5. **OPQ+IVF-PQ (Optimized Product Quantization)**
- **When**: >250k vectors
- **Memory**: ~3% of baseline (33x compression)
- **Quality**: Acceptable (~10-15% loss)
- **Use case**: Massive multilingual corpora, extreme scale

## Real-World Examples

### English Dictionary (100k words)
- **BGE-M3**: 400MB → 40MB with IVF-PQ
- **MiniLM**: 150MB → 15MB with IVF-PQ
- **Savings**: 90% memory reduction, <10% quality loss

### Multilingual Corpus (500k words)
- **BGE-M3**: 2GB → 60MB with OPQ+PQ
- **MiniLM**: 750MB → 23MB with OPQ+PQ
- **Savings**: 97% memory reduction, ~15% quality loss

### Enterprise Scale (1M+ words)
- **BGE-M3**: 4GB → 120MB with OPQ+PQ
- **MiniLM**: 1.5GB → 45MB with OPQ+PQ
- **Savings**: 97% memory reduction, acceptable for most use cases

## Recommendations

1. **Development**: Use exact search for <10k for perfect recall
2. **Production**: Use INT8 for <50k for best quality/memory balance
3. **Scale**: Use IVF-PQ for 50k-250k for good compromise
4. **Extreme Scale**: Use OPQ+PQ for >250k when memory is critical

## Model Selection Guide

### Choose BGE-M3 when:
- Multilingual support needed
- Cross-lingual search required
- Quality is paramount
- Memory budget allows 2.7x overhead vs MiniLM

### Choose MiniLM when:
- English-only corpus
- Speed is critical (2.7x faster)
- Memory constrained environment
- Acceptable quality for monolingual search