# Caching Refactoring Implementation Plan - KISS & Functional
**Execution Time**: 18 hours (3 days)  
**Risk**: LOW (surgical changes with test validation)  
**Philosophy**: Pure functions first, test at every step

---

## Phase 1: Foundation (4 hours) - KISS Quick Wins

### 1.1 Create keys.py - Pure Functions (1 hour)

```bash
# Create new file
touch backend/src/floridify/caching/keys.py
```

```python
# backend/src/floridify/caching/keys.py
"""Pure cache key generation functions - zero dependencies."""

import hashlib
from enum import Enum
from typing import Any

def generate_resource_key(resource_type, resource_id, *qualifiers) -> str:
    """Pure function for versioned resources."""
    parts = [
        p.value if isinstance(p, Enum) else str(p)
        for p in (resource_type, resource_id, *qualifiers)
    ]
    return hashlib.sha256(":".join(parts).encode()).hexdigest()

def generate_http_key(method: str, path: str, params: dict | None) -> str:
    """Pure function for HTTP endpoints."""
    parts = ["api", method, path]
    if params:
        parts.append(str(sorted(params.items())))
    return hashlib.sha256(":".join(parts).encode()).hexdigest()
```

**Update imports**:
```python
# manager.py - REMOVE lines 33-63, ADD:
from .keys import generate_resource_key as _generate_cache_key

# decorators.py - REMOVE lines 80-82, ADD:
from .keys import generate_resource_key

# core.py - REMOVE lines 532,593 nested imports, ADD at top:
from .keys import generate_resource_key
```

**Test**: `pytest tests/caching/ -k cache_key -v`

---

### 1.2 Delete Dead Code (15 minutes)

```bash
# Verify no usages
rg "cached_endpoint|ResponseCache|CacheInvalidator" backend/src --type py

# Delete lines 64-268 in api/core/cache.py
# Keep only: imports, APICacheConfig, generate_cache_key()
```

**Test**: `pytest tests/api/ -v`

---

### 1.3 Create config.py - Data Over Code (2 hours)

```python
# backend/src/floridify/caching/config.py
"""Centralized configuration - immutable data structures."""

from dataclasses import dataclass
from datetime import timedelta
from .models import CacheNamespace, CompressionType, ResourceType

@dataclass(frozen=True)
class NamespaceCacheConfig:
    namespace: CacheNamespace
    memory_limit: int
    memory_ttl: timedelta
    disk_ttl: timedelta | None
    compression: CompressionType | None = None

# All 13 namespaces
DEFAULT_CONFIGS = {
    CacheNamespace.DEFAULT: NamespaceCacheConfig(
        CacheNamespace.DEFAULT, 100, timedelta(hours=1), timedelta(days=1)
    ),
    CacheNamespace.CORPUS: NamespaceCacheConfig(
        CacheNamespace.CORPUS, 100, timedelta(days=30), timedelta(days=90), CompressionType.ZSTD
    ),
    CacheNamespace.SEMANTIC: NamespaceCacheConfig(
        CacheNamespace.SEMANTIC, 50, timedelta(days=7), timedelta(days=30), CompressionType.ZSTD
    ),
    # ... all 13
}

# Complete mappings (no partial coverage!)
NAMESPACE_MAP = {
    "semantic": CacheNamespace.SEMANTIC,
    "corpus": CacheNamespace.CORPUS,
    "search": CacheNamespace.SEARCH,
    "dictionary": CacheNamespace.DICTIONARY,
    "literature": CacheNamespace.LITERATURE,
    "language": CacheNamespace.LANGUAGE,
    "lexicon": CacheNamespace.LEXICON,
    "api": CacheNamespace.API,
    "scraping": CacheNamespace.SCRAPING,
    "openai": CacheNamespace.OPENAI,
    "trie": CacheNamespace.TRIE,
    "wotd": CacheNamespace.WOTD,
    "default": CacheNamespace.DEFAULT,
    "compute": CacheNamespace.SEARCH,  # Legacy alias
}

RESOURCE_TYPE_MAP = {
    ResourceType.CORPUS: CacheNamespace.CORPUS,
    ResourceType.SEMANTIC: CacheNamespace.SEMANTIC,
    ResourceType.TRIE: CacheNamespace.TRIE,
    ResourceType.SEARCH: CacheNamespace.SEARCH,
    ResourceType.DICTIONARY: CacheNamespace.DICTIONARY,
    ResourceType.LITERATURE: CacheNamespace.LITERATURE,
    ResourceType.LANGUAGE: CacheNamespace.LANGUAGE,
}

def validate_namespace(name: str) -> CacheNamespace:
    """Pure validation function."""
    if name not in NAMESPACE_MAP:
        raise ValueError(f"Unknown namespace: {name}")
    return NAMESPACE_MAP[name]
```

