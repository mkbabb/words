# Graph RAG Implementation Roadmap
*Technical Execution Plan*

## Week 1: Foundation

### Day 1-2: Dependencies & Core Graph
```bash
# Update backend/pyproject.toml
uv add rustworkx==0.14.2
uv add faiss-cpu==1.8.0  # Start with CPU, GPU later
```

**Files to create:**
- `backend/src/floridify/graph/__init__.py`
- `backend/src/floridify/graph/core.py` - LiteratureGraph class
- `backend/src/floridify/graph/models.py` - Graph data models

**Key implementation:**
```python
# backend/src/floridify/graph/core.py
class LiteratureGraph:
    def __init__(self):
        self.graph = rx.PyDiGraph()
        self.node_map = {}
        self.embedding_cache = {}
```

### Day 3-4: Personalized PageRank
**Files to modify:**
- `backend/src/floridify/search/graph_rag.py` - New PPR implementation
- `backend/src/floridify/search/core.py` - Add graph search path

**Critical function:**
```python
async def personalized_pagerank(
    graph: rx.PyDiGraph,
    seed_nodes: list[int],
    alpha: float = 0.85
) -> dict[int, float]:
    return rx.pagerank(graph, personalized=seed_nodes, alpha=alpha)
```

### Day 5: MongoDB Models
**Files to modify:**
- `backend/src/floridify/models/__init__.py` - Export new models
- `backend/src/floridify/models/graph_models.py` - Beanie documents

```python
class LiteratureWork(Document):
    title: str
    embeddings: bytes  # Compressed
    citations: list[str]
```

## Week 2: Integration

### Day 6-7: Search Pipeline Enhancement
**Files to modify:**
- `backend/src/floridify/search/core.py`
- `backend/src/floridify/core/search_pipeline.py`

**Add parameter:**
```python
async def search(
    self,
    query: str,
    *,
    literature_context: Optional[list[str]] = None  # NEW
) -> list[SearchResult]:
```

### Day 8-9: Fusion Algorithm
**Files to create:**
- `backend/src/floridify/search/fusion.py`

```python
def reciprocal_rank_fusion(
    result_lists: list[list[SearchResult]],
    k: int = 60
) -> list[SearchResult]:
    """Combine multiple ranked lists."""
```

### Day 10: Caching Layer
**Files to modify:**
- `backend/src/floridify/caching/unified.py`
- `backend/src/floridify/api/core/cache.py`

**Add graph-specific caching:**
```python
@cache_key_builder
def graph_cache_key(query: str, context: list[str]) -> str:
    return f"graph:{hash(query)}:{hash(tuple(context))}"
```

## Week 3: API & Testing

### Day 11-12: API Endpoints
**Files to create:**
- `backend/src/floridify/api/routers/literature.py`

**New endpoints:**
```python
@router.post("/literature/suggest")
@router.post("/literature/add-work")  
@router.get("/literature/graph-stats")
```

### Day 13: Incremental Updates
**Files to create:**
- `backend/src/floridify/graph/updater.py`

```python
class IncrementalUpdater:
    async def add_nodes(self, nodes: list[Node]):
        # Add without full rebuild
    
    async def update_edges(self, edges: list[Edge]):
        # Incremental edge updates
```

### Day 14-15: Testing
**Files to create:**
- `backend/tests/test_graph_rag.py`
- `backend/tests/test_literature_api.py`

**Test cases:**
```python
async def test_ppr_performance():
    # Assert < 50ms for 10K nodes

async def test_incremental_update():
    # Assert no full graph rebuild

async def test_fusion_accuracy():
    # Assert improved recall
```

## Week 4: Optimization

### Day 16-17: GPU Acceleration (Optional)
```bash
uv add faiss-gpu  # If CUDA available
```

**Conditional imports:**
```python
try:
    import faiss.gpu
    USE_GPU = True
except ImportError:
    USE_GPU = False
```

### Day 18: Compression
**Files to modify:**
- `backend/src/floridify/search/models.py` - Already has compression utils

```python
def compress_embeddings(embeddings: np.ndarray) -> bytes:
    # Product quantization
    pq = faiss.ProductQuantizer(d, M=8, nbits=8)
    return pq.compute_codes(embeddings)
```

### Day 19: Monitoring
**Files to create:**
- `backend/src/floridify/graph/metrics.py`

```python
class GraphMetrics:
    traversal_time_p99: float
    cache_hit_rate: float
    graph_size_mb: float
```

### Day 20: Documentation
**Files to update:**
- `backend/CLAUDE.md` - Add graph RAG section
- `docs/api.md` - Document new endpoints

## Milestones & Validation

### Milestone 1 (End of Week 1)
- [ ] Graph structure operational
- [ ] PPR algorithm working
- [ ] MongoDB models defined
- **Validation**: Unit tests pass for graph operations

### Milestone 2 (End of Week 2)  
- [ ] Search pipeline integrated
- [ ] Fusion algorithm implemented
- [ ] Caching operational
- **Validation**: E2E search with literature context

### Milestone 3 (End of Week 3)
- [ ] API endpoints live
- [ ] Incremental updates working
- [ ] Test coverage >80%
- **Validation**: API integration tests pass

### Milestone 4 (End of Week 4)
- [ ] Performance optimized
- [ ] Monitoring deployed
- [ ] Documentation complete
- **Validation**: <100ms P99 latency

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| rustworkx compatibility | Test in isolated env first |
| Memory usage spike | Implement pagination |
| PPR convergence slow | Pre-compute for common seeds |
| FAISS GPU issues | Fallback to CPU |

## Success Metrics

- **Latency**: P99 < 100ms for graph queries
- **Accuracy**: 20% improvement in multi-hop questions
- **Cost**: <$0.01 per 1000 queries
- **Memory**: <100MB per user graph
- **Uptime**: 99.9% availability

## Rollback Plan

If issues arise:
1. Feature flag: `ENABLE_GRAPH_RAG=false`
2. Fallback to existing cascade search
3. Graph operations async/background only
4. Maintain existing API contracts

## Go/No-Go Criteria

**Week 1 Go/No-Go:**
- Graph operations < 50ms
- Memory usage acceptable

**Week 2 Go/No-Go:**
- Integration doesn't break existing search
- Fusion improves accuracy

**Week 3 Go/No-Go:**
- API response times maintained
- Tests comprehensive

**Week 4 Go/No-Go:**
- Performance targets met
- Documentation complete

## Command Summary

```bash
# Week 1
uv add rustworkx faiss-cpu
pytest tests/test_graph_rag.py

# Week 2  
pytest tests/test_search.py
curl localhost:8000/search?context=hamlet

# Week 3
pytest tests/
uvicorn floridify.api.main:app --reload

# Week 4
python -m floridify.graph.metrics
mkdocs build
```