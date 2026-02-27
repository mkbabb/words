# core/

Business logic pipelines. Lookup orchestration, search management, SSE streaming, progress tracking.

```
core/
├── lookup_pipeline.py (504)    # 5-stage lookup orchestration
├── search_pipeline.py (507)    # SearchEngineManager + cascade
├── state_tracker.py (480)      # Real-time progress, multi-subscriber
├── streaming.py (284)          # SSE: chunked responses, heartbeat
└── wotd_pipeline.py (338)      # Word-of-the-Day ML orchestration
```

## Lookup Pipeline

5 stages: Search (10-100ms) → Cache check (0.2-5ms) → Provider fetch (2-5s, `asyncio.gather`) → AI synthesis (1-3s) → Store.

Key: searches first to normalize the word form, then uses best match for provider fetch. `_create_provider_mapped_entry()` for no_ai mode (dedup+cluster only). `_ai_fallback_lookup()` when all providers fail.

## Search Pipeline

**SearchEngineManager**: singleton with hot-reload. Polls `vocabulary_hash` every 30s. On change: lock → double-check → rebuild indices → atomic swap. Old engine serves until swap.

Modes: SMART (cascade with early termination), EXACT, FUZZY, SEMANTIC.

## State Tracker

9 stages (0→100%): START → SEARCH_START → SEARCH_COMPLETE → PROVIDER_FETCH_START → PROVIDER_FETCH_COMPLETE → AI_CLUSTERING → AI_SYNTHESIS → STORAGE_SAVE → COMPLETE.

Multi-subscriber via `asyncio.Queue` per listener. `model_dump_optimized()`: 70% smaller SSE payload.

## SSE Streaming

Heartbeat pings every 30s. Client disconnect cancels background task. 5-minute timeout. Responses >32KB split into chunks. Events: `config`, `progress`, `complete`, `error`.