**Update usages**:
```python
# decorators.py - REMOVE lines 26-34, ADD:
from .config import NAMESPACE_MAP

# core.py - REMOVE lines 125-216 (_init_default_namespaces), ADD:
from .config import DEFAULT_CONFIGS

def __init__(self, ...):
    for namespace, config in DEFAULT_CONFIGS.items():
        self.namespaces[namespace] = NamespaceState(config, ...)

# manager.py - REMOVE lines 752-763 (_get_namespace), ADD:
from .config import RESOURCE_TYPE_MAP
# Replace all: self._get_namespace(type) → RESOURCE_TYPE_MAP[type]
```

**Test**: `pytest tests/caching/ -k namespace -v`

---

### 1.4 Fix Module-Level Imports (30 minutes)

```python
# core.py - Move nested imports to top
from .keys import generate_resource_key

# DELETE lines 532, 593 (nested imports)
# Use generate_resource_key directly
```

**Test**: `pytest tests/caching/ -v` (all must pass)

**Checkpoint**: `git commit -m "Phase 1: keys.py + config.py + deleted dead code"`

---

## Phase 2: Performance (6 hours)

### 2.1 SerializedContent Immutable (2 hours)

```python
# NEW: backend/src/floridify/caching/serialize.py
"""Pure serialization utilities - compute once, reuse."""

from dataclasses import dataclass
import hashlib
import json
from typing import Any

@dataclass(frozen=True)
class SerializedContent:
    """Immutable container - eliminates double serialization."""
    data: dict
    json_str: str
    size_bytes: int

    @classmethod
    def from_data(cls, data: dict, json_encoder=None) -> "SerializedContent":
        json_str = json.dumps(data, sort_keys=True, default=json_encoder)
        return cls(data, json_str, len(json_str.encode()))

def compute_content_hash(content: str) -> str:
    """Pure function - SHA256."""
    return hashlib.sha256(content.encode()).hexdigest()
```

**Update core.py** `set_versioned_content()`:
```python
from .serialize import SerializedContent, compute_content_hash

async def set_versioned_content(versioned_data, content, ...):
    # Compute ONCE!
    serialized = SerializedContent.from_data(content, _json_default)

    if serialized.size_bytes < 16384:
        versioned_data.content_inline = serialized.data
        versioned_data.content_location = None
    else:
        cache_key = generate_resource_key(...)
        await cache.set(namespace, cache_key, serialized.json_str)  # Reuse!
        versioned_data.content_location = ContentLocation(
            ...,
            checksum=compute_content_hash(serialized.json_str),
            size_bytes=serialized.size_bytes,
        )
```

**Test**: `pytest tests/caching/test_cache_performance.py -v`  
**Validate**: 40-50% faster for large saves

---

### 2.2 Per-Resource Locks (2 hours)

