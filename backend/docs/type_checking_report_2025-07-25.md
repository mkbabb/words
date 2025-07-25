# Type Checking Report - Floridify Backend
**Date**: 2025-07-25  
**Tools**: mypy v1.17.0 (strict mode), ruff v0.12.5  
**Target**: `/Users/mkbabb/Programming/words/backend/src/floridify`

## Executive Summary

Type checking revealed **106 mypy errors** and numerous code quality issues across the backend codebase. The errors include missing imports, type annotation issues, and architectural problems with the cache system. While the system can still import and run, these type safety issues pose risks for maintainability and runtime reliability.

### Type Safety Score: ~50% (Critical errors in 25+ files)

## Critical Issues Requiring Immediate Attention

### 1. Cache Manager Type Incompatibility (CRITICAL)
**Files Affected**: `api/core/cache.py`
**Issue**: Fundamental type mismatch - cache manager expects `tuple[Any, ...]` but receives `str`
```python
# Line 75
cached_data = await cache_manager.get(cache_key)  # ERROR: str passed, tuple expected
# Line 119-120
await cache_manager.set(cache_key, {...})  # ERROR: str passed, tuple expected
```
**Impact**: Cache system is broken at the type level
**Resolution**: Update CacheManager to accept string keys or modify all callers

### 2. Missing numpy Module (HIGH)
**File**: `search/semantic.py`
**Issue**: numpy import fails despite being required for semantic search
```python
import numpy as np  # ERROR: Cannot find implementation
```
**Impact**: Semantic search functionality broken
**Resolution**: Either install numpy or disable semantic search features

### 3. Repository Base Class Type Safety (HIGH)
**File**: `api/core/base.py`
**Issues**: Multiple type violations in CRUD operations
- Lines 184-210: Optional[T] not properly handled (accessing attributes on None)
- Line 213: Method `get_many` redefined (already defined on line 134)
- Line 265: DeleteResult might be None
**Impact**: Database operations may fail with AttributeError at runtime

### 4. Model Import Path Issues (HIGH)
**Problem**: Incorrect import paths throughout codebase
```python
# Current (incorrect)
from ...models.models import Language, Word  # Module doesn't export these

# Should be
from floridify.models import Language, Word
```
**Files affected**: 
- `api/repositories/word_repository.py`
- `api/repositories/synthesis_repository.py`
- `api/repositories/fact_repository.py`
- `api/repositories/example_repository.py`

### 5. Missing Type Annotations (MEDIUM)
Systematic issues with missing annotations:
- **Monitoring module**: 11 functions missing return types (`-> None`)
- **Cache decorators**: Missing generic type parameters for Callable
- **Rate limiting**: Missing type annotations for middleware

## Detailed Error Analysis by Module

### Cache System (`api/core/cache.py`) - 10 errors
```python
# Type incompatibilities:
- Line 75: await cache_manager.get(cache_key) - str vs tuple[Any, ...]
- Line 119: await cache_manager.set(...) - multiple type errors
- Line 149: CacheInvalidator.invalidate_pattern - same issues
- Line 223-237: ResponseCache context manager - type mismatches
```

### Repository Pattern (`api/repositories/`) - 45+ errors
```python
# Common pattern causing errors:
query["field"] = {"$ne": None}  # dict assigned to str type
query["field"] = RegEx(pattern, "i")  # RegEx assigned to str type

# Files affected:
- word_repository.py: 12 errors
- synthesis_repository.py: 18 errors  
- fact_repository.py: 8 errors
- example_repository.py: 7 errors
```

### AI Module (`ai/`) - 50+ warnings
```python
# Systematic issues:
- G004: f-strings in logging (performance issue)
- TRY400: Use logging.exception instead of logging.error
- Missing type parameters for Callable
- Magic numbers without constants (e.g., line 245: if len(x) > 50)
```

### Text Processing (`text/`) - 10 errors
```python
# NLTK type stub issues:
import nltk  # type: ignore[import-not-found] - wrong error code
# Should be: # type: ignore[import-untyped]

# Same for contractions, coolname libraries
```

## Recommended Resolution Order

### Phase 1: Critical Cache System Fix (2-3 hours)
```python
# Option 1: Update CacheManager to accept string keys
class CacheManager:
    async def get(self, key: str | tuple[Any, ...]) -> Any:
        ...
    
    async def set(self, key: str | tuple[Any, ...], value: Any, ttl: int) -> None:
        ...

# Option 2: Convert all cache keys to tuples
cache_key = (request.url.path, str(request.query_params))
```

### Phase 2: Fix Import Issues (1-2 hours)
```python
# 1. Fix model imports throughout
# Replace: from ...models.models import X
# With: from floridify.models import X

# 2. Fix NLTK type ignores
# Replace: # type: ignore[import-not-found]
# With: # type: ignore[import-untyped]

# 3. Install numpy or remove semantic search
uv pip install numpy
# OR remove src/floridify/search/semantic.py
```

### Phase 3: Repository Type Safety (3-4 hours)
```python
# Fix Optional handling in BaseRepository
async def update(self, id: str, data: dict, version: int | None = None) -> T:
    doc = await self.get_by_id(id)
    if doc is None:
        raise ValueError(f"Document {id} not found")
    # Now doc is guaranteed to be T, not Optional[T]
    
# Fix query type issues
query: dict[str, Any] = {}  # Not dict[str, str]
```

### Phase 4: Add Missing Annotations (4-6 hours)
```python
# Add return types
def record_request(self, endpoint: str, duration: float) -> None:
    ...

# Fix generic types
def decorator(func: Callable[..., T]) -> Callable[..., T]:
    ...
```

## Type Checking Configuration Updates

### Update pyproject.toml:
```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
no_implicit_reexport = true
plugins = ["pydantic.mypy"]

# Third-party without stubs
[[tool.mypy.overrides]]
module = ["nltk.*", "contractions.*", "coolname.*", "genanki.*"]
ignore_missing_imports = true

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "ANN", "TCH", "TYP"]
ignore = ["E203", "E501", "ANN101", "ANN102"]
```

### Add Pre-commit Hooks:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy
        language: system
        types: [python]
        args: ["--config-file", "pyproject.toml"]
```

## Summary and Next Steps

The codebase has **106 mypy errors** primarily concentrated in:
1. **Cache system architecture** - fundamental type incompatibility
2. **Repository query building** - dict[str, Any] vs dict[str, str] confusion
3. **Missing type annotations** - especially return types
4. **Import issues** - wrong type ignore codes, missing numpy

**Critical Path (Week 1)**:
1. Fix cache manager types (2-3 hours)
2. Install numpy or remove semantic search (30 min)
3. Fix model import paths (1 hour)
4. Add missing return annotations (2 hours)

**Improvement Path (Week 2)**:
1. Fix all repository query types
2. Update logging to remove f-strings
3. Add pre-commit hooks
4. Achieve 100% type coverage

**Commands for Continuous Monitoring**:
```bash
# Run type checks
uv run mypy src/floridify --show-error-codes --pretty
uv run ruff check src/floridify --select ANN,TCH,UP,TYP

# Watch mode during development
uv run watchmedo shell-command \
    --patterns="*.py" \
    --recursive \
    --command='clear && mypy src/floridify' \
    src/
```