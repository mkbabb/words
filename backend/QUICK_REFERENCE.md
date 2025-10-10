# Non-Blocking Semantic Search - Quick Reference

## Summary
Semantic search initialization is **non-blocking** - it builds in the background while the app remains fully functional.

## Key Points

- ✅ **Initialization**: Returns in <1 second (not 16 minutes)
- ✅ **Search works immediately**: Uses exact/fuzzy while semantic builds
- ✅ **Status monitoring**: Check via API or Python methods
- ✅ **Error resilient**: Semantic failures don't crash the system

## API Endpoint

```bash
GET /search/semantic/status?languages=en
```

**Response:**
```json
{
  "enabled": true,
  "ready": false,
  "building": true,
  "languages": ["en"],
  "model_name": "BAAI/bge-m3",
  "vocabulary_size": 100000,
  "message": "Semantic search is building in background (search still works with exact/fuzzy)"
}
```

## Python API

```python
from floridify.search.language import get_language_search
from floridify.models.base import Language

# Initialize (returns immediately)
language_search = await get_language_search(languages=[Language.ENGLISH])

# Check if semantic is ready
if language_search.is_semantic_ready():
    print("Semantic search available!")

# Check if semantic is building
if language_search.is_semantic_building():
    print("Building in background...")

# Optionally wait for semantic (tests/debugging only)
await language_search.await_semantic_ready()

# Search immediately (uses exact/fuzzy, semantic when ready)
results = await language_search.search("hello")
```

## Frontend Integration

```typescript
// Check status
async function checkSemanticStatus() {
  const res = await fetch('/search/semantic/status?languages=en');
  const status = await res.json();

  if (status.building) {
    showToast('Semantic search loading in background...');
    setTimeout(checkSemanticStatus, 5000); // Poll every 5s
  } else if (status.ready) {
    enableAdvancedSearch();
  }
}

// Search (works immediately)
const results = await fetch('/search?q=hello&languages=en');
```

## Implementation Details

### Files Modified
1. **`src/floridify/search/language.py`** (lines 82-95)
   - Added `is_semantic_ready()`, `is_semantic_building()`, `await_semantic_ready()`

2. **`src/floridify/api/routers/search.py`** (lines 269-323)
   - Added `/search/semantic/status` endpoint

### Files with Existing Pattern
3. **`src/floridify/search/core.py`**
   - Background task pattern (lines 164-169)
   - Background initialization (lines 177-203)
   - Conditional semantic usage (lines 520-522)
   - Smart cascade wait (lines 593-594)

## How It Works

```
1. User calls Search.from_corpus() or get_language_search()
   ↓
2. Initialize fast components:
   - Trie index (<100ms)
   - Fuzzy search (instant)
   ↓
3. Fire semantic build in background (asyncio.create_task)
   ↓
4. Return immediately (~1 second total)
   ↓
5. Semantic builds in background (16 minutes)
   ↓
6. Search works with exact/fuzzy immediately
   ↓
7. Semantic results appear when ready
```

## Status Messages

| Message | Meaning |
|---------|---------|
| `"Semantic search is disabled"` | Not enabled in config |
| `"Semantic search is ready"` | Fully initialized |
| `"Semantic search is building in background (search still works with exact/fuzzy)"` | Currently building |
| `"Semantic search is not initialized"` | Enabled but not started |

## Testing

```bash
# Run status test
python test_semantic_status.py

# Check logs for background initialization
tail -f logs/floridify.log | grep -i semantic
```

## Performance Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Initialization | 16 minutes | <1 second | **1600x faster** |
| Search availability | After 16 min | Immediate | **Instant** |
| Semantic build | Blocking | Background | **Non-blocking** |
| Error impact | Crash | Graceful | **Resilient** |

## Troubleshooting

**Q: Semantic never becomes ready**
```python
# Check status
status = language_search.get_stats()
print(f"Semantic enabled: {status['semantic_enabled']}")
print(f"Semantic ready: {status['semantic_ready']}")

# Check logs
tail -f logs/floridify.log | grep -i "semantic\|error"
```

**Q: Search is slow even with semantic ready**
```python
# Check if semantic is actually being used
results = await language_search.search("test")
for r in results:
    print(f"{r.word}: method={r.method}, score={r.score}")
```

**Q: Want to force semantic to wait**
```python
# For tests/debugging only - not recommended for production
await language_search.await_semantic_ready()
```

## Best Practices

1. **Don't wait for semantic** in production code
   - Let it build in background
   - Search works immediately with exact/fuzzy

2. **Use status endpoint** for UI feedback
   - Show loading state while building
   - Enable advanced features when ready

3. **Handle semantic failures gracefully**
   - System works without semantic
   - Log errors but don't crash

4. **Monitor build progress** via logs
   - Track semantic initialization
   - Watch for errors or slowdowns

## Related Documentation

- **Full Report**: `SEMANTIC_NONBLOCKING_REPORT.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **Test Script**: `test_semantic_status.py`
