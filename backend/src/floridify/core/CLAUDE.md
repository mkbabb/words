# Core Module - Pipeline Orchestration

Business logic pipelines for word lookup, search, WOTD, with real-time progress tracking via SSE streaming.

## Structure

```
core/
├── lookup_pipeline.py    # Word lookup: search→providers→AI→storage (504 LOC)
├── search_pipeline.py    # Multi-method search orchestration (254 LOC)
├── state_tracker.py      # Progress tracking, SSE event streaming (469 LOC)
├── streaming.py          # Server-Sent Events, chunked responses (453 LOC)
└── wotd_pipeline.py      # Word-of-the-Day ML pipeline (338 LOC)
```

**Total**: 2,026 LOC across 5 modules

## Key Pipelines

**Lookup Pipeline** (`lookup_pipeline.py:504`)

End-to-end word lookup with 5 stages:

```python
async def lookup_word_pipeline(word, providers, languages, semantic, no_ai, force_refresh):
    # 1. Search (10-100ms) - find best match via multi-method cascade
    match = await find_best_match(word)

    # 2. Cache check (0.2-5ms) - return if cached and not force_refresh
    cached = await get_synthesized_entry(match.word)

    # 3. Provider fetch (2-5s) - parallel requests to 3-5 providers
    provider_data = await asyncio.gather(*[
        _get_provider_definition(provider, match.word)
        for provider in providers
    ])

    # 4. AI synthesis (1-3s) - dedup→cluster→enhance
    if not no_ai:
        entry = await _synthesize_with_ai(provider_data, match.word)
    else:
        entry = await _create_provider_mapped_entry(provider_data)

    # 5. Storage (implicit) - MongoDB via Beanie, cache population
    return entry
```

**Key functions**:
- `lookup_word_pipeline:37-231` - Main orchestrator
- `_get_provider_definition:235-303` - Factory pattern for providers
- `_synthesize_with_ai:307-344` - Delegates to DefinitionSynthesizer
- `_create_provider_mapped_entry:349-458` - Non-AI fallback (dedup+cluster only)
- `_ai_fallback_lookup:462-504` - Pure AI generation when providers fail

**Search Pipeline** (`search_pipeline.py:254`)

Multi-method search with singleton pattern:

```python
async def search_word_pipeline(word, max_results, min_score, mode, semantic):
    # Singleton search engine
    search_engine = await get_search_engine()

    # Mode-based search: SMART (cascade) | EXACT | FUZZY | SEMANTIC
    results = await search_engine.search_with_mode(word, mode)

    return results  # list[SearchResult]
```

**Search modes**:
- `SMART` - Cascade: exact (<1ms) → fuzzy (10-50ms) → semantic (50-200ms)
- `EXACT` - marisa-trie only
- `FUZZY` - RapidFuzz only
- `SEMANTIC` - FAISS only

**Functions**:
- `search_word_pipeline:66-177` - Main search orchestrator
- `get_search_engine:25-54` - Singleton LanguageSearch loader
- `find_best_match:180-216` - Returns single best result
- `search_similar_words:219-254` - Semantic similarity search

## State Tracking

**StateTracker** (`state_tracker.py:469`)

Real-time pipeline progress with async event streaming:

```python
class StateTracker:
    _queue: asyncio.Queue[PipelineState]
    _subscribers: set[asyncio.Queue[PipelineState]]
    _progress_map: dict[str, int]  # stage → percentage

    async def update_stage(stage: str, progress: int | None):
        """Update stage, auto-calculate progress from map"""

    async def subscribe() -> AsyncGenerator[asyncio.Queue[PipelineState]]:
        """Subscribe to state updates via async context manager"""
```

**Lookup stages** (9 stages, 0→100%):
```
START(5%) → SEARCH_START(10%) → SEARCH_COMPLETE(20%)
→ PROVIDER_FETCH_START(25%) → PROVIDER_FETCH_COMPLETE(60%)
→ AI_CLUSTERING(70%) → AI_SYNTHESIS(85%)
→ STORAGE_SAVE(95%) → COMPLETE(100%)
```

**Key methods**:
- `update:349-392` - Core state update with subscriber notification
- `subscribe:434-442` - Async context manager for event subscriptions
- `get_current_state:458-460` - Snapshot of current progress

**PipelineState** (`state_tracker.py:282-320`)

```python
class PipelineState(BaseModel):
    stage: str                    # Current stage identifier
    progress: int                 # 0-100
    message: str                  # Human-readable status
    details: dict | None          # Debug info
    timestamp: datetime
    is_complete: bool
    error: str | None

    def model_dump_optimized():
        """70% payload reduction for SSE"""
```

## SSE Streaming

**StreamingResponse** (`streaming.py:453`)

Server-Sent Events for real-time progress:

```python
async def create_streaming_response(
    word: str,
    process_func: Callable,
    state_tracker: StateTracker,
):
    async def event_generator():
        # Monitor state updates
        async with state_tracker.subscribe() as queue:
            while True:
                state = await queue.get()
                yield SSEEvent("progress", state.model_dump_optimized())

        # Execute process
        result = await process_func(word)

        # Send chunked completion (>32KB split into chunks)
        if len(result) > 32768:
            await _send_chunked_completion(result)
        else:
            yield SSEEvent("complete", result)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Chunking** (`streaming.py:16-68`):
- Threshold: 32KB
- Events: `completion_start` → `completion_chunk` → `complete`
- Definitions sent in logical groups
- Examples batched in groups of 10

## WOTD Pipeline

**ML Pipeline Management** (`wotd_pipeline.py:338`)

```python
# Singleton pattern for model caching
def get_ml_pipeline() -> WOTDPipeline:
    """Load semantic encoder, DSL model, vocabulary"""

def check_wotd_models_status() -> dict:
    """Validate model files, training metadata"""

def get_pipeline_health() -> dict:
    """Health check with vocabulary size, corpus availability"""
```

**Required models**:
- `semantic_encoder.pt` - Sentence transformer
- `dsl_model/` - Domain-specific language decoder
- `semantic_ids.json` - Vocabulary mapping
- `training_metadata.json` - Training info

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Lookup (cached) | <500ms | L1/L2 cache hit |
| Lookup (uncached) | 3-8s | Provider fetch (2-5s) + AI synthesis (1-3s) |
| Search exact | <1ms | marisa-trie O(m) |
| Search fuzzy | 10-50ms | RapidFuzz with signature buckets |
| Search semantic | 50-200ms | FAISS HNSW + embeddings |
| State update | <1ms | Queue put + subscriber notification |
| SSE streaming | <1ms/event | Event formatting overhead |

## Design Patterns

- **Pipeline Orchestration** - Hierarchical: lookup → search, providers, synthesis
- **Singleton** - Search engine, WOTD ML pipeline (lazy init)
- **Factory** - Provider connector creation
- **Subscriber** - StateTracker multi-listener distribution
- **Async Context Manager** - StateTracker.subscribe()
- **Decorator** - @log_timing, @log_stage
- **Strategy** - Pluggable search modes
