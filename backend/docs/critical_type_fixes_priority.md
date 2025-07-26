# Critical Type Fixes - Priority Action Items

## 🚨 Top 5 Critical Issues (Fix First)

### 1. Unreachable Code - Immediate Fix Required
**Files**: 9 locations across caching, search, and text processing  
**Example**:
```python
# src/floridify/utils/sanitization.py:23
if condition:
    return value
    return str(value)  # UNREACHABLE!
```
**Fix**: Remove unreachable lines or restructure logic

### 2. Async Type Decorator Mismatch
**File**: `src/floridify/caching/request_deduplicator.py`  
**Issue**: Decorator expects async function but receives sync
```python
# Line 143: Wrong type
def deduplicate(key: str, func: Callable[..., T]) -> T:
    # But func is actually async!

# Fix:
def deduplicate(key: str, func: Callable[..., Awaitable[T]]) -> Awaitable[T]:
```

### 3. Literal Type Violations in Models
**Files**: Multiple API routers  
**Pattern**:
```python
# Problem: String passed where Literal expected
category: Literal['etymology', 'usage', 'cultural', 'linguistic', 'historical']
category=fact_data.get("category")  # Returns str | None!

# Fix: Validate and cast
from typing import get_args
VALID_CATEGORIES = get_args(Literal['etymology', 'usage', 'cultural', 'linguistic', 'historical'])
category = fact_data.get("category")
if category not in VALID_CATEGORIES:
    category = 'linguistic'  # default
```

### 4. Missing Return Annotations
**Count**: 14 functions  
**Quick Fix**:
```python
# Add to all functions:
def function_name() -> None:  # For procedures
def get_value() -> str:       # For functions returning values
async def fetch() -> dict[str, Any]:  # For async functions
```

### 5. Repository Type Incompatibility
**File**: `src/floridify/api/routers/definitions.py:461`
```python
# Problem: Type variance issue
definition_ids: list[PydanticObjectId]
await repo.get_many(definition_ids)  # Expects list[PydanticObjectId | str]

# Fix: Use Sequence (covariant)
from typing import Sequence
async def get_many(self, ids: Sequence[PydanticObjectId | str]) -> list[T]:
```

## 🔧 Quick Win Fixes (< 1 hour)

1. **Run auto-fixes**:
   ```bash
   uv run ruff check src/floridify --fix --select F,I,UP
   uv run ruff format src/floridify
   ```

2. **Add missing `-> None` to all `__init__` methods**:
   ```bash
   # Find all __init__ without annotations
   grep -r "def __init__(self" src/floridify | grep -v "-> None"
   ```

3. **Fix import order**:
   ```bash
   uv run ruff check src/floridify --select I --fix
   ```

## 📋 Systematic Fix Checklist

- [ ] Remove all unreachable code (9 instances)
- [ ] Fix async decorator types (2 files)
- [ ] Add Enum classes for all Literal types
- [ ] Add return type annotations (14 functions)
- [ ] Fix repository method signatures
- [ ] Replace blocking I/O with aiofiles (17 instances)
- [ ] Update model constructors with proper types
- [ ] Fix function redefinitions in routers
- [ ] Add type guards for runtime validation
- [ ] Configure stricter mypy settings

## 🚀 One-Line Fixes

```bash
# Remove trailing whitespace
uv run ruff check src/floridify --select W291,W292,W293 --fix

# Add trailing commas
uv run ruff check src/floridify --select COM812 --fix

# Fix string quotes
uv run ruff check src/floridify --select Q --fix

# Remove unused imports
uv run ruff check src/floridify --select F401 --fix
```

## 📊 Impact Assessment

**High Impact** (affects runtime):
- Async type mismatches
- Unreachable code
- Missing error handling

**Medium Impact** (affects maintainability):
- Missing annotations
- Type incompatibilities
- Import issues

**Low Impact** (code style):
- Whitespace issues
- Quote consistency
- Import ordering