```python
# manager.py

def create_lock_key(resource_type: ResourceType, resource_id: str) -> str:
    """Pure function for lock key."""
    return f"{resource_type.value}:{resource_id}"

class VersionedDataManager:
    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}  # Per-resource!
        # DELETE: self._lock = asyncio.Lock()

    def _get_lock(self, resource_type, resource_id) -> asyncio.Lock:
        """Get or create lock for specific resource."""
        key = create_lock_key(resource_type, resource_id)
        return self._locks.setdefault(key, asyncio.Lock())

    async def save(self, resource_id, resource_type, ...):
        lock = self._get_lock(resource_type, resource_id)
        async with lock:  # Granular!
            ...
```

**Test**: `pytest tests/caching/test_mongodb_versioning.py::test_concurrent -v`  
**Validate**: 3-5x throughput for concurrent saves

---

### 2.3 OrderedDict LRU (1 hour)

```python
# core.py
from collections import OrderedDict

class GlobalCacheManager:
    def __init__(self, ...):
        for namespace, config in DEFAULT_CONFIGS.items():
            self.namespaces[namespace] = NamespaceState(
                config=config,
                memory_cache=OrderedDict(),  # Not dict!
                ...
            )

    def _evict_lru(self, ns: NamespaceConfig, count: int = 1) -> int:
        """O(1) eviction with OrderedDict."""
        evictions = 0
        for _ in range(min(count, len(ns.memory_cache))):
            ns.memory_cache.popitem(last=False)  # O(1)!
            ns.stats["evictions"] += 1
            evictions += 1
        return evictions
```

**Test**: `pytest tests/caching/test_comprehensive_caching.py -k eviction -v`

---

### 2.4 Cache Loop Reference (1 hour)

```python
# filesystem.py

class FilesystemBackend:
    def __init__(self, ...):
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        return self._loop

    async def get(self, key: str):
        loop = self._get_loop()  # Cached!
        return await loop.run_in_executor(None, lambda: self.cache.get(key))
```

**Test**: `pytest tests/caching/test_comprehensive_caching.py::TestFilesystemBackend -v`

**Checkpoint**: `git commit -m "Phase 2: performance optimizations (50-70% faster)"`

---

## Phase 3: Functional Refactoring (8 hours)

### 3.1 Extract Pure Functions (2 hours)

```python
# NEW: backend/src/floridify/caching/validation.py
"""Pure validation functions - testable without async/MongoDB."""

def validate_cached_type(cached: Any, expected: type) -> bool:
    """Pure type check."""
    return isinstance(cached, expected)

def check_content_integrity(content: str, expected_hash: str) -> bool:
    """Pure hash validation."""
    import hashlib
    actual = hashlib.sha256(content.encode()).hexdigest()
    return actual == expected_hash

def compute_storage_strategy(size_bytes: int) -> tuple[bool, str]:
    """Pure decision - inline vs external."""
    threshold = 16 * 1024
    use_inline = size_bytes < threshold
    reason = "inline" if use_inline else "external"
    return use_inline, reason

# NEW: backend/src/floridify/caching/version_chains.py
"""Version chain management - pure + minimal async."""

async def find_latest_version(collection, resource_id: str):
    """Pure query construction."""
    return await collection.find_one({
        "resource_id": resource_id,
        "version_info.is_latest": True
    })

async def update_version_chain(collection, resource_id: str, new_id) -> int:
    """Update old versions to not-latest."""
    result = await collection.update_many(
        {
            "resource_id": resource_id,
            "version_info.is_latest": True,
            "_id": {"$ne": new_id}
        },
        {"$set": {"version_info.is_latest": False}}
    )
    return result.modified_count
```

**Update manager.py** to use pure functions:
```python
from .validation import validate_cached_type, check_content_integrity
from .version_chains import find_latest_version, update_version_chain

class VersionedDataManager:
    async def save(self, ...):
        # Use pure functions!
        await update_version_chain(collection, resource_id, new_id)
```

**Test**: `pytest tests/caching/test_mongodb_versioning.py -v`

---

### 3.2 Immutable CacheStats (2 hours)

```python
# models.py or core.py
@dataclass(frozen=True)
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0

    def with_hit(self) -> "CacheStats":
        """Functional update - returns new stats."""
        return CacheStats(self.hits + 1, self.misses, self.evictions)

    def with_miss(self) -> "CacheStats":
        return CacheStats(self.hits, self.misses + 1, self.evictions)

    def with_eviction(self) -> "CacheStats":
        return CacheStats(self.hits, self.misses, self.evictions + 1)

# core.py
@dataclass
class NamespaceState:
    config: NamespaceCacheConfig
    memory_cache: OrderedDict
    lock: asyncio.Lock
    stats: CacheStats  # Immutable!

    def record_hit(self) -> None:
        self.stats = self.stats.with_hit()  # Functional update!
```

**Update all stats mutations**:
```python
# BEFORE: ns.stats["hits"] += 1
# AFTER:  ns.stats = ns.stats.with_hit()
```

**Test**: `pytest tests/caching/ -k stats -v`

---

### 3.3 Split manager.py (4 hours)

**Extract to version_chains.py** (already done in 3.1)

**Extract to serialize.py**:
```python
# Already created in Phase 2

def prepare_metadata_params(metadata: dict, model_class) -> tuple[dict, dict]:
    """Pure field separation."""
    from ..utils.introspection import extract_metadata_params
    from .models import BaseVersionedData
    
    typed_fields, generic = extract_metadata_params(metadata, model_class)
    base_fields = set(BaseVersionedData.model_fields.keys())
    filtered = {k: v for k, v in generic.items() if k not in base_fields}
    return typed_fields, filtered
```

**manager.py** becomes orchestrator (~300 lines):
```python
from .serialize import prepare_metadata_params, SerializedContent
from .validation import compute_storage_strategy
from .version_chains import update_version_chain, find_latest_version

class VersionedDataManager:
    async def save(self, ...):
        # Orchestration only - delegates to pure functions!
        serialized = SerializedContent.from_data(content)
        metadata_params = prepare_metadata_params(...)
        await update_version_chain(...)
```

**Test**: `pytest tests/caching/test_mongodb_versioning.py -v`  
**Validate**: manager.py < 400 lines

**Checkpoint**: `git commit -m "Phase 3: functional refactoring (pure functions extracted)"`

---

## Final Validation

```bash
# Run ALL tests
pytest tests/caching/ -v

# Run performance benchmarks
pytest tests/caching/test_cache_performance.py -v

# Lint
ruff check backend/src/floridify/caching/
mypy backend/src/floridify/caching/

# Metrics
wc -l backend/src/floridify/caching/*.py
# manager.py should be ~300 lines (was 798)

# Check for anti-patterns
rg "hasattr|getattr|setattr" backend/src/floridify/caching/
# Should return: 0 results

rg "from.*import.*#.*inside function" backend/src/floridify/caching/
# Should return: 0 results

# Check circular deps
python -m pydeps backend/src/floridify/caching/ --show-cycles
# Should show: NO CYCLES
```

---

## Success Criteria Checklist

- [ ] All 78+ caching tests passing
- [ ] Performance: L1 < 0.5ms, L2 < 10ms, saves 40-50% faster
- [ ] manager.py < 400 lines (target: 300)
- [ ] Zero nested imports
- [ ] Zero circular dependencies
- [ ] Zero hasattr/getattr/setattr
- [ ] Zero dead code
- [ ] Configuration in 1 file (config.py)
- [ ] Pure functions: ~40 (was ~10)
- [ ] Ruff + mypy pass

---

## Rollback Plan

**If any phase fails**:
```bash
git reset --hard <last-good-commit>
# Or individual file:
git checkout HEAD~1 -- backend/src/floridify/caching/manager.py
```

---

## Post-Refactor Maintenance

1. **Add pure function tests** - No mocking needed!
2. **Monitor performance** - Validate 50-70% improvement holds
3. **Document patterns** - Update CLAUDE.md with pure function approach
4. **Future features** - Always extract pure logic first

---

**Total Time**: 18 hours (3 days)  
**Risk**: LOW (test at every step)  
**Philosophy**: Pure functions + immutable data = simple, fast, testable
